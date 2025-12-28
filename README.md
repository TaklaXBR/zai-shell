# ZAI Shell

**AI terminal assistant with self-healing capabilities, GUI automation, web research, and P2P collaboration.**

ZAI doesn't give up when errors occur. It analyzes failures, switches strategies, and retries automatically until successful.

![ZAI Shell Auto-Retry Demo](assets/autoretry.gif)

---

## ⚡ Quick Install (2 Minutes)

```bash
# 1. Core dependencies (required)
pip install google-generativeai colorama psutil

# 2. Get free API key
# Visit: https://aistudio.google.com/app/api-keys

# 3. Set environment variable
# Windows PowerShell:
$env:GEMINI_API_KEY="your_key_here"

# Linux/Mac:
export GEMINI_API_KEY="your_key_here"

# 4. Run ZAI
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

**Advanced features are optional** — install when needed:
```bash
# GUI Automation
pip install pyautogui keyboard

# Web Research
pip install ddgs

# Persistent Memory
pip install chromadb

# Offline Mode
pip install transformers torch accelerate

# Image Analysis & Terminal Sharing (built-in, requires Pillow)
pip install pillow
```

**[📖 Full installation guide](#-installation)**

---

## 🎯 Why ZAI Shell?

### The Problem with Other AI Terminals

**Traditional AI:**
```
You: "Create file with Turkish text: şğüçöı"
AI: [runs command]
Error: UnicodeDecodeError
AI: "Error occurred. Please try again."
You: 😤 Manual debugging
```

**ZAI Shell:**
```
You: "Create file with Turkish text: şğüçöı"

ZAI: [tries UTF-8]
Error: Encoding issue
🔧 Auto-switching to CP850...
Error: Still wrong
🔧 Auto-switching to CP1254...
✓ Success!

You: ✓ Zero manual work
```

---

## 📊 ZAI vs Competition

| Feature | ZAI Shell v7.0 | ShellGPT | Open Interpreter | GitHub Copilot CLI | AutoGPT |
|---------|----------------|----------|------------------|-------------------|---------|
| **Self-Healing Retry** | ✅ 5 attempts with strategy switching | ❌ Manual retry | ❌ Manual retry | ❌ Manual retry | ⚠️ Loops possible |
| **GUI Automation** | ✅ PyAutoGUI + AI vision | ❌ Terminal only | ✅ Computer API + OS mode | ❌ Terminal only | ⚠️ Through web browser |
| **Web Research** | ✅ DuckDuckGo + AI synthesis | ⚠️ Via custom functions | ✅ Full internet access | ❌ No direct web search | ✅ Internet access built-in |
| **Image Analysis** | ✅ Gemini Vision | ❌ Not available | ✅ Vision models supported | ❌ Not available | ✅ GPT-4 Vision (multimodal) |
| **Terminal Sharing (P2P)** | ✅ TCP + ngrok global access | ❌ No sharing | ❌ No sharing | ⚠️ GitHub-integrated workflows | ❌ No sharing feature |
| **Persistent Memory** | ✅ ChromaDB vector + JSON fallback | ✅ Chat sessions (--chat flag) | ✅ Conversation history | ⚠️ Limited context | ✅ Long-term + short-term memory |
| **Thinking Mode** | ✅ Toggleable AI reasoning | ❌ Black box | ❌ Black box | ❌ Black box | ⚠️ Shows planning steps |
| **Multi-Mode System** | ✅ Eco/Lightning/Normal + override | ⚠️ Model switching (no presets) | ⚠️ Model selection via flags | ❌ Fixed Copilot model | ❌ GPT-4/3.5 only |
| **Safety Controls** | ✅ --safe/--show/--force flags | ⚠️ Basic confirmation | ✅ Approval-based execution | ✅ Always confirms + MCP policies | ⚠️ Autonomous (high risk) |
| **Offline Mode** | ✅ Phi-2 local (GPU/CPU) | ❌ API only | ✅ Local models via LM Studio/Ollama | ❌ Requires GitHub account | ❌ OpenAI API required |
| **Shell Support** | ✅ 13 shells (CMD/PS/Bash/WSL/etc) | ✅ Cross-platform shells | ✅ Python/JS/Shell runtimes | ✅ Bash/PowerShell/Zsh | ⚠️ Shell agnostic (Python app) |
| **Smart Path Fix** | ✅ Desktop/ → real paths | ❌ Manual paths | ✅ Full filesystem access | ✅ File system operations | ⚠️ Through file operations |
| **Installation** | ✅ pip install (3 packages) | ✅ pip install (1 package) | ✅ pip install (simple) | ⚠️ npm or curl installer | ⚠️ Docker + API keys required |
| **Cost** | ✅ Free tier + offline mode | ⚠️ API costs | ⚠️ API costs | ❌ Paid subscription required | ⚠️ High API usage costs |
| **Hybrid Workflows** | ✅ Terminal + GUI seamlessly | ❌ Terminal only | ✅ Full system + GUI control | ❌ Terminal + GitHub only | ⚠️ Web browser + terminal |
| **Custom Functions** | ✅ Built-in + extensible | ✅ Plugin system + custom functions | ✅ Python execution unlimited | ✅ MCP integrations (extensible) | ✅ Plugin ecosystem |

### Performance Benchmark

**Stress Test (44 Tasks):**
- ✅ **95.45%** success rate (42/44 completed)
- ✅ **100%** success in file operations, code generation, system info
- ✅ Auto-retries up to **5 times** with different strategies
- ✅ **Zero critical errors** — graceful failure handling
- ❌ Only 2 failures due to API quota limits

**Real-World Example:**
```
Traditional: "List Python files"
└─ Error → Manual fix → Retry → Maybe works

