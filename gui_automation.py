import base64
import json
import time
from io import BytesIO
from typing import Dict, Optional

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.PAUSE = 0.1
    pyautogui.FAILSAFE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from colorama import Fore, Style


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
