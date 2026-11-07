import os
import re
import queue
import subprocess
import time
import tempfile
import threading
import platform
import shutil

class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self.counter = 1
        self.log_dir = os.path.join(tempfile.gettempdir(), "zaishell_bg_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.event_queue = queue.Queue()
        self.lock = threading.Lock()

    def _emit_log_event(self, task_id, matched_line):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            p = task["popen"]
            rc = p.poll()
            cmd_list = task["command"]
            regex_str = task.get("watch_log_regex") or ""
            pid = task["pid"]
        logs = self.get_logs(task_id, max_lines=50)
        self.event_queue.put({
            "type": "watch_log_trigger",
            "task_id": task_id,
            "pid": pid,
            "command": cmd_list,
            "matched_line": matched_line,
            "watch_log_regex": regex_str,
            "rc": rc,
            "logs": logs,
            "timestamp": time.time()
        })

    def _emit_crash_event(self, task_id, rc):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            cmd_list = task["command"]
            pid = task["pid"]
        logs = self.get_logs(task_id, max_lines=50)
        self.event_queue.put({
            "type": "crash_trigger",
            "task_id": task_id,
            "pid": pid,
            "command": cmd_list,
            "rc": rc,
            "logs": logs,
            "timestamp": time.time()
        })

    def _log_monitor(self, task_id, log_path, encoding):
        pos = 0
        while True:
            with self.lock:
                task = self.tasks.get(task_id)
            if not task:
                break
            p = task["popen"]
            rc = p.poll()
            try:
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding=encoding, errors="replace") as f:
                        f.seek(pos)
                        new_lines = f.readlines()
                        pos = f.tell()
                    for line in new_lines:
                        with self.lock:
                            if task.get("compiled_regex") and not task.get("regex_triggered"):
                                if task["compiled_regex"].search(line):
                                    task["regex_triggered"] = True
                                    timer = threading.Timer(0.3, self._emit_log_event, args=(task_id, line.strip()))
                                    timer.daemon = True
                                    timer.start()
            except Exception:
                pass

            if rc is not None:
                with self.lock:
                    if not task["status"].startswith("stopped"):
                        task["status"] = "completed (code: 0)" if rc == 0 else f"terminated (code: {rc})"
                    should_crash_heal = (
                        rc != 0
                        and not task.get("stopped_manually", False)
                        and (task.get("on_crash") == "auto_heal" or task.get("compiled_regex") is not None)
                        and not task.get("crash_triggered", False)
                    )
                    if should_crash_heal:
                        task["crash_triggered"] = True
                if should_crash_heal:
                    self._emit_crash_event(task_id, rc)
                break
            time.sleep(0.25)

    def start_task(self, cmd_list, terminal="cmd", encoding="utf-8", on_crash=None, watch_log_regex=None, cwd=None, env_overrides=None):
        with self.lock:
            task_id = f"bg_{self.counter}"
            self.counter += 1
        log_path = os.path.join(self.log_dir, f"{task_id}.log")
        with open(log_path, "w", encoding=encoding, errors="replace") as f:
            pass

        compiled_regex = None
        if watch_log_regex:
            try:
                compiled_regex = re.compile(watch_log_regex, re.IGNORECASE)
            except re.error:
                compiled_regex = re.compile(re.escape(watch_log_regex), re.IGNORECASE)

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            if env_overrides and isinstance(env_overrides, dict):
                for k, v in env_overrides.items():
                    env[str(k)] = str(v)

            cmd_to_exec = cmd_list
            if isinstance(cmd_list, str):
                raw_str = cmd_list.strip()
                term_lower = str(terminal).lower()
                if any(x in term_lower for x in ["powershell", "pwsh"]):
                    pwsh_bin = "pwsh" if shutil.which("pwsh") else "powershell"
                    cmd_to_exec = [pwsh_bin, "-NoProfile", "-Command", raw_str]
                elif term_lower in ["cmd", "cmd.exe"]:
                    cmd_to_exec = ["cmd", "/c", raw_str]
                elif term_lower in ["bash", "sh", "zsh", "wsl"]:
                    sh_bin = "wsl" if term_lower == "wsl" else (term_lower if shutil.which(term_lower) else "bash")
                    cmd_to_exec = [sh_bin, "-c", raw_str]
                else:
                    cmd_to_exec = ["cmd", "/c", raw_str] if platform.system() == "Windows" else ["bash", "-c", raw_str]
            elif isinstance(cmd_list, list):
                if not cmd_list:
                    return {"success": False, "message": "Empty command list provided."}
                first = os.path.basename(str(cmd_list[0])).lower().replace(".exe", "")
                has_shell = any(str(tok) in [">", ">>", "<", "<<", "|", "&&", ";", "||"] for tok in cmd_list)
                if first not in ["powershell", "pwsh", "cmd", "bash", "sh", "zsh", "wsl"] and (not shutil.which(str(cmd_list[0])) or has_shell):
                    raw_str = " ".join([f'"{x}"' if (" " in str(x) and not str(x).startswith('"')) else str(x) for x in cmd_list])
                    term_lower = str(terminal).lower()
                    if any(x in term_lower for x in ["powershell", "pwsh"]):
                        pwsh_bin = "pwsh" if shutil.which("pwsh") else "powershell"
                        cmd_to_exec = [pwsh_bin, "-NoProfile", "-Command", raw_str]
                    elif term_lower in ["cmd", "cmd.exe"]:
                        cmd_to_exec = ["cmd", "/c", raw_str]
                    elif term_lower in ["bash", "sh", "zsh", "wsl"]:
                        sh_bin = "wsl" if term_lower == "wsl" else (term_lower if shutil.which(term_lower) else "bash")
                        cmd_to_exec = [sh_bin, "-c", raw_str]
                    else:
                        cmd_to_exec = ["cmd", "/c", raw_str] if platform.system() == "Windows" else ["bash", "-c", raw_str]

            log_fh = open(log_path, "ab", buffering=0)
            popen_kwargs = {
                "shell": False,
                "stdout": log_fh,
                "stderr": subprocess.STDOUT,
                "stdin": subprocess.PIPE,
                "text": True,
                "encoding": encoding,
                "errors": "replace",
                "cwd": cwd,
                "env": env,
            }
            if platform.system() != "Windows":
                popen_kwargs["start_new_session"] = True
                popen_kwargs["close_fds"] = True

            try:
                p = subprocess.Popen(cmd_to_exec, **popen_kwargs)
            finally:
                try:
                    log_fh.close()
                except Exception:
                    pass

            with self.lock:
                self.tasks[task_id] = {
                    "task_id": task_id,
                    "pid": p.pid,
                    "command": cmd_list,
                    "terminal": terminal,
                    "encoding": encoding,
                    "start_time": time.time(),
                    "popen": p,
                    "log_path": log_path,
                    "writer_thread": None,
                    "status": "running",
                    "on_crash": on_crash,
                    "watch_log_regex": watch_log_regex,
                    "compiled_regex": compiled_regex,
                    "regex_triggered": False,
                    "crash_triggered": False,
                    "stopped_manually": False
                }

            monitor_thread = threading.Thread(
                target=self._log_monitor,
                args=(task_id, log_path, encoding),
                daemon=True
            )
            monitor_thread.start()

            with self.lock:
                self.tasks[task_id]["writer_thread"] = monitor_thread

            return {"success": True, "task_id": task_id, "pid": p.pid, "message": f"Background task started. Task ID: {task_id}, PID: {p.pid}"}
        except Exception as e:
            return {"success": False, "task_id": task_id, "message": f"Could not start background task: {str(e)}"}

    def _resolve_task_id(self, task_id_or_pid):
        target = str(task_id_or_pid).strip()
        with self.lock:
            if target in self.tasks:
                return target
            for tid, data in self.tasks.items():
                if str(data["pid"]) == target:
                    return tid
        return None

    def send_input(self, task_id_or_pid, input_data, wait_seconds=0.4):
        self.update_task_statuses()
        target_tid = self._resolve_task_id(task_id_or_pid)
        if not target_tid:
            return f"Error: No background task found with ID '{task_id_or_pid}'."
        with self.lock:
            data = self.tasks[target_tid]
            p = data["popen"]
        if p.poll() is not None:
            return f"Error: Task {target_tid} is not running (Status: {data['status']})."
        if p.stdin is None:
            return f"Error: Task {target_tid} does not support stdin channel."
        try:
            p.stdin.write(str(input_data))
            p.stdin.flush()
            with self.lock:
                data["regex_triggered"] = False
            if wait_seconds and float(wait_seconds) > 0:
                time.sleep(float(wait_seconds))
            recent_logs = self.get_logs(target_tid, max_lines=20)
            return f"Input sent to stdin of task {target_tid} (PID: {data['pid']}).\nRecent Logs:\n{recent_logs}"
        except Exception as e:
            return f"Task {target_tid} stdin write error: {str(e)}"

    def wait_for_log(self, task_id_or_pid, contains=None, regex=None, timeout=15.0, interval=0.5):
        target_tid = self._resolve_task_id(task_id_or_pid)
        if not target_tid:
            return False, "", f"Error: No task found with ID '{task_id_or_pid}'."
        compiled = None
        if regex:
            try:
                compiled = re.compile(regex, re.MULTILINE | re.IGNORECASE)
            except re.error as e:
                return False, "", f"Poll regex error: {str(e)}"
        deadline = time.time() + float(timeout)
        interval_val = max(0.05, float(interval))
        while time.time() < deadline:
            log_content = self.get_logs(target_tid, max_lines=500)
            if log_content and log_content != "(No output yet)":
                if contains and contains.lower() in log_content.lower():
                    return True, log_content, f"Expected text ('{contains}') captured."
                if compiled and compiled.search(log_content):
                    return True, log_content, f"Expected regex ('{regex}') captured."
            with self.lock:
                p = self.tasks[target_tid]["popen"]
            if p.poll() is not None:
                final_logs = self.get_logs(target_tid, max_lines=500)
                if contains and contains.lower() in final_logs.lower():
                    return True, final_logs, f"Expected text ('{contains}') captured."
                if compiled and compiled.search(final_logs):
                    return True, final_logs, f"Expected regex ('{regex}') captured."
                return False, final_logs, f"Background process terminated before condition was met (Exit Code: {p.returncode})."
            time.sleep(min(interval_val, max(0.05, deadline - time.time())))
        final_logs = self.get_logs(target_tid, max_lines=100)
        with self.lock:
            p = self.tasks[target_tid]["popen"]
        if p.poll() is None:
            return True, final_logs, f"PROCESS ACTIVE (PID: {p.pid} running). Specific log pattern not observed within poll duration ({timeout}s), but server/process is healthy and up."
        return False, final_logs, f"Poll duration ({timeout}s) expired and process terminated (Exit Code: {p.returncode})."

    def pop_event(self):
        try:
            return self.event_queue.get_nowait()
        except queue.Empty:
            return None

    def update_task_statuses(self):
        with self.lock:
            for tid, data in list(self.tasks.items()):
                p = data["popen"]
                rc = p.poll()
                if rc is not None and not data["status"].startswith("stopped"):
                    data["status"] = "completed (code: 0)" if rc == 0 else f"terminated (code: {rc})"

    def list_tasks(self):
        self.update_task_statuses()
        with self.lock:
            if not self.tasks:
                return "No active or registered background tasks found."
            lines = []
            for tid, data in self.tasks.items():
                uptime = round(time.time() - data["start_time"], 1)
                raw_cmd = data["command"]
                cmd_str = " ".join([f'"{x}"' if ' ' in str(x) else str(x) for x in raw_cmd]) if isinstance(raw_cmd, list) else str(raw_cmd)
                watch_info = f" | Watch: {data['watch_log_regex']}" if data.get("watch_log_regex") else ""
                crash_info = f" | OnCrash: {data['on_crash']}" if data.get("on_crash") else ""
                lines.append(f"[{tid}] PID: {data['pid']} | Status: {data['status']} | Duration: {uptime}s{crash_info}{watch_info} | Command: {cmd_str}")
            return "\n".join(lines)

    def stop_task(self, task_id_or_pid):
        self.update_task_statuses()
        target_tid = self._resolve_task_id(task_id_or_pid)
        if not target_tid:
            return f"Error: No background task found with ID '{task_id_or_pid}'."
        with self.lock:
            data = self.tasks[target_tid]
            data["stopped_manually"] = True
            p = data["popen"]
        if p.poll() is None:
            try:
                if p.stdin:
                    try:
                        p.stdin.close()
                    except Exception:
                        pass
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                with self.lock:
                    data["status"] = "stopped"
                wt = data.get("writer_thread")
                if wt:
                    wt.join(timeout=1)
                return f"Task {target_tid} (PID: {data['pid']}) stopped successfully."
            except Exception as e:
                return f"Error occurred while stopping task: {str(e)}"
        else:
            return f"Task {target_tid} is already not running (Status: {data['status']})."

    def get_logs(self, task_id_or_pid, max_lines=50):
        target_tid = self._resolve_task_id(task_id_or_pid)
        if not target_tid:
            return f"Error: No logs found for '{task_id_or_pid}'."
        with self.lock:
            log_path = self.tasks[target_tid]["log_path"]
            enc = self.tasks[target_tid].get("encoding", "utf-8")
        if not os.path.exists(log_path):
            return "Log file not found."
        try:
            with open(log_path, "r", encoding=enc, errors="replace") as f:
                all_lines = f.readlines()
                if not all_lines:
                    return "(No output yet)"
                return "".join(all_lines[-int(max_lines):])
        except Exception as e:
            return f"Error reading log: {str(e)}"