ZAI: "List Python files"  
└─ Error → Switch encoding → Error → Try different shell → Error → New approach → ✓
    Time: 22.8s | Your effort: Zero | Attempts: 3/5
```

---

## ✨ v7.0 Features

### 🔧 Self-Healing Auto-Retry (5 Attempts)
Automatically analyzes errors and switches strategies:
- **Encoding detection** (UTF-8 → CP850 → CP1254)
- **Shell switching** (PowerShell ↔ CMD ↔ Bash ↔ Git Bash ↔ WSL)
- **Command approach variations**
- Up to **5 retry attempts** with different methods

**Example:**
```bash
You: "Get OS info and Python version"

[1/5] [CMD] Get OS info
└─ ❌ FINDSTR: Cannot open file

🔧 Switching to PowerShell...

[2/5] [PowerShell] Get OS info
└─ ✅ Success!
      [PowerShell] Get Python version
└─ ❌ Python not in PATH

🔧 Trying py launcher...

[3/5] [CMD] Use py launcher
└─ ✅ Success! Python 3.11.8
```

### 🖱️ GUI Automation Bridge (NEW in v7.0)
Control desktop applications with AI:
- **PyAutoGUI integration** for clicks, typing, hotkeys
- **AI-powered element detection** using screen analysis
- **Hybrid workflows**: Terminal commands + GUI actions
- **Error recovery** with visual feedback

![Opera GX Installation Demo](assets/guiuse.gif)
**Hybrid workflow:** Terminal + GUI automation installing Opera GX  
⭐ GUI steps simulate real user behavior, including natural wait times

**Example:**
```bash
You: "Open Chrome, search for Python docs, click first result"

ZAI generates hybrid plan:
[1] [Terminal] start chrome
[2] [GUI] Type "Python docs" + Enter
[3] [GUI] Click first search result

Execute? (Y/N): Y
✓ All steps completed
```

### 🔍 Web Research Engine (NEW in v7.0)
AI-powered web search with synthesis:
- **DuckDuckGo integration** for live searches
- **AI query optimization** (converts any language → English keywords)
- **Result synthesis** with source attribution
- **Research mode** toggle (on/off)

**Example:**
```bash
You: "python son sürümünü araştır"

Optimized search: "python latest version"
Found 5 results:
1. Python 3.14.2 released - python.org
2. What's new in Python 3.14 - docs.python.org
...

AI: Based on search results, Python 3.14.2 is the latest version Python
```

### 📸 Image Analysis (NEW in v7.0)
Gemini Vision for screenshots and images:
- **Error screenshot analysis** with solutions
- **Supports**: PNG, JPG, JPEG, GIF, BMP, WEBP
- **Context-aware** recommendations
- **Automatic detection** in prompts

**Example:**
```bash
You: "analyze error_screenshot.png"

ZAI: Analyzing image...

Error Identified: ModuleNotFoundError: No module named 'requests'
Cause: Missing dependency
Solution: Run 'pip install requests'
```

### 🌐 P2P Terminal Sharing (NEW in v7.0)
Collaborate in real-time:
- **TCP socket-based** with ngrok support for global access
- **Safe mode enforced**: Host approves all commands
- **Local & Remote**: Works on same network or worldwide
- **Session logs** tracking

**Usage:**
```bash
# Host (your computer)
share
→ Address: 192.168.1.10:5757

