import os
import sys
import subprocess
import time
import datetime
import json
import platform
import re
try:
    import keyboard
except ImportError:
    keyboard = None
import locale
from pathlib import Path
from typing import Dict, List, Optional, Any

SYSTEM_ENCODING = locale.getpreferredencoding(False)

import google.generativeai as genai
from colorama import init, Fore, Style

from gui_automation import GUIAutomationBridge, PYAUTOGUI_AVAILABLE
from p2p_sharing import P2PTerminalSharing
from offline_telemetry import OfflineModelManager, TelemetryManager
from research_image import WebResearchEngine, ImageAnalyzer, DDGS_AVAILABLE, REQUESTS_AVAILABLE, BS4_AVAILABLE, SUPPORTED_IMAGE_FORMATS
from sentinel import Sentinel, get_sentinel, ThreatLevel

init(autoreset=True)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "Or Enter Your API Key Here")
genai.configure(api_key=GEMINI_API_KEY)

MEMORY_FILE = ".zaishell_memory.json"
CHROMA_DB_PATH = ".zaishell_chromadb"
CHROMA_COLLECTION_NAME = "zaishell_memory"
OFFLINE_MODEL_PATH = ".zaishell_offline_model"
OFFLINE_MODEL_NAME = "microsoft/phi-2"


def extract_json_from_text(text: str) -> Optional[Dict]:
    """Utility function to extract JSON from AI response text."""
    if not text:
        return None
    try:
        json_start = text.find('{')
        if json_start < 0:
            return None
        bracket_count = 0
        json_end = -1
        for i, char in enumerate(text[json_start:], json_start):
            if char == '{':
                bracket_count += 1
            elif char == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    json_end = i + 1
                    break
        if json_end > json_start:
            return json.loads(text[json_start:json_end])
    except json.JSONDecodeError:
        pass
    return None


SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

DANGEROUS_COMMANDS = [
    'rm -rf', 'sudo rm', 'del /f', 'format', 'reboot', 'shutdown',
    'init 0', 'init 6', 'poweroff', 'halt', 'dd if=', 'mkfs',
    ':(){:|:&};:', 'chmod -R 777 /', 'chown -R', '> /dev/sda',
    'mv /* ', 'rm -r /', 'sudo dd', 'fdisk', 'wipefs',
    'Remove-Item', 'IEX', 'Invoke-Expression', 'Invoke-WebRequest',
    'erase', 'rd /s', 'deltree', 'rmdir /s',
    'find / -delete', 'find . -delete', 'xargs rm',
    'reg add', 'reg delete', 'sc delete', 'sc stop',
    'net user', 'net localgroup', 'netsh',
    'certutil -decode', 'bitsadmin',
    'taskkill /f', 'wmic process', 'Stop-Process',
    'Start-Process', 'New-Object Net.WebClient',
    'DownloadString', 'DownloadFile',
    'Invoke-Command', 'Enter-PSSession',
    'rm -r', 'del /q', 'del /s',
]

DANGEROUS_PATTERNS = [
    r'rm\s+-r',
    r'del\s+/[fqs]',
    r':\s*\(\s*\)\s*\{',
    r'IEX\s*[\(\[]',
    r'Invoke-Expression',
    r'Remove-Item.*-Recurse',
    r'Remove-Item.*-Force',
    r'>\s*/dev/',
    r'>\s*\\\\',
    r'\|\s*rm',
    r'\|\s*del',
    r'wget.*\|.*sh',
    r'curl.*\|.*bash',
    r'-encodedcommand',
    r'-enc\s+',
    r'powershell.*-e\s+',
    r'cmd.*/c.*del',
    r'cmd.*/c.*format',
]

TERMINAL_CAPABILITIES = {
    "windows": {
        "open_url": "start {browser} {url}",
        "notepad": "start notepad",
        "chrome": "start chrome",
        "firefox": "start firefox",
        "edge": "start msedge",
        "explorer": "start explorer",
        "vscode": "code",
        "cmd": "start cmd",
        "powershell": "start powershell",
        "calculator": "calc",
        "paint": "mspaint",
        "task_manager": "taskmgr",
    },
    "linux": {
        "open_url": "xdg-open {url}",
        "file_manager": "nautilus",
        "terminal": "gnome-terminal",
    }
}

GIT_BASH_PATHS = [
    r'C:\Program Files\Git\bin\bash.exe',
    r'C:\Program Files (x86)\Git\bin\bash.exe',
    os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\bash.exe')
]
CYGWIN_PATHS = [r'C:\cygwin64\bin\bash.exe', r'C:\cygwin\bin\bash.exe']


class TaskContext:
    """Manages persistent context for multi-step hybrid tasks"""
    
    def __init__(self, max_history: int = 50):
        self.current_plan = None
        self.completed_steps = []
        self.current_step = 0
        self.variables = {}
        self.action_history = []
        self.max_history = max_history
        self.screenshots = []
    
    def set_plan(self, plan: Dict):
        """Set a new multi-step plan"""
        self.current_plan = plan
        self.completed_steps = []
        self.current_step = 0
        self.screenshots = []
    
    def update(self, step: Dict, result: Dict):
        """Mark a step as completed and update context"""
        self.completed_steps.append({
            "step": step,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        })
        self.current_step += 1
        
        self.action_history.append({
            "type": step.get("type", "unknown"),
            "action": step.get("action", ""),
            "success": result.get("success", False)
        })
        
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]
    
    def get_context_for_ai(self) -> str:
        """Get context string for AI prompt"""
        if not self.current_plan:
            return ""
        
        completed_info = []
        for cs in self.completed_steps[-5:]:
            step = cs["step"]
            result = cs["result"]
            status = "SUCCESS" if result.get("success") else "FAILED"
            completed_info.append(f"  - Step {step.get('step', '?')}: {step.get('type', '?')} - {status}")
        
        context = f"""
CURRENT TASK CONTEXT:
Task: {self.current_plan.get('task', 'Unknown')}
Progress: {self.current_step}/{len(self.current_plan.get('steps', []))} steps completed
Completed Steps:
{chr(10).join(completed_info) if completed_info else '  None yet'}
Variables: {json.dumps(self.variables) if self.variables else 'None'}
"""
        return context
    
    def is_complete(self) -> bool:
        """Check if current plan is completed"""
        if not self.current_plan:
            return True
        return self.current_step >= len(self.current_plan.get('steps', []))
    
    def clear(self):
        """Clear context after task completion"""
        self.current_plan = None
        self.completed_steps = []
        self.current_step = 0
        self.variables = {}
        self.screenshots = []
    
    def add_variable(self, key: str, value: Any):
        """Store a dynamic variable for later steps"""
        self.variables[key] = value


class MemoryManager:
    """Manages persistent memory storage"""
    
    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.memory = self._load_memory()
    
    def _load_memory(self):
        """Load memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._create_default_memory()
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Memory load error: {e}. Creating new memory.{Style.RESET_ALL}")
            return self._create_default_memory()
    
    def _create_default_memory(self):
        """Create default memory structure"""
        return {
            "user": {
                "name": "User",
                "preferences": {},
                "first_seen": datetime.datetime.now().isoformat(),
                "last_seen": datetime.datetime.now().isoformat()
            },
            "conversation_history": [],
            "mode": "normal",
            "thinking_enabled": False,
            "offline_mode": False,
            "gui_enabled": False,
            "research_enabled": False,
            "stats": {
                "total_requests": 0,
                "successful_actions": 0,
                "failed_actions": 0
            }
        }
    
    def save_memory(self):
        """Save memory to file"""
        try:
            self.memory["user"]["last_seen"] = datetime.datetime.now().isoformat()
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, indent=2, fp=f)
        except Exception as e:
            print(f"{Fore.RED}❌ Memory save error: {e}{Style.RESET_ALL}")
    
    def add_conversation(self, role, message):
        """Add conversation entry"""
        entry = {
            "role": role,
            "message": message[:500],
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.memory["conversation_history"].append(entry)
        if len(self.memory["conversation_history"]) > 50:
            self.memory["conversation_history"] = self.memory["conversation_history"][-50:]
        self.save_memory()
    
    def get_recent_history(self, count=5):
        """Get recent conversation history"""
        return self.memory["conversation_history"][-count:]
    
    def update_stats(self, successful=0, failed=0):
        """Update statistics"""
        self.memory["stats"]["total_requests"] += 1
        self.memory["stats"]["successful_actions"] += successful
        self.memory["stats"]["failed_actions"] += failed
        self.save_memory()
    
    def set_mode(self, mode):
        """Set current mode"""
        self.memory["mode"] = mode
        self.save_memory()
    
    def get_mode(self):
        """Get current mode"""
        return self.memory.get("mode", "normal")
    
    def set_thinking(self, enabled):
        """Set thinking mode"""
        self.memory["thinking_enabled"] = enabled
        self.save_memory()
    
    def get_thinking(self):
        """Get thinking mode"""
        return self.memory.get("thinking_enabled", False)
    
    def set_offline_mode(self, enabled):
        """Set offline mode"""
        self.memory["offline_mode"] = enabled
        self.save_memory()
    
    def get_offline_mode(self):
        """Get offline mode status"""
        return self.memory.get("offline_mode", False)
    
    def set_gui_enabled(self, enabled):
        """Set GUI enabled"""
        self.memory["gui_enabled"] = enabled
        self.save_memory()
    
    def get_gui_enabled(self):
        """Get GUI enabled status"""
        return self.memory.get("gui_enabled", False)
    
    def set_research_enabled(self, enabled):
        """Set research enabled"""
        self.memory["research_enabled"] = enabled
        self.save_memory()
    
    def get_research_enabled(self):
        """Get research enabled status"""
        return self.memory.get("research_enabled", False)


class ChromaMemoryManager:
    """ChromaDB-based persistent memory manager"""
    
    def __init__(self, fallback_to_json=True):
        self.use_chromadb = False
        self.chroma_client = None
        self.collection = None
        self.fallback_to_json = fallback_to_json
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.chroma_client = chromadb.PersistentClient(
                path=CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.chroma_client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"description": "ZAIShell conversation memory"}
            )
            
            self.use_chromadb = True
            print(f"{Fore.GREEN}✓ ChromaDB memory initialized{Style.RESET_ALL}")
            
        except ImportError:
            print(f"{Fore.YELLOW}⚠️ ChromaDB not installed. Install: pip install chromadb{Style.RESET_ALL}")
            if fallback_to_json:
                print(f"{Fore.YELLOW}→ Falling back to JSON memory{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ ChromaDB error: {e}. Using JSON memory{Style.RESET_ALL}")
        
        self.json_manager = MemoryManager()
        self.memory = self.json_manager.memory
    
    def get_offline_mode(self):
        return self.json_manager.get_offline_mode()
    
    def set_offline_mode(self, enabled):
        self.json_manager.set_offline_mode(enabled)
    
    def add_conversation(self, role, message):
        timestamp = datetime.datetime.now().isoformat()
        self.json_manager.add_conversation(role, message)
        if self.use_chromadb and self.collection:
            try:
                doc_id = f"{role}_{timestamp}"
                self.collection.add(
                    documents=[message[:1000]],
                    metadatas=[{"role": role, "timestamp": timestamp, "full_message": message[:2000]}],
                    ids=[doc_id]
                )
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ ChromaDB add error: {e}{Style.RESET_ALL}")
    
    def get_recent_history(self, count=5):
        if self.use_chromadb and self.collection:
            try:
                results = self.collection.get(limit=count, include=["metadatas", "documents"])
                history = []
                for i, metadata in enumerate(results["metadatas"]):
                    history.append({
                        "role": metadata["role"],
                        "message": metadata.get("full_message", results["documents"][i]),
                        "timestamp": metadata["timestamp"]
                    })
                return sorted(history, key=lambda x: x["timestamp"])[-count:]
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ ChromaDB query error: {e}{Style.RESET_ALL}")
        return self.json_manager.get_recent_history(count)
    
    def search_memory(self, query, n_results=3):
        if self.use_chromadb and self.collection:
            try:
                results = self.collection.query(query_texts=[query], n_results=n_results, include=["metadatas", "documents", "distances"])
                return results
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ ChromaDB search error: {e}{Style.RESET_ALL}")
        return None
    
    def save_memory(self):
        self.json_manager.save_memory()
    
    def update_stats(self, successful=0, failed=0):
        self.json_manager.update_stats(successful, failed)
    
    def set_mode(self, mode):
        self.json_manager.set_mode(mode)
        self.memory = self.json_manager.memory
    
    def get_mode(self):
        return self.json_manager.get_mode()
    
    def set_thinking(self, enabled):
        self.json_manager.set_thinking(enabled)
    
    def get_thinking(self):
        return self.json_manager.get_thinking()
    
    def set_gui_enabled(self, enabled):
        self.json_manager.set_gui_enabled(enabled)
        self.memory = self.json_manager.memory
    
    def get_gui_enabled(self):
        return self.json_manager.get_gui_enabled()
    
    def set_research_enabled(self, enabled):
        self.json_manager.set_research_enabled(enabled)
        self.memory = self.json_manager.memory
    
    def get_research_enabled(self):
        return self.json_manager.get_research_enabled()


class ModeManager:
    """Manages operation modes"""
    
    MODES = {
        "normal": {
            "model": "gemini-2.5-flash",
            "temperature": 0.7,
            "description": "Standard mode - Balanced performance",
            "instruction_modifier": ""
        },
        "eco": {
            "model": "gemini-2.5-flash-lite",
            "temperature": 0.3,
            "max_output_tokens": 2048,
            "top_p": 0.8,
            "top_k": 20,
            "response_mime_type": "application/json",
            "description": "Economy mode - Maximum token efficiency with deterministic output",
            "instruction_modifier": """
