# ZAI Shell

**The AI terminal assistant that actually fixes its own mistakes.**

Most AI tools give up when something fails. ZAI doesn't. It analyzes errors, switches shells, tries different encodings, and keeps going until it works.

![ZAI Shell Auto-Retry Demo](assets/autoretry.gif)

---

## ⚡ Quick Install (2 Minutes)

```bash
# 1. Install dependencies
pip install google-generativeai colorama psutil

# 2. Get free API key from https://aistudio.google.com/app/api-keys

# 3. Set environment variable
# Windows (PowerShell):
$env:GEMINI_API_KEY="your_key_here"

# Linux/Mac:
export GEMINI_API_KEY="your_key_here"

# 4. Run ZAI
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

**[📖 Detailed installation guide below](#-installation-2-minutes)**

---

## 🎯 Why Choose ZAI?

### The Problem with Other AI Assistants

**Traditional AI Assistant:**
```
You: "Create a file with Turkish characters: şğüçöı"
AI: [runs command]
Error: UnicodeDecodeError
AI: "Sorry, there was an error. Please try again."
You: 😤 Manual debugging needed
```

**ZAI:**
```
You: "Create a file with Turkish characters: şğüçöı"

ZAI: [tries UTF-8]
Error: Encoding issue
🔧 Auto-switching to CP850...
Error: Still wrong
🔧 Auto-switching to CP1254...
✓ Success!

You: ✓ File created perfectly, zero manual intervention
```

---

## 📊 ZAI vs Competition

| Feature | ZAI Shell | ShellGPT | Open Interpreter | GitHub Copilot CLI | AutoGPT |
|---------|-----------|----------|------------------|-------------------|---------|
| **Self-Healing Retry** | ✅ 3-attempt auto-fix | ❌ Manual retry | ❌ Manual retry | ❌ Manual retry | ⚠️ Loop-prone |
| **Thinking Mode** | ✅ See AI's logic | ❌ Black box | ❌ Black box | ❌ Black box | ⚠️ Self-feedback |
| **Persistent Memory** | ✅ Cross-session | ✅ Chat sessions | ✅ Session-based | ⚠️ Context only | ✅ Long-term |
| **Multi-Mode System** | ✅ Eco/Lightning/Normal | ❌ Single mode | ❌ Single mode | ❌ Single mode | ❌ Single mode |
| **Force Mode** | ✅ Bypass approval | ❌ N/A | ⚠️ Unsafe auto | ⚠️ Policy-based | ⚠️ Fully autonomous |
| **Shell Intelligence** | ✅ Auto-detect & switch | ✅ Cross-shell | ✅ Multi-language | ✅ Terminal native | ❌ Not terminal-focused |
| **Installation** | ✅ 2 commands | ✅ `pip install` | ⚠️ Docker setup | ⚠️ Auth required | ❌ Complex platform |
| **Cost** | ✅ Free tier friendly | ✅ API costs | ✅ API costs | ⚠️ Limited free tier | ❌ High API costs |
| **Local Execution** | ✅ Terminal-based | ✅ Terminal-based | ✅ Full system access | ✅ Repository aware | ⚠️ Platform/Server |

### Real-World Performance

**Stress Test Results (44 Tasks):**
- ✅ **95.45% success rate** (42/44 completed)
- ✅ **100% success** in file operations, code generation, system info
- ✅ **Auto-retry up to 3 times** with different strategies
- ✅ **Zero critical errors** - handles failures gracefully
- ❌ Only 2 failures due to API quota limits (not ZAI errors)

**What This Means:**
```
Traditional AI: "List all Python files"
└─ Error → You manually fix → Retry → Maybe works

ZAI: "List all Python files"
└─ Error → Auto-switches encoding → Error → Tries different shell → Success ✓
    Time: 22.8 seconds | Your effort: Zero
```

---

## ✨ Key Features

### 🔧 Self-Healing Auto-Retry
When commands fail, ZAI automatically:
- Analyzes errors (encoding, permissions, wrong shell)
- Switches between shells (PowerShell ↔ CMD ↔ bash)
- Changes encoding (UTF-8 → CP850 → CP1254)
- Tries up to 3 times with different strategies

**Real Example:**
```bash
You: "What OS am I on and what's my Python version?"

Attempt 1: [CMD] Get OS info
└─ ❌ FINDSTR: Cannot open AdÄ±"

🔧 Switching to PowerShell...

Attempt 2: [PowerShell] Get OS info
└─ ✅ Success!
      [PowerShell] Get Python version
└─ ❌ Python not found in PATH

🔧 Trying py launcher...

Attempt 3: [CMD] Use py launcher
└─ ✅ Success! Python 3.11.8
```

### 🐚 Multi-Shell Intelligence
- **Windows:** CMD, PowerShell, PowerShell Core
- **Linux/Mac:** bash, sh, zsh
- Auto-selects best shell for each task
- Can use different shells in same request

### 🧠 Thinking Mode
See exactly how ZAI solves problems:
```bash
thinking on   # Show AI's reasoning
thinking off  # Hide thinking process
```

Example output:
```
🧠 Thinking Process:

