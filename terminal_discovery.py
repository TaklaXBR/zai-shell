import os
import platform
import queue
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

def discover_terminals():
    terminals = set()
    comspec = os.environ.get('COMSPEC')
    if comspec:
        terminals.add(os.path.basename(comspec).lower().replace('.exe', ''))
    shell_patterns = {
        'powershell', 'pwsh', 'bash', 'wsl', 'sh', 'zsh', 'git-bash',
        'nu', 'xonsh', 'fish', 'csh', 'tcsh', 'ksh', 'ash', 'dash',
        'cygwin', 'mintty', 'msys2'
    }
    path_env = os.environ.get('PATH', '')
    for path_dir in path_env.split(os.pathsep):
        if os.path.isdir(path_dir):
            try:
                for file_name in os.listdir(path_dir):
                    base_name = file_name.lower().replace('.exe', '')
                    if base_name in shell_patterns:
                        terminals.add(base_name)
            except (PermissionError, FileNotFoundError):
                continue
    common_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\git-bash.exe",
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\msys64\msys2_shell.cmd"
    ]
    for cp in common_paths:
        if os.path.exists(cp):
            base_name = os.path.basename(cp).lower().replace('.exe', '').replace('.cmd', '')
            terminals.add("git-bash" if base_name == "bash" else base_name)
    return list(terminals) if terminals else ["cmd"]