⚡ ECO MODE RULES:
- ULTRA CONCISE: Keep response text under 2 sentences.
- NO fluff, NO chat.
- PREFER CHAINING: Combine commands (e.g., 'mkdir test && cd test') instead of multiple steps.
- DIRECT JSON output only.
- Token budget: MINIMAL.
"""
        },
        "lightning": {
            "model": "gemini-2.5-flash-lite",
            "temperature": 0.0,
            "max_output_tokens": 2048,
            "top_p": 0.9,
            "top_k": 1,
            "response_mime_type": "application/json",
            "description": "Lightning mode - Ultra-fast, zero-confirmation, deterministic",
            "instruction_modifier": """
⚡ LIGHTNING MODE - EXTREME SPEED:
- ZERO chat, ZERO explanation.
- OUTPUT MINIMAL JSON. Format: {"understanding":"brief","actions":[...],"response":"1 word"}
- NO <thinking> tags.
- ONE action only (chain commands with && or ; if needed).
- Example: {"understanding":"Delete logs","actions":[{"type":"command","details":{"shell":"cmd","content":"del *.log","encoding":"cp1254"}}],"response":"Done"}
"""
        }
    }
    
    @staticmethod
    def get_mode_config(mode_name):
        return ModeManager.MODES.get(mode_name.lower(), ModeManager.MODES["normal"])
    
    @staticmethod
    def is_valid_mode(mode_name):
        return mode_name.lower() in ModeManager.MODES
    
    @staticmethod
    def list_modes():
        return list(ModeManager.MODES.keys())


class AITools:
    """Tools that AI can use"""
    
    def handle_file(self, details):
        """File operations with Security validation"""
        try:
            path = details.get('path', '')
            content = details.get('content', '')
            encoding = details.get('encoding')
            if not encoding or str(encoding).lower() == 'system':
                encoding = SYSTEM_ENCODING
            mode = details.get('mode', 'text')
            
            if not path:
                return {"success": False, "error": "File path not specified"}
            
            security_check = self._validate_path_security(path)
            if security_check:
                return {"success": False, "error": security_check}
            
            path = os.path.normpath(os.path.expanduser(path))
            
            final_check = self._validate_path_security(path)
            if final_check:
                return {"success": False, "error": final_check}
            
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            if mode == 'binary':
                if isinstance(content, bytes):
                    with open(path, 'wb') as f:
                        f.write(content)
                    file_size = len(content)
                else:
                    with open(path, 'wb') as f:
                        pass
                    file_size = 0
            else:
                with open(path, 'w', encoding=encoding, errors='replace') as f:
                    f.write(content)
                file_size = len(content)
            
            return {"success": True, "path": path, "size": file_size, "mode": mode}
            
        except Exception as e:
            return {"success": False, "error": f"File error: {str(e)}"}
    
    def _validate_path_security(self, path):
        if not path:
            return None
        
        if '..' in path:
            return "Path traversal blocked: contains .."
        
        if path.startswith('\\\\') or path.startswith('//'):
            return "UNC network path blocked"
        
        path_lower = path.lower()
        blocked_paths = [
            'windows\\system32', 'windows/system32',
            'system32\\drivers', 'system32/drivers', 
            '\\windows\\', '/windows/',
            '/etc/', '/dev/', '/proc/', '/sys/',
            'program files', 'programdata',
        ]
        for blocked in blocked_paths:
            if blocked in path_lower:
                return f"System path blocked: {blocked}"
        
        reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                   'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                   'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        basename = os.path.basename(path).upper().split('.')[0]
        if basename in reserved:
            return f"Reserved device name blocked: {basename}"
        
        if len(path) > 260:
            return "Path too long (max 260 characters)"
        
        invalid_chars = '<>"|?*'
        for char in invalid_chars:
            if char in os.path.basename(path):
                return f"Invalid character in filename: {char}"
        
        return None
    
    def run_command(self, details):
        """Execute system command - optimized"""
        command = details.get('content', '')
        shell_type = details.get('shell', 'cmd').lower()
        encoding = details.get('encoding')
        if not encoding or str(encoding).lower() == 'system':
            encoding = SYSTEM_ENCODING
        
        if not command:
            return {"success": False, "error": "Command not specified"}
        
        def _run(cmd_args, use_shell=False, executable=None):
            return subprocess.run(
                cmd_args, shell=use_shell, executable=executable,
                capture_output=True, text=True, timeout=600,
                encoding=encoding, errors='replace'
            )
        
        def _find_path(paths):
            for p in paths:
                if os.path.exists(p):
                    return p
            return None
        
        try:
            shell_cmds = {
                'powershell': ['powershell', '-NoProfile', '-Command', command],
                'pwsh': ['pwsh', '-NoProfile', '-Command', command],
                'cmd': ['cmd', '/c', command],
                'wsl': ['wsl', 'bash', '-c', command],
            }
            
            if shell_type in shell_cmds:
                result = _run(shell_cmds[shell_type])
            elif shell_type == 'git-bash':
                bash = _find_path(GIT_BASH_PATHS)
                if not bash:
                    return {"success": False, "error": "Git Bash not found"}
                result = _run([bash, '-c', command])
            elif shell_type == 'cygwin':
                bash = _find_path(CYGWIN_PATHS)
                if not bash:
                    return {"success": False, "error": "Cygwin not found"}
                result = _run([bash, '-c', command])
            elif shell_type in ['bash', 'sh', 'zsh', 'fish', 'ksh', 'tcsh', 'dash']:
                result = _run(command, use_shell=True, executable=f'/bin/{shell_type}')
            else:
                result = _run(command, use_shell=True)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000] if result.stdout else "",
                "error": result.stderr[:1000] if result.stderr else "",
                "returncode": result.returncode,
                "shell": shell_type
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out (600s)"}
        except Exception as e:
            return {"success": False, "error": f"Command error: {e}"}
    
    def create_code(self, details):
        """Create code"""
        return self.handle_file(details)
    
    def gather_info(self, details):
        """Gather information"""
        try:
            info_type = details.get('type', 'system')
            
            if info_type == 'system':
                try:
                    import psutil
                    info = {
                        "cpu_percent": psutil.cpu_percent(interval=1),
                        "memory_percent": psutil.virtual_memory().percent,
                        "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                        "disk_percent": psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:\\').percent,
                        "process_count": len(psutil.pids()),
                        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
                    }
                except:
                    info = {"message": "System information unavailable (psutil required)"}
            elif info_type == 'files':
                path = details.get('path', '.')
                try:
                    files = os.listdir(path)
                    info = {"path": path, "file_count": len(files), "files": files[:50]}
                except:
                    info = {"error": f"Cannot read directory: {path}"}
            elif info_type == 'network':
                try:
                    import psutil
                    net_io = psutil.net_io_counters()
                    info = {
                        "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                        "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv
                    }
                except:
                    info = {"message": "Network information unavailable"}
            else:
                info = {"message": "Information gathered"}
            
            return {"success": True, "info": info}
            
        except Exception as e:
            return {"success": False, "error": f"Information gathering error: {str(e)}"}
    
    def multi_task(self, details):
        """Multi-tasking"""
        tasks = details.get('tasks', [])
        results = []
        
        if not tasks:
            return {"success": False, "error": "Task list is empty"}
        
        for task in tasks:
            task_type = task.get('type')
            task_details = task.get('details', task)
            
            if task_type == 'file':
                result = self.handle_file(task_details)
            elif task_type == 'command':
                result = self.run_command(task_details)
            elif task_type == 'code':
                result = self.create_code(task_details)
            elif task_type == 'info':
                result = self.gather_info(task_details)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success'))
        return {"success": success_count > 0, "completed": success_count, "total": len(tasks), "results": results}


class AIBrain:
    """AI Brain - COMPLETELY FREE, no restrictions"""
    
    def __init__(self, memory_manager, telemetry=None):
        self.memory = memory_manager
        self.telemetry = telemetry
        self.current_mode = self.memory.get_mode()
        self.thinking_enabled = self.memory.get_thinking()
        self.offline_mode = self.memory.get_offline_mode()
        self.gui_enabled = self.memory.get_gui_enabled()
        self.research_enabled = self.memory.get_research_enabled()
        self.offline_model = None
        
        if self.offline_mode:
            print(f"\n{Fore.YELLOW}System started in OFFLINE mode. Loading model...{Style.RESET_ALL}")
            self.offline_model = OfflineModelManager()
            self.offline_model.load_model()
        
        self.model = self._create_model()
        self.tools = AITools()
        self.context = self._build_context()
        self.max_retries = 5
        self.temp_mode = None
        self._task_context = TaskContext()
        self._web_research = None
        self._image_analyzer = None
        self._gui_bridge = None
        self._p2p_sharing = None
        self._sentinel = get_sentinel()
    
    @property
    def task_context(self) -> TaskContext:
        return self._task_context
    
    @property
    def sentinel(self) -> Sentinel:
        return self._sentinel
    
    @property
    def web_research(self) -> Optional[WebResearchEngine]:
        if self.offline_mode:
            return None
        if self._web_research is None:
            self._web_research = WebResearchEngine()
            self._web_research.set_ai_model(self.model)
        return self._web_research
    
    @property
    def image_analyzer(self) -> ImageAnalyzer:
        if self._image_analyzer is None:
            self._image_analyzer = ImageAnalyzer()
        return self._image_analyzer
    
    @property
    def gui_bridge(self) -> Optional[GUIAutomationBridge]:
        if self.offline_mode:
            return None
        if self._gui_bridge is None:
            self._gui_bridge = GUIAutomationBridge(self)
        return self._gui_bridge
    
    @property
    def p2p_sharing(self) -> P2PTerminalSharing:
        if self._p2p_sharing is None:
            self._p2p_sharing = P2PTerminalSharing()
        return self._p2p_sharing
    
    def detect_intent(self, user_message: str) -> Dict:
        intents = {
            'needs_research': False, 
            'needs_image_analysis': False, 
            'needs_gui': False, 
            'needs_hybrid': False, 
            'needs_p2p': False,
            'p2p_action': None,
            'image_path': None, 
            'research_query': None
        }
        
        for fmt in SUPPORTED_IMAGE_FORMATS:
            pattern = rf'[\w/\\:.-]+\.{fmt}\b'
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                intents['needs_image_analysis'] = True
                intents['image_path'] = match.group(0)
                break
        
        if self.offline_mode or not self.model:
            return intents
        
        if self._p2p_sharing and self._p2p_sharing.is_connected:
            p2p_context = self._p2p_sharing.get_p2p_context()
            available_actions = p2p_context.get('available_actions', [])
            users = p2p_context.get('connected_users', [])
            
            p2p_prompt = f'''Analyze this user message in P2P sharing context.
User message: "{user_message}"

P2P SESSION INFO:
- Role: {"HOST" if p2p_context.get('is_host') else "HELPER"}
- Connected Users: {', '.join(users)}
- Available Actions: {', '.join(available_actions)}
- Pending Commands: {p2p_context.get('pending_commands', 0)}
- Pending Files: {p2p_context.get('pending_files', 0)}

DETERMINE if this is a P2P command. Return JSON:
{{
    "is_p2p_command": true/false,
    "action": "action_name or null",
    "params": {{"target_user": "username or null", "message": "text or null", "file_path": "path or null", "command": "cmd or null"}}
}}

ACTIONS:
- show_logs: user wants to see terminal logs
- show_chat: user wants to see chat history  
- list_users: user wants to see connected users
- show_status: user wants P2P status
- send_message: user wants to send a message (extract message text)
- send_file: user wants to send a file (extract file_path and target_user if mentioned)
- send_command: user wants to send/run command on another user's machine (extract command and target_user)
- approve_command: user wants to approve pending command
- reject_command: user wants to reject pending command
- accept_file: user wants to accept incoming file
- deny_file: user wants to reject incoming file

If NOT a P2P command, set is_p2p_command to false.'''

            try:
                response = self.model.generate_content(p2p_prompt)
                text = response.text
                start = text.find('{')
                end = text.rfind('}') + 1
                if start >= 0 and end > start:
                    result = json.loads(text[start:end])
                    if result.get('is_p2p_command'):
                        intents['needs_p2p'] = True
                        intents['p2p_action'] = {
                            'action': result.get('action'),
                            'params': result.get('params', {})
                        }
                        return intents
            except Exception:
                pass
        
        if not self.gui_enabled and not self.research_enabled:
            return intents
        
        try:
            intent_prompt = f'Analyze: "{user_message}"\nReturn JSON: {{"needs_research": bool, "needs_gui": bool, "needs_hybrid": bool}}\nRules: needs_research=user asks current info/versions; needs_gui=clicking UI; needs_hybrid=both terminal+GUI'
            response = self.model.generate_content(intent_prompt)
            text = response.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                if self.research_enabled:
                    intents['needs_research'] = result.get('needs_research', False)
                    if intents['needs_research']:
                        intents['research_query'] = user_message
                if self.gui_enabled:
                    intents['needs_gui'] = result.get('needs_gui', False)
                    intents['needs_hybrid'] = result.get('needs_hybrid', False)
                    if intents['needs_hybrid']:
                        intents['needs_gui'] = True
        except Exception:
            pass
        return intents

    
    def generate_hybrid_plan(self, user_request: str) -> Optional[Dict]:
        if self.offline_mode:
            return None
        plan_prompt = f'''Analyze this user request and create an execution plan.
User request: "{user_request}"

DECISION RULES:
1. Opening programs/sites = TERMINAL (e.g., "start chrome url")
2. Clicking buttons = GUI
3. Typing in browser = GUI
4. File operations = TERMINAL
5. System commands = TERMINAL

Return a JSON plan:
{{
    "task": "description",
    "needs_gui": true/false,
    "steps": [
        {{"step": 1, "type": "terminal", "action": "command here", "description": "what it does", "wait_after": 2}},
        {{"step": 2, "type": "gui", "action": "click", "target": "element description", "wait_after": 1.5}}
    ]
}}

If the task can be done entirely with terminal, set needs_gui to false.'''
        try:
            response = self.model.generate_content(plan_prompt)
            text = response.text
            start = text.find('{')
            if start >= 0:
                depth = 0
                end = start
                for i, c in enumerate(text[start:], start):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > start:
                    json_str = text[start:end]
                    plan = json.loads(json_str)
                    return plan
        except json.JSONDecodeError as e:
            print(f"{Fore.YELLOW}Plan JSON error: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Plan generation error: {e}{Style.RESET_ALL}")
        return None
    
    def execute_hybrid_plan(self, plan: Dict, safe_mode: bool = False) -> Dict:
        if not plan or not plan.get('steps'):
            return {"success": False, "error": "Invalid plan"}
        self._task_context.set_plan(plan)
        results = []
        print(f"\n{Fore.CYAN}Executing hybrid plan: {plan.get('task', 'Unknown task')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Total steps: {len(plan['steps'])}{Style.RESET_ALL}\n")
        for step in plan['steps']:
            step_num = step.get('step', '?')
            step_type = step.get('type', 'unknown')
            description = step.get('description', step.get('action', 'Action'))
            print(f"{Fore.BLUE}[Step {step_num}] [{step_type.upper()}] {description}{Style.RESET_ALL}", end=' ')
            try:
                if step_type == 'terminal':
                    command = step.get('action', '')
                    if safe_mode:
                        for dangerous in DANGEROUS_COMMANDS:
                            if dangerous.lower() in command.lower():
                                print(f"{Fore.RED}BLOCKED{Style.RESET_ALL}")
                                result = {"success": False, "error": f"Blocked: {dangerous}"}
                                results.append(result)
                                continue
                    result = self.tools.run_command({'content': command, 'shell': step.get('shell', 'cmd'), 'encoding': step.get('encoding') or SYSTEM_ENCODING})
                    if result.get('success') and self.telemetry:
                        self.telemetry.track_interface_preference(is_gui=False)
                elif step_type == 'gui':
                    if not self.gui_bridge or not self.gui_bridge.is_available():
                        print(f"{Fore.YELLOW}SKIPPED (GUI not available){Style.RESET_ALL}")
                        result = {"success": False, "error": "GUI not available"}
                    else:
                        action = step.get('action', 'click')
                        target = step.get('target', '')
                        max_gui_retries = 2
                        gui_retry = 0
                        while gui_retry <= max_gui_retries:
                            if action == 'click' and target:
                                result = self.gui_bridge.find_and_click(target)
                            elif action == 'type':
                                result = self.gui_bridge.execute_action({'action': 'type', 'text': step.get('text', ''), 'wait_after': step.get('wait_after', 1)})
                            elif action == 'press':
                                result = self.gui_bridge.execute_action({'action': 'press', 'key': step.get('key', 'enter'), 'wait_after': step.get('wait_after', 1)})
                            else:
                                result = self.gui_bridge.execute_action(step)
                            if result.get('success'):
                                if self.telemetry:
                                    self.telemetry.track_interface_preference(is_gui=True)
                                break
                            if gui_retry < max_gui_retries:
                                print(f"{Fore.YELLOW}Retry {gui_retry+1}/{max_gui_retries}...{Style.RESET_ALL}")
                                time.sleep(1)
                                gui_retry += 1
                            else:
                                break
                else:
                    result = {"success": False, "error": f"Unknown step type: {step_type}"}
                if result.get('success'):
                    print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}FAILED: {result.get('error', 'Unknown')}{Style.RESET_ALL}")
                results.append(result)
                self._task_context.update(step, result)
                wait_time = step.get('wait_after', 1)
                time.sleep(wait_time)
            except Exception as e:
                print(f"{Fore.RED}ERROR: {e}{Style.RESET_ALL}")
                result = {"success": False, "error": str(e)}
                results.append(result)
                self._task_context.update(step, result)
        success_count = sum(1 for r in results if r.get('success'))
        total = len(results)
        if success_count < total and total > 0:
            print(f"\n{Fore.YELLOW}Some steps failed. Asking AI for recovery plan...{Style.RESET_ALL}")
            try:
                failed_steps = [s for s, r in zip(plan['steps'], results) if not r.get('success')]
                recovery_prompt = f"These GUI/terminal steps failed: {json.dumps(failed_steps, ensure_ascii=False)}. Suggest alternative approach in 1 sentence."
                recovery = self.model.generate_content(recovery_prompt)
                print(f"{Fore.CYAN}AI Suggestion: {recovery.text[:200]}{Style.RESET_ALL}")
            except:
                pass
        print(f"\n{Fore.CYAN}Plan completed: {success_count}/{total} steps successful{Style.RESET_ALL}")
        self._task_context.clear()
        return {"success": success_count == total, "results": results, "success_count": success_count, "total": total}
    
    def _create_model(self):
        if self.offline_mode:
            return None
        mode_config = ModeManager.get_mode_config(self.current_mode)
        temperature = mode_config["temperature"]
        if self.current_mode == "lightning":
            temperature = 0.0
        return genai.GenerativeModel(mode_config["model"], generation_config={"temperature": temperature})
    
    def switch_to_offline(self):
        print(f"\n{Fore.CYAN}Switching to OFFLINE mode...{Style.RESET_ALL}")
        if self.offline_model is None:
            self.offline_model = OfflineModelManager()
        if not self.offline_model.is_ready:
            if not self.offline_model.load_model():
                print(f"{Fore.RED}Failed to load offline model{Style.RESET_ALL}")
                return False
        self.offline_mode = True
        self.memory.set_offline_mode(True)
        if self.telemetry:
            self.telemetry.track_model_usage(True)
        print(f"\n{Fore.GREEN}OFFLINE mode activated{Style.RESET_ALL}")
        print(f"{Fore.CYAN}All operations will use local AI model{Style.RESET_ALL}")
        return True
    
    def switch_to_online(self):
        self.offline_mode = False
        self.memory.set_offline_mode(False)
        self.model = self._create_model()
        if self.telemetry:
            self.telemetry.track_model_usage(False)
        print(f"\n{Fore.GREEN}ONLINE mode activated{Style.RESET_ALL}")
        return True
    
    def switch_mode(self, new_mode, permanent=True):
        if not ModeManager.is_valid_mode(new_mode):
            return False
        if permanent:
            self.current_mode = new_mode
            self.memory.set_mode(new_mode)
            if not self.offline_mode:
                self.model = self._create_model()
            if self.telemetry:
                self.telemetry.track_mode_preference(new_mode)
        else:
            self.temp_mode = new_mode
        return True
    
    def toggle_thinking(self):
        self.thinking_enabled = not self.thinking_enabled
        self.memory.set_thinking(self.thinking_enabled)
        return self.thinking_enabled
    
    def _get_active_mode(self):
        return self.temp_mode if self.temp_mode else self.current_mode
    
    def _build_context(self):
        try:
            import psutil
            ctx = {
                "os": platform.system(),
                "os_version": platform.version(),
                "python": platform.python_version(),
                "hostname": platform.node(),
                "cwd": os.getcwd(),
                "desktop": os.path.join(os.path.expanduser('~'), 'Desktop'),
                "documents": os.path.join(os.path.expanduser('~'), 'Documents'),
                "cpu_cores": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "username": os.getenv('USERNAME') or os.getenv('USER') or 'User',
                "available_shells": self._detect_shells()
            }
        except:
            ctx = {
                "os": platform.system(),
                "python": platform.python_version(),
                "cwd": os.getcwd(),
                "desktop": os.path.join(os.path.expanduser('~'), 'Desktop'),
                "documents": os.path.join(os.path.expanduser('~'), 'Documents'),
                "username": os.getenv('USERNAME') or os.getenv('USER') or 'User',
                "available_shells": self._detect_shells()
            }
        return ctx
    
    def _detect_shells(self):
        shells = []
        if os.name == 'nt':
            shells.extend(['cmd', 'powershell'])
            if subprocess.run(['where', 'pwsh'], capture_output=True, shell=True).returncode == 0:
                shells.append('pwsh')
            for path in GIT_BASH_PATHS:
                if os.path.exists(path):
                    shells.append('git-bash')
                    break
            if subprocess.run(['where', 'wsl'], capture_output=True, shell=True).returncode == 0:
                shells.append('wsl')
            if any(os.path.exists(p) for p in CYGWIN_PATHS):
                shells.append('cygwin')
        else:
            shells.extend(['bash', 'sh'])
            shells_to_check = ['zsh', 'fish', 'ksh', 'tcsh', 'dash']
            for shell in shells_to_check:
                try:
                    if subprocess.run(['which', shell], capture_output=True, shell=True).returncode == 0:
                        shells.append(shell)
                except:
                    pass
        return shells

    
    def think_and_act(self, user_message, retry_context=None, force_execute=False, safe_mode=False, show_only=False, retry_count=0):
        if self.temp_mode and not retry_context:
            self.temp_mode = None
        if retry_context is None:
            self.memory.add_conversation("user", user_message)
        if retry_context:
            retry_prompt = f'''
ERROR IN PREVIOUS ATTEMPT - REPLANNING REQUIRED
User Request: {user_message}
Failed Action:
- Type: {retry_context['action_type']}
- Description: {retry_context['description']}
- Shell: {retry_context.get('shell', 'Not specified')}
- Error Message: {retry_context['error']}
- Attempt: {retry_context['retry_count']}/{self.max_retries}
YOUR TASK NOW:
1. ANALYZE ERROR IN DETAIL
2. FIND A COMPLETELY DIFFERENT METHOD
3. CREATE NEW PLAN
REMEMBER: System has {len(self.context['available_shells'])} different shells: {', '.join(self.context['available_shells'])}
'''
            system_instruction = self._build_system_instruction(retry_prompt, safe_mode)
        else:
            system_instruction = self._build_system_instruction(user_message, safe_mode)
        try:
            if self.offline_mode:
                active_mode = self._get_active_mode()
                mode_config = ModeManager.get_mode_config(active_mode)
                mode_temperature = mode_config.get("temperature", 0.7)
                if mode_temperature <= 0.0:
                    mode_temperature = 0.1
                response_text = self.offline_model.generate(system_instruction, max_length=1024, temperature=mode_temperature)
            else:
                response = self.model.generate_content(system_instruction)
                response_text = response.text
            return self._process_ai_response(response_text, user_message, retry_count=retry_count, force_execute=force_execute, safe_mode=safe_mode, show_only=show_only)
        except Exception as e:
            return self._handle_error(e, user_message)
        finally:
            if self.telemetry and retry_count == 0:
                active_mode = self._get_active_mode()
                self.telemetry.track_mode_preference(active_mode)
                self.telemetry.track_model_usage(self.offline_mode)
                self.telemetry.track_thinking_usage(self.thinking_enabled)
    
    def _build_system_instruction(self, main_content, safe_mode=False):
        if self.offline_mode:
            if self.thinking_enabled:
                return f'''You are a command line tool.
First, analyze the user request inside <thinking> tags.
Then, output valid JSON for the action.
Example:
User: list files
Output:
<thinking>
User wants to see files in the current directory.
This is a safe read-only operation.
I will use the 'dir' command for Windows.
</thinking>
{{"understanding": "list files", "actions": [{{"type": "command", "description": "list files", "details": {{"shell": "cmd", "content": "dir"}}}}], "response": "Listing files."}}
Current Task:
User: {main_content}
Output:'''
            return f'''You are a command line tool. Output valid JSON only.
Example 1:
User: list files
JSON: {{"understanding": "list files", "actions": [{{"type": "command", "description": "list files", "details": {{"shell": "cmd", "content": "dir"}}}}], "response": "Listing files."}}
Example 2 (Turkish):
User: masaustu ne notlar.txt olustur
JSON: {{"understanding": "create file", "actions": [{{"type": "file", "description": "create file", "details": {{"path": "Desktop/notlar.txt", "content": "", "encoding": "utf-8"}}}}], "response": "Dosya olusturuldu."}}
Current Task:
User: {main_content}
JSON:'''
        active_mode = self._get_active_mode()
        mode_config = ModeManager.get_mode_config(active_mode)
        mode_modifier = mode_config["instruction_modifier"]
        safe_mode_text = ""
        if safe_mode:
            safe_mode_text = f'''
SAFE MODE IS ACTIVE:
CRITICAL RESTRICTIONS - These commands are STRICTLY FORBIDDEN:
{', '.join(DANGEROUS_COMMANDS)}
YOU MUST:
- Reject any dangerous/destructive commands
- Refuse system-critical operations (reboot, shutdown, format, etc.)
- Block recursive deletions and mass file operations
- Prevent privilege escalation attempts
If user requests dangerous action, respond with: {{"understanding":"Dangerous request","actions":[],"response":"BLOCKED: This operation is dangerous and blocked by safe mode"}}
'''
        thinking_instruction = ""
        if self.thinking_enabled:
            thinking_instruction = '''
THINKING MODE IS ENABLED:
Before creating your JSON response, you MUST perform detailed analysis inside <thinking> tags:
<thinking>
1. User Intent Analysis
2. Security Assessment
3. Method Selection
4. Shell Selection
5. Potential Issues
6. Alternative Approaches
</thinking>
'''
        recent_history = self.memory.get_recent_history()
        history_text = self._format_history(recent_history)
        
        p2p_context = ""
        if self._p2p_sharing and self._p2p_sharing.is_connected:
            p2p_info = self._p2p_sharing.get_p2p_context()
            role = "HOST" if p2p_info.get('is_host') else "HELPER"
            users = p2p_info.get('connected_users', [])
            p2p_context = f"""
