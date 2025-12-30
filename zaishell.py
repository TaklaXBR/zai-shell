import os
import sys
import subprocess
import time
import datetime
import json
import platform
import threading
import socket
import base64
import re
import keyboard
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from io import BytesIO

import google.generativeai as genai
from colorama import init, Fore, Style

# Optional imports with fallback
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.PAUSE = 0.1
    pyautogui.FAILSAFE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

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

DANGEROUS_COMMANDS = [
    'rm -rf', 'sudo rm', 'del /f', 'format', 'reboot', 'shutdown',
    'init 0', 'init 6', 'poweroff', 'halt', 'dd if=', 'mkfs',
    ':(){:|:&};:', 'chmod -R 777 /', 'chown -R', '> /dev/sda',
    'mv /* ', 'rm -r /', 'sudo dd', 'fdisk', 'wipefs'
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

SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']

# Shell paths (used in _detect_shells and run_command)
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


class WebResearchEngine:
    """DuckDuckGo web research engine using official library"""
    
    def __init__(self):
        self.max_results = 5
        self.is_available_flag = DDGS_AVAILABLE or (REQUESTS_AVAILABLE and BS4_AVAILABLE)
        self.ai_model = None
    
    def set_ai_model(self, model):
        """Set AI model for query optimization"""
        self.ai_model = model
    
    def is_available(self) -> bool:
        """Check if web research is available"""
        return self.is_available_flag
    
    def optimize_query(self, user_query: str) -> str:
        """Use AI to extract optimal English search keywords"""
        if not self.ai_model:
            return user_query
        
        try:
            prompt = f"""Convert this user query to optimal English search keywords.
User query: "{user_query}"

Rules:
- Extract the main topic/subject
- Convert to English
- Use 2-5 keywords only
- For version queries: add "latest version" or "current version"
- No full sentences, just keywords

Examples:
- "python son sürümünü araştır" → "python latest version"
- "nodejs nasıl kurulur" → "nodejs install tutorial"
- "react ile proje nasıl başlatılır" → "react create project"

Return ONLY the optimized search keywords, nothing else."""

            response = self.ai_model.generate_content(prompt)
            optimized = response.text.strip().strip('"').strip("'")
            if optimized and len(optimized) < 100:
                return optimized
        except:
            pass
        
        return user_query
    
    def search(self, query: str) -> List[Dict]:
        """Perform DuckDuckGo search"""
        
        if DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = []
                    for r in ddgs.text(query, max_results=self.max_results):
                        results.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": r.get("href", "")
                        })
                    return results
            except Exception as e:
                print(f"{Fore.YELLOW}DDGS search error: {e}{Style.RESET_ALL}")
        
        if REQUESTS_AVAILABLE and BS4_AVAILABLE:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
                
                response = requests.get(search_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                for result in soup.select('.result')[:self.max_results]:
                    title_elem = result.select_one('.result__title')
                    snippet_elem = result.select_one('.result__snippet')
                    link_elem = result.select_one('.result__url')
                    
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "url": link_elem.get_text(strip=True) if link_elem else ""
                        })
                
                return results
                
            except Exception as e:
                print(f"{Fore.YELLOW}Web search error: {e}{Style.RESET_ALL}")
        
        return []
    
    def format_results_for_ai(self, results: List[Dict], query: str) -> str:
        """Format search results for AI consumption"""
        if not results:
            return f"No results found for: {query}"
        
        formatted = f"""IMPORTANT: Use the following web search results to answer the user's question.
User asked: "{query}"

Search Results:
"""
        for i, r in enumerate(results, 1):
            formatted += f"\n{i}. {r['title']}\n"
            formatted += f"   Source: {r['url']}\n"
            formatted += f"   Summary: {r['snippet']}\n"
        
        formatted += "\nBased on these search results, provide a helpful and accurate answer."
        return formatted
    
    def print_results_to_user(self, results: List[Dict], query: str):
        """Print formatted results to console for user to see"""
        print(f"\n{Fore.CYAN}Web Search Results for '{query}':{Style.RESET_ALL}\n")
        for i, r in enumerate(results, 1):
            print(f"{Fore.GREEN}{i}. {r['title']}{Style.RESET_ALL}")
            print(f"   {Fore.BLUE}{r['url']}{Style.RESET_ALL}")
            print(f"   {r['snippet'][:150]}...\n")


class ImageAnalyzer:
    """Image file analyzer using Gemini Vision"""
    
    def __init__(self):
        self.model = None
        self.is_available_flag = PIL_AVAILABLE
    
    def _init_model(self):
        """Lazy initialize the model"""
        if self.model is None:
            self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        ext = Path(file_path).suffix.lower().lstrip('.')
        return ext in SUPPORTED_IMAGE_FORMATS
    
    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64"""
        if not self.is_available_flag:
            return None
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"{Fore.RED}Image encoding error: {e}{Style.RESET_ALL}")
            return None
    
    def analyze_image(self, image_path: str, context: str = None) -> Dict:
        """Analyze image and return structured analysis"""
        self._init_model()
        
        if not os.path.exists(image_path):
            return {"success": False, "error": f"File not found: {image_path}"}
        
        if not self.is_supported_format(image_path):
            return {"success": False, "error": f"Unsupported format. Supported: {SUPPORTED_IMAGE_FORMATS}"}
        
        try:
            img_data = self.encode_image_to_base64(image_path)
            if not img_data:
                return {"success": False, "error": "Failed to encode image"}
            
            ext = Path(image_path).suffix.lower().lstrip('.')
            mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
            
            prompt = """Analyze this image in detail. 
