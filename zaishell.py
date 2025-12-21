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

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "Enter Your API Key Here")
genai.configure(api_key=GEMINI_API_KEY)

# Memory file path
MEMORY_FILE = ".zaishell_memory.json"

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
            "message": message[:500],  # Limit message length
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.memory["conversation_history"].append(entry)
        # Keep only last 50 conversations
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
- OUTPUT RAW JSON ONLY. No markdown formatting.
- INSTANT action - DO NOT use <thinking> tags.
- ONE action preferred (combine if possible).
- Example response: {"understanding": "Delete logs", "actions": [{"type": "command", "details": {"shell": "cmd", "content": "del *.log"}}], "response": "Done."}
SPEED IS EVERYTHING. BE MINIMAL.
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
        self.model = self._create_model()
        self.tools = AITools()
        self.context = self._build_context()
        self.max_retries = 3
        self.temp_mode = None  # For single-command mode override
        
    def _create_model(self):
        """Create model based on current mode"""
        mode_config = ModeManager.get_mode_config(self.current_mode)
        return genai.GenerativeModel(
            mode_config["model"],
            generation_config={"temperature": mode_config["temperature"]}
        )
    
    def switch_mode(self, new_mode, permanent=True):
        """Switch operation mode"""
        if not ModeManager.is_valid_mode(new_mode):
            return False
        
        if permanent:
            self.current_mode = new_mode
            self.memory.set_mode(new_mode)
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
        """Build system context - Give AI RAW information"""
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
            shells.extend(['cmd', 'powershell'])
            if subprocess.run(['where', 'pwsh'], capture_output=True, shell=True).returncode == 0:
                shells.append('pwsh')
        else:  # Linux/Mac
            shells.extend(['bash', 'sh'])
            if subprocess.run(['which', 'zsh'], capture_output=True, shell=True).returncode == 0:
                shells.append('zsh')
        
        return shells
    
    def think_and_act(self, user_message, retry_context=None, force_execute=False):
        """Main thinking and action engine - Auto retry on error"""
        
        # Reset temp mode after use
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
1. ANALYZE ERROR IN DETAIL:
   - Why did it fail?
   - Was the right shell used?
   - Is command structure appropriate?
   - Encoding issue?

2. FIND A COMPLETELY DIFFERENT METHOD:
   - Use DIFFERENT shell (PowerShell -> CMD or vice versa)
   - Try DIFFERENT commands
   - Use DIFFERENT encoding
   - Apply DIFFERENT approach
   
3. CREATE NEW PLAN:
   - DO NOT REPEAT previous error
   - Choose BEST shell for each command
   - Think freely - you can do anything

REMEMBER: System has {len(self.context['available_shells'])} different shells: {', '.join(self.context['available_shells'])}
You can use all of them! Use different shells for different commands in same task!
"""
            system_instruction = self._build_system_instruction(retry_prompt)
        else:
            system_instruction = self._build_system_instruction(user_message)

        try:
            response = self.model.generate_content(system_instruction)
            return self._process_ai_response(response.text, user_message, force_execute=force_execute)
            
        except Exception as e:
            return self._handle_error(e, user_message)
    
    def _build_system_instruction(self, main_content):
        """Build system instruction - COMPLETELY FREE AI + FULL SHELL FREEDOM"""
        
        active_mode = self._get_active_mode()
        mode_config = ModeManager.get_mode_config(active_mode)
        mode_modifier = mode_config["instruction_modifier"]
        
        thinking_instruction = ""
        if self.thinking_enabled:
            thinking_instruction = """
🧠 THINKING MODE IS ENABLED:
Before creating your JSON response, you MUST perform detailed analysis inside <thinking> tags:

<thinking>
1. User Intent Analysis: What exactly does the user want?
2. Security Assessment: Are there any risks?
3. Method Selection: What's the best approach?
4. Shell Selection: Which shell is most appropriate for each command?
5. Potential Issues: What could go wrong?
6. Alternative Approaches: What are the backup plans?
</thinking>

This thinking process is MANDATORY. Only after completing it, provide your JSON response.
"""
        
        recent_history = self.memory.get_recent_history()
        history_text = self._format_history(recent_history)
        
        return f"""You are ZAI, a COMPLETELY FREE artificial intelligence assistant.

═══════════════════════════════════════════════════════════════
🚀 YOUR POWER (No restrictions):
═══════════════════════════════════════════════════════════════

🔧 CURRENT MODE: {active_mode.upper()}
{mode_modifier}

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
1. FILE/DIRECTORY OPERATIONS:
   - Create/edit/delete files in any format (.py, .txt, .html, .exe, everything)
   - Setup, delete, manage directory structures
   - Handle binary files and everything else

