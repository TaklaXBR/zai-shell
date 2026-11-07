import ctypes
import json
import locale
import logging
import os
import platform
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import warnings
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types

import prompts
import terminal_discovery
import security_rules
from background_manager import bg_manager, buffer_manager
from terminal_discovery import session_pool
from file_surgery import FileSurgeryEngine

from rich.console import Console
from rich.markup import escape
from rich.markdown import Markdown

console = Console()

warnings.filterwarnings("ignore", module="google.genai")
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google.generativeai").setLevel(logging.ERROR)

DEFAULT_CMD_TIMEOUT = 180
API_CALL_TIMEOUT = 125

API_KEY = os.environ.get("GEMINI_API_KEY", "ENTER_YOUR_API_KEY_HERE")
client = None
if API_KEY and API_KEY != "ENTER_YOUR_API_KEY_HERE":
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception:
        client = None

MODEL_NAME = os.environ.get("ZAISHELL_MODEL", "gemini-3.5-flash-lite")

def get_default_encoding():
    if platform.system() != "Windows":
        return "utf-8"
    try:
        oem = ctypes.cdll.kernel32.GetOEMCP()
        return f"cp{oem}"
    except Exception:
        return locale.getpreferredencoding() or "utf-8"

def truncate_output(text, step_id=None):
    return buffer_manager.store_and_truncate(text, step_id=step_id)

_INVALID_ESCAPE_RE = re.compile(r'\\(?<!\\\\)(?!["\\/bfnrt]|u[0-9a-fA-F]{4})')

def _repair_invalid_json_escapes(s):
    return _INVALID_ESCAPE_RE.sub(r"\\\\", s)