If it's an error screenshot, identify:
1. Error type and message
2. Possible causes
3. Suggested solutions

If it's a general image, describe:
1. Main content
2. Text visible (if any)
3. Key elements

Respond in a structured format."""
            
            if context:
                prompt = f"Context: {context}\n\n{prompt}"
            
            response = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": img_data}
            ])
            
            return {
                "success": True,
                "analysis": response.text,
                "file": image_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_error_screenshot(self, image_path: str) -> Dict:
        """Specialized analysis for error screenshots"""
        return self.analyze_image(image_path, context="This is an error screenshot. Focus on identifying the error and providing solutions.")


class GUIAutomationBridge:
    """Bridge between ZAI Shell and GUI Automation"""
    
    def __init__(self, ai_brain=None):
        self.ai_brain = ai_brain
        self.is_available_flag = PYAUTOGUI_AVAILABLE
        self.screen_width = 0
        self.screen_height = 0
        self.model = None
        self.action_history = []
        
        if self.is_available_flag:
            self.screen_width, self.screen_height = pyautogui.size()
    
    def _init_model(self):
        """Initialize model with temperature 0 for deterministic GUI actions"""
        if self.model is None:
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config={'temperature': 0.0, 'top_k': 1}
            )
    
    def is_available(self) -> bool:
        """Check if GUI automation is available"""
        return self.is_available_flag
    
    def capture_screen(self) -> Optional[str]:
        """Capture screen and return as base64"""
        if not self.is_available_flag:
            return None
        try:
            screenshot = pyautogui.screenshot()
            buffer = BytesIO()
            screenshot.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"{Fore.RED}Screenshot error: {e}{Style.RESET_ALL}")
            return None
    
    def execute_action(self, action: Dict) -> Dict:
        """Execute a GUI action"""
        if not self.is_available_flag:
            return {"success": False, "error": "GUI automation not available"}
        
        try:
            action_type = action.get('action', '')
            
            if action_type == 'click':
                x = action.get('x', self.screen_width // 2)
                y = action.get('y', self.screen_height // 2)
                pyautogui.click(x, y)
                print(f"{Fore.GREEN}GUI: Click at ({x}, {y}){Style.RESET_ALL}")
                
            elif action_type == 'doubleclick':
                x = action.get('x', self.screen_width // 2)
                y = action.get('y', self.screen_height // 2)
                pyautogui.doubleClick(x, y)
                print(f"{Fore.GREEN}GUI: Double-click at ({x}, {y}){Style.RESET_ALL}")
                
            elif action_type == 'type':
                text = action.get('text', '')
                pyautogui.write(text, interval=0.03)
                print(f"{Fore.GREEN}GUI: Type '{text[:30]}...'{Style.RESET_ALL}")
                
            elif action_type == 'press':
                key = action.get('key', 'enter')
                pyautogui.press(key)
                print(f"{Fore.GREEN}GUI: Press '{key}'{Style.RESET_ALL}")
                
            elif action_type == 'hotkey':
                keys = action.get('keys', '').split('+')
                pyautogui.hotkey(*keys)
                print(f"{Fore.GREEN}GUI: Hotkey '{'+'.join(keys)}'{Style.RESET_ALL}")
                
            elif action_type == 'scroll':
                amount = action.get('amount', -3)
                pyautogui.scroll(amount)
                print(f"{Fore.GREEN}GUI: Scroll {amount}{Style.RESET_ALL}")
            
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
            
            wait_time = action.get('wait_after', 1)
            time.sleep(wait_time)
            
            self.action_history.append(action)
        
            if len(self.action_history) > 100:
                self.action_history = self.action_history[-100:]
            return {"success": True, "action": action_type}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _draw_grid(self, image, grid_size=10):
        draw = ImageDraw.Draw(image)
        width, height = image.size
        color = (255, 0, 0, 128)
        
        for i in range(1, grid_size):
            y = int(height * i / grid_size)
            draw.line([(0, y), (width, y)], fill=color, width=1)
            
        for i in range(1, grid_size):
            x = int(width * i / grid_size)
            draw.line([(x, 0), (x, height)], fill=color, width=1)
            
        for i in range(grid_size):
            for j in range(grid_size):
                label = f"{chr(65+i)}{j+1}"
                x = int((width * i / grid_size) + 10)
                y = int((height * j / grid_size) + 10)
                try:
                    font = ImageFont.load_default()
                    draw.text((x, y), label, fill=color, font=font)
                except:
                    pass
            
        return image
    
    def find_and_click(self, target_description: str) -> Dict:
        self._init_model()
        
        if not self.is_available_flag:
            return {"success": False, "error": "GUI automation not available"}

        if not PIL_AVAILABLE:
            return {"success": False, "error": "PIL library is required for this feature"}
        
        time.sleep(2)
        
        screen_b64 = self.capture_screen()
        if not screen_b64:
            return {"success": False, "error": "Failed to capture screen"}
            
        try:
            screenshot = Image.open(BytesIO(base64.b64decode(screen_b64)))
            width, height = screenshot.size
            
            grid_image = screenshot.copy()
            self._draw_grid(grid_image)
            
            buffered = BytesIO()
            grid_image.save(buffered, format="PNG")
            grid_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            try:
                logical_width, logical_height = pyautogui.size()
                scale_x = logical_width / width
                scale_y = logical_height / height
            except:
                logical_width, logical_height = width, height
                scale_x, scale_y = 1.0, 1.0
            
            prompt = f"""TASK: find_element_center