bg_manager = BackgroundManager()

class VirtualBufferManager:
    def __init__(self):
        self.buffers = {}
        self.counter = 1
        self.lock = threading.Lock()

    def store_and_truncate(self, text, step_id=None):
        if not text:
            return ""
        lines = text.splitlines()
        n = len(lines)
        with self.lock:
            buf_id = f"buf_{self.counter}"
            self.counter += 1
            self.buffers[buf_id] = {
                "id": buf_id,
                "step_id": str(step_id) if step_id else buf_id,
                "lines": lines,
                "total_lines": n,
                "created_at": time.time()
            }
        if n <= 400 and len(text) <= 24000:
            return text
        if n <= 400 and len(text) > 24000:
            notice = f"\n... [Output too long ({len(text)} characters). Full output in '{buf_id}'. You can read it with buffer_action] ...\n"
            return text[:10000] + notice + text[-10000:]
        head_n = 150
        tail_n = 200
        if head_n + tail_n >= n:
            return text
        skipped = n - (head_n + tail_n)
        notice = f"\n... [{skipped} lines hidden (Total {n} lines). Full output in '{buf_id}'. Use buffer_action to read or filter] ...\n"
        return "\n".join(lines[:head_n] + [notice] + lines[-tail_n:])

    def handle_action(self, action_dict):
        if not isinstance(action_dict, dict):
            return 1, "", "Invalid buffer_action format."
        act_type = str(action_dict.get("action", "")).lower()
        if act_type == "list":
            with self.lock:
                if not self.buffers:
                    return 0, "No active buffers found.", ""
                summary = [f"[{bid}] (Step: {b['step_id']}) Total Lines: {b['total_lines']}" for bid, b in self.buffers.items()]
                return 0, "\n".join(summary), ""

        raw_id = action_dict.get("id") or action_dict.get("buffer_id") or action_dict.get("target")
        with self.lock:
            buf_id = str(raw_id).strip() if raw_id else (list(self.buffers.keys())[-1] if self.buffers else None)
            if not buf_id or buf_id not in self.buffers:
                return 1, "", f"Error: Buffer '{raw_id}' not found. Available buffers: {list(self.buffers.keys())}"
            bdata = self.buffers[buf_id]
            lines = bdata["lines"]
            total = bdata["total_lines"]

        grep_pattern = action_dict.get("grep") or action_dict.get("search") or action_dict.get("pattern")
        if grep_pattern is not None:
            ctx = int(action_dict.get("context_lines", 3))
            flags = re.IGNORECASE if action_dict.get("ignore_case", True) else 0
            try:
                regex = re.compile(str(grep_pattern), flags)
            except re.error:
                regex = re.compile(re.escape(str(grep_pattern)), flags)

            matched_indices = [idx for idx, line in enumerate(lines) if regex.search(line)]
            if not matched_indices:
                return 0, f"[{buf_id}] No lines matching '{grep_pattern}' found (Total {total} lines).", ""

            ranges = []
            for idx in matched_indices:
                start_i = max(0, idx - ctx)
                end_i = min(total - 1, idx + ctx)
                if ranges and start_i <= ranges[-1][1] + 1:
                    ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end_i))
                else:
                    ranges.append((start_i, end_i))

            out_blocks = [f"[{buf_id}] '{grep_pattern}' Search Results ({len(matched_indices)} matches, Total {total} lines):"]
            match_set = set(matched_indices)
            for r_start, r_end in ranges:
                block_lines = [f"{'>> ' if i in match_set else '   '}{i + 1}: {lines[i]}" for i in range(r_start, r_end + 1)]
                out_blocks.append("\n".join(block_lines))
                out_blocks.append("---")
            return 0, "\n".join(out_blocks), ""

        lines_range = action_dict.get("lines")
        start_line = action_dict.get("start_line")
        end_line = action_dict.get("end_line")
        if lines_range and isinstance(lines_range, str) and "-" in lines_range:
            parts = lines_range.split("-", 1)
            try:
                start_line = int(parts[0].strip())
                end_line = int(parts[1].strip())
            except ValueError:
                return 1, "", f"Invalid line range: {lines_range}"
        elif lines_range and str(lines_range).isdigit():
            start_line = int(lines_range)
            end_line = start_line + 50

        if start_line is not None or end_line is not None:
            s_idx = max(1, int(start_line or 1))
            e_idx = min(total, int(end_line or (s_idx + 50)))
            if s_idx > total:
                return 0, f"[{buf_id}] Requested start line ({s_idx}) is greater than total line count ({total}).", ""
            sliced = [f"{i}: {lines[i - 1]}" for i in range(s_idx, e_idx + 1)]
            return 0, f"[{buf_id}] Lines {s_idx}-{e_idx} / {total}:\n" + "\n".join(sliced), ""

        if "head" in action_dict:
            count = min(total, max(1, int(action_dict["head"])))
            sliced = [f"{i + 1}: {lines[i]}" for i in range(count)]
            return 0, f"[{buf_id}] First {count} lines:\n" + "\n".join(sliced), ""

        if "tail" in action_dict:
            count = min(total, max(1, int(action_dict["tail"])))
            start_i = max(0, total - count)
            sliced = [f"{i + 1}: {lines[i]}" for i in range(start_i, total)]
            return 0, f"[{buf_id}] Last {count} lines:\n" + "\n".join(sliced), ""

        preview_end = min(total, 100)
        sliced = [f"{i + 1}: {lines[i]}" for i in range(preview_end)]
        return 0, f"[{buf_id}] Lines 1-{preview_end} / {total}:\n" + "\n".join(sliced), ""

buffer_manager = VirtualBufferManager()