P2P SHARING ACTIVE:
- Role: {role}
- Your Name: {p2p_info.get('my_name', 'Unknown')}
- Connected Users: {', '.join(users)}
- Pending Commands: {p2p_info.get('pending_commands', 0)}
- Pending Files: {p2p_info.get('pending_files', 0)}
NOTE: You are in a collaborative session. Commands will be visible to team members.
"""
        
        return f'''You are ZAI, a COMPLETELY FREE artificial intelligence assistant.
CURRENT MODE: {active_mode.upper()}{' (OFFLINE)' if self.offline_mode else ''}
{mode_modifier}
{safe_mode_text}
{p2p_context}
SYSTEM INFORMATION:
- Operating System: {self.context['os']}
- Python: {self.context['python']}
- Available Shells: {', '.join(self.context['available_shells'])}
- User: {self.context['username']}
- Working Directory: {self.context['cwd']}
- Desktop: {self.context['desktop']}
- Documents: {self.context['documents']}
{thinking_instruction}
YOUR CAPABILITIES:
1. FILE/DIRECTORY OPERATIONS
2. SYSTEM COMMANDS - FULL SHELL FREEDOM
3. CODE WRITING
4. INFORMATION GATHERING
5. MULTI-TASKING
RESPONSE FORMAT (JSON):
{{
    "understanding": "User request in ONE SENTENCE",
    "actions": [
        {{
            "type": "file|command|code|info|multi",
            "description": "What will be done",
            "details": {{
                "path": "file/path (if applicable)",
                "content": "content/command",
                "shell": "cmd|powershell|pwsh|bash|sh",
                "language": "code language (if applicable)",
                "encoding": "REQUIRED! Choose the best encoding for the task",
                "mode": "binary|text (if applicable)"
            }}
        }}
    ],
    "response": "Natural language response to user"
}}
ENCODING RULE: You MUST always specify encoding! Use 'utf-8' for text files. For shell commands, use '{SYSTEM_ENCODING}' or 'utf-8'. NEVER output 'system' as the encoding string.
CONVERSATION HISTORY:
{history_text}
CURRENT TASK:
{main_content}
START!'''
    
    def _format_history(self, history):
        if not history:
            return "First conversation"
        formatted = []
        for msg in history:
            role = "User" if msg['role'] == 'user' else "ZAI"
            formatted.append(f"{role}: {msg['message'][:100]}...")
        return "\n".join(formatted)

    
    def _process_ai_response(self, ai_text, original_request, retry_count=0, force_execute=False, safe_mode=False, show_only=False):
        try:
            if "<thinking>" in ai_text and "</thinking>" in ai_text:
                thinking_start = ai_text.find("<thinking>") + 10
                thinking_end = ai_text.find("</thinking>")
                thinking_content = ai_text[thinking_start:thinking_end].strip()
                print(f"\n{Fore.CYAN}Thinking Process:{Style.RESET_ALL}")
                print(f"{Fore.WHITE}{thinking_content}{Style.RESET_ALL}\n")
            json_start = ai_text.find('{')
            json_end = ai_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = ai_text[json_start:json_end]
                ai_plan = json.loads(json_str)
                if retry_count == 0:
                    understanding = ai_plan.get('understanding', 'Analyzing...')
                    print(f"\n{Fore.CYAN}Understanding: {understanding}{Style.RESET_ALL}")
                actions = ai_plan.get('actions', [])
                if show_only:
                    self._show_actions_preview(actions, ai_plan.get('response', ''))
                    return {"success": True, "message": "Preview only - no actions executed"}
                if safe_mode and actions:
                    blocked = self._check_dangerous_commands(actions)
                    if blocked:
                        print(f"\n{Fore.RED}BLOCKED by safe mode: {blocked}{Style.RESET_ALL}")
                        if self.telemetry:
                            self.telemetry.track_safe_mode_block(blocked)
                        return {"success": False, "message": f"Blocked: {blocked}"}
                if actions and not force_execute:
                    if not self._confirm_actions(actions, user_request=original_request, retry_count=retry_count):
                        print(f"\n{Fore.YELLOW}Actions cancelled by user{Style.RESET_ALL}")
                        return {"success": False, "message": "Cancelled by user"}
                results = []
                if actions:
                    print(f"{Fore.YELLOW}Executing {len(actions)} action(s)...{Style.RESET_ALL}\n")
                    for i, action in enumerate(actions, 1):
                        result = self._execute_action(action, i, len(actions), user_request=original_request, retry_count=retry_count)
                        results.append(result)
                        if not result.get('success') and retry_count < self.max_retries:
                            print(f"\n{Fore.YELLOW}Error detected, trying alternative method ({retry_count + 1}/{self.max_retries})...{Style.RESET_ALL}")
                            if self.telemetry:
                                self.telemetry.track_auto_retry(retry_count + 1, self.max_retries, False)
                            retry_context = {
                                'action_type': action.get('type', 'unknown'),
                                'description': action.get('description', 'Action'),
                                'shell': action.get('details', {}).get('shell', 'Not specified'),
                                'error': result.get('error', 'Unknown error'),
                                'retry_count': retry_count + 1
                            }
                            return self.think_and_act(original_request, retry_context, force_execute=force_execute, safe_mode=safe_mode, show_only=show_only, retry_count=retry_count + 1)
                        elif not result.get('success') and retry_count >= self.max_retries:
                            print(f"\n{Fore.RED}Max retry limit ({self.max_retries}) reached. Stopping.{Style.RESET_ALL}")
                            if self.telemetry:
                                self.telemetry.track_task_failure(True)
                                self.telemetry.track_auto_retry(retry_count, self.max_retries, False)
                            break
                        time.sleep(0.1)
                success_count = sum(1 for r in results if r.get('success'))
                fail_count = len(results) - success_count
                self.memory.update_stats(successful=success_count, failed=fail_count)
                needs_final_response = any(r.get('success') and r.get('output') for r in results)
                if needs_final_response:
                    final_response = self._generate_final_response(original_request, results)
                    print(f"\n{Fore.GREEN}ZAI: {final_response}{Style.RESET_ALL}")
                    response = final_response
                else:
                    response = ai_plan.get('response', 'Operation completed!')
                    print(f"\n{Fore.GREEN}ZAI: {response}{Style.RESET_ALL}")
                if self._p2p_sharing and self._p2p_sharing.is_connected and self._p2p_sharing.is_host:
                    self._p2p_sharing.broadcast_output(f"ZAI: {response[:400]}")
                if results:
                    color = Fore.GREEN if success_count == len(results) else Fore.YELLOW
                    print(f"{color}Result: {success_count}/{len(results)} successful{Style.RESET_ALL}")
                if retry_count > 0 and success_count == len(results) and self.telemetry:
                    self.telemetry.track_auto_retry(retry_count, self.max_retries, True)
                if retry_count == 0 or not any(not r.get('success') for r in results):
                    self.memory.add_conversation("assistant", response)
                return {"success": True, "results": results}
            else:
                print(f"\n{Fore.CYAN}ZAI: {ai_text}{Style.RESET_ALL}")
                self.memory.add_conversation("assistant", ai_text)
                if self._p2p_sharing and self._p2p_sharing.is_connected and self._p2p_sharing.is_host:
                    self._p2p_sharing.broadcast_output(f"ZAI: {ai_text[:400]}")
                return {"success": True, "message": ai_text}
        except json.JSONDecodeError:
            print(f"\n{Fore.YELLOW}ZAI: {ai_text[:500]}{Style.RESET_ALL}")
            return {"success": True, "message": ai_text}
        except Exception as e:
            return self._handle_error(e, original_request)
    
    def _check_dangerous_commands(self, actions):
        import unicodedata
        
        def normalize_command(cmd):
            normalized = ''.join(
                c for c in cmd 
                if unicodedata.category(c) not in ('Cf', 'Mn', 'Mc', 'Me')
            )
            ascii_map = {
                'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'х': 'x',
                'А': 'A', 'Е': 'E', 'О': 'O', 'Р': 'P', 'С': 'C', 'Х': 'X',
                'м': 'm', 'М': 'M', 'і': 'i', 'І': 'I',
            }
            for cyrillic, latin in ascii_map.items():
                normalized = normalized.replace(cyrillic, latin)
            normalized = ' '.join(normalized.split())
            return normalized
        
        def check_single_content(content, source_type="command"):
            original = content
            content = normalize_command(content)
            content_lower = content.lower()
            
            for dangerous in DANGEROUS_COMMANDS:
                if dangerous.lower() in content_lower:
                    return f"Dangerous {source_type} detected: {dangerous}"
            
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    return f"Dangerous pattern detected: {pattern[:30]}..."
            
            return None
        
        for action in actions:
            action_type = action.get('type', '')
            details = action.get('details', {})
            
            if action_type == 'command':
                content = details.get('content', '')
                result = check_single_content(content, "command")
                if result:
                    return result
            
            elif action_type in ('file', 'code'):
                path = details.get('path', '')
                file_content = details.get('content', '')
                
                path_result = self._check_dangerous_path(path)
                if path_result:
                    return path_result
                
                if path.lower().endswith(('.bat', '.cmd', '.ps1', '.sh', '.bash')):
                    result = check_single_content(file_content, "script content")
                    if result:
                        return result
            
            elif action_type == 'multi':
                tasks = details.get('tasks', [])
                for task in tasks:
                    task_type = task.get('type', '')
                    task_details = task.get('details', task)
                    if task_type == 'command':
                        result = check_single_content(task_details.get('content', ''), "command")
                        if result:
                            return result
        
        return None
    
    def _check_dangerous_path(self, path):
        if not path:
            return None
        
        dangerous_patterns = ['..', '\\..', '/..']
        for pattern in dangerous_patterns:
            if pattern in path:
                return f"Path traversal detected: {pattern}"
        
        system_paths = [
            'windows\\system32', 'windows/system32',
            'system32\\drivers', 'system32/drivers',
            '/etc/passwd', '/etc/shadow', '/etc/hosts',
            'c:\\windows', 'c:/windows',
            '/dev/', '/proc/', '/sys/',
        ]
        path_lower = path.lower()
        for sys_path in system_paths:
            if sys_path in path_lower:
                return f"System path access blocked: {sys_path}"
        
        if path.startswith('\\\\') or path.startswith('//'):
            return "UNC path blocked for security"
        
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 
                         'COM1', 'COM2', 'COM3', 'COM4',
                         'LPT1', 'LPT2', 'LPT3', 'LPT4']
        basename = os.path.basename(path).upper().split('.')[0]
        if basename in reserved_names:
            return f"Reserved filename blocked: {basename}"
        
        return None
    
    def _show_actions_preview(self, actions, response):
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ACTION PREVIEW (--show mode){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            description = action.get('description', 'No description')
            details = action.get('details', {})
            print(f"{Fore.GREEN}[{i}] {action_type.upper()}: {description}{Style.RESET_ALL}")
            if action_type == 'file':
                print(f"    Path: {details.get('path', 'N/A')}")
                print(f"    Encoding: {details.get('encoding', 'utf-8')}")
            elif action_type == 'command':
                print(f"    Shell: {details.get('shell', 'N/A')}")
                print(f"    Command: {Fore.YELLOW}{details.get('content', 'N/A')}{Style.RESET_ALL}")
            elif action_type == 'code':
                print(f"    Language: {details.get('language', 'N/A')}")
                print(f"    Path: {details.get('path', 'N/A')}")
            print()
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Expected Response:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}No actions were executed (--show mode){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    def _confirm_actions(self, actions, user_request="", retry_count=0):
        print(f"\n{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.RED}ACTION CONFIRMATION REQUIRED{Style.RESET_ALL}")
        print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}\n")
        
        sentinel_warnings = []
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            description = action.get('description', 'No description')
            details = action.get('details', {})
            
            if self._sentinel.is_enabled:
                verdict = self._sentinel.evaluate_action(
                    action_type=action_type,
                    details=details,
                    user_request=user_request,
                    retry_count=retry_count
                )
                if verdict.should_warn_user:
                    sentinel_warnings.append((i, verdict))
            
            print(f"{Fore.YELLOW}[{i}] Type: {action_type.upper()}{Style.RESET_ALL}")
            print(f"    Description: {description}")
            if action_type == 'file':
                print(f"    Path: {details.get('path', 'N/A')}")
                content_preview = str(details.get('content', ''))[:100]
                print(f"    Content: {content_preview}...")
            elif action_type == 'command':
                print(f"    Shell: {details.get('shell', 'N/A')}")
                print(f"    Command: {details.get('content', 'N/A')}")
            elif action_type == 'code':
                print(f"    Language: {details.get('language', 'N/A')}")
                print(f"    Path: {details.get('path', 'N/A')}")
            print()
        
        if sentinel_warnings:
            print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.RED}🛡️ SENTINEL 1.5 WARNINGS{Style.RESET_ALL}")
            print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
            for action_idx, verdict in sentinel_warnings:
                self._sentinel.log_warning(actions[action_idx-1].get('type', 'unknown'), 
                                          actions[action_idx-1].get('details', {}), verdict)
                if verdict.sentinel_recommends_stop:
                    print(f"\n{Fore.RED}[Action {action_idx}] SENTINEL WARNING - RECOMMENDS STOPPING{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.YELLOW}[Action {action_idx}] SENTINEL WARNING{Style.RESET_ALL}")
                
                color = Fore.RED if verdict.sentinel_recommends_stop else Fore.YELLOW
                print(f"  {color}Threat Level: {verdict.threat_level.name}{Style.RESET_ALL}")
                
                if verdict.risk_breakdown:
                    rb = verdict.risk_breakdown
                    if rb.total_score > 0:
                        print(f"  {Fore.CYAN}Risk Breakdown:{Style.RESET_ALL}")
                        if rb.structural_score > 0:
                            print(f"    {Fore.WHITE}Structural: {rb.structural_score} - {'; '.join(rb.structural_reasons)}{Style.RESET_ALL}")
                        if rb.behavioral_score > 0:
                            print(f"    {Fore.WHITE}Behavioral: {rb.behavioral_score} - {'; '.join(rb.behavioral_reasons)}{Style.RESET_ALL}")
                        if rb.contextual_score > 0:
                            print(f"    {Fore.WHITE}Contextual: {rb.contextual_score} - {'; '.join(rb.contextual_reasons)}{Style.RESET_ALL}")
                        if rb.intent_score > 0:
                            print(f"    {Fore.WHITE}Intent: {rb.intent_score} - {'; '.join(rb.intent_reasons)}{Style.RESET_ALL}")
                        print(f"    {Fore.MAGENTA}Total Risk: {rb.total_score}/100{Style.RESET_ALL}")
                        if rb.is_accumulated:
                            print(f"    {Fore.RED}⚠️ Risk is accumulated, not sudden.{Style.RESET_ALL}")
                
                if verdict.lessons_applied:
                    print(f"  {Fore.CYAN}Past Lessons:{Style.RESET_ALL}")
                    for lesson in verdict.lessons_applied:
                        print(f"    {Fore.WHITE}📚 {lesson.trigger} → {lesson.consequence} ({lesson.times_seen}x){Style.RESET_ALL}")
                
                if verdict.recommendation:
                    print(f"  {Fore.GREEN}→ {verdict.recommendation}{Style.RESET_ALL}")
            print()
        
        print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
        while True:
            response = input(f"{Fore.YELLOW}Execute these actions? (Y/N): {Style.RESET_ALL}").strip().upper()
            if response in ['Y', 'YES']:
                return True
            elif response in ['N', 'NO']:
                return False
            else:
                print(f"{Fore.RED}Please enter Y or N{Style.RESET_ALL}")
    
    def _execute_action(self, action, index, total, user_request="", retry_count=0):
        action_type = action.get('type', 'unknown')
        description = action.get('description', 'Processing')
        details = action.get('details', {})
        shell_info = details.get('shell', '')
        
        if shell_info:
            print(f"{Fore.BLUE}[{index}/{total}] [{shell_info}] {description}...{Style.RESET_ALL}", end=' ')
        else:
            print(f"{Fore.BLUE}[{index}/{total}] {description}...{Style.RESET_ALL}", end=' ')
        try:
            if action_type == 'file':
                result = self.tools.handle_file(details)
            elif action_type == 'command':
                result = self.tools.run_command(details)
                if result.get('success') and self.telemetry:
                    self.telemetry.track_interface_preference(is_gui=False)
            elif action_type == 'code':
                result = self.tools.create_code(details)
            elif action_type == 'info':
                result = self.tools.gather_info(details)
            elif action_type == 'multi':
                result = self.tools.multi_task(details)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            if self._sentinel.is_enabled:
                self._sentinel.record_behavior(
                    action_type=action_type,
                    details=details,
                    success=result.get('success', False),
                    error_message=result.get('error'),
                    retry_attempt=retry_count
                )
            
            if result.get('success'):
                print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"{Fore.RED}FAIL{Style.RESET_ALL}")
                if error_msg and len(error_msg) > 50:
                    print(f"  {Fore.RED}{error_msg[:200]}...{Style.RESET_ALL}")
                else:
                    print(f"  {Fore.RED}{error_msg}{Style.RESET_ALL}")
            return result
        except Exception as e:
            error_str = str(e)
            if self._sentinel.is_enabled:
                self._sentinel.record_behavior(
                    action_type=action_type,
                    details=details,
                    success=False,
                    error_message=error_str,
                    retry_attempt=retry_count
                )
            print(f"{Fore.RED}FAIL{Style.RESET_ALL}")
            print(f"  {Fore.RED}{error_str[:200]}{Style.RESET_ALL}")
            return {"success": False, "error": error_str}
    
    def _handle_error(self, error, request):
        error_msg = str(error)
        print(f"\n{Fore.RED}An issue occurred: {error_msg[:200]}{Style.RESET_ALL}")
        return {"success": False, "error": error_msg}
    
    def _generate_final_response(self, original_request, results):
        try:
            outputs = []
            for result in results:
                if result.get('success'):
                    if result.get('output'):
                        outputs.append(result['output'])
                    elif result.get('info'):
                        outputs.append(str(result['info']))
            if not outputs:
                return "Operation completed successfully!"
            if self.offline_mode:
                return outputs[0] if outputs else "Operation completed!"
            prompt = f'''User's question: {original_request}
Operation outputs:
{chr(10).join(outputs)}
Using the outputs above, respond to the user in NATURAL LANGUAGE.
Only write the response text, nothing else. No JSON, no explanation, just the response.'''
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return outputs[0] if outputs else "Operation completed!"


class ZAIShell:
    """Main shell interface v8.0 - E2E Encryption"""
    
    def __init__(self):
        self.memory = ChromaMemoryManager()
        self.telemetry = TelemetryManager(self.memory.json_manager)
        self.brain = AIBrain(self.memory, self.telemetry)
        self.start_time = datetime.datetime.now()
        self.request_count = 0
        if self.telemetry.is_enabled():
            shells = self.brain.context.get('available_shells', [])
            primary_shell = shells[0] if shells else "unknown"
            self.telemetry.track_session_start(
                self.brain.current_mode,
                self.brain.offline_mode,
                self.brain.gui_enabled,
                self.brain.research_enabled,
                primary_shell
            )
    
    def show_banner(self):
        ctx = self.brain.context
        shells = ', '.join(ctx['available_shells'])
        mode = self.brain.current_mode
        mode_config = ModeManager.get_mode_config(mode)
        thinking = "ON" if self.brain.thinking_enabled else "OFF"
        offline = "OFFLINE" if self.brain.offline_mode else "ONLINE"
        user_name = self.memory.memory["user"]["name"]
        first_seen = self.memory.memory["user"]["first_seen"][:10]
        stats = self.memory.memory["stats"]
        memory_type = "ChromaDB" if hasattr(self.memory, 'use_chromadb') and self.memory.use_chromadb else "JSON"
        gui_status = "ON" if self.brain.gui_enabled else "OFF"
        research_status = "ON" if self.brain.research_enabled else "OFF"
        sharing_line = ""
        if self.brain._p2p_sharing and self.brain._p2p_sharing.is_connected:
            code = self.brain._p2p_sharing.share_code
            sharing_line = f"\n{Fore.MAGENTA}Terminal Sharing: ACTIVE ({code}){Style.RESET_ALL}"
        encryption_status = "OFF"
        if self.brain._p2p_sharing and self.brain._p2p_sharing.encryption_enabled:
            encryption_status = "ON"
        sentinel_status = "ON" if self.brain.sentinel.is_enabled else "OFF"
        lessons_count = len(self.brain.sentinel.lesson_memory.lessons)
        print(f"""
{Fore.CYAN}========================================================
          ZAI v9.0.2 - Advanced AI Shell + SENTINEL 1.5
   Terminal | GUI | Research | P2P | E2E | Self-Preserve