Target: "{target_description}"

INSTRUCTIONS:
1. Analyze the red grid overlay (10x10) on the image.
2. Return NORMALIZED coordinates (0-1000 range) for the center of the target.
   - (0,0) = Top-Left, (1000,1000) = Bottom-Right
3. Output JSON ONLY:
   {{
       "found": true,
       "x": <0-1000 int>,
       "y": <0-1000 int>,
       "confidence": <0-100>
   }}
   or {{ "found": false }}"""
            
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/png", "data": grid_b64}
            ])
            
            result_text = response.text.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[0].strip()
                
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                result = json.loads(result_text[start:end])
                
                if result.get('found', False) and result.get('confidence', 0) >= 60:
                    norm_x = result.get('x', 500)
                    norm_y = result.get('y', 500)
                    
                    actual_x = int((norm_x / 1000.0) * width)
                    actual_y = int((norm_y / 1000.0) * height)
                    
                    click_x = int(actual_x * scale_x)
                    click_y = int(actual_y * scale_y)
                    
                    if 0 <= click_x <= logical_width and 0 <= click_y <= logical_height:
                        print(f"{Fore.CYAN}GUI: Click at ({click_x}, {click_y}) confidence: {result.get('confidence')}%{Style.RESET_ALL}")
                        
                        return self.execute_action({
                            'action': 'click',
                            'x': click_x,
                            'y': click_y,
                            'wait_after': 1.5
                        })
                    else:
                        return {"success": False, "error": f"Coordinates out of bounds: ({click_x}, {click_y})"}
                elif result.get('found', False) and result.get('confidence', 0) < 60:
                    return {"success": False, "error": f"Low confidence ({result.get('confidence')}%) for: {target_description}"}
                else:
                    return {"success": False, "error": f"Element not found: {target_description}"}
            
            return {"success": False, "error": "Failed to parse AI response"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class P2PTerminalSharing:
    """Terminal sharing via TCP sockets + ngrok for global access"""
    
    DEFAULT_PORT = 5757
    
    def __init__(self):
        self.share_code = None
        self.is_host = False
        self.is_connected = False
        self.socket = None
        self.client_socket = None
        self.pending_commands = []
        self.safe_mode_always = True
        self.terminal_logs = []
        self.receive_thread = None
        self.running = False
        self.host_port = self.DEFAULT_PORT
    
    def get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def start_sharing_session(self, port: int = None) -> Dict:
        """Start hosting a sharing session"""
        if port:
            self.host_port = port
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.host_port))
            self.socket.listen(1)
            self.socket.settimeout(1)
            
            local_ip = self.get_local_ip()
            self.share_code = f"{local_ip}:{self.host_port}"
            self.is_host = True
            self.is_connected = True
            self.running = True
            self.pending_commands = []
            self.terminal_logs = []
            
            print(f"\n{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   TERMINAL SHARING STARTED{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Local: {Fore.YELLOW}{self.share_code}{Style.RESET_ALL}")
            print(f"\n{Fore.MAGENTA}FOR GLOBAL ACCESS (different cities/countries):{Style.RESET_ALL}")
            print(f"{Fore.WHITE}1. Install ngrok: https://ngrok.com/download{Style.RESET_ALL}")
            print(f"{Fore.WHITE}2. Run: ngrok tcp {self.host_port}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}3. Use the ngrok URL (e.g., 0.tcp.ngrok.io:12345){Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Safe mode: ALWAYS ACTIVE{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Waiting for helper...{Style.RESET_ALL}\n")
            
            self.receive_thread = threading.Thread(target=self._host_listen_loop, daemon=True)
            self.receive_thread.start()
            
            return {"success": True, "local": self.share_code, "port": self.host_port}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _host_listen_loop(self):
        """Host loop: listen for connections"""
        while self.running:
            try:
                if self.client_socket is None:
                    try:
                        client, addr = self.socket.accept()
                        self.client_socket = client
                        self.client_socket.settimeout(0.5)
                        print(f"\n{Fore.GREEN}Helper connected from: {addr[0]}:{addr[1]}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
                        self._send_to_client({"type": "connected"})
                    except socket.timeout:
                        continue
                else:
                    try:
                        data = self.client_socket.recv(4096)
                        if data:
                            msg = json.loads(data.decode('utf-8'))
                            self._handle_helper_message(msg)
                        else:
                            print(f"\n{Fore.YELLOW}Helper disconnected{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
                            self.client_socket.close()
                            self.client_socket = None
                    except socket.timeout:
                        continue
                    except:
                        pass
            except:
                if self.running:
                    time.sleep(0.1)
    
    def _handle_helper_message(self, msg: Dict):
        """Host: handle message from helper"""
        msg_type = msg.get("type", "")
        
        if msg_type == "command":
            cmd_text = msg.get("command", "")
            cmd_id = str(uuid.uuid4())[:8]
            
            print(f"\n{Fore.YELLOW}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}INCOMING COMMAND:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{cmd_text}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*50}{Style.RESET_ALL}")
            
            self.pending_commands.append({
                "id": cmd_id,
                "command": cmd_text,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            print(f"{Fore.YELLOW}Type 'share approve' or 'share reject'{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "log_request":
            self._send_to_client({"type": "logs", "logs": self.terminal_logs[-20:]})
    
    def _send_to_client(self, msg: Dict) -> bool:
        """Send message to helper"""
        if self.client_socket:
            try:
                self.client_socket.send(json.dumps(msg).encode('utf-8'))
                return True
            except:
                return False
        return False
    
    def connect_to_session(self, address: str) -> Dict:
        """Connect to a host (local IP or ngrok URL)"""
        try:
            if ':' in address:
                parts = address.split(':')
                host = parts[0]
                port = int(parts[1])
            else:
                host = address
                port = self.DEFAULT_PORT
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(15)
            
            print(f"{Fore.CYAN}Connecting to {host}:{port}...{Style.RESET_ALL}")
            self.socket.connect((host, port))
            self.socket.settimeout(0.5)
            
            self.share_code = f"{host}:{port}"
            self.is_host = False
            self.is_connected = True
            self.running = True
            
            print(f"\n{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   CONNECTED TO HOST{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Host: {self.share_code}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Use 'share send <command>' to send commands{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Commands need host approval{Style.RESET_ALL}\n")
            
            self.receive_thread = threading.Thread(target=self._helper_receive_loop, daemon=True)
            self.receive_thread.start()
            
            return {"success": True, "host": self.share_code}
            
        except socket.timeout:
            return {"success": False, "error": "Connection timeout"}
        except ConnectionRefusedError:
            return {"success": False, "error": "Connection refused - check address"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _helper_receive_loop(self):
        """Helper: receive messages from host"""
        while self.running:
            try:
                data = self.socket.recv(4096)
                if data:
                    msg = json.loads(data.decode('utf-8'))
                    self._handle_host_message(msg)
                else:
                    print(f"\n{Fore.YELLOW}Host disconnected{Style.RESET_ALL}")
                    self.running = False
                    self.is_connected = False
                    break
            except socket.timeout:
                continue
            except:
                if self.running:
                    time.sleep(0.1)
    
    def _handle_host_message(self, msg: Dict):
        """Helper: handle message from host"""
        msg_type = msg.get("type", "")
        
        if msg_type == "connected":
            print(f"{Fore.GREEN}Connection confirmed{Style.RESET_ALL}")
        elif msg_type == "approved":
            result = msg.get("result", "")
            print(f"\n{Fore.GREEN}Command approved!{Style.RESET_ALL}")
            if result:
                print(f"{Fore.WHITE}{result[:500]}{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
        elif msg_type == "rejected":
            print(f"\n{Fore.RED}Command rejected{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
        elif msg_type == "logs":
            logs = msg.get("logs", [])
            print(f"\n{Fore.CYAN}=== HOST LOGS ==={Style.RESET_ALL}")
            for log in logs:
                ts = log.get('timestamp', '').split('T')[1][:8] if 'T' in log.get('timestamp', '') else ''
                print(f"  [{ts}] {log.get('log', '')[:80]}")
            print(f"\n{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
        elif msg_type == "output":
            output = msg.get("output", "")
            print(f"\n{Fore.CYAN}[HOST]{Style.RESET_ALL} {output}")
            print(f"\n{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
    
    def send_command(self, command: str) -> Dict:
        """Helper: send command to host"""
        if not self.is_connected or self.is_host:
            return {"success": False, "error": "Only helpers can send"}
        
        try:
            msg = {"type": "command", "command": command}
            self.socket.send(json.dumps(msg).encode('utf-8'))
            print(f"{Fore.CYAN}Sent, waiting for approval...{Style.RESET_ALL}")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def approve_pending(self, approve: bool = True) -> Optional[str]:
        """Host: approve/reject pending command"""
        if not self.pending_commands:
            return None
        
        cmd = self.pending_commands.pop(0)
        cmd_text = cmd["command"]
        
        if approve:
            print(f"{Fore.GREEN}Approved{Style.RESET_ALL}")
            self._send_to_client({"type": "approved", "command": cmd_text, "result": "Executing..."})
            return cmd_text
        else:
            print(f"{Fore.YELLOW}Rejected{Style.RESET_ALL}")
            self._send_to_client({"type": "rejected", "command": cmd_text})
            return None
    
    def add_terminal_log(self, log: str, show: bool = False):
        """Add log entry"""
        entry = {"timestamp": datetime.datetime.now().isoformat(), "log": log[:500]}
        self.terminal_logs.append(entry)
        if len(self.terminal_logs) > 100:
            self.terminal_logs = self.terminal_logs[-100:]
        if self.is_host and self.client_socket:
            self._send_to_client({"type": "output", "output": log[:200]})
    
    def broadcast_output(self, output: str):
        """Host: send output to helper"""
        if self.is_host and self.client_socket:
            self._send_to_client({"type": "output", "output": output})
    
    def request_logs(self):
        """Helper: request logs"""
        if not self.is_host and self.socket:
            try:
                self.socket.send(json.dumps({"type": "log_request"}).encode('utf-8'))
            except:
                pass
    
    def get_pending_count(self) -> int:
        return len(self.pending_commands)
    
    def show_recent_logs(self, count: int = 10):
        """Show logs"""
        if not self.is_host:
            self.request_logs()
            print(f"{Fore.CYAN}Requesting logs...{Style.RESET_ALL}")
            return
        
        logs = self.terminal_logs[-count:]
        if not logs:
            print(f"{Fore.YELLOW}No logs{Style.RESET_ALL}")
            return
        print(f"\n{Fore.CYAN}Logs:{Style.RESET_ALL}")
        for log in logs:
            ts = log['timestamp'].split('T')[1][:8]
            print(f"  [{ts}] {log['log'][:80]}")
    
    def end_session(self):
        """End session with proper cleanup"""
        self.running = False
        # Memory leak fix: wait for thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        self.receive_thread = None
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.share_code = None
        self.is_connected = False
        self.is_host = False
        self.pending_commands = []
        self.terminal_logs = []
        print(f"\n{Fore.GREEN}Session ended{Style.RESET_ALL}\n")


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
    
    def set_gui_enabled(self, enabled):
        """Set GUI enabled"""
        self.json_manager.set_gui_enabled(enabled)
        self.memory = self.json_manager.memory
    
    def get_gui_enabled(self):
        """Get GUI enabled status"""
        return self.json_manager.get_gui_enabled()
    
    def set_research_enabled(self, enabled):
        """Set research enabled"""
        self.json_manager.set_research_enabled(enabled)
        self.memory = self.json_manager.memory
    
    def get_research_enabled(self):
        """Get research enabled status"""
        return self.json_manager.get_research_enabled()


class TelemetryManager:
    """PostHog telemetry manager - Privacy-first analytics"""
    
    POSTHOG_API_KEY = 'phc_CXvoppyzIO8O9wbYIheua9XqjBbmWylvuO928J6vI0a'
    POSTHOG_HOST = 'https://us.i.posthog.com'
    
    def __init__(self, memory_manager=None):
        self.enabled = True
        self.memory = memory_manager
        self._user_id = None
        self._initialized = False
        self._posthog = None
        self._init_posthog()
    
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
            
            # Extract thinking block if present
            thinking_part = ""
            if "<thinking>" in response and "</thinking>" in response:
                t_start = response.find("<thinking>")
                t_end = response.find("</thinking>") + 11
                thinking_part = response[t_start:t_end]
            
            # Extract JSON part
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
            
            # Combine if we have thinking
            if thinking_part:
                return f"{thinking_part}\n{json_part}"
            
            return json_part
            
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
    
    @property
    def task_context(self) -> TaskContext:
        """Get task context manager"""
        return self._task_context
    
    @property
    def web_research(self) -> Optional[WebResearchEngine]:
        """Lazy load web research engine (disabled in offline mode)"""
        if self.offline_mode:
            return None
        if self._web_research is None:
            self._web_research = WebResearchEngine()
            self._web_research.set_ai_model(self.model)
        return self._web_research
    
    @property
    def image_analyzer(self) -> ImageAnalyzer:
        """Lazy load image analyzer"""
        if self._image_analyzer is None:
            self._image_analyzer = ImageAnalyzer()
        return self._image_analyzer
    
    @property
    def gui_bridge(self) -> Optional[GUIAutomationBridge]:
        """Lazy load GUI automation bridge (disabled in offline mode)"""
        if self.offline_mode:
            return None
        if self._gui_bridge is None:
            self._gui_bridge = GUIAutomationBridge(self)
        return self._gui_bridge
    
    @property
    def p2p_sharing(self) -> P2PTerminalSharing:
        """Lazy load P2P terminal sharing"""
        if self._p2p_sharing is None:
            self._p2p_sharing = P2PTerminalSharing()
        return self._p2p_sharing
    
    def detect_intent(self, user_message: str) -> Dict:
        """Detect user intent - optimized: skips AI if features disabled"""
        intents = {
            'needs_research': False,
            'needs_image_analysis': False,
            'needs_gui': False,
            'needs_hybrid': False,
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
        

        if not self.gui_enabled and not self.research_enabled:
            return intents
        
        try:
            # Simplified prompt based on enabled features
            intent_prompt = f"""Analyze: "{user_message}"
