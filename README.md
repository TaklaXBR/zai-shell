# ZAI Shell v9.2.0
### Autonomous P2P System Administration Agent

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL%20v3.0-green?style=for-the-badge)
![Sentinel](https://img.shields.io/badge/Sentinel-ACTIVE-red?style=for-the-badge)

[![🇹🇷 Türkçe](https://img.shields.io/badge/🇹🇷_TÜRKÇE_BELGELENDİRME-FF0000?style=for-the-badge&logoColor=white)](README_TR.md)

**Manual system administration is dead.**

ZAI Shell is an **autonomous SysOps agent** designed to navigate, repair, and secure complex environments. It translates natural language intent into verified system actions, protects you with **Sentinel 1.5**, and enables secure collaboration via **P2P Encrypted Mesh**.

---

## 🚀 Why ZAI Shell? (Key Features)

### 🤖 1. Full Autonomy with `--auto`
Don't just give ZAI a command; give it a **mission**. By appending the `--auto` flag, ZAI Shell transitions into a fully autonomous agent. It executes steps, reads terminal outputs, realizes what went wrong, fixes its own mistakes, and loops until the task is **100% complete**.

### ⏱️ 2. Adaptive Operating Modes
Your tasks require different pacing. Switch your agent's mindset instantly:
- 🛠️ **`fixer`**: Sick of reinstalling and blind-guessing? Fixer mode focuses exclusively on system repair and troubleshooting. It acts as a pure system medic to save you time.
- ⚡ **`lightning`**: Need to act faster than other agents? Lightning mode optimizes the thought process for blistering fast command execution.
- 🍃 **`eco`**: Running out of API quotas? Eco mode cuts the fat and preserves your token limits without sacrificing core functionality.
- ⚖️ **`normal`**: The perfect balance of reasoning and action.

### 🛡️ 3. Safe Execution: Undo & Sentinel 1.5
- ⏪ **1-Click Rollback (`undo`)**: Trusted the AI with your file and it broke everything? No worries! ZAI automatically backs up any file it edits. Just type `undo` to restore it instantly.
- 🛑 **Sentinel Risk Intelligence**: Your guardian angel running in the background. It warns you when a destructive command is generated. It even blocks hidden **Prompt Injection** attacks when reading files! Run `sentinel report` to get a summary of your day.

### 👁️ 4. Multi-Modal Context & Vision
- **Conversation Chain Memory**: ZAI doesn't have the memory of a goldfish. It remembers the exact input/output of the last 5 actions to make logical connections.
- **The Agent That Sees (Ctrl+Shift+Z)**: Got an error? No need to copy-paste the code! Take an instant screenshot with a single hotkey, and ZAI will spot the bug immediately.

### 🕒 5. The Sleepless Watchdog (`--watch` + `--force`)
Give the AI a guard duty: `--watch if CPU usage is over 90%`. ZAI will quietly monitor and alert you when it happens.
🔥 **Even crazier:** If you type it as `--watch ... --force`, ZAI won't just alert you. It will **automatically switch to Fixer mode and resolve the issue on its own!** Your system heals itself while you drink your coffee.

### 🌐 6. E2E Encrypted P2P Terminal Sharing
Your friend's PC is broken? No need to install AnyDesk or TeamViewer!
Run `share start` via ZAI's P2P network, and have your friend type `share connect IP`. Your terminals are instantly linked with **end-to-end encryption**. Fix the remote PC directly from your own terminal, fully assisted by your AI agent!

### 🕵️‍♂️ 7. Ultimate Privacy: Local Mode (Microsoft Phi-2)
Paranoid about privacy? Don't want a single byte of your code, error logs, or terminal output leaving your PC? We got you!
Just run `switch offline` to download and run the **Microsoft Phi-2** model entirely on your local machine with **100% offline privacy**.
⚠️ **But be warned!** *"Small model, big problems."* It is nowhere near as smart as Gemini. Keep a close eye on it so it doesn't wreck your system!

---

## ⚡ Quick Install (2 Minutes)
```bash
# 1. Install Dependencies
pip install google-generativeai colorama psutil posthog pyautogui keyboard requests beautifulsoup4

# 2. Set Free Gemini API Key
# For Windows (PowerShell):
$env:GEMINI_API_KEY="your_key_here"
# For Linux/macOS (Bash):
export GEMINI_API_KEY="your_key_here"

# 3. Run
git clone https://github.com/TaklaXBR/zai-shell.git
cd zai-shell
python zaishell.py
```
*Optional: `pip install cryptography` (P2P Encryption), `chromadb` (Long-term Memory)*

---

## 🕹️ Command Reference

| Category | Command | Description |
| :--- | :--- | :--- |
| **Autonomy** | `[your request] --auto` | Fully autonomous loop until task completion. |
| **Safety** | `undo` | Revert the last file modification made by ZAI. |
| | `--safe` / `--show` | Ask for permission before every action / Preview mode. |
| **Sentinel** | `sentinel status` / `on/off` | View risk metrics and health score. |
| | `sentinel report` | Generate a detailed markdown security report. |
| **Watch** | `--watch <condition>` | Create a background system monitor. |
| | `watch list` / `stop <ID>` | View active monitors or stop them. |
| **Modes** | `normal` / `eco` / `lightning` / `fixer` | Change AI behavior dynamically. |
| **P2P Sharing** | `share start` / `connect <IP>` | Host or join a secure encrypted terminal session. |

---

## 🔥 Battle-Tested: The "Doomsday" Protocol
> **"It is not enough for an AI to write code. It must be able to survive the consequences."**

We subjected ZAI to a hostile simulator (KERNEL_PANIC, DELETED_BINARIES, PERMISSION_CHAOS).
- **Result**: **65.5% Survival Rate** (57/87 scenarios resolved autonomously).
- **[📄 Read the Full Stress Test Results](BENCHMARK/ZAI_DOOMSDAY_PROTOCOL.md)**

---

## 🐛 Issues & Contributing
Found a bug while testing the project, or have an awesome idea for a new feature? Please don't hesitate to open an **Issue** on GitHub! Your feedback is incredibly valuable in making ZaiShell even smarter.

---

## 🔐 Privacy & Telemetry
ZAI Shell collects **anonymous** usage data (success rates, error counts) to improve the system. **We NEVER collect your code, file contents, command text, or personal data.**
To disable telemetry: `telemetry off`

**Made with ❤️ by @TaklaXBR | Turkey 🇹🇷**