class PersistentShellSession:
    def __init__(self, session_id, terminal="powershell", encoding="utf-8"):
        self.session_id = session_id
        self.terminal = (terminal or ("powershell" if platform.system() == "Windows" else "bash")).lower()
        self.encoding = encoding
        self.shell_family = self._detect_family(self.terminal)
        self.proc = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.lock = threading.Lock()
        self._start_process()

    def _detect_family(self, term):
        t = term.lower()
        if any(x in t for x in ["powershell", "pwsh"]):
            return "powershell"
        if t in ["cmd", "cmd.exe", "command"]:
            return "cmd"
        return "posix"

    def _resolve_executable(self):
        t = self.terminal
        if self.shell_family == "powershell":
            if "pwsh" in t and shutil.which("pwsh"):
                return ["pwsh", "-NoLogo", "-NoExit", "-Command", "-"]
            return ["powershell", "-NoLogo", "-NoExit", "-Command", "-"]
        if self.shell_family == "cmd":
            return ["cmd.exe", "/Q", "/K", "prompt $S"]
        if t == "git-bash":
            git_bash = r"C:\Program Files\Git\bin\bash.exe"
            if os.path.exists(git_bash):
                return [git_bash, "--norc", "--noprofile"]
        if t == "wsl":
            return ["wsl"]
        exe = shutil.which(t) or shutil.which("bash") or shutil.which("sh") or t
        if "bash" in os.path.basename(exe).lower():
            return [exe, "--norc", "--noprofile"]
        return [exe]

    def _reader_loop(self, stream, q):
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                q.put(line)
        except Exception:
            pass

    def _start_process(self):
        launch_cmd = self._resolve_executable()
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self.proc = subprocess.Popen(
            launch_cmd,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=self.encoding,
            errors="replace",
            bufsize=1,
            env=env
        )
        threading.Thread(target=self._reader_loop, args=(self.proc.stdout, self.stdout_queue), daemon=True).start()
        threading.Thread(target=self._reader_loop, args=(self.proc.stderr, self.stderr_queue), daemon=True).start()

    def is_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _drain_queues(self):
        while not self.stdout_queue.empty():
            try:
                self.stdout_queue.get_nowait()
            except queue.Empty:
                break
        while not self.stderr_queue.empty():
            try:
                self.stderr_queue.get_nowait()
            except queue.Empty:
                break

    def unwrap_command(self, cmd):
        if isinstance(cmd, str):
            raw = cmd.strip()
            low = raw.lower()
            for pfx in ["bash -c ", "sh -c ", "zsh -c ", "powershell -command ", "pwsh -command ", "powershell -c ", "pwsh -c ", "cmd /c "]:
                if low.startswith(pfx):
                    inner = raw[len(pfx):].strip()
                    if (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
                        return inner[1:-1]
                    return inner
            return raw
        elif isinstance(cmd, list):
            items = [str(x) for x in cmd]
            if not items:
                return ""
            first = os.path.basename(items[0]).lower().replace(".exe", "")
            if first in ["powershell", "pwsh"]:
                for idx, arg in enumerate(items):
                    if arg.lower() in ["-command", "-c"] and idx + 1 < len(items):
                        return " ".join(items[idx + 1:])
                return " ".join(items[1:]) if len(items) > 1 else items[0]
            elif first == "cmd":
                for idx, arg in enumerate(items):
                    if arg.lower() in ["/c", "/k"] and idx + 1 < len(items):
                        return " ".join(items[idx + 1:])
                return " ".join(items[1:]) if len(items) > 1 else items[0]
            elif first in ["bash", "sh", "zsh", "wsl", "git-bash"]:
                for idx, arg in enumerate(items):
                    if arg in ["-c", "-e", "--"] and idx + 1 < len(items):
                        return " ".join(items[idx + 1:])
                return " ".join(items[1:]) if len(items) > 1 else items[0]
            if self.shell_family == "posix":
                return " ".join(shlex.quote(x) for x in items)
            return " ".join([f'"{x}"' if (" " in str(x) and not str(x).startswith('"')) else str(x) for x in items])
        return str(cmd)

    def execute(self, cmd, timeout=None):
        with self.lock:
            if not self.is_alive():
                self._start_process()
            self._drain_queues()
            inner_cmd = self.unwrap_command(cmd).strip()
            if not inner_cmd:
                return 0, "", ""
            uid = uuid.uuid4().hex
            marker = f"__ZAI_SYNC_{uid}__"
            err_marker = f"{marker}_ERR"
            tmp_script_path = None

            if self.shell_family == "powershell":
                payload = (
                    f"$global:LASTEXITCODE = 0\n"
                    f"{inner_cmd}\n"
                    f"$__zai_ok = $?\n"
                    f"$__zai_ec = if ($global:LASTEXITCODE -ne $null -and $global:LASTEXITCODE -ne 0) {{ $global:LASTEXITCODE }} elseif ($__zai_ok) {{ 0 }} else {{ 1 }}\n"
                    f"[Console]::Out.WriteLine(\"{marker}:$__zai_ec\")\n"
                    f"[Console]::Error.WriteLine(\"{err_marker}\")\n"
                )
            elif self.shell_family == "cmd":
                cmd_line = inner_cmd
                low_cmd = cmd_line.lower()
                if (low_cmd.endswith(".bat") or low_cmd.endswith(".cmd") or "scripts\\activate" in low_cmd) and not low_cmd.startswith("call "):
                    cmd_line = f"call {cmd_line}"
                payload = f"{cmd_line}\r\necho {marker}:%ERRORLEVEL%\r\necho {err_marker} 1>&2\r\n"
            else:
                if platform.system() != "Windows":
                    try:
                        tmp_dir = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
                        tmp_script_path = os.path.join(tmp_dir, f"__zai_sess_{uid}.sh")
                        with open(tmp_script_path, "w", encoding=self.encoding, errors="replace", newline="\n") as sf:
                            sf.write(inner_cmd + "\n")
                        quoted_script = shlex.quote(tmp_script_path)
                        payload = (
                            f"set +e\n"
                            f". {quoted_script} </dev/null\n"
                            f"__zai_ec=$?\n"
                            f"set +e\n"
                            f"rm -f {quoted_script} >/dev/null 2>&1\n"
                            f"echo \"{marker}:$__zai_ec\"\n"
                            f"echo \"{err_marker}\" >&2\n"
                        )
                    except Exception:
                        tmp_script_path = None
                if tmp_script_path is None:
                    payload = f"set +e\n{inner_cmd}\n__zai_ec=$?\nset +e\necho \"{marker}:$__zai_ec\"\necho \"{err_marker}\" >&2\n"

            try:
                self.proc.stdin.write(payload)
                self.proc.stdin.flush()
            except Exception as e:
                if tmp_script_path and os.path.exists(tmp_script_path):
                    try:
                        os.remove(tmp_script_path)
                    except Exception:
                        pass
                return -1, "", f"Session stdin write error: {str(e)}"

            out_lines = []
            err_lines = []
            rc = 0
            found_out_marker = False
            found_err_marker = False
            start_t = time.time()
            max_wait = float(timeout) if timeout else 180.0

            while not found_out_marker:
                if time.time() - start_t > max_wait:
                    self.close()
                    self._start_process()
                    return -1, "".join(out_lines), "".join(err_lines) + f"\n[TIMEOUT] Session command timed out after {max_wait}s."
                if not self.is_alive() and self.stdout_queue.empty():
                    rc = self.proc.returncode if self.proc.returncode is not None else -1
                    break
                try:
                    line = self.stdout_queue.get(timeout=0.05)
                    if marker in line:
                        idx = line.find(marker)
                        prefix_part = line[:idx]
                        if prefix_part.strip():
                            out_lines.append(prefix_part)
                        tail_part = line[idx + len(marker):].strip()
                        if tail_part.startswith(":"):
                            tail_part = tail_part[1:].strip()
                        try:
                            rc = int(tail_part.split()[0])
                        except Exception:
                            rc = 0
                        found_out_marker = True
                    else:
                        out_lines.append(line)
                except queue.Empty:
                    pass

                while not self.stderr_queue.empty():
                    try:
                        eline = self.stderr_queue.get_nowait()
                        if err_marker in eline:
                            e_idx = eline.find(err_marker)
                            if eline[:e_idx].strip():
                                err_lines.append(eline[:e_idx])
                            found_err_marker = True
                        else:
                            err_lines.append(eline)
                    except queue.Empty:
                        break

            err_wait_start = time.time()
            while not found_err_marker and (time.time() - err_wait_start < 0.25):
                try:
                    eline = self.stderr_queue.get(timeout=0.03)
                    if err_marker in eline:
                        e_idx = eline.find(err_marker)
                        if eline[:e_idx].strip():
                            err_lines.append(eline[:e_idx])
                        found_err_marker = True
                    else:
                        err_lines.append(eline)
                except queue.Empty:
                    if not self.is_alive():
                        break

            if tmp_script_path and os.path.exists(tmp_script_path):
                try:
                    os.remove(tmp_script_path)
                except Exception:
                    pass

            return rc, "".join(out_lines), "".join(err_lines)

    def close(self):
        if self.proc and self.proc.poll() is None:
            try:
                if self.proc.stdin:
                    try:
                        self.proc.stdin.close()
                    except Exception:
                        pass
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

class SessionPool:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def get_or_create(self, session_id, terminal="powershell", encoding="utf-8"):
        sid = str(session_id).strip()
        with self.lock:
            if sid in self.sessions:
                sess = self.sessions[sid]
                if sess.is_alive():
                    return sess
            sess = PersistentShellSession(sid, terminal=terminal, encoding=encoding)
            self.sessions[sid] = sess
            return sess

    def execute(self, session_id, cmd, terminal="powershell", encoding="utf-8", timeout=None):
        sess = self.get_or_create(session_id, terminal=terminal, encoding=encoding)
        return sess.execute(cmd, timeout=timeout)

    def close_session(self, session_id):
        sid = str(session_id).strip()
        with self.lock:
            sess = self.sessions.pop(sid, None)
        if sess:
            sess.close()
            return f"Session '{sid}' closed."
        return f"Session '{sid}' not found."

    def list_sessions(self):
        with self.lock:
            if not self.sessions:
                return "No active persistent sessions found."
            lines = []
            for sid, sess in self.sessions.items():
                status = "active" if sess.is_alive() else "closed"
                pid = sess.proc.pid if sess.proc else "None"
                lines.append(f"[{sid}] Terminal: {sess.terminal} | PID: {pid} | Status: {status} | Encoding: {sess.encoding}")
            return "\n".join(lines)

    def close_all(self):
        with self.lock:
            all_sessions = list(self.sessions.values())
            self.sessions.clear()
        for s in all_sessions:
            s.close()

session_pool = SessionPool()