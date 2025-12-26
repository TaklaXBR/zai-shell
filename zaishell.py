import os
import sys
import subprocess
import time
import datetime
import json
import platform
import threading
from pathlib import Path

import google.generativeai as genai
from colorama import init, Fore, Style

init(autoreset=True)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "Or Enter Your API Key Here")
genai.configure(api_key=GEMINI_API_KEY)

# Memory file path
MEMORY_FILE = ".zaishell_memory.json"

# ChromaDB settings
CHROMA_DB_PATH = ".zaishell_chromadb"
CHROMA_COLLECTION_NAME = "zaishell_memory"

# Offline model settings
OFFLINE_MODEL_PATH = ".zaishell_offline_model"
OFFLINE_MODEL_NAME = "microsoft/phi-2"

SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

# Dangerous commands for --safe mode
DANGEROUS_COMMANDS = [
    'rm -rf', 'sudo rm', 'del /f', 'format', 'reboot', 'shutdown',
    'init 0', 'init 6', 'poweroff', 'halt', 'dd if=', 'mkfs',
    ':(){:|:&};:', 'chmod -R 777 /', 'chown -R', '> /dev/sda',
    'mv /* ', 'rm -r /', 'sudo dd', 'fdisk', 'wipefs'
]


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
        
        # Always keep JSON as backup/fallback
        self.json_manager = MemoryManager()
        self.memory = self.json_manager.memory
    
    def get_offline_mode(self):
        """Get offline mode status"""
        return self.json_manager.get_offline_mode()
    
    def set_offline_mode(self, enabled):
        """Set offline mode"""
        self.json_manager.set_offline_mode(enabled)
    
    def add_conversation(self, role, message):
        """Add conversation to both ChromaDB and JSON"""
        timestamp = datetime.datetime.now().isoformat()
        
        # Add to JSON (always)
        self.json_manager.add_conversation(role, message)
        
        # Add to ChromaDB if available
        if self.use_chromadb and self.collection:
            try:
                doc_id = f"{role}_{timestamp}"
                self.collection.add(
                    documents=[message[:1000]],
                    metadatas=[{
                        "role": role,
                        "timestamp": timestamp,
                        "full_message": message[:2000]
                    }],
                    ids=[doc_id]
                )
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ ChromaDB add error: {e}{Style.RESET_ALL}")
    
    def get_recent_history(self, count=5):
        """Get recent history from ChromaDB or JSON"""
        if self.use_chromadb and self.collection:
            try:
                results = self.collection.get(
                    limit=count,
                    include=["metadatas", "documents"]
                )
                
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
        
        # Fallback to JSON
        return self.json_manager.get_recent_history(count)
    
    def search_memory(self, query, n_results=3):
        """Search similar conversations in ChromaDB"""
        if self.use_chromadb and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["metadatas", "documents", "distances"]
                )
                return results
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ ChromaDB search error: {e}{Style.RESET_ALL}")
        return None
    
    def save_memory(self):
        """Save to JSON (ChromaDB auto-persists)"""
        self.json_manager.save_memory()
    
    def update_stats(self, successful=0, failed=0):
        """Update statistics"""
        self.json_manager.update_stats(successful, failed)
    
    def set_mode(self, mode):
        """Set current mode"""
        self.json_manager.set_mode(mode)
        self.memory = self.json_manager.memory
    
    def get_mode(self):
        """Get current mode"""
        return self.json_manager.get_mode()
    
    def set_thinking(self, enabled):
        """Set thinking mode"""
        self.json_manager.set_thinking(enabled)
    
    def get_thinking(self):
        """Get thinking mode"""
        return self.json_manager.get_thinking()


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