1. User Intent: "Analyze system performance" - needs CPU, memory, disk
2. Security: Read-only operations, safe
3. Method: PowerShell Get-Process for rich data
4. Plan: Top 5 CPU → Top 5 memory → Disk usage
5. Potential Issues: Large output → limit results

⚡ Executing 3 action(s)...
```

### ⚡ Three Speed Modes

| Mode | Best For | Speed |
|------|----------|-------|
| **Lightning** | Quick operations | ⚡⚡⚡ (2.78s) |
| **Normal** | Regular tasks | ⚡⚡ (3.01s) |
| **Eco** | Long sessions | ⚡ (3.21s) |

```bash
lightning     # Switch permanently
"command" eco # Single command override
```

### 💾 Persistent Memory
Remembers across sessions:
- Your preferences and paths
- Last 50 conversations
- Usage statistics

```bash
# Monday
You: "My project is in C:\Dev\WebApp"
ZAI: ✓ Remembered

# Wednesday (new session)
You: "Add README to my project"
ZAI: ✓ Created C:\Dev\WebApp\README.md
```

### 🛡️ Safety with Force Mode
- **Default:** Confirms every action
- **Force mode:** Skip confirmation with `--force` or `-f`

```bash
"delete temp files" --force  # Executes immediately
```

### 📁 Advanced File Operations
- Any file type (.py, .txt, .md, .json, .csv, .html, .css, .js)
- Auto-detects encoding
- Creates parent directories automatically
- Handles special characters in any language

### 💻 Multi-Task Execution
Execute multiple operations in one request:
```bash
You: "Analyze system and save report to desktop"

⚡ Executing 5 action(s)...
[1/5] Create report file... ✓
[2/5] Get CPU processes... ✓
[3/5] Get memory stats... ✓
[4/5] Get disk usage... ✓
[5/5] Get network info... ✓

📊 Result: 5/5 successful
⏱️ 15.39 seconds
```

### 🎨 Code Generation
Generate code in any language:
- Python, JavaScript, HTML/CSS
- Bash, PowerShell, Batch
- C++, Java, and more

```bash
"Write a web scraper"
→ ✓ Created scraper.py (120 lines with error handling)

"Create calculator webpage"
→ ✓ Created calculator.html (HTML + CSS + JS)
```

---

## 📥 Installation (2 Minutes)

### Prerequisites
- Python 3.8+
- Internet connection

### Quick Setup

**1. Install dependencies:**
```bash
pip install google-generativeai colorama psutil
```

**2. Get free Gemini API key:**
- Visit: https://aistudio.google.com/app/api-keys
- Create API Key

**3. Set environment variable:**

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

**4. Run ZAI:**
```bash
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell
python zaishell.py
```

---

## 📚 Usage Examples

### Basic Operations
```bash
"list files in current directory"
"show disk space"
"create hello.txt with 'Hello World'"
"delete old.txt"
"what's my IP address"
```

### File Management
```bash
"create project folder MyApp"
"add README.md and main.py to MyApp"
"delete all .tmp files"
"move all images to Pictures folder"
```

### System Administration
```bash
"analyze system performance"
"show top 5 CPU processes"
"check disk usage"
"list installed programs"
```

### Development
```bash
"create Python web scraper with error handling"
"generate HTML landing page with CSS"
"write bash backup script"
"setup virtual environment and requirements.txt"
```

### Multi-Step Tasks
```bash
"create project structure: src/, tests/, docs/, README"
"find all log files older than 30 days and archive them"
"scan directory, count file types, create summary"
```

---

## 📋 Command Reference

```bash
# Mode Control
normal          # Balanced mode
eco             # Token-efficient
lightning       # Maximum speed

# Thinking Mode
thinking on     # Show reasoning
thinking off    # Hide reasoning
thinking        # Check status

# Memory
memory          # Show stats
memory show     # View history
memory clear    # Reset history

# Special
--force, -f     # Skip confirmation
clear, cls      # Clear screen
exit, quit      # Exit ZAI
```

---

## 🐛 Known Limitations

- Non-English characters: 90% success with auto-retry
- Thinking mode can be verbose (toggle off when not needed)
- Force mode bypasses safety checks
- Gemini free tier has rate limits (use eco mode)

---

## 🤝 Contributing

**Ways to help:**
- 🐛 Report bugs via GitHub issues
- 💡 Suggest features
- 🔧 Submit pull requests
- 📝 Improve documentation

**Good first issues:**
- Add fish/nushell shell support
- Improve encoding detection
- Create automated tests
- Add code templates

---

## 📝 License

**GNU Affero General Public License v3.0**

---

## 📧 Contact

**Creator:** Ömer Efe Başol (15, learning AI and Python)  
**Email:** oe67111@gmail.com  
**GitHub:** [TaklaXBR](https://github.com/TaklaXBR)

---

<div align="center">
⭐ <strong>If ZAI saved your terminal session, give it a star!</strong> ⭐
</div>
