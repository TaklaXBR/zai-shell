# ZAI Shell
### Autonomous P2P System Administration

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL%20v3.0-green?style=for-the-badge)
![Sentinel](https://img.shields.io/badge/Sentinel-ACTIVE-red?style=for-the-badge)

[![🇹🇷 Türkçe](https://img.shields.io/badge/🇹🇷_TÜRKÇE_BELGELENDİRME-FF0000?style=for-the-badge&logoColor=white)](README_TR.md)

**Manual system administration is dead.**

ZAI Shell is an **autonomous SysOps agent** designed to navigate, repair, and secure complex environments. It translates natural language intent into verified system actions, protects you with **Sentinel**, and enables secure collaboration via **P2P Encrypted Mesh**.

---

## ⚡ Quick Install (2 Minutes)
```bash
# 1. Install Dependencies
pip install google-generativeai colorama psutil posthog pyautogui keyboard

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

## ✨ What's New in v9.1.0?
- ⏱️ **Watch System (`--watch`)**: Set up stateful background monitors (e.g., `--watch if RAM > 80%`). ZAI runs lightweight background scripts and alerts you when conditions are met.
- 🛠️ **Fixer Mode**: A dedicated mode focused exclusively on system repair and troubleshooting. It ignores generic chatter and acts as a pure system medic.
- 👁️ **Visual Context (Ctrl+Shift+Z)**: Take an instant screenshot of your screen and send it directly to ZAI's vision model for context-aware debugging.
- 🛡️ **Enhanced `--show` Mode**: Before executing a command, ZAI now explicitly explains what the command will do, preventing blind executions.

---

## The Core Pillars

### 🧠 Hybrid Intelligence
- **Multi-Modal**: Analyzes screen content (GUI) and images for error diagnosis.
- **Self-Healing**: If a command fails, ZAI changes strategy automatically until the task is done.
- **P2P Mesh**: Collaborate on terminals globally with end-to-end encryption.

### 🛡️ Sentinel 1.5: Risk Intelligence
Sentinel is a self-preservation system that understands context and learns from mistakes.
- Breaks down actions into Structural, Behavioral, Contextual, and Intent risks.
- Maintains a lightweight memory of past failures that caused actual damage.
- Non-blocking: It warns and explains, but the final decision is yours.

### 🔥 Battle-Tested: The "Doomsday" Protocol
> **"It is not enough for an AI to write code. It must be able to survive the consequences."**

We subjected ZAI to a hostile simulator (KERNEL_PANIC, DELETED_BINARIES, PERMISSION_CHAOS).
- **Result**: **65.5% Survival Rate** (57/87 scenarios resolved autonomously).
- **Key Win**: Restored a missing `libssl.so.3` by manually extracting a `.deb` package without `sudo`.
- **[📄 Read the Full Stress Test Results](BENCHMARK/ZAI_DOOMSDAY_PROTOCOL.md)**

---

## Command Reference

| Category | Command | Description |
| :--- | :--- | :--- |
| **Sentinel** | `sentinel status` / `on/off` | View risk metrics, recent warnings, and health score. |
| **P2P Sharing** | `share start` / `connect <IP>` | Host or join a secure encrypted terminal session. |
| **Watch (NEW)** | `--watch <condition>` | Create a background system monitor. |
| | `watch list` / `stop <ID>` | View active monitors or stop them. |
| | `fix watch` | Pass a triggered watch alert to Fixer mode for auto-resolution. |
| **Core** | `switch <mode>` | `online` (Gemini API) or `offline` (Phi-2 Local). |
| | `gui on/off` | Enable desktop automation tools & Vision. |
| | `research on/off` | Enable live web search capability. |
| **Modes** | `normal` / `eco` / `lightning` | Balanced / Token-efficient / Maximum speed. |
| | `fixer` **(NEW)** | Dedicated system repair and troubleshooting. |

---

## 🔐 Privacy & Telemetry
ZAI Shell collects **anonymous** usage data (success rates, error counts) to improve the system. **We NEVER collect your code, file contents, command text, or personal data.**
To disable telemetry: `telemetry off`

**Made with ❤️ by @TaklaXBR | Turkey 🇹🇷**