def parse_agent_json(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    candidates = [text]
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        extracted = text[first_brace:last_brace + 1]
        if extracted != text:
            candidates.append(extracted)

    last_err = None
    for cand in candidates:
        for attempt_str in (
            cand,
            _repair_invalid_json_escapes(cand),
            re.sub(r",\s*([}\]])", r"\1", _repair_invalid_json_escapes(cand)),
        ):
            try:
                parsed = json.loads(attempt_str, strict=False)
                if isinstance(parsed, list):
                    parsed = {"response": "", "run_parallel": False, "steps": parsed}
                if not isinstance(parsed, dict):
                    raise ValueError("JSON must be a top-level object.")
                known_keys = {"steps", "response", "file_action", "buffer_action", "session_action", "interactive_action"}
                if not any(k in parsed for k in known_keys):
                    raise ValueError(f"Expected keys not found. Received keys: {list(parsed.keys())}")
                return parsed, None
            except Exception as e:
                last_err = e
    return None, str(last_err)

def split_command_safe(cmd_str):
    try:
        parts = shlex.split(cmd_str, posix=(platform.system() != "Windows"))
    except ValueError:
        return [cmd_str]
    if platform.system() == "Windows":
        parts = [p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in ('"', "'") else p for p in parts]
    return parts

def has_shell_syntax(cmd):
    shell_ops = {"|", "||", "&&", ";", ">", ">>", "<", "<<", "2>&1", "&"}
    if isinstance(cmd, str):
        return any(op in cmd for op in ["|", "&&", ";", ">", "<", "$(", "`", "\n"])
    if isinstance(cmd, list):
        if not cmd:
            return False
        first = os.path.basename(str(cmd[0])).lower().replace(".exe", "")
        if first in {"python", "python3", "bash", "sh", "zsh", "powershell", "pwsh", "cmd", "node", "perl", "ruby", "php"}:
            return False
        return any(str(tok).strip() in shell_ops for tok in cmd)
    return False

def wrap_cmd_with_terminal(cmd, terminal="bash"):
    term_lower = str(terminal or ("powershell" if platform.system() == "Windows" else "bash")).lower()
    if isinstance(cmd, str):
        raw_str = cmd.strip()
        if not raw_str:
            return []
        if platform.system() != "Windows" or term_lower in ["bash", "sh", "zsh"]:
            sh_bin = term_lower if term_lower in ["bash", "sh", "zsh"] and shutil.which(term_lower) else ("bash" if shutil.which("bash") else "sh")
            return [sh_bin, "-c", raw_str]
        if any(x in term_lower for x in ["powershell", "pwsh"]):
            pwsh_bin = "pwsh" if shutil.which("pwsh") else "powershell"
            return [pwsh_bin, "-NoProfile", "-Command", raw_str]
        return ["cmd", "/c", raw_str]

    if isinstance(cmd, list):
        if not cmd:
            return []
        first = os.path.basename(str(cmd[0])).lower().replace(".exe", "")
        if first in ["bash", "sh", "zsh", "powershell", "pwsh", "cmd", "wsl"]:
            return [str(x) for x in cmd]
        if has_shell_syntax(cmd) or not shutil.which(str(cmd[0])):
            if platform.system() != "Windows":
                joined = " ".join(str(x) if str(x) in {"|", "||", "&&", ";", ">", ">>", "<", "2>&1", "&"} else shlex.quote(str(x)) for x in cmd)
                sh_bin = "bash" if shutil.which("bash") else "sh"
                return [sh_bin, "-c", joined]
        return [str(x) for x in cmd]
    return [str(cmd)]

def _kill_process_tree(p):
    if p is None:
        return
    try:
        if platform.system() != "Windows":
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:
                p.kill()
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            p.kill()
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

def run_single_cmd(cmd_list, timeout_sec, encoding, terminal="bash"):
    effective_timeout = float(timeout_sec) if timeout_sec is not None else float(DEFAULT_CMD_TIMEOUT)
    exec_cmd = wrap_cmd_with_terminal(cmd_list, terminal=terminal)
    if not exec_cmd:
        return 0, "", ""
    p = None
    try:
        popen_kwargs = {
            "shell": False,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": encoding,
            "errors": "replace",
        }
        if platform.system() != "Windows":
            popen_kwargs["start_new_session"] = True
            popen_kwargs["close_fds"] = True

        p = subprocess.Popen(exec_cmd, **popen_kwargs)
        out_chunks, err_chunks = [], []

        def _drain(stream, bucket):
            try:
                for chunk in iter(lambda: stream.read(4096), ""):
                    if not chunk:
                        break
                    bucket.append(chunk)
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=_drain, args=(p.stdout, out_chunks), daemon=True)
        t_err = threading.Thread(target=_drain, args=(p.stderr, err_chunks), daemon=True)
        t_out.start()
        t_err.start()

        p.wait(timeout=effective_timeout)
        t_out.join(timeout=0.5)
        t_err.join(timeout=0.5)
        return p.returncode, "".join(out_chunks), "".join(err_chunks)
    except subprocess.TimeoutExpired:
        _kill_process_tree(p)
        time.sleep(0.1)
        return -1, "".join(out_chunks), "".join(err_chunks) + f"\n[TIMEOUT] Task exceeded timeout of {effective_timeout}s and was stopped."
    except Exception as e:
        _kill_process_tree(p)
        return -1, "", str(e)