========================================================{Style.RESET_ALL}

{Fore.GREEN}I understand natural language in ANY language{Style.RESET_ALL}
{Fore.GREEN}Auto-retry with different methods on errors{Style.RESET_ALL}
{Fore.GREEN}SENTINEL 1.5: Observes, understands, explains - but never judges{Style.RESET_ALL}
{Fore.CYAN}Shells: {shells}{Style.RESET_ALL}

{Fore.BLUE}Thinking: {thinking} | Network: {offline} | Memory: {memory_type}{Style.RESET_ALL}
{Fore.BLUE}GUI: {gui_status} | Research: {research_status} | Sentinel: {sentinel_status}{Style.RESET_ALL}{sharing_line}

{Fore.YELLOW}User: {user_name} (since {first_seen}){Style.RESET_ALL}
{Fore.YELLOW}Stats: {stats['total_requests']} requests | {stats['successful_actions']} success | {stats['failed_actions']} failed{Style.RESET_ALL}
{Fore.YELLOW}Mode: {mode.upper()} - {mode_config['description']}{Style.RESET_ALL}

{Fore.BLUE}Commands:{Style.RESET_ALL}
  {Fore.CYAN}Features:{Style.RESET_ALL} gui on/off, research on/off
  {Fore.CYAN}Modes:{Style.RESET_ALL} normal, eco, lightning
  {Fore.CYAN}Network:{Style.RESET_ALL} switch offline, switch online
  {Fore.CYAN}Thinking:{Style.RESET_ALL} thinking on/off
  {Fore.CYAN}Sharing:{Style.RESET_ALL} share, share connect IP:PORT, share end
  {Fore.CYAN}Memory:{Style.RESET_ALL} memory clear/show/search [query]
  {Fore.CYAN}Sentinel:{Style.RESET_ALL} sentinel on/off/status/reset
  {Fore.CYAN}Safety:{Style.RESET_ALL} --safe, --show, --force
  {Fore.CYAN}Other:{Style.RESET_ALL} clear, exit