class OfflineModelManager:
    """Manages offline/local AI model"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_ready = False
        self.model_path = OFFLINE_MODEL_PATH
        self.model_name = OFFLINE_MODEL_NAME
    
    def check_model_exists(self):
        """Check if model is already downloaded"""
        return os.path.exists(self.model_path) and os.path.isdir(self.model_path)
    
    def download_model(self):
        """Download offline model"""
        try:
            print(f"\n{Fore.CYAN}📥 Downloading offline model (Phi-2 - ~5GB)...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}This may take a few minutes depending on your internet speed{Style.RESET_ALL}\n")
            
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            print(f"{Fore.CYAN}[1/2] Downloading tokenizer...{Style.RESET_ALL}")
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            print(f"{Fore.CYAN}[2/2] Downloading model...{Style.RESET_ALL}")
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True
            )
            
            # Save locally
            os.makedirs(self.model_path, exist_ok=True)
            print(f"{Fore.CYAN}💾 Saving model locally...{Style.RESET_ALL}")
            model.save_pretrained(self.model_path)
            tokenizer.save_pretrained(self.model_path)
            
            print(f"\n{Fore.GREEN}✓ Model downloaded successfully!{Style.RESET_ALL}")
            return True
            
        except ImportError:
            print(f"\n{Fore.RED}❌ Missing libraries. Install with:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}pip install transformers torch accelerate{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"\n{Fore.RED}❌ Download failed: {e}{Style.RESET_ALL}")
            return False
    
    def load_model(self):
        """Load the offline model"""
        try:
            if not self.check_model_exists():
                print(f"\n{Fore.YELLOW}⚠️ Offline model not found{Style.RESET_ALL}")
                if not self.download_model():
                    return False
            
            print(f"\n{Fore.CYAN}🔄 Loading offline model...{Style.RESET_ALL}")
            
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True
            )
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                print(f"{Fore.GREEN}✓ Model loaded on GPU{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}✓ Model loaded on CPU (slower){Style.RESET_ALL}")
            
            self.is_ready = True
            return True
            
        except Exception as e:
            print(f"\n{Fore.RED}❌ Failed to load model: {e}{Style.RESET_ALL}")
            return False
    
    def generate(self, prompt, max_length=1024, temperature=0.1):
        """Generate response using offline model"""
        if not self.is_ready:
            return "Error: Offline model not loaded"
        
        try:
            import torch
            
            formatted_prompt = prompt
            
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt", truncation=True, max_length=2048)
            
            if torch.cuda.is_available():
                try:
                    inputs = {k: v.to('cuda') for k, v in inputs.items()}
                except:
                    pass
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            
            if formatted_prompt in response:
                response = response.replace(formatted_prompt, "").strip()
            
            if "{" in response:
                start_index = response.find("{")
                bracket_count = 0
                end_index = -1
                
                for i, char in enumerate(response[start_index:], start_index):
                    if char == "{":
                        bracket_count += 1
                    elif char == "}":
                        bracket_count -= 1
                        
                    if bracket_count == 0:
                        end_index = i + 1
                        break
                
                if end_index != -1:
                    response = response[start_index:end_index]
            
            return response
            
        except Exception as e:
            return f"Error generating response: {str(e)}"


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
            "temperature": 0.1,
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
- Example: {"understanding":"Delete logs","actions":[{"type":"command","details":{"shell":"cmd","content":"del *.log"}}],"response":"Done"}
"""
        }
    }
    
    @staticmethod
    def get_mode_config(mode_name):
        """Get configuration for a mode"""
        return ModeManager.MODES.get(mode_name.lower(), ModeManager.MODES["normal"])
    
    @staticmethod
    def is_valid_mode(mode_name):
        """Check if mode is valid"""
        return mode_name.lower() in ModeManager.MODES
    
    @staticmethod
    def list_modes():
        """List all available modes"""
        return list(ModeManager.MODES.keys())