def execute_step_with_polling(step, cmd, session_id, term, timeout, enc):
    poll_cfg = step.get("poll_until")
    if not isinstance(poll_cfg, dict):
        if session_id:
            return session_pool.execute(session_id, cmd, terminal=term, encoding=enc, timeout=timeout)
        return run_single_cmd(cmd, timeout, enc, terminal=term)

    contains_str = poll_cfg.get("contains")
    regex_str = poll_cfg.get("regex")
    target_rc = poll_cfg.get("rc")
    poll_timeout = float(poll_cfg.get("timeout", timeout or 15.0))
    poll_interval = max(0.1, float(poll_cfg.get("interval", 1.0)))
    compiled = re.compile(regex_str, re.MULTILINE) if regex_str else None
    deadline = time.time() + poll_timeout
    last_rc, last_out, last_err = -1, "", ""

    while time.time() < deadline:
        per_try = min(poll_timeout, max(2.0, deadline - time.time()))
        if session_id:
            last_rc, last_out, last_err = session_pool.execute(session_id, cmd, terminal=term, encoding=enc, timeout=per_try)
        else:
            last_rc, last_out, last_err = run_single_cmd(cmd, per_try, enc, terminal=term)

        combined = (last_out or "") + "\n" + (last_err or "")
        matched = False
        if contains_str and contains_str in combined:
            matched = True
        elif compiled and compiled.search(combined):
            matched = True
        elif target_rc is not None and last_rc == int(target_rc):
            matched = True
        elif not contains_str and not compiled and target_rc is None and last_rc == 0:
            matched = True

        if matched:
            return 0, last_out, last_err

        rem = deadline - time.time()
        if rem <= 0:
            break
        time.sleep(min(poll_interval, rem))

    return -1, last_out, (last_err or "") + f"\n[POLL TIMEOUT] Condition not met within {poll_timeout}s."

def spawn_interactive_step(sid, cmd_list, check_sec, encoding, active_dict):
    try:
        p = subprocess.Popen(
            cmd_list, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding=encoding, errors="replace", bufsize=1
        )
    except Exception as e:
        return -1, "", str(e), False

    output_chunks = []
    def stream_reader(stream):
        try:
            while True:
                c = stream.read(1)
                if not c:
                    break
                output_chunks.append(c)
        except Exception:
            pass

    t1 = threading.Thread(target=stream_reader, args=(p.stdout,), daemon=True)
    t2 = threading.Thread(target=stream_reader, args=(p.stderr,), daemon=True)
    t1.start()
    t2.start()

    active_dict[sid] = {
        "popen": p, "output_chunks": output_chunks, "threads": (t1, t2),
        "cmd": cmd_list, "encoding": encoding, "start_time": time.time()
    }

    start_wait = time.time()
    while time.time() - start_wait < check_sec:
        if p.poll() is not None:
            break
        time.sleep(0.05)

    if p.poll() is not None:
        t1.join(timeout=0.3)
        t2.join(timeout=0.3)
        rc = p.returncode
        out = "".join(output_chunks)
        del active_dict[sid]
        return rc, out, "", False
    else:
        out_so_far = "".join(output_chunks)
        return 0, out_so_far, "", True

