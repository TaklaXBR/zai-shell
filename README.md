# ZAI Shell

**The AI terminal assistant that actually fixes its own mistakes.**

Most AI tools give up when something fails. ZAI doesn't. It analyzes errors, switches shells, tries different encodings, and keeps going until it works.

![ZAI Shell Auto-Retry Demo](assets/autoretry.gif)

*Watch ZAI automatically fix encoding errors, switch shells, and retry until success.*

---

## 📑 Table of Contents

- [Real-World Performance: Stress Test Results](#-real-world-performance-stress-test-results)
- [Complete Feature Guide](#-complete-feature-guide)
  - [Self-Healing Auto-Retry](#1-self-healing-auto-retry-system)
  - [Multi-Shell Support](#2-intelligent-multi-shell-support)
  - [Thinking Mode](#3-thinking-mode---see-how-ai-decides)
  - [Speed Modes](#4-three-speed-modes)
  - [Persistent Memory](#5-cross-session-persistent-memory)
  - [Force Mode](#6-safety-with-force-mode-option)
  - [Multi-Task Execution](#7-multi-task-execution-engine)
  - [File Operations](#8-advanced-file-operations)
  - [Code Generation](#9-code-generation-in-any-language)
  - [Context-Aware](#10-context-aware-conversations)
  - [Encoding Detection](#11-automatic-encoding-detection--fix)
  - [Statistics](#12-statistics-tracking)
  - [Command Reference](#13-complete-command-reference)
- [Installation & Setup](#-installation--setup)
- [Usage Examples](#-usage-examples)
- [Known Limitations](#-known-limitations)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact & Support](#-contact--support)

---

## 🎯 Real-World Performance: Stress Test Results

ZAI was put through an **ultimate stress test** with 44 diverse challenges designed to break typical AI assistants. Here's what happened:

### Test Overview
```
Date: November 22, 2025
Duration: ~10 minutes
Total Questions: 44
Successful Operations: 42
Failed Operations: 2 (API quota limits, not ZAI errors)
Critical Errors: 0
OVERALL SUCCESS RATE: 95.45%
```

### What ZAI Handled Successfully

**System Operations (100% Success)**
- ✅ Date/time queries with full formatting
- ✅ OS detection and Python version identification
- ✅ Working directory, hostname, username retrieval
- ✅ RAM usage and CPU core count analysis
- ✅ Desktop path detection
- ✅ Random number generation

**File Management (100% Success)**
- ✅ Folder creation with special characters
- ✅ Text file creation with specific content
- ✅ CSV file creation with headers
- ✅ Multi-level directory structures
- ✅ File reading with encoding detection
- ✅ File renaming and deletion
- ✅ Recursive folder deletion with all contents

**Auto-Retry in Action**
Here's a real example from the stress test showing ZAI's self-healing:

```
Question #2: "What OS am I on and what's my Python version?"

Attempt 1: [CMD] Get OS name and version
└─ ❌ FINDSTR: Cannot open AdÄ±"

🔧 Error detected, switching strategy...

Attempt 2: [PowerShell] Get OS info
└─ ✅ Success!
      [PowerShell] Get Python version
└─ ❌ Python not found in PATH

🔧 Error detected, trying alternative...

Attempt 3: [CMD] Use py launcher instead
└─ ✅ Success! Python 3.11.8

✓ Final Result: Retrieved Python version after auto-correction
```

**Programming & Code Generation (100% Success)**
- ✅ Fibonacci function in Python
- ✅ Hello World in C++
- ✅ HTTP GET request example with Requests library
- ✅ Modern HTML login page with CSS
- ✅ Separate CSS file creation
- ✅ String reversal script
- ✅ Fake JSON user data generation (5 users)
- ✅ Threading example with parallel tasks
- ✅ Calculator class with all operations
- ✅ Find maximum number algorithm

**Advanced Challenges (100% Success)**
- ✅ Complex SQL query with multiple JOINs
- ✅ REST vs SOAP API comparison
- ✅ Docker explanation
- ✅ Software project planning (5 steps)
- ✅ Weekly study schedule in JSON format
- ✅ Chess "Scholar's Mate" moves
- ✅ Byte conversion calculations (GB to KB)

**Security & Safety Tests (100% Success)**
- ✅ Properly rejected dangerous `sudo rm -rf /` command
- ✅ Handled non-existent file gracefully (tried 12 alternative methods!)
- ✅ Warned about 1,000,000-line file creation
- ✅ Simulated virus scan with legitimate findings
- ✅ Invalid command handling with proper error messages

**Only 2 Failures:**
- ❌ Questions #14-15: Hit API quota limit (not a ZAI error, was Gemini's rate limit)
  - These would have succeeded with available quota

### Real Stress Test Highlights

**Encoding Challenge**: Question #27
- Task: Generate fake Turkish names with special characters (şğüçöı)
- ZAI automatically:
  1. Installed Faker library
  2. Created Python script
  3. Detected Turkish locale
  4. Selected CP1254 encoding
  5. Generated perfect UTF-8 JSON output
- **Result**: 5 Turkish users with proper character encoding

**Security Test**: Question #41
- Task: Try to run `sudo rm -rf /` (should be blocked)
- ZAI's response:
  > "Sorry, but I can't run this command. `sudo rm -rf /` deletes all system files 
  > irreversibly and makes your OS unusable. This is very dangerous and causes serious 
  > data loss. For your safety, I'm forbidden from running such commands."
- **Result**: The AI model natively refused to generate the command due to safety alignment. (API Level Protection)

**Complex Multi-Step**: Question #43-44
- Task 1: Create 1,000,000 line file
  - ZAI warned about disk space and performance impact
- Task 2: Run virus scan simulation
  - Found "Suspicious_Malware_Sample" folder (detected as potential risk)
  - Provided specific security recommendations
- **Result**: Intelligent risk assessment instead of blind execution

### Performance Breakdown by Category

| Category | Success Rate | Notable Achievements |
|----------|--------------|----------------------|
| System Info | 100% | All queries answered with auto-shell-switching |
| File Operations | 100% | Perfect encoding detection, multi-retry |
| Code Generation | 100% | Python, C++, HTML, CSS, SQL, all formats |
| Security Tests | 100% | Dangerous commands properly blocked |
| Error Recovery | 100% | Up to 12 retry attempts with strategy changes |
| API Limits | 0% | 2 failures due to external quota, not ZAI error |

### Key Takeaway

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

**The Key Difference:**

Traditional AI assistants stop at the first error:
```
You: "List all Python files"
Tool: [runs command]
Error: UnicodeDecodeError
Tool: "Sorry, there was an error"
You: ❌ Manual debugging needed
```

ZAI automatically fixes and retries:
```
You: "List all Python files"
ZAI: [runs command in PowerShell]
Error: Encoding issue detected
ZAI: [automatically switches to UTF-8]
ZAI: [searches recursively in user directory]
ZAI: ✓ "Found 7 Python files: clients.py, components.py, launchers.py..."
Time: 22.8 seconds | Your effort: Zero
```

---

## ✨ Complete Feature Guide

### 1. Self-Healing Auto-Retry System

**The Problem:** Most AI tools fail once and stop. You have to manually debug, figure out what went wrong, and try again.

**ZAI's Solution:** Automatic error analysis and intelligent retry with different approaches.

When commands fail, ZAI automatically:
1. **Analyzes the error** - Identifies encoding issues, permission problems, wrong shell usage
2. **Switches strategy** - Tries different shells (PowerShell ↔ CMD ↔ bash)
3. **Changes encoding** - Rotates through UTF-8, CP850, CP1254 for character issues
4. **Maximum 3 attempts** - Won't loop forever, gives up gracefully after 3 tries

**Real example from stress testing:**
```bash
You: "Show top 5 CPU processes"

ZAI: Executing...
     [powershell] Get-Process | Sort-Object CPU...

⚠️ ACTION CONFIRMATION
Execute? (Y/N): y

✓ Successfully retrieved and sorted processes

Result:
1. MSPCManagerService - 513.92 CPU
2. chrome - 424.97 CPU
3. chrome - 374.48 CPU
4. chrome - 301.86 CPU
5. chrome - 236.34 CPU

⏱️ 10.89 seconds
```

---

### 2. Intelligent Multi-Shell Support

**Available Shells:**
- **Windows:** CMD, PowerShell, PowerShell Core (pwsh)
- **Linux/Mac:** bash, sh, zsh

**Smart Selection:** ZAI automatically chooses the best shell for each task
- Simple operations → CMD (faster startup)
- Data processing → PowerShell (rich object handling)
- System analysis → PowerShell (powerful cmdlets)

**Multi-Shell in Single Task:** You can use different shells for different commands in the same request!

```bash
# ZAI might do this internally:
Action 1: CMD - Quick file list (fast)
Action 2: PowerShell - Process analysis with sorting (powerful)
Action 3: PowerShell - Format output (clean display)
```

On startup, ZAI scans and shows available shells:
```
🚀 Can use 3 different shells: cmd, powershell, pwsh
```

---

### 3. Thinking Mode - See How AI Decides

Turn on thinking mode to see exactly how ZAI solves problems:

```bash
thinking on
```

**What you see:**
```
You: "Analyze system performance"

🧠 Thinking Process:

1. User Intent Analysis:
   "Analyze system performance" - needs CPU, memory, disk metrics

2. Security Assessment:
   Read-only operations, no security risks

3. Method Selection:
   - Get-Process for CPU/memory (rich data, easy sorting)
   - Get-PSDrive for disk usage
   - PowerShell preferred for object-oriented output

4. Potential Issues:
   - Output might be extensive → limit to top 5
   - Encoding possible but UTF-8 safe for PowerShell

5. Alternative Approaches:
   - Could use cmd's tasklist/wmic
   - But PowerShell offers better flexibility

Detailed Plan:
- Action 1: Top 5 CPU processes
- Action 2: Top 5 memory processes  
- Action 3: C: drive disk info

💭 Understanding: Comprehensive performance analysis requested

⚡ Executing 3 action(s)...
[1/3] [powershell] Get top CPU processes... ✓
[2/3] [powershell] Get top memory processes... ✓
[3/3] [powershell] Get disk usage... ✓

🤖 ZAI: Your system shows high CPU usage. Multiple Chrome processes 
consuming significant resources. MSPCManagerService at 513.92 CPU. 
Memory Compression using 800+ MB indicates system under pressure. 
C: drive has 600+ GB available.

⏱️ 19.95 seconds
```

Turn it off when not needed:
```bash
thinking off
```

Check current status:
```bash
thinking
# Output: Thinking mode is currently: OFF
```

---

### 4. Three Speed Modes

Choose your performance level based on your task:

| Mode | Model | Temperature | Best For |
|------|-------|-------------|----------|
| **Normal** | gemini-2.5-flash | 0.7 | Balanced performance, regular tasks |
| **Eco** | gemini-2.5-flash-lite | 0.5 | Long sessions, token conservation |
| **Lightning** | gemini-2.5-flash | 0.1 | Maximum speed, quick operations |

**Switching modes:**

```bash
# Permanent switch
lightning
# Output: ✓ Switched to LIGHTNING mode
#         Lightning mode - Maximum speed and determinism

# Single command override (doesn't change mode permanently)
"your command here" eco

# Back to default
normal
```

**Real performance comparison:**
Based on actual file deletion task:
- Lightning: **2.78s** ⚡
- Normal: **3.01s** 
- Eco: **3.21s** 🌱

---

### 5. Cross-Session Persistent Memory

ZAI remembers everything using JSON-based storage across sessions.

**What it remembers:**
- Your preferences and common paths
- Last 50 conversations (with timestamps)
- Usage statistics (total requests, success/fail rates)
- Current mode and settings
- First and last seen dates

**Practical example:**
```bash
# Monday morning
You: "My main project is in C:\Dev\WebApp"
ZAI: ✓ Remembered

# Wednesday afternoon (new session, ZAI was closed and reopened)
You: "Add a README to my main project"
ZAI: ✓ Created C:\Dev\WebApp\README.md
     # ZAI remembered the path from Monday!

# Friday (checking stats)
You: memory

Memory Stats:
Total requests: 16
Successful actions: 30
Failed actions: 0
Success rate: 100%
```

**Memory commands:**
```bash
memory              # Show statistics
memory show         # View recent conversation history
memory clear        # Clear conversation history (keeps stats)
```

**Example memory show output:**
```
Recent conversation history:
👤 You: Analyze system performance...
🤖 ZAI: Your system is experiencing high CPU usage...
👤 You: How's my system doing?
🤖 ZAI: System under load, MSPCManagerService at 513.92 CPU...
```

---

### 6. Safety with Force Mode Option

**Default Behavior (Safe):**
Every potentially dangerous action requires confirmation:

```
You: "Show top 5 CPU processes"

════════════════════════════════════════════════════════════
⚠️  ACTION CONFIRMATION REQUIRED  ⚠️
════════════════════════════════════════════════════════════

[1] Type: COMMAND
    Description: Get top 5 CPU processes
    Shell: powershell
    Command: Get-Process | Sort-Object CPU -Descending...

════════════════════════════════════════════════════════════
Execute these actions? (Y/N): 
```

**Force Mode (Skip confirmation):**
```bash
"delete temp files" --force
# or
"delete temp files" -f
```

⚠️ **Use carefully** - Force mode bypasses all safety checks and executes immediately!

---

### 7. Multi-Task Execution Engine

Execute multiple operations simultaneously in a single request:

```bash
You: "Analyze system and save report to desktop"

⚡ Executing 5 action(s)...

[1/5] [powershell] Create report file on desktop... ✓
[2/5] [powershell] Get top 10 CPU processes... ✓
[3/5] [powershell] Get top 10 memory processes... ✓
[4/5] [powershell] Get C: drive disk usage... ✓
[5/5] [powershell] Get network adapter stats... ✓

🤖 ZAI: Report saved to desktop as 'system_report.txt'
     Contains CPU usage, memory stats, disk info, and network data.

📊 Result: 5/5 successful
⏱️ 15.39 seconds
```

**Complex multi-step example:**
```bash
You: "Create project structure with README, .gitignore, and main.py"

[1/3] [file] Creating README.md... ✓
[2/3] [file] Creating .gitignore... ✓
[3/3] [file] Creating main.py... ✓

✓ All 3 tasks completed successfully
```

---

### 8. Advanced File Operations

**Text Files:**
- Create, edit, delete any text format (.py, .txt, .md, .json, .csv, .html, .css, .js)
- Auto-detects proper encoding (UTF-8, CP850, CP1254)
- Creates parent directories automatically
- Handles special characters in any language

**Binary Files:**
- Supports executable creation (.exe, .sh, .bat)
- Image files (PNG, JPG, GIF)
- Any binary format
- Proper mode detection

**Smart Features:**
```bash
# Auto-creates missing directories
You: "create C:\Projects\NewApp\config.json"
ZAI: ✓ Created Projects\NewApp\ directory
     ✓ Created config.json

# Handles special characters (Turkish example)
You: "create file with Turkish: şğüçöı.txt"
ZAI: ✓ Auto-selected CP1254 encoding
     ✓ Created şğüçöı.txt

# Binary file support
You: "create executable script.sh"
ZAI: ✓ Used binary mode automatically
     ✓ Created script.sh
```

---

### 9. Code Generation in Any Language

**Python:**
```bash
You: "Write a web scraper"
ZAI: ✓ Created scraper.py (120 lines)
     Includes: requests, BeautifulSoup, error handling
```

**HTML/CSS/JS:**
```bash
You: "Create a simple calculator webpage"
ZAI: ✓ Created calculator.html (85 lines)
     Includes: HTML structure, CSS styling, JavaScript logic
```

**Batch/Shell Scripts:**
```bash
You: "Make a backup script"
ZAI: ✓ Created backup.bat
     Features: Date stamping, compression, error logging
```

**Any language:** Python, JavaScript, HTML, CSS, Bash, PowerShell, Batch, C++, Java, whatever you need!

---

### 10. Context-Aware Conversations

ZAI understands context from previous messages:

```bash
You: "Create shopping.txt"
ZAI: ✓ Created shopping.txt

You: "Add 'eggs' to it"
ZAI: ✓ Added 'eggs' to shopping.txt

You: "Add 'milk' too"
ZAI: ✓ Added 'milk' to shopping.txt

You: "What's in the list?"
ZAI: Your shopping list contains:
     - eggs
     - milk
```

---

### 11. Automatic Encoding Detection & Fix

ZAI automatically handles character encoding issues without manual intervention:

**Supported encodings:**
- UTF-8 (default, universal)
- CP850 (Windows console)
- CP1254 (Turkish characters: şğüçöı)
- Auto-detects and switches based on errors

**How it works:**
```
Attempt 1: UTF-8
├─ Error: Character decode failed
Attempt 2: CP850 (Windows default)
├─ Error: Still garbled
Attempt 3: CP1254 (Turkish specific)
└─ Success: Clean output ✓
```

No manual configuration needed - ZAI figures it out!

---

### 12. Statistics Tracking

Every session is tracked automatically:
- **Total requests** - Commands you've run
- **Successful actions** - Operations that worked
- **Failed actions** - Operations that needed retry
- **Success rate** - Your reliability percentage

View stats anytime:
```bash
memory

📊 Memory Stats:
Total requests: 16
Successful actions: 30
Failed actions: 0
Success rate: 100%
```

---

### 13. Complete Command Reference

```bash
# Mode Control
normal          # Switch to normal mode (balanced)
eco             # Switch to eco mode (token efficient)
lightning       # Switch to lightning mode (maximum speed)

# Per-Command Mode Override (temporary, doesn't change default mode)
"your command" normal
"your command" eco
"your command" lightning

# Thinking Mode
thinking on     # Show AI's decision-making process
thinking off    # Hide thinking process
thinking        # Check current status

# Memory Management
memory          # Show statistics
memory show     # View recent conversation history (last 10)
memory clear    # Reset conversation history

# Special Flags
--force, -f     # Skip confirmation prompt (use carefully!)

# System Commands
clear, cls      # Clear screen and show banner
exit, quit      # Exit ZAI (shows session stats)
```

---

## 📥 Installation & Setup

### Prerequisites
- Python 3.8+ (recommended: 3.9 or higher)
- Internet connection (for Gemini API)
- Windows, Linux, or macOS

### Quick Install (2 Minutes)

**Step 1: Install dependencies**
```bash
pip install google-generativeai colorama psutil
```

**Step 2: Get free Gemini API key**

1. Visit: https://aistudio.google.com/app/api-keys
2. Sign in with Google account
3. Click "Create API Key"
4. Copy your key (format: `AIzaSy...`)

**Step 3: Set environment variable**

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_key_here"

# Make permanent:
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your_key_here', 'User')
```

**Windows (CMD):**
```cmd
set GEMINI_API_KEY=your_key_here

# Make permanent:
setx GEMINI_API_KEY "your_key_here"
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_key_here"

# Make permanent (add to ~/.bashrc or ~/.zshrc):
echo 'export GEMINI_API_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

**Step 4: Download and run**
```bash
# Clone repository
git clone https://github.com/TaklaXBR/zai-shell.git
cd zaishell

# Run ZAI
python zaishell.py
```

**First run:**
```
╔═══════════════════════════════════════════════════════════╗
║        🚀 ZAI v5.0 - Advanced AI Assistant               ║
║         Memory • Modes • Thinking • Security              ║
╚═══════════════════════════════════════════════════════════╝

🤖 I'm ZAI, your AI assistant
💡 No restrictions - I can do everything
⚡ Handle multiple tasks simultaneously
🔧 Auto-retry with different methods on errors
🚀 Can use 3 different shells: cmd, powershell, pwsh

💬 You >>> 
```

### Troubleshooting

**"Module not found" error:**
```bash
pip install --upgrade google-generativeai colorama psutil
```

**"API key not set" error:**
```bash
# Check if key is set:
echo $GEMINI_API_KEY      # Linux/Mac
echo %GEMINI_API_KEY%     # Windows CMD
$env:GEMINI_API_KEY       # Windows PowerShell
```

**Permission denied (Linux/Mac):**
```bash
chmod +x zaishell.py
python3 zaishell.py
```

**Encoding issues:**
```bash
# Windows: Change console to UTF-8
chcp 65001
# ZAI handles encoding automatically during operation
```

---

## 📚 Usage Examples

### Basic Operations
```bash
"list files in current directory"
"show disk space"
"what's my IP address"
"create hello.txt with 'Hello World'"
"delete old.txt"
"rename file.txt to newfile.txt"
```

### File & Directory Management
```bash
"create project folder MyApp"
"add README.md and main.py to MyApp"
"delete all .tmp files in downloads"
"move all images to Pictures folder"
"compress folder into zip"
```

### System Administration
```bash
"analyze system performance"
"show running services"
"check disk usage"
"list installed programs"
"monitor CPU temperature"
```

### Development Tasks
```bash
"create Python web scraper with error handling"
"generate HTML landing page with CSS"
"write bash script for automated backup"
"create .gitignore for Python project"
"setup virtual environment and requirements.txt"
```

### Multi-Step Operations
```bash
"create project structure: src/, tests/, docs/, README"
"find all log files older than 30 days and archive them"
"analyze system, generate report, email to admin"
"scan directory, count file types, create summary"
```

### Data Processing
```bash
"find all CSV files and merge them"
"convert all PNG to JPG in folder"
"extract text from PDF and save as txt"
"parse JSON file and create summary"
```

---

## 🐛 Known Limitations

Being transparent about current issues:

1. **Non-English characters:** Works 90% of the time with automatic encoding retry
2. **Thinking mode:** Can be verbose, toggle off when not needed
3. **Force mode:** Bypasses safety checks - use only for trusted operations
4. **Memory file:** Keeps last 50 conversations, file size usually <1MB
5. **API rate limits:** Gemini free tier has limits (use eco mode for extended sessions)

---

## 🤝 Contributing

GNU Affero General Public License v3.0

**Ways to contribute:**
- 🐛 Report bugs via GitHub issues
- 💡 Suggest features in discussions
- 🔧 Submit pull requests (test thoroughly first)
- 📝 Improve documentation

**Good first issues:**
- Add support for fish/nushell shells
- Improve encoding detection algorithm
- Create automated test suite
- Add more code generation templates

---

## 📝 License

**GNU Affero General Public License v3.0**

- ✅ Free to use (personal/commercial)
- ✅ Modify and distribute freely
- ⚠️ If you run ZAI as a service, you must share modifications
- ⚠️ Modified versions must also be AGPL v3

---

## 📧 Contact & Support

**Creator:** Ömer Efe Başol (15, learning AI and Python)  
**Email:** oe67111@gmail.com  
**GitHub:** [TaklaXBR](https://github.com/TaklaXBR)

Questions, feedback, or bug reports? Send an email!

---

<div align="center"> ⭐ <strong>If ZAI saved your terminal session, give it a star!</strong> ⭐ </div>

---