2. SYSTEM COMMANDS - FULL SHELL FREEDOM:
   - Use DIFFERENT shell for each command
   - PowerShell, CMD, bash, sh - all at your command
   - Use multiple shells in same task
   - Leverage advantages of each shell
   - YOU DECIDE which command runs in which shell
   - YOU SOLVE encoding issues yourself (utf-8, cp850, cp1254, whatever needed)
   
3. CODE WRITING:
   - Write and execute code in any language
   - Full applications, tools, games, everything
   
4. INFORMATION GATHERING:
   - System status, processes, network
   - File scanning, analysis
   
5. MULTI-TASKING:
   - Do multiple jobs SIMULTANEOUSLY

═══════════════════════════════════════════════════════════════
⚡ IMPORTANT RULES:
═══════════════════════════════════════════════════════════════

✅ YOUR FREEDOMS:
- YOU decide which command to use
- YOU decide which shell to run it in (PowerShell/CMD/bash/sh)
- YOU set encoding (utf-8, cp850, cp1254)
- If error occurs, try DIFFERENT shell and method
- Be creative - explore all system capabilities
- NO fixed rules - YOU find the best solution for each situation
- Use different shells for different commands in same task

❌ WHAT NOT TO DO:
- Don't say "I can't" - you CAN do EVERYTHING
- Don't repeat the same error
- Don't give technical details to user
- Don't ask for confirmation

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
                "content": "content/command - YOU DECIDE THE BEST",
                "shell": "cmd|powershell|pwsh|bash|sh - YOU CHOOSE BASED ON COMMAND",
                "language": "code language (if applicable)",
                "encoding": "utf-8|cp850|cp1254 - YOU CHOOSE",
                "mode": "binary|text (if applicable)"
            }}
        }}
    ],
    "response": "Natural language response to user"
}}

═══════════════════════════════════════════════════════════════
🎯 SHELL SELECTION GUIDE:
═══════════════════════════════════════════════════════════════

Shells you can use on Windows:
1. CMD (cmd):
   - Simple commands: dir, copy, del, type, echo
   - For quick and simple operations
   - Example: "shell": "cmd", "content": "dir C:\\\\"

2. PowerShell (powershell):
   - Advanced commands: Get-ChildItem, Get-Process, Get-Content
   - Object-based outputs
   - Powerful for filtering and processing
   - Example: "shell": "powershell", "content": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5"

3. PowerShell Core (pwsh):
   - Modern version of PowerShell
   - Faster, cross-platform
   - Use if available

Shells you can use on Linux/Mac:
1. bash: Standard in modern OS
2. sh: Old but universal, for simple operations
3. zsh: Use if available, advanced features

IMPORTANT POINTS:
- You can use DIFFERENT shells in same task!
- Example: CMD for file list, PowerShell for process list
- Adjust command structure based on shell
- PowerShell -> Get-Process, CMD -> tasklist
- PowerShell -> Get-ChildItem, CMD -> dir

═══════════════════════════════════════════════════════════════
💡 USAGE EXAMPLES:
═══════════════════════════════════════════════════════════════

Multi-shell usage example:
{{
    "understanding": "Perform system analysis",
    "actions": [
        {{
            "type": "command",
            "description": "List files",
            "details": {{
                "content": "dir C:\\\\Users",
                "shell": "cmd",
                "encoding": "cp850"
            }}
        }},
        {{
            "type": "command",
            "description": "Analyze processes",
            "details": {{
                "content": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 | Format-Table Name,CPU,WorkingSet",
                "shell": "powershell",
                "encoding": "utf-8"
            }}
        }}
    ],
    "response": "System analysis completed"
}}

═══════════════════════════════════════════════════════════════
📚 CONVERSATION HISTORY:
═══════════════════════════════════════════════════════════════
{history_text}

═══════════════════════════════════════════════════════════════
🎯 CURRENT TASK:
═══════════════════════════════════════════════════════════════
{main_content}