class StdinCoordinator:
    def __init__(self):
        self.line_queue = queue.Queue()
        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()

    def _reader(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                self.line_queue.put(line.rstrip("\r\n"))
            except Exception:
                time.sleep(0.1)

    def wait_for_input_or_event(self, prompt_markup):
        console.print(prompt_markup, end="")
        sys.stdout.flush()
        while True:
            bg_event = bg_manager.pop_event()
            if bg_event is not None:
                console.print()
                return "BG_EVENT", bg_event
            try:
                user_line = self.line_queue.get(timeout=0.15)
                return "USER_INPUT", user_line
            except queue.Empty:
                continue

    def read_line_blocking(self, prompt_markup):
        console.print(prompt_markup, end="")
        sys.stdout.flush()
        return self.line_queue.get()

def format_auto_heal_prompt(bg_event):
    ev_type = bg_event.get("type")
    tid = bg_event.get("task_id")
    pid = bg_event.get("pid")
    cmd = bg_event.get("command")
    rc = bg_event.get("rc")
    logs = bg_event.get("logs", "")
    matched = bg_event.get("matched_line", "")
    regex = bg_event.get("watch_log_regex", "")
    if ev_type == "watch_log_trigger":
        header = f"PROACTIVE LOG ALERT:\nTask ID: {tid} | PID: {pid} | Command: {cmd}\nMatched Pattern: {regex}\nTriggering Line: {matched}\nExit Code: {rc}\n"
    else:
        header = f"PROACTIVE CRASH ALERT (auto_heal):\nTask ID: {tid} | PID: {pid} | Command: {cmd}\nExit Code: {rc}\n"
    return f"{header}\nLAST 50 LOG LINES:\n{logs}\n\nAnalyze this error, fix the service, and get it running again."

def check_step_should_run(step, last_output_map, last_step_output, forced_targets, conditional_only_targets):
    sid = str(step.get("step_id", ""))
    if sid in conditional_only_targets and sid not in forced_targets:
        return False, f"Step '{sid}' skipped because it is only a conditional branch target."
    if "if_contains" in step and step["if_contains"]:
        ic = step["if_contains"]
        if isinstance(ic, dict):
            ref_sid = str(ic.get("step_id", ""))
            exp_text = str(ic.get("text", ""))
            target_out = last_output_map.get(ref_sid, last_step_output)
        else:
            exp_text = str(ic)
            target_out = last_step_output
        if exp_text not in (target_out or ""):
            return False, f"Skipped because if_contains condition ('{exp_text}') was not met."
    return True, ""

def create_resilient_chat(genai_client, model_name, sys_instruction, max_retries=6, base_delay=2.0):
    for attempt in range(max_retries):
        try:
            chat = genai_client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json",
                )
            )
            orig_send = chat.send_message
            def safe_send(msg):
                for s_attempt in range(max_retries):
                    try:
                        return orig_send(msg)
                    except Exception as e:
                        err_str = str(e).lower()
                        is_transient = any(x in err_str for x in ["503", "500", "502", "504", "429", "unavailable", "overloaded", "deadline", "timeout", "connection", "rate", "resource_exhausted", "service unavailable"])
                        if s_attempt < max_retries - 1 and is_transient:
                            time.sleep(base_delay * (1.5 ** s_attempt))
                            continue
                        raise
            chat.send_message = safe_send
            return chat
        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(x in err_str for x in ["503", "500", "502", "504", "429", "unavailable", "overloaded", "deadline", "timeout", "connection", "rate", "resource_exhausted", "service unavailable"])
            if attempt < max_retries - 1 and is_transient:
                time.sleep(base_delay * (1.5 ** attempt))
                continue
            raise