{Fore.MAGENTA}Just tell me what you need - I'll figure out how!{Style.RESET_ALL}
{Fore.WHITE}{'=' * 60}{Style.RESET_ALL}
""")
    
    def handle_share_command(self, user_input: str) -> bool:
        parts = user_input.split()
        if len(parts) == 1:
            self._show_share_help()
            return True
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            if subcommand == 'start':
                no_ai = '--no-ai' in user_input.lower()
                remaining_parts = [p for p in parts[2:] if p.lower() != '--no-ai']
                port = int(remaining_parts[0]) if remaining_parts and remaining_parts[0].isdigit() else None
                self.brain.p2p_sharing.start_sharing_session(port, no_ai=no_ai)
                return True
            elif subcommand == 'encrypt':
                if len(parts) >= 4 and parts[2].lower() == 'key':
                    full_key = ' '.join(parts[3:])
                    self.brain.p2p_sharing.enable_encryption(f'key:{full_key}')
                elif len(parts) >= 3:
                    mode = parts[2]
                    self.brain.p2p_sharing.enable_encryption(mode)
                else:
                    self.brain.p2p_sharing.enable_encryption(None)
                return True
            elif subcommand == 'name' and len(parts) >= 3:
                new_name = ' '.join(parts[2:])
                self.brain.p2p_sharing.set_name(new_name)
                return True
            elif subcommand == 'name':
                current = self.brain.p2p_sharing.my_name or "Not set"
                print(f"{Fore.CYAN}Current name: {Fore.YELLOW}{current}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Change with: share name <newname>{Style.RESET_ALL}")
                return True
            elif subcommand == 'connect' and len(parts) >= 3:
                connection_string = parts[2]
                result = self.brain.p2p_sharing.connect_to_session(connection_string)
                if not result.get('success'):
                    print(f"{Fore.RED}Connection failed: {result.get('error')}{Style.RESET_ALL}")
                return True
            elif subcommand == 'message' and len(parts) >= 3:
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                message_text = ' '.join(parts[2:])
                self.brain.p2p_sharing.send_message(message_text)
                return True
            elif subcommand == 'chat':
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                self.brain.p2p_sharing.show_chat_history()
                return True
            elif subcommand == 'send' and len(parts) >= 3:
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                if self.brain.p2p_sharing.is_host:
                    print(f"{Fore.YELLOW}Only helpers can send commands{Style.RESET_ALL}")
                    return True
                command_text = ' '.join(parts[2:])
                self.brain.p2p_sharing.send_command(command_text)
                return True
            elif subcommand == 'file' and len(parts) >= 3:
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                file_path = parts[2]
                target_user = parts[3] if len(parts) >= 4 else None
                result = self.brain.p2p_sharing.send_file(file_path, target_user)
                if not result.get('success'):
                    print(f"{Fore.RED}File send failed: {result.get('error')}{Style.RESET_ALL}")
                return True
            elif subcommand == 'accept':
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                save_path = parts[2] if len(parts) >= 3 else None
                result = self.brain.p2p_sharing.accept_file(save_path)
                if not result.get('success'):
                    print(f"{Fore.RED}{result.get('error')}{Style.RESET_ALL}")
                return True
            elif subcommand == 'deny':
                if not self.brain.p2p_sharing.is_connected:
                    print(f"{Fore.YELLOW}Not connected to any session{Style.RESET_ALL}")
                    return True
                self.brain.p2p_sharing.deny_file()
                return True
            elif subcommand == 'end':
                self.brain.p2p_sharing.end_session()
                return True
            elif subcommand == 'status':
                if self.brain.p2p_sharing.is_connected:
                    role = "HOST" if self.brain.p2p_sharing.is_host else "HELPER"
                    users = self.brain.p2p_sharing.get_connected_users()
                    print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}SHARING STATUS{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}Role: {role}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Your Name: {self.brain.p2p_sharing.my_name}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Address: {self.brain.p2p_sharing.share_code}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Connected Users: {', '.join(users)}{Style.RESET_ALL}")
                    if self.brain.p2p_sharing.is_host:
                        pending_cmds = self.brain.p2p_sharing.get_pending_count()
                        pending_files = self.brain.p2p_sharing.get_pending_files_count()
                        with self.brain.p2p_sharing.client_lock:
                            connected = len(self.brain.p2p_sharing.clients)
                        print(f"{Fore.CYAN}Helpers Connected: {connected}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Pending Commands: {pending_cmds}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Pending Files: {pending_files}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.YELLOW}Not connected to any sharing session{Style.RESET_ALL}")
                return True
            elif subcommand == 'logs':
                self.brain.p2p_sharing.show_recent_logs()
                return True
            elif subcommand == 'list':
                if self.brain.p2p_sharing.is_host:
                    self.brain.p2p_sharing.list_clients()
                else:
                    users = self.brain.p2p_sharing.get_connected_users()
                    print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}CONNECTED USERS{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                    for i, user in enumerate(users):
                        marker = " (Host)" if i == 0 else (" (You)" if user == self.brain.p2p_sharing.my_name else "")
                        print(f"  {Fore.GREEN}{i+1}. {user}{marker}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
                return True
            elif subcommand == 'approve':
                if self.brain.p2p_sharing.is_host:
                    cmd = self.brain.p2p_sharing.approve_pending(True)
                    if cmd:
                        print(f"{Fore.GREEN}Executing: {cmd}{Style.RESET_ALL}")
                        if self.brain.p2p_sharing.no_ai_mode:
                            shell_aliases = {
                                'cmd': 'cmd', 'powershell': 'powershell', 'ps': 'powershell',
                                'pwsh': 'pwsh', 'wsl': 'wsl', 'git-bash': 'git-bash',
                                'cygwin': 'cygwin', 'bash': 'bash', 'sh': 'sh',
                                'zsh': 'zsh', 'fish': 'fish', 'ksh': 'ksh',
                                'tcsh': 'tcsh', 'dash': 'dash'
                            }
                            parts = cmd.rsplit(' ', 1)
                            if len(parts) == 2 and parts[1].lower() in shell_aliases:
                                actual_cmd = parts[0]
                                shell_type = shell_aliases[parts[1].lower()]
                                print(f"{Fore.CYAN}[{shell_type.upper()}] {actual_cmd}{Style.RESET_ALL}")
                            else:
                                actual_cmd = cmd
                                shell_type = 'cmd'
                            result = self.brain.tools.run_command({'content': actual_cmd, 'shell': shell_type, 'encoding': 'utf-8'})
                            if result.get('success'):
                                output = result.get('output', '')
                                print(f"{Fore.GREEN}{output}{Style.RESET_ALL}" if output else f"{Fore.GREEN}Command executed{Style.RESET_ALL}")
                                self.brain.p2p_sharing.broadcast_output(output[:500] if output else "Command executed")
                            else:
                                print(f"{Fore.RED}Error: {result.get('error', 'Unknown')}{Style.RESET_ALL}")
                        else:
                            result = self.brain.think_and_act(cmd, force_execute=True, safe_mode=True)
                            if result.get('results'):
                                for r in result['results']:
                                    if r.get('output'):
                                        self.brain.p2p_sharing.broadcast_output(r['output'][:300])
                    else:
                        print(f"{Fore.YELLOW}No pending commands{Style.RESET_ALL}")
                return True
            elif subcommand == 'reject':
                if self.brain.p2p_sharing.is_host:
                    self.brain.p2p_sharing.approve_pending(False)
                return True
            elif subcommand == 'users':
                users = self.brain.p2p_sharing.get_connected_users()
                print(f"\n{Fore.CYAN}Connected Users: {', '.join(users)}{Style.RESET_ALL}")
                return True
            elif subcommand == 'end':
                self.brain.p2p_sharing.end_session()
                return True
        self._show_share_help()
        return True
    
    def _show_share_help(self):
        """Show share command help"""
        current_name = self.brain.p2p_sharing.my_name or "Not set"
        encryption = "ON" if self.brain.p2p_sharing.encryption_enabled else "OFF"
        key_info = ""
        if self.brain.p2p_sharing.encryption_enabled and self.brain.p2p_sharing.encryption_key_display:
            key_info = f" ({self.brain.p2p_sharing.encryption_key_display})"
        print(f"""
{Fore.CYAN}{'='*55}{Style.RESET_ALL}
{Fore.CYAN}TERMINAL SHARING (MULTI-CLIENT P2P + E2E ENCRYPTION){Style.RESET_ALL}
{Fore.CYAN}{'='*55}{Style.RESET_ALL}
{Fore.YELLOW}Your Name: {current_name} | Encryption: {encryption}{key_info}{Style.RESET_ALL}