REMEMBER: 
- You are COMPLETELY FREE!
- Choose BEST shell for each command
- Use different shells in same task
- No fixed rules
- YOU find best method for each situation
- If error occurs, try DIFFERENT shell and method
- You can use all system capabilities!

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
    
    def _process_ai_response(self, ai_text, original_request, retry_count=0, force_execute=False):
        """Process AI response and execute actions"""
        try:
            # Extract thinking if present
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
                
                # Show actions and ask for confirmation (unless force)
                if actions and not force_execute:
                    if not self._confirm_actions(actions):
                        print(f"\n{Fore.YELLOW}⚠️ Actions cancelled by user{Style.RESET_ALL}")
                        return {"success": False, "message": "Cancelled by user"}
                
                results = []
                
                if actions:
                    if retry_count > 0:
                        print(f"{Fore.MAGENTA}🔄 Retry {retry_count}/{self.max_retries}...{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}⚡ Executing {len(actions)} action(s)...{Style.RESET_ALL}\n")
                    
                    for i, action in enumerate(actions, 1):
                        result = self._execute_action(action, i, len(actions))
                        results.append(result)
                        
                        if not result.get('success') and retry_count < self.max_retries:
                            print(f"\n{Fore.YELLOW}🔧 Error detected, trying alternative method...{Style.RESET_ALL}")
                            
                            retry_context = {
                                'action_type': action.get('type', 'unknown'),
                                'description': action.get('description', 'Action'),
                                'shell': action.get('details', {}).get('shell', 'Not specified'),
                                'error': result.get('error', 'Unknown error'),
                                'retry_count': retry_count + 1
                            }
                            
                            return self.think_and_act(original_request, retry_context, force_execute)
                        
                        time.sleep(0.1)
                
                # Update statistics
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
    """Tools that AI can use - COMPLETELY FREE + FULL SHELL SUPPORT"""
    
    def handle_file(self, details):
        """File operations"""
        try:
            path = details.get('path', '')
            content = details.get('content', '')
            encoding = details.get('encoding', 'utf-8')
            mode = details.get('mode', 'text')
            
            if not path:
                return {"success": False, "error": "File path not specified"}
            
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
        """Execute system command - FULL SHELL FREEDOM"""
        try:
            command = details.get('content', '')
            shell_type = details.get('shell', 'cmd').lower()
            encoding = details.get('encoding', 'utf-8')
            
            if not command:
                return {"success": False, "error": "Command not specified"}
            
            # Execute command based on shell type
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
            elif shell_type in ['bash', 'sh', 'zsh']:
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
        self.memory = MemoryManager()
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
        
        user_name = self.memory.memory["user"]["name"]
        first_seen = self.memory.memory["user"]["first_seen"][:10]
        stats = self.memory.memory["stats"]
        
        print(f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════╗
║        🚀 ZAI v5.0.1 - Advanced AI Assistant               ║
║         Memory • Modes • Thinking • Security              ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}🤖 I'm ZAI, your COMPLETELY FREE AI assistant{Style.RESET_ALL}
{Fore.GREEN}💡 No restrictions - I can do everything{Style.RESET_ALL}
{Fore.GREEN}⚡ Handle multiple tasks simultaneously{Style.RESET_ALL}
{Fore.MAGENTA}🔧 Auto-retry with DIFFERENT methods on errors{Style.RESET_ALL}
{Fore.CYAN}🐚 Can use {len(ctx['available_shells'])} different shells: {shells}{Style.RESET_ALL}
{Fore.BLUE}🧠 Thinking Mode: {thinking}{Style.RESET_ALL}

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
  {Fore.CYAN}Mode Override:{Style.RESET_ALL} "your command eco" (single use)
  {Fore.CYAN}Thinking:{Style.RESET_ALL} thinking on/off
  {Fore.CYAN}Force Execute:{Style.RESET_ALL} "your command --force" or "-f"
  {Fore.CYAN}Memory:{Style.RESET_ALL} memory clear/show
  {Fore.CYAN}Other:{Style.RESET_ALL} clear, exit

{Fore.MAGENTA}🎯 Whatever you want, however you want - I'll handle it!{Style.RESET_ALL}
{Fore.MAGENTA}🐚 I choose the best shell for each command!{Style.RESET_ALL}
{Fore.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
""")
    
    def parse_command(self, user_input):
        """Parse command for special flags and mode overrides"""
        force = False
        temp_mode = None
        
        # Check for --force or -f
        if user_input.endswith(' --force') or user_input.endswith(' -f'):
            force = True
            user_input = user_input.replace(' --force', '').replace(' -f', '')
        
        # Check for mode override at the end
        words = user_input.split()
        if len(words) > 1:
            last_word = words[-1].lower()
            if ModeManager.is_valid_mode(last_word):
                temp_mode = last_word
                user_input = ' '.join(words[:-1])
        
        return user_input, force, temp_mode
    
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
                        else:
                            stats = self.memory.memory["stats"]
                            print(f"\n{Fore.CYAN}Memory Stats:{Style.RESET_ALL}")
                            print(f"Total requests: {stats['total_requests']}")
                            print(f"Successful actions: {stats['successful_actions']}")
                            print(f"Failed actions: {stats['failed_actions']}")
                        continue
                    
                    # Parse command for special flags
                    parsed_input, force, temp_mode = self.parse_command(user_input)
                    
                    # Apply temporary mode if specified
                    if temp_mode:
                        self.brain.switch_mode(temp_mode, permanent=False)
                        mode_config = ModeManager.get_mode_config(temp_mode)
                        print(f"\n{Fore.MAGENTA}⚡ Using {temp_mode.upper()} mode for this command{Style.RESET_ALL}")
                    
                    self.request_count += 1
                    start = time.time()
                    
                    print(f"\n{Fore.YELLOW}🧠 Thinking...{Style.RESET_ALL}")
                    self.brain.think_and_act(parsed_input, force_execute=force)
                    
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