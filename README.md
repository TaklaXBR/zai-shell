# ZaiShell

**Autonomous SysOps, DevOps, and Terminal Engineering Agent**

[![Türkçe Belgelendirme](https://img.shields.io/badge/T%C3%BCrk%C3%A7e_Belgelendirme-README__TR.md-red?style=for-the-badge)](README_TR.md)

ZaiShell is an autonomous command-line agent powered by Google Gemini. Built for system administration, software development, and DevOps workflows, it executes multi-step terminal tasks, maintains stateful shell sessions, edits files with precision, and supervises background services.

---

## Core Features

* **Persistent Shell Sessions:** Automatically detects installed shells such as bash, zsh, powershell, pwsh, cmd, wsl, and git-bash. Preserves working directories, environment variables, and active virtual environments across execution steps.
* **Advanced File Editing:** Detects character encodings and preserves original line endings automatically. Supports reading specific line ranges, inserting lines, replacing or deleting line blocks, regex search-and-replace, whitespace-tolerant block matching, and Base64 binary file writing.
* **Virtual Output Buffering:** Captures long command outputs in memory instead of discarding truncated text. Allows the agent to filter outputs via regex search or read specific line ranges on demand without re-running commands.
* **Background Task Management and Auto-Heal:** Runs long-lived services in the background, monitors logs in real time, sends standard input to active tasks, triggers alerts on regex log patterns, and automatically initiates recovery when a service crashes.
* **Interactive Process Control:** Handles command-line tools that wait for user prompts or passwords by inspecting interim outputs and sending live standard input to the running process.
* **Workflow Control and Piping:** Supports piping standard output from one step directly into another, conditional execution based on previous outputs, failure branching, instant local fallback commands, readiness polling, and sequential or parallel execution modes.
* **Resilient Execution and Security:** Includes automatic API retry logic, JSON syntax self-repair, complete process-tree termination on timeouts, and regex-based protection against destructive system commands.

---

## Project Structure

* `zaishell.py` — Main agent loop, workflow orchestration, JSON repair parser, and interactive process handler.
* `terminal_discovery.py` — Dynamic shell discovery and persistent shell session pool.
* `background_manager.py` — Background service supervisor and in-memory virtual output buffer.
* `file_surgery.py` — Encoding-aware file reading, writing, and line-level editing module.
* `security_rules.py` — Regex security filters that block destructive system operations.
* `prompts.py` — System instructions and JSON error recovery templates.

---

## Installation and Usage

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/zaishell.git
cd zaishell
```

### 2. Install Dependencies
```bash
pip install google-genai rich
```

### 3. Set Your API Key

**Linux and macOS:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

**Windows CMD:**
```cmd
set GEMINI_API_KEY=your_api_key_here
```

To use a different model than the default `gemini-3.5-flash-lite`, set the `ZAISHELL_MODEL` environment variable:
```bash
export ZAISHELL_MODEL="gemini-3.8-flash"
```

### 4. Run ZaiShell
```bash
python zaishell.py
```

---

## Execution Controls

Before running a command batch, ZaiShell asks for confirmation:
* `y` — Approve and run the actions.
* `n` — Cancel the current task.
* `skip` — Skip the current approach and ask the agent for an alternative method.
* `q` or `quit` — Close all active sessions and exit.