def run_agent():
    if client is None:
        console.print("[bold red]ERROR:[/bold red] GEMINI_API_KEY is not configured!")
        console.print("Please set your Gemini API key via environment variable:")
        console.print("  [bold]Windows (PowerShell):[/bold] [green]$env:GEMINI_API_KEY=\"your_key_here\"[/green]")
        console.print("  [bold]Linux / macOS (Bash):[/bold]  [green]export GEMINI_API_KEY=\"your_key_here\"[/green]")
        console.print("Or edit [cyan]zaishell.py[/cyan] and replace [yellow]'ENTER_YOUR_API_KEY_HERE'[/yellow] with your key.\n")
        return

    os_info = f"{platform.system()} {platform.release()}"
    available_terms = terminal_discovery.discover_terminals()
    default_enc = get_default_encoding()
    stdin_coord = StdinCoordinator()

    console.print(f"[bold cyan]===========================================================[/bold cyan]")
    console.print(f"[bold white]  ZAI Shell - Autonomous SysOps & Terminal Agent[/bold white]")
    console.print(f"[dim]  OS: {os_info} | Terminals: {', '.join(available_terms)} | Model: {MODEL_NAME}[/dim]")
    console.print(f"[bold cyan]===========================================================[/bold cyan]")

    sys_instruction = prompts.get_system_instruction(os_info, available_terms)
    chat = create_resilient_chat(client, MODEL_NAME, sys_instruction)
    last_output_map = {}

    while True:
        source_type, payload = stdin_coord.wait_for_input_or_event("\n[bold cyan]Give the agent a task (or 'q' to quit) > [/bold cyan]")
        auto_heal_mode = False

        if source_type == "BG_EVENT":
            auto_heal_mode = True
            tid = payload.get("task_id")
            ev_type = payload.get("type")
            console.print(f"\n[bold red][PROACTIVE AUTO-HEAL] Background task '{tid}' ({ev_type}) triggered.[/bold red]")
            active_prompt = format_auto_heal_prompt(payload)
        else:
            user_input = payload.strip()
            if not user_input:
                continue
            if user_input.lower() in ["q", "quit"]:
                session_pool.close_all()
                break
            active_prompt = user_input

        task_start_time = time.time()
        api_calls = 0
        consecutive_json_errors = 0
        max_json_errors = 8
        consecutive_cmd_failures = 0
        max_cmd_failures = 25
        max_total_turns = 80
        active_interactive = {}

        with console.status("[bold yellow]Agent is thinking...[/bold yellow]", spinner="dots"):
            response = chat.send_message(active_prompt)
            api_calls += 1

        while api_calls <= max_total_turns:
            agent_response, json_err = parse_agent_json(response.text)
            if agent_response is None:
                consecutive_json_errors += 1
                if consecutive_json_errors > max_json_errors:
                    console.print("[bold red]Maximum JSON error retry limit reached, task cancelled.[/bold red]")
                    break
                with console.status("[bold yellow]Repairing JSON output...[/bold yellow]", spinner="dots"):
                    response = chat.send_message(prompts.get_json_error_feedback(json_err))
                    api_calls += 1
                continue

            consecutive_json_errors = 0

            top_buffer_action = agent_response.get("buffer_action")
            if top_buffer_action and not agent_response.get("steps"):
                b_rc, b_out, b_err = buffer_manager.handle_action(top_buffer_action)
                feedback = f"BUFFER ACTION RESULT (Code: {b_rc}):\n{b_out}\n{b_err}".strip()
                response = chat.send_message(feedback)
                api_calls += 1
                continue

            top_file_action = agent_response.get("file_action")
            if top_file_action and not agent_response.get("steps"):
                f_rc, f_out, f_err = FileSurgeryEngine.execute(top_file_action)
                feedback = f"FILE ACTION RESULT (Code: {f_rc}):\n{f_out}\n{f_err}".strip()
                response = chat.send_message(feedback)
                api_calls += 1
                continue

            top_session_action = agent_response.get("session_action")
            if top_session_action and not agent_response.get("steps"):
                s_act = str(top_session_action.get("action", "list")).lower()
                s_out = session_pool.close_session(top_session_action.get("session_id", "")) if s_act == "close" else session_pool.list_sessions()
                response = chat.send_message(f"SESSION ACTION RESULT:\n{s_out}")
                api_calls += 1
                continue

            interactive_action = agent_response.get("interactive_action")
            if interactive_action:
                act_type = interactive_action.get("action")
                target_sid = str(interactive_action.get("target_step_id", ""))
                if not target_sid and active_interactive:
                    target_sid = next(iter(active_interactive.keys()))
                if target_sid not in active_interactive:
                    feedback = f"ERROR: No active process found with ID '{target_sid}'. Available: {list(active_interactive.keys())}"
                    response = chat.send_message(feedback)
                    api_calls += 1
                    continue

                target_proc_data = active_interactive[target_sid]
                p = target_proc_data["popen"]
                output_chunks = target_proc_data["output_chunks"]

                if act_type == "send_input":
                    inp_text = interactive_action.get("input_text", "")
                    check_sec = float(interactive_action.get("check_after_seconds", 2.0))
                    try:
                        p.stdin.write(inp_text)
                        p.stdin.flush()
                    except Exception:
                        pass
                    start_w = time.time()
                    while time.time() - start_w < check_sec:
                        if p.poll() is not None:
                            break
                        time.sleep(0.05)
                elif act_type == "wait":
                    wait_sec = float(interactive_action.get("wait_seconds", 3.0))
                    start_w = time.time()
                    while time.time() - start_w < wait_sec:
                        if p.poll() is not None:
                            break
                        time.sleep(0.05)
                elif act_type == "kill":
                    _kill_process_tree(p)
                    del active_interactive[target_sid]
                    response = chat.send_message(f"INTERACTIVE PROCESS TERMINATED: Step {target_sid} stopped.")
                    api_calls += 1
                    continue

                if p.poll() is not None:
                    rc = p.returncode
                    out_text = truncate_output("".join(output_chunks), step_id=target_sid)
                    del active_interactive[target_sid]
                    feedback = f"INTERACTIVE PROCESS COMPLETED:\nStep: {target_sid}\nExit Code: {rc}\nFull Output:\n{out_text}"
                else:
                    out_text = truncate_output("".join(output_chunks), step_id=target_sid)
                    feedback = f"INTERACTIVE PROCESS STILL ACTIVE:\nStep: {target_sid}\nLatest Output:\n{out_text}"
                response = chat.send_message(feedback)
                api_calls += 1
                continue

            response_msg = agent_response.get("response", "")
            steps = agent_response.get("steps", [])
            run_parallel = agent_response.get("run_parallel", False)

            if not steps:
                if response_msg:
                    console.print("\n[bold green][AGENT]:[/bold green]")
                    console.print(Markdown(response_msg))
                duration = round(time.time() - task_start_time, 2)
                console.print(f"\n[dim][METRICS] \\[Duration: {duration}s | API: {api_calls} | Model: {MODEL_NAME}][/dim]")
                break

            security_violation = False
            for step in steps:
                cmd = step.get("command", [])
                fallback = step.get("fallback_command", [])
                cmd_check = split_command_safe(cmd) if isinstance(cmd, str) else ([str(x) for x in cmd] if isinstance(cmd, list) else [])
                fb_check = split_command_safe(fallback) if isinstance(fallback, str) else ([str(x) for x in fallback] if isinstance(fallback, list) else [])
                if cmd_check and security_rules.is_dangerous(cmd_check):
                    console.print(f"[bold red][DANGER ZONE]: Forbidden command blocked![/bold red] -> {escape(' '.join(cmd_check))}")
                    security_violation = True
                    break
                if fb_check and security_rules.is_dangerous(fb_check):
                    console.print(f"[bold red][DANGER ZONE]: Forbidden fallback command blocked![/bold red] -> {escape(' '.join(fb_check))}")
                    security_violation = True
                    break

            if security_violation:
                consecutive_cmd_failures += 1
                response = chat.send_message(
                    "SECURITY VIOLATION: The command triggered the Danger Zone shield (root directory deletion/permission change). Generate a safe command specifying only the target subfolder."
                )
                api_calls += 1
                continue

            if auto_heal_mode:
                confirm = "y"
            else:
                mode_text = "[bold blue]PARALLEL[/bold blue]" if run_parallel else "[bold cyan]SEQUENTIAL[/bold cyan]"
                confirm = stdin_coord.read_line_blocking(f"[bold yellow]Execute these actions? Mode: {mode_text} (Y/N/skip): [/bold yellow]").strip()

            if confirm.lower() == "skip":
                response = chat.send_message("User declined the operation by choosing 'skip'.")
                api_calls += 1
                continue
            elif confirm.lower() != "y":
                break

            execution_results = []
            all_successful = True
            any_step_succeeded = False

            conditional_only_targets = set()
            for s in steps:
                if isinstance(s.get("on_failure"), str):
                    conditional_only_targets.add(s["on_failure"].strip())

            forced_targets = set()
            last_step_output = ""

            for i, step in enumerate(steps, 1):
                sid = str(step.get("step_id", f"step_{i}"))
                should_run, skip_reason = check_step_should_run(
                    step, last_output_map, last_step_output, forced_targets, conditional_only_targets
                )
                if not should_run:
                    execution_results.append(f"Step: {sid}\nStatus: SKIPPED ({skip_reason})\n")
                    continue

                desc = step.get("description", "Processing")
                raw_cmd = step.get("command", [])
                enc = step.get("encoding") or default_enc
                term = step.get("terminal", "powershell" if platform.system() == "Windows" else "bash")
                session_id = step.get("session_id")
                timeout = step.get("timeout")
                check_sec = step.get("check_after_seconds")
                step_esc = escape(f"[{sid}]")
                desc_esc = escape(desc)

                if step.get("file_action"):
                    f_rc, f_out, f_err = FileSurgeryEngine.execute(step["file_action"])
                    last_step_output = f_out + "\n" + f_err
                    last_output_map[sid] = last_step_output
                    f_out_trunc = truncate_output(f_out, step_id=sid)
                    if f_rc == 0:
                        any_step_succeeded = True
                        console.print(f"[cyan]{step_esc}[/cyan] [blue][File Surgery][/blue] {desc_esc}.... [bold green][OK][/bold green]")
                        execution_results.append(f"Step: {sid}\nFile Surgery Result:\n{f_out_trunc}\n")
                    else:
                        console.print(f"[cyan]{step_esc}[/cyan] [blue][File Surgery][/blue] {desc_esc}.... [bold red][ERROR][/bold red]")
                        execution_results.append(f"Step: {sid}\nFile Surgery Error:\n{f_err}\n")
                        all_successful = False
                        break
                    if not raw_cmd:
                        continue

                if step.get("buffer_action"):
                    b_rc, b_out, b_err = buffer_manager.handle_action(step["buffer_action"])
                    any_step_succeeded = True
                    last_step_output = b_out
                    last_output_map[sid] = b_out
                    execution_results.append(f"Step: {sid}\nBuffer Result:\n{b_out}\n{b_err}\n")
                    if not raw_cmd:
                        continue

                if step.get("background_action"):
                    act = step.get("background_action")
                    action_name = act.get("action")
                    if action_name == "list":
                        b_out = bg_manager.list_tasks()
                    elif action_name == "stop":
                        b_out = bg_manager.stop_task(act.get("task_id", ""))
                    elif action_name == "logs":
                        b_out = bg_manager.get_logs(act.get("task_id", ""), max_lines=act.get("max_lines", 100))
                    elif action_name == "send_input":
                        inp_val = act.get("input") if "input" in act else act.get("input_text", "")
                        b_out = bg_manager.send_input(act.get("task_id", ""), inp_val, wait_seconds=act.get("wait_seconds", 0.4))
                    else:
                        b_out = f"Unknown action: {action_name}"
                    any_step_succeeded = True
                    last_step_output = b_out
                    last_output_map[sid] = b_out
                    execution_results.append(f"Step: {sid}\nBackground Action: {action_name}\nResult:\n{b_out}\n")
                    if not raw_cmd:
                        continue

                cmd = raw_cmd if (isinstance(raw_cmd, str) and has_shell_syntax(raw_cmd)) else (split_command_safe(raw_cmd) if isinstance(raw_cmd, str) else raw_cmd)
                cmd_display = " ".join([f'"{x}"' if " " in str(x) else str(x) for x in cmd]) if isinstance(cmd, list) and cmd else str(raw_cmd)
                term_label = f"{term}:{session_id}" if session_id else term
                term_esc = escape(f"[{term_label}]")

                if step.get("is_background"):
                    res_dict = bg_manager.start_task(
                        raw_cmd, terminal=term, encoding=enc,
                        on_crash=step.get("on_crash"), watch_log_regex=step.get("watch_log_regex")
                    )
                    if res_dict["success"]:
                        bg_tid = res_dict["task_id"]
                        bg_msg = res_dict["message"]
                        bg_rc = 0
                        if step.get("poll_until") and isinstance(step["poll_until"], dict):
                            p_cfg = step["poll_until"]
                            ok_poll, poll_logs, poll_msg = bg_manager.wait_for_log(
                                bg_tid, contains=p_cfg.get("contains"), regex=p_cfg.get("regex"),
                                timeout=p_cfg.get("timeout", 15.0), interval=p_cfg.get("interval", 0.5)
                            )
                            bg_msg += f"\n[POLL RESULT]: {poll_msg}\nLogs:\n{poll_logs}"
                            if not ok_poll:
                                bg_rc = -1
                        last_step_output = bg_msg
                        last_output_map[sid] = bg_msg
                        if bg_rc == 0:
                            any_step_succeeded = True
                            console.print(f"[cyan]{step_esc}[/cyan] [blue][Background][/blue] {desc_esc}.... [bold green][OK][/bold green]")
                            execution_results.append(f"Step: {sid} Terminal: {term}\nCommand: {cmd_display}\nStatus: {bg_msg}\n")
                        else:
                            all_successful = False
                            execution_results.append(f"Step: {sid}\nError: {bg_msg}\n")
                            break
                    else:
                        all_successful = False
                        execution_results.append(f"Step: {sid}\nError: {res_dict['message']}\n")
                        break
                    continue

                cmd_to_pass = raw_cmd if session_id else cmd
                rc, out, err = execute_step_with_polling(step, cmd_to_pass, session_id, term, timeout, enc)

                if rc != 0 and step.get("fallback_command"):
                    fb_raw = step.get("fallback_command")
                    if session_id:
                        f_rc, f_out, f_err = session_pool.execute(session_id, fb_raw, terminal=term, encoding=enc, timeout=timeout)
                    else:
                        fb_cmd = fb_raw if (isinstance(fb_raw, str) and has_shell_syntax(fb_raw)) else (split_command_safe(fb_raw) if isinstance(fb_raw, str) else fb_raw)
                        f_rc, f_out, f_err = run_single_cmd(fb_cmd, timeout, enc, terminal=term)
                    if f_rc == 0:
                        rc, out, err = 0, f_out, "(RECOVERED WITH FALLBACK PLAN)\n" + f_err
                    else:
                        err += f"\n[FALLBACK ERROR]: {f_err}"

                last_step_output = (out or "") + ("\n" + err if err else "")
                last_output_map[sid] = last_step_output
                out_trunc = truncate_output((out or "").strip(), step_id=sid)
                err_trunc = truncate_output((err or "").strip(), step_id=f"{sid}_err")
                output_str = f"Step: {sid} Terminal: {term_label}\nCommand: {cmd_display}\nExit Code: {rc}\n"
                if out_trunc:
                    output_str += f"Output:\n{out_trunc}\n"
                if err_trunc:
                    output_str += f"Error Output:\n{err_trunc}\n"
                execution_results.append(output_str)

                if rc == 0:
                    any_step_succeeded = True
                    console.print(f"[cyan]{step_esc}[/cyan] [blue]{term_esc}[/blue] {desc_esc}.... [bold green][OK][/bold green]")
                else:
                    console.print(f"[cyan]{step_esc}[/cyan] [blue]{term_esc}[/blue] {desc_esc}.... [bold red][ERROR][/bold red]")
                    all_successful = False
                    break

            if all_successful:
                consecutive_cmd_failures = 0
                feedback = "OPERATION SUCCESSFUL. OUTPUTS:\n" + "\n---\n".join(execution_results)
                feedback += "\n\nPlease review the outputs. If the task is finished, leave the 'steps' list empty and explain the result in the 'response' field."
                response = chat.send_message(feedback)
                api_calls += 1
                continue

            if any_step_succeeded:
                consecutive_cmd_failures = 0
            else:
                consecutive_cmd_failures += 1

            if consecutive_cmd_failures > max_cmd_failures:
                console.print(f"\n[bold red][ERROR] Maximum consecutive error limit ({max_cmd_failures}) reached.[/bold red]")
                break

            feedback = "OPERATION RESULTS (Some steps returned rc != 0):\n" + "\n---\n".join(execution_results)
            feedback += "\n\nReview the output and error messages; send a NEW 'steps' list to resolve the issue or proceed to the next step."
            response = chat.send_message(feedback)
            api_calls += 1

if __name__ == "__main__":
    run_agent()