class AIBrain:
    """AI Brain - COMPLETELY FREE, no restrictions"""
    
    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.current_mode = self.memory.get_mode()
        self.thinking_enabled = self.memory.get_thinking()
        
        self.offline_mode = self.memory.get_offline_mode()
        self.offline_model = None
        
        if self.offline_mode:
            print(f"\n{Fore.YELLOW}⚠️ System started in OFFLINE mode. Loading model...{Style.RESET_ALL}")
            self.offline_model = OfflineModelManager()
            self.offline_model.load_model()
        
        self.model = self._create_model()
        self.tools = AITools()
        self.context = self._build_context()
        self.max_retries = 5
        self.temp_mode = None
        
    def _create_model(self):
        """Create model based on current mode"""
        if self.offline_mode:
            return None  # Will use offline model
        mode_config = ModeManager.get_mode_config(self.current_mode)
        return genai.GenerativeModel(
            mode_config["model"],
            generation_config={"temperature": mode_config["temperature"]}
        )
    
    def switch_to_offline(self):
        """Switch to offline mode"""
        print(f"\n{Fore.CYAN}🔄 Switching to OFFLINE mode...{Style.RESET_ALL}")
        
        if self.offline_model is None:
            self.offline_model = OfflineModelManager()
        
        if not self.offline_model.is_ready:
            if not self.offline_model.load_model():
                print(f"{Fore.RED}❌ Failed to load offline model{Style.RESET_ALL}")
                return False
        
        self.offline_mode = True
        self.memory.set_offline_mode(True)
        print(f"\n{Fore.GREEN}✓ OFFLINE mode activated{Style.RESET_ALL}")
        print(f"{Fore.CYAN}→ All operations will use local AI model{Style.RESET_ALL}")
        return True
    
    def switch_to_online(self):
        """Switch back to online mode"""
        self.offline_mode = False
        self.memory.set_offline_mode(False)
        self.model = self._create_model()
        print(f"\n{Fore.GREEN}✓ ONLINE mode activated{Style.RESET_ALL}")
        return True
    
    def switch_mode(self, new_mode, permanent=True):
        """Switch operation mode"""
        if not ModeManager.is_valid_mode(new_mode):
            return False
        
        if permanent:
            self.current_mode = new_mode
            self.memory.set_mode(new_mode)
            if not self.offline_mode:
                self.model = self._create_model()
        else:
            self.temp_mode = new_mode
        
        return True
    
    def toggle_thinking(self):
        """Toggle thinking mode"""
        self.thinking_enabled = not self.thinking_enabled
        self.memory.set_thinking(self.thinking_enabled)
        return self.thinking_enabled
    
    def _get_active_mode(self):
        """Get currently active mode (temp or permanent)"""
        return self.temp_mode if self.temp_mode else self.current_mode
    
    def _build_context(self):
        """Build system context"""
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
        """Detect available shells on system"""
        shells = []
        
        if os.name == 'nt':  # Windows
            # Core shells
            shells.extend(['cmd', 'powershell'])
            
            # Check PowerShell Core
            if subprocess.run(['where', 'pwsh'], capture_output=True, shell=True).returncode == 0:
                shells.append('pwsh')
            
            # Check Git Bash
            git_bash_paths = [
                r'C:\Program Files\Git\bin\bash.exe',
                r'C:\Program Files (x86)\Git\bin\bash.exe',
                os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\bash.exe')
            ]
            for path in git_bash_paths:
                if os.path.exists(path):
                    shells.append('git-bash')
                    break
            
            # Check WSL (Windows Subsystem for Linux)
            if subprocess.run(['where', 'wsl'], capture_output=True, shell=True).returncode == 0:
                shells.append('wsl')
            
            # Check Cygwin
            if os.path.exists(r'C:\cygwin64\bin\bash.exe') or os.path.exists(r'C:\cygwin\bin\bash.exe'):
                shells.append('cygwin')
        
        else:  # Linux/Mac
            # Core shells
            shells.extend(['bash', 'sh'])
            
            # Check additional shells
            shells_to_check = ['zsh', 'fish', 'ksh', 'tcsh', 'dash']
            for shell in shells_to_check:
                try:
                    if subprocess.run(['which', shell], capture_output=True, shell=True).returncode == 0:
                        shells.append(shell)
                except:
                    pass
        
        return shells
    
    def think_and_act(self, user_message, retry_context=None, force_execute=False, safe_mode=False, show_only=False, retry_count=0):
        """Main thinking and action engine"""
        
        if self.temp_mode and not retry_context:
            self.temp_mode = None
        
        if retry_context is None:
            self.memory.add_conversation("user", user_message)
        
        if retry_context:
            retry_prompt = f"""
⚠️ ERROR IN PREVIOUS ATTEMPT - REPLANNING REQUIRED

User Request: {user_message}

Failed Action:
- Type: {retry_context['action_type']}
- Description: {retry_context['description']}
- Shell: {retry_context.get('shell', 'Not specified')}
- Error Message: {retry_context['error']}
- Attempt: {retry_context['retry_count']}/{self.max_retries}

🔧 YOUR TASK NOW:
1. ANALYZE ERROR IN DETAIL
2. FIND A COMPLETELY DIFFERENT METHOD
3. CREATE NEW PLAN

REMEMBER: System has {len(self.context['available_shells'])} different shells: {', '.join(self.context['available_shells'])}
"""
            system_instruction = self._build_system_instruction(retry_prompt, safe_mode)
        else:
            system_instruction = self._build_system_instruction(user_message, safe_mode)

        try:
            if self.offline_mode:

                active_mode = self._get_active_mode()
                mode_config = ModeManager.get_mode_config(active_mode)
                mode_temperature = mode_config.get("temperature", 0.7)
                
                response_text = self.offline_model.generate(
                    system_instruction,
                    max_length=1024,
                    temperature=mode_temperature
                )
            else:
                response = self.model.generate_content(system_instruction)
                response_text = response.text
            
            return self._process_ai_response(response_text, user_message, retry_count=retry_count, force_execute=force_execute, safe_mode=safe_mode, show_only=show_only)
            
        except Exception as e:
            return self._handle_error(e, user_message)
    
    def _build_system_instruction(self, main_content, safe_mode=False):
        """Build system instruction"""
        
        
        if self.offline_mode:
            shells = ', '.join(self.context['available_shells'])
            
            return f"""You are a command line tool. Output valid JSON only.

Example 1:
User: list files
JSON: {{"understanding": "list files", "actions": [{{"type": "command", "description": "list files", "details": {{"shell": "cmd", "content": "dir"}}}}], "response": "Listing files."}}

Example 2 (Turkish):
User: masaustu ne notlar.txt olustur
JSON: {{"understanding": "create file", "actions": [{{"type": "file", "description": "create file", "details": {{"path": "Desktop/notlar.txt", "content": "", "encoding": "utf-8"}}}}], "response": "Dosya olusturuldu."}}

Current Task:
User: {main_content}
JSON:"""
        
        active_mode = self._get_active_mode()
        mode_config = ModeManager.get_mode_config(active_mode)
        mode_modifier = mode_config["instruction_modifier"]
        
        safe_mode_text = ""
        if safe_mode:
            safe_mode_text = f"""
🛡️ SAFE MODE IS ACTIVE:
CRITICAL RESTRICTIONS - These commands are STRICTLY FORBIDDEN:
{', '.join(DANGEROUS_COMMANDS)}

YOU MUST:
- Reject any dangerous/destructive commands
- Refuse system-critical operations (reboot, shutdown, format, etc.)
- Block recursive deletions and mass file operations
- Prevent privilege escalation attempts
If user requests dangerous action, respond with: {{"understanding":"Dangerous request","actions":[],"response":"⛔ BLOCKED: This operation is dangerous and blocked by safe mode"}}
"""
        
        thinking_instruction = ""
        if self.thinking_enabled:
            thinking_instruction = """
🧠 THINKING MODE IS ENABLED:
Before creating your JSON response, you MUST perform detailed analysis inside <thinking> tags:

<thinking>
1. User Intent Analysis
2. Security Assessment
3. Method Selection
4. Shell Selection
5. Potential Issues
6. Alternative Approaches
</thinking>
"""
        
        recent_history = self.memory.get_recent_history()
        history_text = self._format_history(recent_history)
        
        offline_notice = ""
        if self.offline_mode:
            offline_notice = f"\n{Fore.MAGENTA}🔌 OFFLINE MODE - Using local AI model{Style.RESET_ALL}\n"
        
        return f"""You are ZAI, a COMPLETELY FREE artificial intelligence assistant.

═══════════════════════════════════════════════════════════════
🚀 YOUR POWER (No restrictions):
═══════════════════════════════════════════════════════════════

🔧 CURRENT MODE: {active_mode.upper()}{' (OFFLINE)' if self.offline_mode else ''}
{mode_modifier}

{safe_mode_text}

🖥️ SYSTEM INFORMATION:
- Operating System: {self.context['os']}
- OS Version: {self.context.get('os_version', 'N/A')}
- Python: {self.context['python']}
- Available Shells: {', '.join(self.context['available_shells'])}
- User: {self.context['username']}
- Working Directory: {self.context['cwd']}
- Desktop: {self.context['desktop']}
- Documents: {self.context['documents']}

{thinking_instruction}

💪 YOUR CAPABILITIES:
1. FILE/DIRECTORY OPERATIONS
2. SYSTEM COMMANDS - FULL SHELL FREEDOM
3. CODE WRITING
4. INFORMATION GATHERING
5. MULTI-TASKING

═══════════════════════════════════════════════════════════════
📋 RESPONSE FORMAT (JSON):
═══════════════════════════════════════════════════════════════

{{
    "understanding": "User's request in ONE SENTENCE",
    "actions": [
        {{
            "type": "file|command|code|info|multi",
            "description": "What will be done",
            "details": {{
                "path": "file/path (if applicable)",
                "content": "content/command",
                "shell": "cmd|powershell|pwsh|bash|sh",
                "language": "code language (if applicable)",
                "encoding": "utf-8|cp850|cp1254",
                "mode": "binary|text (if applicable)"
            }}
        }}
    ],
    "response": "Natural language response to user"
}}

═══════════════════════════════════════════════════════════════
📚 CONVERSATION HISTORY:
═══════════════════════════════════════════════════════════════
{history_text}

═══════════════════════════════════════════════════════════════
🎯 CURRENT TASK:
═══════════════════════════════════════════════════════════════
{main_content}

START!"""
    
    def _format_history(self, history):
        """Format conversation history"""
        if not history:
            return "First conversation"
        
        formatted = []
        for msg in history:
            role = "👤 User" if msg['role'] == 'user' else "🤖 ZAI"
            formatted.append(f"{role}: {msg['message'][:100]}...")
        
        return "\n".join(formatted)
    
    def _process_ai_response(self, ai_text, original_request, retry_count=0, force_execute=False, safe_mode=False, show_only=False):
        """Process AI response and execute actions"""
        try:
            if "<thinking>" in ai_text and "</thinking>" in ai_text:
                thinking_start = ai_text.find("<thinking>") + 10
                thinking_end = ai_text.find("</thinking>")
                thinking_content = ai_text[thinking_start:thinking_end].strip()
                
                print(f"\n{Fore.CYAN}🧠 Thinking Process:{Style.RESET_ALL}")
                print(f"{Fore.WHITE}{thinking_content}{Style.RESET_ALL}\n")
            
            json_start = ai_text.find('{')
            json_end = ai_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_text[json_start:json_end]
                ai_plan = json.loads(json_str)
                
                if retry_count == 0:
                    understanding = ai_plan.get('understanding', 'Analyzing...')
                    print(f"\n{Fore.CYAN}💭 Understanding: {understanding}{Style.RESET_ALL}")
                
                actions = ai_plan.get('actions', [])
                
                # --show mode: Display actions but don't execute
                if show_only:
                    self._show_actions_preview(actions, ai_plan.get('response', ''))
                    return {"success": True, "message": "Preview only - no actions executed"}
                
                # --safe mode: Check for dangerous commands
                if safe_mode and actions:
                    blocked = self._check_dangerous_commands(actions)
                    if blocked:
                        print(f"\n{Fore.RED}⛔ BLOCKED by safe mode: {blocked}{Style.RESET_ALL}")
                        return {"success": False, "message": f"Blocked: {blocked}"}
                
                # Show actions and ask for confirmation (unless force)
                if actions and not force_execute:
                    if not self._confirm_actions(actions):
                        print(f"\n{Fore.YELLOW}⚠️ Actions cancelled by user{Style.RESET_ALL}")
                        return {"success": False, "message": "Cancelled by user"}
                
                results = []
                
                if actions:
                    print(f"{Fore.YELLOW}⚡ Executing {len(actions)} action(s)...{Style.RESET_ALL}\n")
                    
                    for i, action in enumerate(actions, 1):
                        result = self._execute_action(action, i, len(actions))
                        results.append(result)
                        
                        if not result.get('success') and retry_count < self.max_retries:
                            print(f"\n{Fore.YELLOW}🔧 Error detected, trying alternative method ({retry_count + 1}/{self.max_retries})...{Style.RESET_ALL}")
                            
                            retry_context = {
                                'action_type': action.get('type', 'unknown'),
                                'description': action.get('description', 'Action'),
                                'shell': action.get('details', {}).get('shell', 'Not specified'),
                                'error': result.get('error', 'Unknown error'),
                                'retry_count': retry_count + 1
                            }
                            
                            return self.think_and_act(original_request, retry_context, force_execute, safe_mode, show_only, retry_count=retry_count + 1)
                        
                        elif not result.get('success') and retry_count >= self.max_retries:
                            print(f"\n{Fore.RED}❌ Max retry limit ({self.max_retries}) reached. Stopping.{Style.RESET_ALL}")
                            break
                        
                        time.sleep(0.1)
                
                success_count = sum(1 for r in results if r.get('success'))
                fail_count = len(results) - success_count
                self.memory.update_stats(successful=success_count, failed=fail_count)
                
                needs_final_response = any(
                    r.get('success') and r.get('output') 
                    for r in results
                )
                
                if needs_final_response:
                    final_response = self._generate_final_response(original_request, results)
                    print(f"\n{Fore.GREEN}🤖 ZAI: {final_response}{Style.RESET_ALL}")
                    response = final_response
                else:
                    response = ai_plan.get('response', 'Operation completed!')
                    print(f"\n{Fore.GREEN}🤖 ZAI: {response}{Style.RESET_ALL}")
                
                if results:
                    color = Fore.GREEN if success_count == len(results) else Fore.YELLOW
                    print(f"{color}📊 Result: {success_count}/{len(results)} successful{Style.RESET_ALL}")
                
                if retry_count == 0 or not any(not r.get('success') for r in results):
                    self.memory.add_conversation("assistant", response)
                
                return {"success": True, "results": results}
            
            else:
                print(f"\n{Fore.CYAN}🤖 ZAI: {ai_text}{Style.RESET_ALL}")
                self.memory.add_conversation("assistant", ai_text)
                return {"success": True, "message": ai_text}
                
        except json.JSONDecodeError:
            print(f"\n{Fore.YELLOW}🤖 ZAI: {ai_text[:500]}{Style.RESET_ALL}")
            return {"success": True, "message": ai_text}
        except Exception as e:
            return self._handle_error(e, original_request)
    
    def _check_dangerous_commands(self, actions):
        """Check if actions contain dangerous commands"""
        for action in actions:
            if action.get('type') == 'command':
                content = action.get('details', {}).get('content', '').lower()
                for dangerous in DANGEROUS_COMMANDS:
                    if dangerous.lower() in content:
                        return f"Dangerous command detected: {dangerous}"
        return None
    
    def _show_actions_preview(self, actions, response):
        """Show actions without executing (--show mode)"""
        print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}👁️  ACTION PREVIEW (--show mode)  👁️{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}\n")
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            description = action.get('description', 'No description')
            details = action.get('details', {})
            
            print(f"{Fore.GREEN}[{i}] {action_type.upper()}: {description}{Style.RESET_ALL}")
            
            if action_type == 'file':
                print(f"    📄 Path: {details.get('path', 'N/A')}")
                print(f"    📝 Encoding: {details.get('encoding', 'utf-8')}")
                content = str(details.get('content', ''))
                if len(content) > 200:
                    print(f"    💾 Content ({len(content)} chars):")
                    print(f"    {Fore.WHITE}{content[:200]}...{Style.RESET_ALL}")
                else:
                    print(f"    💾 Content:\n    {Fore.WHITE}{content}{Style.RESET_ALL}")
            
            elif action_type == 'command':
                print(f"    🐚 Shell: {details.get('shell', 'N/A')}")
                print(f"    💻 Command: {Fore.YELLOW}{details.get('content', 'N/A')}{Style.RESET_ALL}")
                print(f"    📝 Encoding: {details.get('encoding', 'utf-8')}")
            
            elif action_type == 'code':
                print(f"    🔤 Language: {details.get('language', 'N/A')}")
                print(f"    📄 Path: {details.get('path', 'N/A')}")
                content = str(details.get('content', ''))
                if len(content) > 200:
                    print(f"    💾 Code ({len(content)} chars):")
                    print(f"    {Fore.WHITE}{content[:200]}...{Style.RESET_ALL}")
            
            print()
        
        print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🤖 Expected Response:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}⚠️ No actions were executed (--show mode){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}\n")
    
    def _confirm_actions(self, actions):
        """Show actions and ask for confirmation"""
        print(f"\n{Fore.RED}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.RED}⚠️  ACTION CONFIRMATION REQUIRED  ⚠️{Style.RESET_ALL}")
        print(f"{Fore.RED}{'═' * 60}{Style.RESET_ALL}\n")
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            description = action.get('description', 'No description')
            details = action.get('details', {})
            
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
        
        print(f"{Fore.RED}{'═' * 60}{Style.RESET_ALL}")
        
        while True:
            response = input(f"{Fore.YELLOW}Execute these actions? (Y/N): {Style.RESET_ALL}").strip().upper()
            if response in ['Y', 'YES']:
                return True
            elif response in ['N', 'NO']:
                return False
            else:
                print(f"{Fore.RED}Please enter Y or N{Style.RESET_ALL}")
    
    def _execute_action(self, action, index, total):
        """Execute a single action"""
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
            elif action_type == 'code':
                result = self.tools.create_code(details)
            elif action_type == 'info':
                result = self.tools.gather_info(details)
            elif action_type == 'multi':
                result = self.tools.multi_task(details)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            if result.get('success'):
                print(f"{Fore.GREEN}✓{Style.RESET_ALL}")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"{Fore.RED}✗{Style.RESET_ALL}")
                if error_msg and len(error_msg) > 50:
                    print(f"  {Fore.RED}↳ {error_msg[:200]}...{Style.RESET_ALL}")
                else:
                    print(f"  {Fore.RED}↳ {error_msg}{Style.RESET_ALL}")
            
            return result
            
        except Exception as e:
            error_str = str(e)
            print(f"{Fore.RED}✗{Style.RESET_ALL}")
            print(f"  {Fore.RED}↳ {error_str[:200]}{Style.RESET_ALL}")
            return {"success": False, "error": error_str}
    
    def _handle_error(self, error, request):
        """Error handling"""
        error_msg = str(error)
        print(f"\n{Fore.RED}❌ An issue occurred: {error_msg[:200]}{Style.RESET_ALL}")
        return {"success": False, "error": error_msg}
    
    def _generate_final_response(self, original_request, results):
        """Generate final response with command outputs"""
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
            
            prompt = f"""User's question: {original_request}

Operation outputs:
{chr(10).join(outputs)}

Using the outputs above, respond to the user in NATURAL LANGUAGE.
Only write the response text, nothing else. No JSON, no explanation, just the response."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return outputs[0] if outputs else "Operation completed!"


class AITools:
    """Tools that AI can use"""
    
    def handle_file(self, details):
        """File operations with Smart Path Correction"""
        try:
            path = details.get('path', '')
            content = details.get('content', '')
            encoding = details.get('encoding', 'utf-8')
            mode = details.get('mode', 'text')
            
            if not path:
                return {"success": False, "error": "File path not specified"}
            
            # --- AKILLI YOL DÜZELTME (SMART PATH FIX) ---
            # Eğer yol "Desktop/" veya "Documents/" ile başlıyorsa gerçek yola çevir
            path_lower = path.lower()
            if path_lower.startswith("desktop/") or path_lower.startswith("desktop\\"):
                # "Desktop/dosya.txt" -> "C:/Users/Ad/Desktop/dosya.txt"
                real_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                clean_name = path[7:].lstrip('/\\')
                path = os.path.join(real_desktop, clean_name)
                
            elif path_lower.startswith("documents/") or path_lower.startswith("documents\\"):
                real_docs = os.path.join(os.path.expanduser('~'), 'Documents')
                clean_name = path[9:].lstrip('/\\')
                path = os.path.join(real_docs, clean_name)
            # -------------------------------------------
            
            path = os.path.normpath(os.path.expanduser(path))
            
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
            
            return {
                "success": True,
                "path": path,
                "size": file_size,
                "mode": mode
            }
            
        except Exception as e:
            return {"success": False, "error": f"File error: {str(e)}"}
    
    def run_command(self, details):
        """Execute system command"""
        try:
            command = details.get('content', '')
            shell_type = details.get('shell', 'cmd').lower()
            encoding = details.get('encoding', 'utf-8')
            
            if not command:
                return {"success": False, "error": "Command not specified"}
            
            # PowerShell variants
            if shell_type == 'powershell':
                full_command = ['powershell', '-NoProfile', '-Command', command]
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            elif shell_type == 'pwsh':
                full_command = ['pwsh', '-NoProfile', '-Command', command]
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            
            # CMD
            elif shell_type == 'cmd':
                full_command = ['cmd', '/c', command]
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            
            # Git Bash
            elif shell_type == 'git-bash':
                git_bash_paths = [
                    r'C:\Program Files\Git\bin\bash.exe',
                    r'C:\Program Files (x86)\Git\bin\bash.exe',
                    os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\bash.exe')
                ]
                git_bash = None
                for path in git_bash_paths:
                    if os.path.exists(path):
                        git_bash = path
                        break
                
                if git_bash:
                    result = subprocess.run(
                        [git_bash, '-c', command],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        encoding=encoding,
                        errors='replace'
                    )
                else:
                    return {"success": False, "error": "Git Bash not found"}
            
            # WSL
            elif shell_type == 'wsl':
                result = subprocess.run(
                    ['wsl', 'bash', '-c', command],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            
            # Cygwin
            elif shell_type == 'cygwin':
                cygwin_paths = [r'C:\cygwin64\bin\bash.exe', r'C:\cygwin\bin\bash.exe']
                cygwin_bash = None
                for path in cygwin_paths:
                    if os.path.exists(path):
                        cygwin_bash = path
                        break
                
                if cygwin_bash:
                    result = subprocess.run(
                        [cygwin_bash, '-c', command],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        encoding=encoding,
                        errors='replace'
                    )
                else:
                    return {"success": False, "error": "Cygwin not found"}
            
            # Unix shells (bash, sh, zsh, fish, ksh, tcsh, dash)
            elif shell_type in ['bash', 'sh', 'zsh', 'fish', 'ksh', 'tcsh', 'dash']:
                result = subprocess.run(
                    command,
                    shell=True,
                    executable=f'/bin/{shell_type}',
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            
            # Default fallback
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    encoding=encoding,
                    errors='replace'
                )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000] if result.stdout else "",
                "error": result.stderr[:1000] if result.stderr else "",
                "returncode": result.returncode,
                "shell": shell_type
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out (600 seconds)"}
        except Exception as e:
            return {"success": False, "error": f"Command error: {str(e)}"}
    
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
                    info = {
                        "path": path,
                        "file_count": len(files),
                        "files": files[:50]
                    }
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
        return {
            "success": success_count > 0,
            "completed": success_count,
            "total": len(tasks),
            "results": results
        }


class ZAIShell:
    """Main shell interface"""
    
    def __init__(self):
        self.memory = ChromaMemoryManager()
        self.brain = AIBrain(self.memory)
        self.start_time = datetime.datetime.now()
        self.request_count = 0
    
    def show_banner(self):
        """Startup banner"""
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
        
        print(f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════╗
║        🚀 ZAI v6.0 - Advanced AI Assistant               ║
║    Memory • Modes • Thinking • Security • Offline         ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}🤖 I'm ZAI, your COMPLETELY FREE AI assistant{Style.RESET_ALL}
{Fore.GREEN}💡 No restrictions - I can do everything{Style.RESET_ALL}
{Fore.GREEN}⚡ Handle multiple tasks simultaneously{Style.RESET_ALL}
{Fore.MAGENTA}🔧 Auto-retry with DIFFERENT methods on errors{Style.RESET_ALL}
{Fore.CYAN}🐚 Can use {len(ctx['available_shells'])} different shells: {shells}{Style.RESET_ALL}
{Fore.BLUE}🧠 Thinking Mode: {thinking}{Style.RESET_ALL}
{Fore.BLUE}🌐 Network Mode: {offline}{Style.RESET_ALL}
{Fore.BLUE}💾 Memory System: {memory_type}{Style.RESET_ALL}

{Fore.YELLOW}👤 User: {user_name} (since {first_seen}){Style.RESET_ALL}
{Fore.YELLOW}📊 Stats: {stats['total_requests']} requests | {stats['successful_actions']} success | {stats['failed_actions']} failed{Style.RESET_ALL}
{Fore.YELLOW}🔧 Mode: {mode.upper()} - {mode_config['description']}{Style.RESET_ALL}
{Fore.YELLOW}📊 System: {ctx['os']} | Python {ctx['python']}{Style.RESET_ALL}
{Fore.YELLOW}📂 Directory: {ctx['cwd']}{Style.RESET_ALL}

{Fore.BLUE}💬 Examples:{Style.RESET_ALL}
  "Write calculator to desktop"
  "Analyze system status and report"
  "Show top 5 CPU-intensive processes"
  "List all files on desktop"

{Fore.BLUE}🔧 Commands:{Style.RESET_ALL}
  {Fore.CYAN}Modes:{Style.RESET_ALL} normal, eco, lightning (permanent switch)
  {Fore.CYAN}Network:{Style.RESET_ALL} switch offline, switch online
  {Fore.CYAN}Mode Override:{Style.RESET_ALL} "your command eco" (single use)
  {Fore.CYAN}Thinking:{Style.RESET_ALL} thinking on/off
  {Fore.CYAN}Safety Flags:{Style.RESET_ALL}
    --safe / -s  : Block dangerous commands
    --show       : Preview actions without executing
    --force / -f : Skip confirmation
  {Fore.CYAN}Memory:{Style.RESET_ALL} memory clear/show/search [query]
  {Fore.CYAN}Other:{Style.RESET_ALL} clear, exit

{Fore.MAGENTA}🎯 Whatever you want, however you want - I'll handle it!{Style.RESET_ALL}
{Fore.MAGENTA}🐚 I choose the best shell for each command!{Style.RESET_ALL}
{Fore.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
""")
    
    def parse_command(self, user_input):
        """Parse command for special flags and mode overrides"""
        force = False
        safe_mode = False
        show_only = False
        temp_mode = None
        
        # Check for flags (case insensitive)
        user_input_lower = user_input.lower()
        
        if '--force' in user_input_lower or ' -f' in user_input_lower:
            force = True
            # Remove both variations
            user_input = user_input.replace('--force', '').replace('--FORCE', '')
            user_input = user_input.replace(' -f', '').replace(' -F', '')
        
        if '--safe' in user_input_lower or ' -s' in user_input_lower:
            safe_mode = True
            user_input = user_input.replace('--safe', '').replace('--SAFE', '')
            user_input = user_input.replace(' -s', '').replace(' -S', '')
        
        if '--show' in user_input_lower:
            show_only = True
            user_input = user_input.replace('--show', '').replace('--SHOW', '')
        
        # Check for mode override at the end
        words = user_input.split()
        if len(words) > 1:
            last_word = words[-1].lower()
            if ModeManager.is_valid_mode(last_word):
                temp_mode = last_word
                user_input = ' '.join(words[:-1])
        
        return user_input.strip(), force, safe_mode, show_only, temp_mode
    
    def run(self):
        """Main loop"""
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            self.show_banner()
            
            while True:
                try:
                    user_input = input(f"\n{Fore.GREEN}💬 You >>> {Style.RESET_ALL}").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle exit commands
                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        duration = datetime.datetime.now() - self.start_time
                        print(f"\n{Fore.CYAN}👋 Goodbye! Processed {self.request_count} requests.{Style.RESET_ALL}")
                        print(f"{Fore.BLUE}⏱️ Duration: {str(duration).split('.')[0]}{Style.RESET_ALL}")
                        break
                    
                    # Handle clear commands
                    if user_input.lower() in ['clear', 'cls']:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        self.show_banner()
                        continue
                    
                    # Handle offline/online switch
                    if user_input.lower() == 'switch offline':
                        self.brain.switch_to_offline()
                        continue
                    
                    if user_input.lower() == 'switch online':
                        self.brain.switch_to_online()
                        continue
                    
                    # Handle mode switching
                    if user_input.lower() in ModeManager.list_modes():
                        self.brain.switch_mode(user_input.lower(), permanent=True)
                        mode_config = ModeManager.get_mode_config(user_input.lower())
                        print(f"\n{Fore.GREEN}✓ Switched to {user_input.upper()} mode{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}  {mode_config['description']}{Style.RESET_ALL}")
                        continue
                    
                    # Handle thinking toggle
                    if user_input.lower().startswith('thinking'):
                        if 'on' in user_input.lower():
                            self.brain.thinking_enabled = True
                            self.memory.set_thinking(True)
                            print(f"\n{Fore.GREEN}✓ Thinking mode ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.thinking_enabled = False
                            self.memory.set_thinking(False)
                            print(f"\n{Fore.YELLOW}✓ Thinking mode DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.thinking_enabled else "OFF"
                            print(f"\n{Fore.CYAN}Thinking mode is currently: {status}{Style.RESET_ALL}")
                        continue
                    
                    # Handle memory commands
                    if user_input.lower().startswith('memory'):
                        if 'clear' in user_input.lower():
                            self.memory.memory["conversation_history"] = []
                            self.memory.save_memory()
                            print(f"\n{Fore.GREEN}✓ Conversation history cleared{Style.RESET_ALL}")
                        elif 'show' in user_input.lower():
                            history = self.memory.get_recent_history(10)
                            print(f"\n{Fore.CYAN}Recent conversation history:{Style.RESET_ALL}")
                            for msg in history:
                                role = "👤 You" if msg['role'] == 'user' else "🤖 ZAI"
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
                    
                    # Parse command for special flags
                    parsed_input, force, safe_mode, show_only, temp_mode = self.parse_command(user_input)
                    
                    # Apply temporary mode if specified
                    if temp_mode:
                        self.brain.switch_mode(temp_mode, permanent=False)
                        mode_config = ModeManager.get_mode_config(temp_mode)
                        print(f"\n{Fore.MAGENTA}⚡ Using {temp_mode.upper()} mode for this command{Style.RESET_ALL}")
                    
                    # Show mode indicators
                    indicators = []
                    if safe_mode:
                        indicators.append(f"{Fore.GREEN}🛡️ SAFE MODE{Style.RESET_ALL}")
                    if show_only:
                        indicators.append(f"{Fore.CYAN}👁️ SHOW MODE (Preview Only){Style.RESET_ALL}")
                    if force:
                        indicators.append(f"{Fore.RED}⚡ FORCE MODE{Style.RESET_ALL}")
                    
                    if indicators:
                        print(f"\n{' | '.join(indicators)}")
                    
                    self.request_count += 1
                    start = time.time()
                    
                    print(f"\n{Fore.YELLOW}🧠 Thinking...{Style.RESET_ALL}")
                    self.brain.think_and_act(parsed_input, force_execute=force, safe_mode=safe_mode, show_only=show_only)
                    
                    duration = time.time() - start
                    print(f"\n{Fore.WHITE}⏱️ {duration:.2f} seconds{Style.RESET_ALL}")
                    
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}⚠️ Type 'exit' to quit{Style.RESET_ALL}")
                except Exception as e:
                    print(f"\n{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}❌ Shell error: {str(e)}{Style.RESET_ALL}")


def main():
    """Start the program"""
    try:
        zai = ZAIShell()
        zai.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Closing program...{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Startup error: {str(e)}{Style.RESET_ALL}")


if __name__ == "__main__":

    main()