{Fore.GREEN}Session:{Style.RESET_ALL}
  share start [port]        - Start host session (AI-assisted)
  share start --no-ai       - Start without AI (direct command execution)
  share connect IP:PORT     - Connect to host
  share end                 - End session

{Fore.GREEN}Encryption:{Style.RESET_ALL}
  share encrypt             - Show encryption status & full key
  share encrypt on          - Enable with saved/new random key
  share encrypt off         - Disable encryption
  share encrypt random      - Generate new random key (shows full key)
  share encrypt <password>  - Use password-based key
  share encrypt key <key>   - Use specific Fernet key

{Fore.GREEN}Communication:{Style.RESET_ALL}
  share message <text>      - Send message to all
  share chat                - Show chat history

{Fore.GREEN}File Transfer:{Style.RESET_ALL}
  share file <path> [user]  - Send file (user optional, default: host/broadcast)
  share accept [path]       - Accept pending file
  share deny                - Reject pending file

{Fore.GREEN}Commands:{Style.RESET_ALL}
  share send <command>      - Send command (helper only)
  share approve/reject      - Handle pending commands (host only)

{Fore.GREEN}Info:{Style.RESET_ALL}
  share name <newname>      - Change your name
  share status              - Show connection status
  share list/users          - List connected users
  share logs                - Show terminal logs

