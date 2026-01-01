import os
import sys
import subprocess
import platform
import uuid

try:
    from posthog import Posthog
    POSTHOG_AVAILABLE = True
except ImportError:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'posthog', '-q'])
        from posthog import Posthog
        POSTHOG_AVAILABLE = True
    except:
        POSTHOG_AVAILABLE = False

from colorama import Fore, Style

OFFLINE_MODEL_PATH = ".zaishell_offline_model"
OFFLINE_MODEL_NAME = "microsoft/phi-2"


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
            
            thinking_part = ""
            if "<thinking>" in response and "</thinking>" in response:
                t_start = response.find("<thinking>")
                t_end = response.find("</thinking>") + 11
                thinking_part = response[t_start:t_end]
            
            json_part = response
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
                    json_part = response[start_index:end_index]
            
            if thinking_part:
                return f"{thinking_part}\n{json_part}"
            
            return json_part
            
        except Exception as e:
            return f"Error generating response: {str(e)}"


class TelemetryManager:
    """PostHog telemetry manager - Privacy-first analytics"""
    
    POSTHOG_API_KEY = 'phc_CXvoppyzIO8O9wbYIheua9XqjBbmWylvuO928J6vI0a'
    POSTHOG_HOST = 'https://us.i.posthog.com'
    
    def __init__(self, memory_manager=None):
        self.memory = memory_manager
        self._user_id = None
        self._initialized = False
        self._posthog = None
        self._load_enabled_state()
        self._init_posthog()
    
    def _load_enabled_state(self):
        """Load telemetry enabled state from memory"""
        if self.memory and hasattr(self.memory, 'memory'):
            self.enabled = self.memory.memory.get("telemetry_enabled", True)
        else:
            self.enabled = True
    
    def _init_posthog(self):
        if not POSTHOG_AVAILABLE:
            self._initialized = False
            return
        try:
            self._posthog = Posthog(self.POSTHOG_API_KEY, host=self.POSTHOG_HOST)
            self._user_id = self._get_or_create_user_id()
            self._initialized = True
        except:
            self._initialized = False
    
    def _get_or_create_user_id(self):
        user_id_file = ".zaishell_telemetry_id"
        try:
            if os.path.exists(user_id_file):
                with open(user_id_file, 'r') as f:
                    return f.read().strip()
            new_id = str(uuid.uuid4())
            with open(user_id_file, 'w') as f:
                f.write(new_id)
            return new_id
        except:
            return str(uuid.uuid4())
    
    def is_enabled(self):
        return self.enabled and self._initialized and POSTHOG_AVAILABLE
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        if self.memory:
            self.memory.memory["telemetry_enabled"] = enabled
            self.memory.save_memory()
    
    def _get_platform_info(self):
        shell_name = "unknown"
        if os.name == 'nt':
            if os.getenv('PSModulePath'):
                shell_name = "powershell"
            else:
                shell_name = "cmd"
        else:
            shell_name = os.getenv('SHELL', 'bash').split('/')[-1]
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "shell": shell_name
        }
    
    def track_event(self, event_name, properties=None):
        if not self.is_enabled() or not self._posthog:
            return
        try:
            event_props = self._get_platform_info()
            if properties:
                event_props.update(properties)
            self._posthog.capture(self._user_id, event_name, event_props)
            self._posthog.flush()
        except:
            pass
    
    def track_interface_preference(self, is_gui):
        self.track_event("interface_preference", {
            "interface_type": "gui" if is_gui else "terminal"
        })
    
    def track_mode_preference(self, mode_name):
        self.track_event("mode_preference", {
            "mode": mode_name
        })
    
    def track_auto_retry(self, retry_count, max_retries, final_success):
        self.track_event("auto_retry", {
            "retry_count": retry_count,
            "max_retries": max_retries,
            "final_success": final_success
        })
    
    def track_task_failure(self, is_complete_failure):
        self.track_event("task_failure", {
            "complete_failure": is_complete_failure
        })
    
    def track_safe_mode_block(self, blocked_command_type):
        self.track_event("safe_mode_block", {
            "blocked_type": blocked_command_type
        })
    
    def track_model_usage(self, is_offline):
        self.track_event("model_usage", {
            "model_type": "offline" if is_offline else "online"
        })
    
    def track_thinking_usage(self, is_enabled):
        self.track_event("thinking_usage", {
            "thinking_enabled": is_enabled
        })
    
    def track_force_command(self):
        self.track_event("force_command_used")
    
    def track_session_start(self, mode, is_offline, gui_enabled, research_enabled, shell_type="unknown"):
        self.track_event("session_start", {
            "initial_mode": mode,
            "offline_mode": is_offline,
            "gui_enabled": gui_enabled,
            "research_enabled": research_enabled,
            "primary_shell": shell_type
        })
    
    def track_session_end(self, request_count, duration_seconds):
        self.track_event("session_end", {
            "total_requests": request_count,
            "duration_seconds": duration_seconds
        })