# For global access:
ngrok tcp 5757
→ Share: 0.tcp.ngrok.io:12345

# Helper (remote computer)
share connect 0.tcp.ngrok.io:12345

# Helper sends command
share send "list files"

# Host approves
share approve
→ Executing: list files
✓ Results sent to helper
```

### 🐚 13 Shell Support
**Windows:** CMD, PowerShell, PWSH, Git Bash, WSL, Cygwin  
**Linux/Unix:** Bash, Zsh, Fish, Sh, Ksh, Tcsh, Dash

![Cross-Shell Demo](assets/crossshell.gif)
*Using WSL → CMD → PowerShell → WSL in single request*

### 🧠 Thinking Mode
See AI's reasoning process:
```bash
thinking on   # Show reasoning
thinking off  # Hide (faster)
thinking      # Check status
```

**Output:**
```
🧠 Thinking Process:
1. User Intent: System performance analysis
2. Security: Read-only operations, safe
3. Method: PowerShell Get-Process
4. Shell: PowerShell for Windows integration
5. Plan: Top 5 CPU → Top 5 memory → Disk usage
6. Issues: Large output → limit to top 5
7. Alternative: If fails, try tasklist
```

### ⚡ Three Speed Modes + Override
| Mode | Model | Use Case | Speed |
|------|-------|----------|-------|
| **Lightning** | flash-lite (T=0.0) | Max speed, no chat | ⚡⚡⚡ 1.90s |
| **Eco** | flash-lite (T=0.3) | Token-efficient | ⚡⚡ 1.99s |
| **Normal** | flash (T=0.7) | Highest accuracy | ⚡ 3.01s |

```bash
# Permanent switch
lightning
eco  
normal

# Temporary override
"organize desktop" eco
"complex script" normal
```

### 🌐 Offline Mode
Run completely locally:
- **Microsoft Phi-2** (2.7B parameters)
- **GPU or CPU** automatic detection
- **No API costs**, no rate limits
- **Privacy-focused**: Data never leaves machine

```bash
switch offline  # Download model (~5GB first time)
switch online   # Return to API
```

### 💾 Persistent Memory
**Dual system:**
- **ChromaDB**: Vector search for semantic queries
- **JSON**: Automatic fallback, last 50 conversations

```bash
memory              # Stats
memory show         # Recent history
memory search "web scraper"  # Find related
memory clear        # Reset
```

### 🛡️ Safety Controls
```bash
--safe / -s   # Block dangerous commands (rm -rf, format, etc)
--show        # Preview without executing
--force / -f  # Skip confirmation

# Examples
"delete logs" --safe     # Validates first
"organize files" --show  # Shows plan
"create script" --force  # Auto-execute
```

### 📁 Smart Path Correction
Automatically converts shortcuts:
```bash
"Desktop/file.txt" → "C:\Users\YourName\Desktop\file.txt"
"Documents/report.pdf" → "/home/user/Documents/report.pdf"
```

### 💻 Multi-Task Execution
Execute multiple actions in one request:
```bash
You: "Analyze system and save report to Desktop"

⚡ Executing 5 action(s)...
[1/5] [PowerShell] Create report... ✓
[2/5] [PowerShell] CPU stats... ✓
[3/5] [PowerShell] Memory stats... ✓
[4/5] [PowerShell] Disk usage... ✓
[5/5] [PowerShell] Network info... ✓

📊 5/5 successful | ⏱️ 15.39s
```

---

## 📥 Installation

### Prerequisites
- **Python 3.8+** (3.10+ recommended)
- **Internet** (for online mode)

### Step 1: Core Dependencies
```bash
pip install google-generativeai colorama psutil
```

### Step 2: Optional Features
Install only what you need:

```bash
# GUI Automation (enable with: gui on)
pip install pyautogui keyboard

# Web Research (enable with: research on)
pip install ddgs

# Vector Memory (automatic enhancement)
pip install chromadb

# Offline Mode (local AI)
pip install transformers torch accelerate

# Image Analysis (usually pre-installed)
pip install pillow
```

### Step 3: API Key
Get free Gemini API key: https://aistudio.google.com/app/api-keys

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_key_here"

# Permanent:
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your_key_here', 'User')
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_key_here"

# Permanent:
echo 'export GEMINI_API_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Run ZAI
```bash
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