{Fore.MAGENTA}Global Access (ngrok):{Style.RESET_ALL}
  1. Host: Run 'ngrok tcp 5757'
  2. Share the ngrok URL (e.g., 0.tcp.ngrok.io:12345)
  3. Helper: 'share connect 0.tcp.ngrok.io:12345'
""")
    
    def parse_command(self, user_input):
        force = False
        safe_mode = False
        show_only = False
        temp_mode = None
        user_input_lower = user_input.lower()
        if '--force' in user_input_lower or ' -f' in user_input_lower:
            force = True
            user_input = user_input.replace('--force', '').replace('--FORCE', '')
            user_input = user_input.replace(' -f', '').replace(' -F', '')
        if '--safe' in user_input_lower or ' -s' in user_input_lower:
            safe_mode = True
            user_input = user_input.replace('--safe', '').replace('--SAFE', '')
            user_input = user_input.replace(' -s', '').replace(' -S', '')
        if '--show' in user_input_lower:
            show_only = True
            user_input = user_input.replace('--show', '').replace('--SHOW', '')
        words = user_input.split()
        if len(words) > 1:
            last_word = words[-1].lower()
            if ModeManager.is_valid_mode(last_word):
                temp_mode = last_word
                user_input = ' '.join(words[:-1])
        return user_input.strip(), force, safe_mode, show_only, temp_mode

    
    def run(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            self.show_banner()
            while True:
                try:
                    user_input = input(f"\n{Fore.GREEN}You >>> {Style.RESET_ALL}").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        duration = datetime.datetime.now() - self.start_time
                        if self.telemetry.is_enabled():
                            self.telemetry.track_session_end(self.request_count, duration.total_seconds())
                        print(f"\n{Fore.CYAN}Goodbye! Processed {self.request_count} requests.{Style.RESET_ALL}")
                        print(f"{Fore.BLUE}Duration: {str(duration).split('.')[0]}{Style.RESET_ALL}")
                        break
                    if user_input.lower() in ['clear', 'cls']:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        self.show_banner()
                        continue
                    if user_input.lower().startswith('share'):
                        self.handle_share_command(user_input)
                        continue
                    if user_input.lower() == 'switch offline':
                        self.brain.switch_to_offline()
                        continue
                    if user_input.lower() == 'switch online':
                        self.brain.switch_to_online()
                        continue
                    if user_input.lower() in ModeManager.list_modes():
                        self.brain.switch_mode(user_input.lower(), permanent=True)
                        mode_config = ModeManager.get_mode_config(user_input.lower())
                        print(f"\n{Fore.GREEN}Switched to {user_input.upper()} mode{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}  {mode_config['description']}{Style.RESET_ALL}")
                        continue
                    if user_input.lower().startswith('gui'):
                        if 'on' in user_input.lower():
                            if not PYAUTOGUI_AVAILABLE or keyboard is None:
                                print(f"\n{Fore.YELLOW}GUI automation requires pyautogui and keyboard packages.{Style.RESET_ALL}")
                                choice = input(f"{Fore.CYAN}Install now? (Y/N): {Style.RESET_ALL}").upper()
                                if choice == 'Y':
                                    os.system('pip install pyautogui keyboard')
                                    print(f"\n{Fore.GREEN}Installed! Please restart ZAI Shell to use GUI.{Style.RESET_ALL}")
                                continue
                            self.brain.gui_enabled = True
                            self.memory.set_gui_enabled(True)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_interface_preference(True)
                            print(f"\n{Fore.GREEN}GUI automation ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.gui_enabled = False
                            self.memory.set_gui_enabled(False)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_interface_preference(False)
                            print(f"\n{Fore.YELLOW}GUI automation DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.gui_enabled else "OFF"
                            print(f"\n{Fore.CYAN}GUI automation: {status}{Style.RESET_ALL}")
                        continue
                    if user_input.lower().startswith('research'):
                        if 'on' in user_input.lower():
                            if not DDGS_AVAILABLE and not (REQUESTS_AVAILABLE and BS4_AVAILABLE):
                                print(f"\n{Fore.YELLOW}Web research requires ddgs package.{Style.RESET_ALL}")
                                choice = input(f"{Fore.CYAN}Install now? (Y/N): {Style.RESET_ALL}").upper()
                                if choice == 'Y':
                                    os.system('pip install ddgs')
                                    print(f"\n{Fore.GREEN}Installed! Please restart ZAI Shell to use research.{Style.RESET_ALL}")
                                continue
                            self.brain.research_enabled = True
                            self.memory.set_research_enabled(True)
                            print(f"\n{Fore.GREEN}Web research ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.research_enabled = False
                            self.memory.set_research_enabled(False)
                            print(f"\n{Fore.YELLOW}Web research DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.research_enabled else "OFF"
                            print(f"\n{Fore.CYAN}Web research: {status}{Style.RESET_ALL}")
                        continue
                    if user_input.lower().startswith('thinking'):
                        if 'on' in user_input.lower():
                            self.brain.thinking_enabled = True
                            self.memory.set_thinking(True)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_thinking_usage(True)
                            print(f"\n{Fore.GREEN}Thinking mode ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.thinking_enabled = False
                            self.memory.set_thinking(False)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_thinking_usage(False)
                            print(f"\n{Fore.YELLOW}Thinking mode DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.thinking_enabled else "OFF"
                            print(f"\n{Fore.CYAN}Thinking mode is currently: {status}{Style.RESET_ALL}")
                        continue
                    if user_input.lower().startswith('telemetry'):
                        if 'on' in user_input.lower():
                            self.telemetry.set_enabled(True)
                            print(f"\n{Fore.GREEN}Telemetry ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.telemetry.set_enabled(False)
                            print(f"\n{Fore.YELLOW}Telemetry DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.telemetry.is_enabled() else "OFF"
                            print(f"\n{Fore.CYAN}Telemetry is currently: {status}{Style.RESET_ALL}")
                        continue
                    if user_input.lower().startswith('memory'):
                        if 'clear' in user_input.lower():
                            self.memory.memory["conversation_history"] = []
                            self.memory.save_memory()
                            print(f"\n{Fore.GREEN}Conversation history cleared{Style.RESET_ALL}")
                        elif 'show' in user_input.lower():
                            history = self.memory.get_recent_history(10)
                            print(f"\n{Fore.CYAN}Recent conversation history:{Style.RESET_ALL}")
                            for msg in history:
                                role = "You" if msg['role'] == 'user' else "ZAI"
                                print(f"{role}: {msg['message'][:100]}...")
                        elif 'search' in user_input.lower():
                            query = user_input.replace('memory search', '').strip()
                            if query and hasattr(self.memory, 'search_memory'):
                                results = self.memory.search_memory(query)
                                if results:
                                    print(f"\n{Fore.CYAN}Search results for '{query}':{Style.RESET_ALL}")
                                    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                                        print(f"\n{Fore.YELLOW}{meta['role']}: {doc[:150]}...{Style.RESET_ALL}")
                                else:
                                    print(f"\n{Fore.YELLOW}No results found{Style.RESET_ALL}")
                            else:
                                print(f"\n{Fore.YELLOW}Usage: memory search <query>{Style.RESET_ALL}")
                        else:
                            stats = self.memory.memory["stats"]
                            print(f"\n{Fore.CYAN}Memory Stats:{Style.RESET_ALL}")
                            print(f"Total requests: {stats['total_requests']}")
                            print(f"Successful actions: {stats['successful_actions']}")
                            print(f"Failed actions: {stats['failed_actions']}")
                        continue
                    if user_input.lower().startswith('sentinel'):
                        parts = user_input.lower().split()
                        subcommand = parts[1] if len(parts) > 1 else None
                        if subcommand == 'on':
                            self.brain.sentinel.enable()
                            print(f"\n{Fore.GREEN}🛡️ SENTINEL ENABLED - System protection active{Style.RESET_ALL}")
                        elif subcommand == 'off':
                            print(f"\n{Fore.RED}⚠️ WARNING: Disabling Sentinel removes system protection!{Style.RESET_ALL}")
                            confirm = input(f"{Fore.YELLOW}Are you sure? (Y/N): {Style.RESET_ALL}").upper()
                            if confirm == 'Y':
                                self.brain.sentinel.disable()
                                print(f"\n{Fore.YELLOW}🛡️ SENTINEL DISABLED - System protection OFF{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}Sentinel remains active{Style.RESET_ALL}")
                        elif subcommand == 'reset':
                            print(f"\n{Fore.YELLOW}This will reset Sentinel's behavioral memory.{Style.RESET_ALL}")
                            confirm = input(f"{Fore.YELLOW}Confirm reset? (Y/N): {Style.RESET_ALL}").upper()
                            if confirm == 'Y':
                                self.brain.sentinel.force_reset()
                                print(f"\n{Fore.GREEN}Sentinel state reset completed{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.CYAN}Reset cancelled{Style.RESET_ALL}")
                        elif subcommand == 'status' or subcommand is None:
                            status = "ON" if self.brain.sentinel.is_enabled else "OFF"
                            summary = self.brain.sentinel.get_behavior_summary()
                            print(f"\n{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}🛡️ SENTINEL 1.5 STATUS: {Fore.GREEN if status == 'ON' else Fore.RED}{status}{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                            if 'message' in summary:
                                print(f"{Fore.YELLOW}{summary['message']}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.WHITE}Monitored Actions: {summary['total_actions']}{Style.RESET_ALL}")
                                print(f"{Fore.GREEN}Successful: {summary['successes']} ({summary['success_rate']}%){Style.RESET_ALL}")
                                print(f"{Fore.RED}Failed: {summary['failures']}{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}Consecutive Failures: {summary['consecutive_failures']}{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}Repair Attempts: {summary['repair_attempts']}{Style.RESET_ALL}")
                                print(f"{Fore.MAGENTA}Average Risk: {summary['average_risk_score']}/100{Style.RESET_ALL}")
                                print(f"{Fore.CYAN}Lessons Learned: {summary.get('lessons_learned', 0)}{Style.RESET_ALL}")
                                print(f"{Fore.CYAN}Warnings This Session: {summary.get('warnings_this_session', 0)}{Style.RESET_ALL}")
                                if summary.get('is_panic_mode'):
                                    print(f"{Fore.RED}⚠️ PANIC MODE ACTIVE{Style.RESET_ALL}")
                                if summary['is_degraded']:
                                    print(f"{Fore.RED}⚠️ SYSTEM DEGRADATION DETECTED{Style.RESET_ALL}")
                                if summary['risk_trend']:
                                    print(f"{Fore.CYAN}Risk Trend: {summary['risk_trend']}{Style.RESET_ALL}")
                                if summary['damage_indicators']:
                                    print(f"{Fore.RED}Damage Indicators: {summary['damage_indicators']}{Style.RESET_ALL}")
                            blocked = self.brain.sentinel.get_warnings_log()
                            if blocked:
                                print(f"\n{Fore.YELLOW}Recent Warnings: {len(blocked)}{Style.RESET_ALL}")
                                for b in blocked[-3:]:
                                    stop_icon = "⚠️ " if b.get('sentinel_recommends_stop') else ""
                                    rb = b.get('risk_breakdown', {})
                                    acc = " [accumulated]" if rb.get('is_accumulated') else ""
                                    print(f"  - {stop_icon}{b['action_type']}: {b['reason'][:40]}{acc}")
                            lessons = self.brain.sentinel.get_lessons_summary()
                            if lessons:
                                print(f"\n{Fore.CYAN}📚 Lessons Learned:{Style.RESET_ALL}")
                                for l in lessons[:5]:
                                    print(f"  - [{l['type']}] {l['trigger'][:30]} → {l['consequence'][:30]} ({l['times_seen']}x)")
                            print(f"{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                        elif subcommand == 'lessons':
                            lessons = self.brain.sentinel.get_lessons_summary()
                            print(f"\n{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}📚 SENTINEL LESSON MEMORY{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                            if lessons:
                                for l in lessons:
                                    print(f"  [{l['type']}] {l['trigger']} → {l['consequence']} ({l['times_seen']}x)")
                            else:
                                print(f"{Fore.YELLOW}No lessons learned yet.{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
                        elif subcommand == 'clear-lessons':
                            print(f"{Fore.YELLOW}This will clear all lessons learned by Sentinel.{Style.RESET_ALL}")
                            if input(f"{Fore.RED}Are you sure? (Y/N): {Style.RESET_ALL}").strip().upper() == 'Y':
                                self.brain.sentinel.clear_lessons()
                                print(f"{Fore.GREEN}Lessons cleared{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.CYAN}Cancelled{Style.RESET_ALL}")
                        else:
                            print(f"\n{Fore.YELLOW}Usage: sentinel [on|off|status|reset|lessons|clear-lessons]{Style.RESET_ALL}")
                        continue
                    parsed_input, force, safe_mode, show_only, temp_mode = self.parse_command(user_input)
                    if temp_mode:
                        self.brain.switch_mode(temp_mode, permanent=False)
                        mode_config = ModeManager.get_mode_config(temp_mode)
                        print(f"\n{Fore.MAGENTA}Using {temp_mode.upper()} mode for this command{Style.RESET_ALL}")
                    indicators = []
                    if safe_mode:
                        indicators.append(f"{Fore.GREEN}SAFE{Style.RESET_ALL}")
                    if show_only:
                        indicators.append(f"{Fore.CYAN}PREVIEW{Style.RESET_ALL}")
                    if force:
                        indicators.append(f"{Fore.RED}FORCE{Style.RESET_ALL}")
                        if self.telemetry.is_enabled():
                            self.telemetry.track_force_command()
                    if self.brain.p2p_sharing.is_connected and self.brain.p2p_sharing.safe_mode_always:
                        indicators.append(f"{Fore.MAGENTA}SHARING-SAFE{Style.RESET_ALL}")
                        safe_mode = True
                    if indicators:
                        print(f"\n[{' | '.join(indicators)}]")
                    self.request_count += 1
                    start = time.time()
                    intents = self.brain.detect_intent(parsed_input)
                    
                    if intents['needs_p2p'] and intents['p2p_action']:
                        p2p_action = intents['p2p_action']
                        action_type = p2p_action.get('action')
                        params = p2p_action.get('params', {})
                        
                        print(f"\n{Fore.MAGENTA}[P2P Action: {action_type}]{Style.RESET_ALL}")
                        
                        if action_type == 'show_logs':
                            self.brain.p2p_sharing.show_recent_logs()
                        elif action_type == 'show_chat':
                            self.brain.p2p_sharing.show_chat_history()
                        elif action_type == 'list_users':
                            if self.brain.p2p_sharing.is_host:
                                self.brain.p2p_sharing.list_clients()
                            else:
                                users = self.brain.p2p_sharing.get_connected_users()
                                print(f"\n{Fore.CYAN}Connected Users: {', '.join(users)}{Style.RESET_ALL}")
                        elif action_type == 'send_file':
                            file_path = params.get('file_path', '')
                            target_user = params.get('target_user')
                            if file_path:
                                result = self.brain.p2p_sharing.send_file(file_path, target_user)
                                if not result.get('success'):
                                    print(f"{Fore.RED}File send failed: {result.get('error')}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.YELLOW}No file path detected in your message{Style.RESET_ALL}")
                        elif action_type == 'send_message':
                            message = params.get('message', '')
                            if message:
                                self.brain.p2p_sharing.send_message(message)
                            else:
                                print(f"{Fore.YELLOW}No message detected in your input{Style.RESET_ALL}")
                        elif action_type == 'send_command':
                            command = params.get('command', '')
                            target_user = params.get('target_user')
                            if command:
                                result = self.brain.p2p_sharing.send_command_to_user(command, target_user)
                                if not result.get('success'):
                                    print(f"{Fore.RED}Command send failed: {result.get('error')}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.YELLOW}No command detected in your input{Style.RESET_ALL}")
                        elif action_type == 'approve_command':
                            if self.brain.p2p_sharing.is_host:
                                cmd = self.brain.p2p_sharing.approve_pending(True)
                                if cmd:
                                    print(f"{Fore.GREEN}Executing: {cmd}{Style.RESET_ALL}")
                                    result = self.brain.think_and_act(cmd, force_execute=True, safe_mode=True)
                                    if result.get('results'):
                                        for r in result['results']:
                                            if r.get('output'):
                                                self.brain.p2p_sharing.broadcast_output(r['output'][:300])
                                else:
                                    print(f"{Fore.YELLOW}No pending commands{Style.RESET_ALL}")
                        elif action_type == 'reject_command':
                            if self.brain.p2p_sharing.is_host:
                                self.brain.p2p_sharing.approve_pending(False)
                        elif action_type == 'accept_file':
                            save_path = params.get('save_path')
                            result = self.brain.p2p_sharing.accept_file(save_path)
                            if not result.get('success'):
                                print(f"{Fore.RED}{result.get('error')}{Style.RESET_ALL}")
                        elif action_type == 'deny_file':
                            self.brain.p2p_sharing.deny_file()
                        elif action_type == 'show_status':
                            self.handle_share_command("share status")
                        
                        duration = time.time() - start
                        print(f"\n{Fore.WHITE}{duration:.2f}s{Style.RESET_ALL}")
                        continue
                    
                    if intents['needs_image_analysis'] and intents['image_path']:
                        print(f"\n{Fore.CYAN}Analyzing image: {intents['image_path']}{Style.RESET_ALL}")
                        analysis = self.brain.image_analyzer.analyze_image(intents['image_path'])
                        if analysis.get('success'):
                            print(f"\n{Fore.GREEN}ZAI: {analysis.get('analysis', 'No analysis available')}{Style.RESET_ALL}")
                            self.memory.add_conversation("user", parsed_input)
                            self.memory.add_conversation("assistant", analysis.get('analysis', ''))
                        else:
                            print(f"\n{Fore.RED}Image analysis failed: {analysis.get('error')}{Style.RESET_ALL}")
                    elif intents['needs_research'] and not self.brain.offline_mode:
                        if not self.brain.research_enabled:
                            print(f"\n{Fore.YELLOW}Web research is disabled. Enable with 'research on'{Style.RESET_ALL}")
                            self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                        elif self.brain.web_research and self.brain.web_research.is_available():
                            print(f"\n{Fore.CYAN}Searching web...{Style.RESET_ALL}")
                            original_query = intents['research_query']
                            optimized_query = self.brain.web_research.optimize_query(original_query)
                            if optimized_query != original_query:
                                print(f"{Fore.YELLOW}Optimized search: {optimized_query}{Style.RESET_ALL}")
                            results = self.brain.web_research.search(optimized_query)
                            if results:
                                self.brain.web_research.print_results_to_user(results, original_query)
                                print(f"{Fore.GREEN}Analyzing {len(results)} results...{Style.RESET_ALL}\n")
                                formatted = self.brain.web_research.format_results_for_ai(results, original_query)
                                enhanced_input = f"{formatted}"
                                self.brain.think_and_act(enhanced_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                            else:
                                print(f"{Fore.YELLOW}No results found, answering from knowledge...{Style.RESET_ALL}")
                                self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                        else:
                            print(f"{Fore.YELLOW}Web research not available. Install with 'research on'{Style.RESET_ALL}")
                            self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                    elif intents['needs_gui'] and not self.brain.offline_mode:
                        if not self.brain.gui_enabled:
                            print(f"\n{Fore.YELLOW}GUI automation is disabled. Enable with 'gui on'{Style.RESET_ALL}")
                            self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                        else:
                            print(f"\n{Fore.CYAN}Generating hybrid plan (Terminal + GUI)...{Style.RESET_ALL}")
                            plan = self.brain.generate_hybrid_plan(parsed_input)
                            if plan and plan.get('needs_gui'):
                                print(f"{Fore.GREEN}Plan generated with {len(plan.get('steps', []))} steps{Style.RESET_ALL}")
                                if not show_only:
                                    if force or input(f"{Fore.YELLOW}Execute hybrid plan? (Y/N): {Style.RESET_ALL}").upper() == 'Y':
                                        self.brain.execute_hybrid_plan(plan, safe_mode=safe_mode)
                                    else:
                                        print(f"{Fore.YELLOW}Plan cancelled{Style.RESET_ALL}")
                                else:
                                    print(f"\n{Fore.CYAN}Hybrid Plan Preview:{Style.RESET_ALL}")
                                    for step in plan.get('steps', []):
                                        print(f"  [{step.get('step')}] {step.get('type').upper()}: {step.get('description', step.get('action'))}")
                            else:
                                self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                    else:
                        print(f"\n{Fore.YELLOW}Processing...{Style.RESET_ALL}")
                        self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                    if self.brain.p2p_sharing.is_connected:
                        self.brain.p2p_sharing.add_terminal_log(f"Request: {parsed_input[:100]}")
                    duration = time.time() - start
                    print(f"\n{Fore.WHITE}{duration:.2f}s{Style.RESET_ALL}")
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}Type 'exit' to quit{Style.RESET_ALL}")
                except Exception as e:
                    print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Shell error: {str(e)}{Style.RESET_ALL}")


def main():
    try:
        zai = ZAIShell()
        zai.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Closing program...{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Startup error: {str(e)}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()