Return JSON: {{"needs_research": bool, "needs_gui": bool, "needs_hybrid": bool}}
Rules: needs_research=user asks current info/versions; needs_gui=clicking UI; needs_hybrid=both terminal+GUI"""
            
            response = self.model.generate_content(intent_prompt)
            text = response.text
            
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                # Only set if feature is enabled
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
        """Generate a hybrid plan with terminal and GUI steps"""
        if self.offline_mode:
            return None
        
        plan_prompt = f"""Analyze this user request and create an execution plan.
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

If the task can be done entirely with terminal, set needs_gui to false.
Only include GUI steps if clicking/typing in a GUI application is truly needed."""

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
        """Execute a hybrid plan step by step"""
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
                    
                    result = self.tools.run_command({
                        'content': command,
                        'shell': 'cmd',
                        'encoding': 'utf-8'
                    })
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
                                result = self.gui_bridge.execute_action({
                                    'action': 'type',
                                    'text': step.get('text', ''),
                                    'wait_after': step.get('wait_after', 1)
                                })
                            elif action == 'press':
                                result = self.gui_bridge.execute_action({
                                    'action': 'press',
                                    'key': step.get('key', 'enter'),
                                    'wait_after': step.get('wait_after', 1)
                                })
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
        
        return {
            "success": success_count == total,
            "results": results,
            "success_count": success_count,
            "total": total
        }

        
    def _create_model(self):
        """Create model based on current mode"""
        if self.offline_mode:
            return None  # Will use offline model
        mode_config = ModeManager.get_mode_config(self.current_mode)
        
        temperature = mode_config["temperature"]
        if self.current_mode == "lightning":
            temperature = 0.0
        
        return genai.GenerativeModel(
            mode_config["model"],
            generation_config={"temperature": temperature}
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
        if self.telemetry:
            self.telemetry.track_model_usage(True)
        print(f"\n{Fore.GREEN}✓ OFFLINE mode activated{Style.RESET_ALL}")
        print(f"{Fore.CYAN}→ All operations will use local AI model{Style.RESET_ALL}")
        return True
    
    def switch_to_online(self):
        """Switch back to online mode"""
        self.offline_mode = False
        self.memory.set_offline_mode(False)
        self.model = self._create_model()
        if self.telemetry:
            self.telemetry.track_model_usage(False)
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
            if self.telemetry:
                self.telemetry.track_mode_preference(new_mode)
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
            
            # Check Git Bash - use global constant
            for path in GIT_BASH_PATHS:
                if os.path.exists(path):
                    shells.append('git-bash')
                    break
            
            # Check WSL (Windows Subsystem for Linux)
            if subprocess.run(['where', 'wsl'], capture_output=True, shell=True).returncode == 0:
                shells.append('wsl')
            
            # Check Cygwin - use global constant
            if any(os.path.exists(p) for p in CYGWIN_PATHS):
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
                
                if mode_temperature <= 0.0:
                    mode_temperature = 0.1
                
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
        finally:
            if self.telemetry and retry_count == 0:
                active_mode = self._get_active_mode()
                self.telemetry.track_mode_preference(active_mode)
                self.telemetry.track_model_usage(self.offline_mode)
                self.telemetry.track_thinking_usage(self.thinking_enabled)
    
    def _build_system_instruction(self, main_content, safe_mode=False):
        """Build system instruction"""
        
        
        if self.offline_mode:
            
            if self.thinking_enabled:
                return f"""You are a command line tool.
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
Output:"""
            
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
                        if self.telemetry:
                            self.telemetry.track_safe_mode_block(blocked)
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
                            if self.telemetry:
                                self.telemetry.track_auto_retry(retry_count + 1, self.max_retries, False)
                            
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
                            if self.telemetry:
                                self.telemetry.track_task_failure(True)
                                self.telemetry.track_auto_retry(retry_count, self.max_retries, False)
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
                
                if retry_count > 0 and success_count == len(results) and self.telemetry:
                    self.telemetry.track_auto_retry(retry_count, self.max_retries, True)
                
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
            
        except Exception:
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
            
            path_lower = path.lower()
            if path_lower.startswith("desktop/") or path_lower.startswith("desktop\\"):

                real_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                clean_name = path[7:].lstrip('/\\')
                path = os.path.join(real_desktop, clean_name)
                
            elif path_lower.startswith("documents/") or path_lower.startswith("documents\\"):
                real_docs = os.path.join(os.path.expanduser('~'), 'Documents')
                clean_name = path[9:].lstrip('/\\')
                path = os.path.join(real_docs, clean_name)
            
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
        """Execute system command - optimized"""
        command = details.get('content', '')
        shell_type = details.get('shell', 'cmd').lower()
        encoding = details.get('encoding', 'utf-8')
        
        if not command:
            return {"success": False, "error": "Command not specified"}
        
        def _run(cmd_args, use_shell=False, executable=None):
            """Helper to run subprocess with common params"""
            return subprocess.run(
                cmd_args, shell=use_shell, executable=executable,
                capture_output=True, text=True, timeout=600,
                encoding=encoding, errors='replace'
            )
        
        def _find_path(paths):
            """Find first existing path from list"""
            for p in paths:
                if os.path.exists(p):
                    return p
            return None
        
        try:
            # Direct command mappings
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
    """Main shell interface v7.0"""
    
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
        """Startup banner v7.0"""
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
            sharing_line = f"\n{Fore.MAGENTA}🔗 Terminal Sharing: ACTIVE ({code}){Style.RESET_ALL}"
        
        print(f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════╗
║            🚀 ZAI v7.0.2 - Advanced AI Shell                 ║
║     Terminal • GUI • Research • Image • P2P Sharing        ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}🤖 I understand natural language in ANY language{Style.RESET_ALL}
{Fore.GREEN}💡 No restrictions - completely free AI assistant{Style.RESET_ALL}
{Fore.GREEN}⚡ Auto-retry with different methods on errors{Style.RESET_ALL}
{Fore.CYAN}🐚 Shells: {shells}{Style.RESET_ALL}

{Fore.BLUE}🧠 Thinking: {thinking} | 🌐 Network: {offline} | 💾 Memory: {memory_type}{Style.RESET_ALL}
{Fore.BLUE}🖱️ GUI: {gui_status} | 🔍 Research: {research_status}{Style.RESET_ALL}{sharing_line}

{Fore.YELLOW}👤 User: {user_name} (since {first_seen}){Style.RESET_ALL}
{Fore.YELLOW}📊 Stats: {stats['total_requests']} requests | {stats['successful_actions']} success | {stats['failed_actions']} failed{Style.RESET_ALL}
{Fore.YELLOW}🔧 Mode: {mode.upper()} - {mode_config['description']}{Style.RESET_ALL}

{Fore.BLUE}🔧 Commands:{Style.RESET_ALL}
  {Fore.CYAN}Features:{Style.RESET_ALL} gui on/off, research on/off
  {Fore.CYAN}Modes:{Style.RESET_ALL} normal, eco, lightning
  {Fore.CYAN}Network:{Style.RESET_ALL} switch offline, switch online
  {Fore.CYAN}Thinking:{Style.RESET_ALL} thinking on/off
  {Fore.CYAN}Sharing:{Style.RESET_ALL} share, share connect IP:PORT, share end
  {Fore.CYAN}Memory:{Style.RESET_ALL} memory clear/show/search [query]
  {Fore.CYAN}Safety:{Style.RESET_ALL} --safe, --show, --force
  {Fore.CYAN}Other:{Style.RESET_ALL} clear, exit

{Fore.MAGENTA}🎯 Just tell me what you need - I'll figure out how!{Style.RESET_ALL}
{Fore.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
""")
    
    def handle_share_command(self, user_input: str) -> bool:
        """Handle share command - returns True if handled"""
        parts = user_input.split()
        
        if len(parts) == 1:
            self.brain.p2p_sharing.start_sharing_session()
            return True
        
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            
            if subcommand == 'start':
                port = int(parts[2]) if len(parts) >= 3 else None
                self.brain.p2p_sharing.start_sharing_session(port)
                return True
            
            elif subcommand == 'connect' and len(parts) >= 3:
                connection_string = parts[2]
                result = self.brain.p2p_sharing.connect_to_session(connection_string)
                if not result.get('success'):
                    print(f"{Fore.RED}Connection failed: {result.get('error')}{Style.RESET_ALL}")
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
            
            elif subcommand == 'end':
                self.brain.p2p_sharing.end_session()
                return True
            
            elif subcommand == 'status':
                if self.brain.p2p_sharing.is_connected:
                    role = "HOST" if self.brain.p2p_sharing.is_host else "HELPER"
                    print(f"\n{Fore.CYAN}=== SHARING STATUS ==={Style.RESET_ALL}")
                    print(f"{Fore.GREEN}Role: {role}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Address: {self.brain.p2p_sharing.share_code}{Style.RESET_ALL}")
                    if self.brain.p2p_sharing.is_host:
                        pending = self.brain.p2p_sharing.get_pending_count()
                        connected = self.brain.p2p_sharing.client_socket is not None
                        print(f"{Fore.CYAN}Helper Connected: {'Yes' if connected else 'No'}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Pending Commands: {pending}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.YELLOW}Not connected to any sharing session{Style.RESET_ALL}")
                return True
            
            elif subcommand == 'logs':
                self.brain.p2p_sharing.show_recent_logs()
                return True
            
            elif subcommand == 'approve':
                if self.brain.p2p_sharing.is_host:
                    cmd = self.brain.p2p_sharing.approve_pending(True)
                    if cmd:
                        print(f"{Fore.GREEN}Executing: {cmd}{Style.RESET_ALL}")
                        self.brain.think_and_act(cmd, force_execute=True, safe_mode=True)
                    else:
                        print(f"{Fore.YELLOW}No pending commands{Style.RESET_ALL}")
                return True
            
            elif subcommand == 'reject':
                if self.brain.p2p_sharing.is_host:
                    self.brain.p2p_sharing.approve_pending(False)
                return True
        
        print(f"""
{Fore.CYAN}=== TERMINAL SHARING ==={Style.RESET_ALL}
  share                   - Start session (port 5757)
  share connect IP:PORT   - Connect to host
  share send <command>    - Send command (helper)
  share approve/reject    - Handle commands (host)
  share status/logs/end   - Other commands

{Fore.MAGENTA}FOR GLOBAL ACCESS:{Style.RESET_ALL}
  1. Host: Run 'ngrok tcp 5757'
  2. Share the ngrok URL (e.g., 0.tcp.ngrok.io:12345)
  3. Helper: 'share connect 0.tcp.ngrok.io:12345'
""")
        return True
    
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
        """Main loop v7.0 with intent-based processing"""
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
                    
                    # Handle mode switching
                    if user_input.lower() in ModeManager.list_modes():
                        self.brain.switch_mode(user_input.lower(), permanent=True)
                        mode_config = ModeManager.get_mode_config(user_input.lower())
                        print(f"\n{Fore.GREEN}✓ Switched to {user_input.upper()} mode{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}  {mode_config['description']}{Style.RESET_ALL}")
                        continue
                    
                    # Handle GUI toggle
                    if user_input.lower().startswith('gui'):
                        if 'on' in user_input.lower():
                            if not PYAUTOGUI_AVAILABLE:
                                print(f"\n{Fore.YELLOW}GUI automation requires pyautogui and keyboard packages.{Style.RESET_ALL}")
                                choice = input(f"{Fore.CYAN}Install now? (Y/N): {Style.RESET_ALL}").upper()
                                if choice == 'Y':
                                    os.system('pip install pyautogui keyboard')
                                    print(f"\n{Fore.GREEN}✓ Installed! Please restart ZAI Shell to use GUI.{Style.RESET_ALL}")
                                continue
                            self.brain.gui_enabled = True
                            self.memory.set_gui_enabled(True)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_interface_preference(True)
                            print(f"\n{Fore.GREEN}✓ GUI automation ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.gui_enabled = False
                            self.memory.set_gui_enabled(False)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_interface_preference(False)
                            print(f"\n{Fore.YELLOW}✓ GUI automation DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.gui_enabled else "OFF"
                            print(f"\n{Fore.CYAN}GUI automation: {status}{Style.RESET_ALL}")
                        continue
                    
                    # Handle Research toggle
                    if user_input.lower().startswith('research'):
                        if 'on' in user_input.lower():
                            if not DDGS_AVAILABLE and not (REQUESTS_AVAILABLE and BS4_AVAILABLE):
                                print(f"\n{Fore.YELLOW}Web research requires ddgs package.{Style.RESET_ALL}")
                                choice = input(f"{Fore.CYAN}Install now? (Y/N): {Style.RESET_ALL}").upper()
                                if choice == 'Y':
                                    os.system('pip install ddgs')
                                    print(f"\n{Fore.GREEN}✓ Installed! Please restart ZAI Shell to use research.{Style.RESET_ALL}")
                                continue
                            self.brain.research_enabled = True
                            self.memory.set_research_enabled(True)
                            print(f"\n{Fore.GREEN}✓ Web research ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.research_enabled = False
                            self.memory.set_research_enabled(False)
                            print(f"\n{Fore.YELLOW}✓ Web research DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.research_enabled else "OFF"
                            print(f"\n{Fore.CYAN}Web research: {status}{Style.RESET_ALL}")
                        continue
                    
                    # Handle thinking toggle
                    if user_input.lower().startswith('thinking'):
                        if 'on' in user_input.lower():
                            self.brain.thinking_enabled = True
                            self.memory.set_thinking(True)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_thinking_usage(True)
                            print(f"\n{Fore.GREEN}✓ Thinking mode ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.brain.thinking_enabled = False
                            self.memory.set_thinking(False)
                            if self.telemetry.is_enabled():
                                self.telemetry.track_thinking_usage(False)
                            print(f"\n{Fore.YELLOW}✓ Thinking mode DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.brain.thinking_enabled else "OFF"
                            print(f"\n{Fore.CYAN}Thinking mode is currently: {status}{Style.RESET_ALL}")
                        continue
                    
                    # Handle telemetry toggle
                    if user_input.lower().startswith('telemetry'):
                        if 'on' in user_input.lower():
                            self.telemetry.set_enabled(True)
                            print(f"\n{Fore.GREEN}✓ Telemetry ENABLED{Style.RESET_ALL}")
                        elif 'off' in user_input.lower():
                            self.telemetry.set_enabled(False)
                            print(f"\n{Fore.YELLOW}✓ Telemetry DISABLED{Style.RESET_ALL}")
                        else:
                            status = "ON" if self.telemetry.is_enabled() else "OFF"
                            print(f"\n{Fore.CYAN}Telemetry is currently: {status}{Style.RESET_ALL}")
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
                    
                    if intents['needs_image_analysis'] and intents['image_path']:
                        print(f"\n{Fore.CYAN}Analyzing image: {intents['image_path']}{Style.RESET_ALL}")
                        analysis = self.brain.image_analyzer.analyze_image(intents['image_path'])
                        if analysis.get('success'):
                            print(f"\n{Fore.GREEN}🤖 ZAI: {analysis.get('analysis', 'No analysis available')}{Style.RESET_ALL}")
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