---

## 📋 Command Reference

### Mode Control
```bash
normal          # Balanced (flash, T=0.7)
eco             # Token-efficient (flash-lite, T=0.3)
lightning       # Maximum speed (flash-lite, T=0.1)

# Temporary override
"command" eco
"command" lightning
```

### Feature Toggles
```bash
gui on/off          # GUI automation
research on/off     # Web research
thinking on/off     # AI reasoning display
```

### Network Mode
```bash
switch offline      # Local Phi-2 model
switch online       # Gemini API
```

### Memory
```bash
memory              # Statistics
memory show         # Recent history
memory search "query"  # Semantic search (ChromaDB)
memory clear        # Reset
```

### Terminal Sharing
```bash
share                    # Start hosting
share connect IP:PORT    # Connect to host
share send <command>     # Send command (helper)
share approve/reject     # Handle commands (host)
share status/logs/end    # Utilities
```

### Safety Flags
```bash
--safe, -s      # Block dangerous
--show          # Preview only
--force, -f     # Skip confirmation
```

### Utility
```bash
clear, cls      # Clear screen
exit, quit      # Exit ZAI
```

---

## 🎯 Usage Examples

### Basic Terminal Tasks
```bash
You: "list Python files on Desktop"
You: "show disk space"
You: "create backup folder in Documents"
```

### GUI Automation
```bash
You: "open calculator and compute 123 * 456"
You: "open notepad and type hello world"
You: "search google for AI news and click first result"
```

### Web Research
```bash
You: "what is the latest Python version"
You: "research best practices for REST APIs"
You: "find recent developments in AI"
```

### Image Analysis
```bash
You: "analyze screenshot.png"
You: "explain error in error_log.jpg"
```

### Hybrid Workflows
```bash
You: "download Python installer and run it"
You: "open Chrome, go to GitHub, and clone a repo"
```

### Terminal Sharing
```bash
# Scenario: Help a colleague remotely
Host: share
→ Address: 192.168.1.100:5757

Colleague: share connect 192.168.1.100:5757
Colleague: share send "check server logs"

Host: share approve
→ Command executed, results sent
```

---

## 🐛 Known Limitations

- **Offline mode**: ~5GB download, slower on CPU
- **GUI automation**: Requires display environment
- **Non-English characters**: 95% success with 5-retry system
- **Free API tier**: Rate limits (use eco/offline mode)
- **ChromaDB memory**: Separate installation
- **Terminal sharing**: Requires port forwarding for remote access

---

## 🗺️ Roadmap

### Completed (v7.0 - December 27, 2025)

- ✅ **Hybrid GUI & CLI**: Full terminal + GUI automation
- ✅ **Visual Error Analysis**: Screenshot-based debugging with Gemini Vision
- ✅ **P2P Terminal Sharing**: TCP + ngrok for global collaboration
- ✅ **Live Web Research**: DuckDuckGo integration with AI synthesis

### Future Focus

**v7.x Maintenance:**
- Performance optimizations
- Enhanced error recovery
- Memory management improvements
- Cross-platform compatibility
- Documentation and examples
- Bug fixes and stability

> ZAI v7.0 represents a feature-complete release. Future updates focus on reliability and user experience.

---

## 🤝 Contributing

**Ways to help:**
- 🐛 Report bugs via [GitHub Issues](https://github.com/TaklaXBR/zai-shell/issues)
- 💡 Suggest features
- 🔧 Submit pull requests
- 📝 Improve documentation
- 🌍 Add shell configurations

**Good first issues:**
- Shell configuration examples (Nushell, Fish)
- Encoding detection for other languages
- Automated test suite
- Code templates library
- Performance profiling

---

## 📝 License

**GNU Affero General Public License v3.0**

Open source, free to use and modify.

---

## 🔗 Links

- **GitHub**: [TaklaXBR/zai-shell](https://github.com/TaklaXBR/zai-shell)
- **Legacy Versions**: Check `legacy/` folder for older releases

---

## 📧 Contact

**Creator:** Ömer Efe Başol  
**Age:** 15 (AI & Python enthusiast)  
**Email:** oe67111@gmail.com  
**GitHub:** [@TaklaXBR](https://github.com/TaklaXBR)

---

<div align="center">

⭐ **Star this repo if ZAI saved your terminal session!** ⭐

**Made with by a 15-year-old developer ❤️**

</div>
