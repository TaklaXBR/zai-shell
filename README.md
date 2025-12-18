# ZAI Shell

**A Python-based terminal assistant I built to learn how AI agents work**

> **Stop chatting via bloated agents. Start executing with ZAI.**

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

I'm 15 and learning to code. This project started as a way to understand how AI assistants handle commands, retry failed operations, and interact with the system. It's still rough around the edges, but the core features work pretty well.

```bash
pip install google-generativeai colorama
python zaishell.py
```

---

## What It Does

ZAI is a terminal assistant that:
- Runs shell commands (PowerShell, CMD, bash)
- Creates files and folders
- Writes code in different languages
- Auto-retries when commands fail (switches shells, tries different approaches)
- Remembers conversations across sessions
- Has different speed modes

**The cool part:** When something fails, it doesn't just give up. It tries again with a different shell or method. I tested it with 44 different commands and it handled most of them automatically.

---

## Features I'm Proud Of

### 1. Auto-Retry System
If a command fails, ZAI analyzes the error and tries a different approach:
- Switches between PowerShell and CMD
- Changes encoding (UTF-8, CP850)
- Uses Python as a fallback
- Maximum 3 attempts before giving up

**Real example from testing:**
```
User: "Read a file that doesn't exist"
├─ Try 1: PowerShell Get-Content → Failed
├─ Try 2: CMD type command → Failed  
├─ Try 3: Python script → Failed
└─ Try 4: Check if file exists → Success (reports file not found)
```

### 2. Thinking Mode
Toggle `thinking on` to see how ZAI analyzes each request before executing:
```
🧠 ZAI'S THINKING PROCESS:
1. USER ANALYSIS: User wants to list Desktop files
2. METHOD SELECTION: PowerShell Get-ChildItem gives better output
3. RISK ASSESSMENT: Safe operation, no permissions needed
4. EXECUTION PLAN: Single PowerShell command
```

---

### 3. Speed Modes

ZAI supports three execution modes designed to balance **performance, speed, and response quality** depending on your needs.

> ⚠️ Note: The following benchmark is based on a **simple file deletion task**, used only as a baseline test.
> In real-world workloads, performance differences between modes may vary depending on task complexity.

####  Benchmark (File Deletion Test)

* **Normal**: 3.01s
* **Eco**: 3.21s
* **Lightning**: 2.98s

####  Mode Descriptions

* **Normal**
  The most balanced and reliable mode.
  Optimized for **best overall performance and stability**, making it the recommended default for most tasks.

* **Eco**
  Focuses on **token efficiency and reduced resource usage**.
  Slightly slower in some cases, but ideal for longer sessions or cost-sensitive operations.

* **Lightning**
  Tuned for **maximum execution speed** with minimal overhead.
  Provides the fastest responses, trading off detailed reasoning and verbosity.


Switch permanently: `eco` or `lightning`  
Single command: `"your command" eco`

---

### 4. Persistent Memory
ZAI remembers things across sessions:
```bash
# Monday
zai "My favorite color is blue"

# Friday (new session)
zai "What's my favorite color?"
# Remembers: "Your favorite color is blue"
```

Tracks stats: total requests, success rate, etc.

### 5. Force Mode
Skip confirmation prompts when you know what you're doing:
```bash
zai "delete temp files" --force
```
⚠️ Use carefully!

---

## How I Tested It

I ran 44 different commands to see how well it handles real scenarios. Here's what happened:

**Results:**
- ✅ 42/44 successful (95.45%)
- ❌ 2 failed (API rate limits, not ZAI's fault)
- 🔄 12 commands needed auto-retry (all recovered)

**Test categories:**
- File operations (creating, reading, deleting)
- Code generation (Python, C++, HTML/CSS)
- System queries (CPU, memory, processes)
- Error handling (non-existent files, encoding issues)
- Edge cases (dangerous commands, invalid input)

The stress test logs are in Turkish because that's my system language, but ZAI adapts to whatever language your system uses.

---

## Installation

```bash
# 1. Install dependencies
pip install google-generativeai colorama

# 2. Get a free Gemini API key
# Visit: https://makersuite.google.com/app/apikey

# 3. Set your API key
export GEMINI_API_KEY="your_key_here"  # Linux/Mac
$env:GEMINI_API_KEY="your_key_here"    # Windows

# 4. Run ZAI
python zaishell.py
```

---

## Commands

```bash
# Mode switching (permanent)
normal / eco / lightning

# Mode override (single command)
"your command" eco

# Special commands
--force, -f          # Skip approval prompts
thinking on/off      # Show/hide AI thinking process
memory show/clear    # View or clear conversation history
clear / cls          # Clear screen
exit / quit          # Exit ZAI
```

---

## Comparison with Other Tools

I looked at tools like ShellGPT, Open Interpreter, GitHub Copilot CLI, and AutoGPT to understand different approaches:

- **ShellGPT**: Great for quick commands, but no retry on failure
- **Open Interpreter**: Powerful multi-language execution, but manual error handling
- **Copilot CLI**: Repository-aware, but limited free tier (2K requests/month)
- **AutoGPT**: Fully autonomous, but can get stuck in loops

**What makes ZAI different:** The auto-retry system. When other tools fail, you have to manually debug. ZAI tries different shells and methods automatically.

---

## What I Learned

Building this taught me:
- How to work with LLM APIs (Gemini)
- Handling subprocess calls across different shells
- Error recovery strategies
- JSON parsing and validation
- Managing persistent state

## Known Issues

- Sometimes encoding gets messy with Turkish characters
- The thinking mode can be verbose
- Force mode is powerful but risky
- Memory file grows over time (need to implement cleanup)

---

## Contributing

This is an AGPL v3 project. Feel free to fork it, improve it, or suggest changes. I'm still learning, so any feedback helps!

---

## License

**GNU Affero General Public License v3.0**

Created by: Ömer Efe Başol (15, learning to code)

---

**⭐ If this helped you learn something or solved a problem, star it!**  
**🐛 Found a bug? Open an issue - I'll try to fix it**  
**💡 Have an idea? PRs welcome**

---
