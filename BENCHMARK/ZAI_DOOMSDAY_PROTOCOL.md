# ZAI Shell "Doomsday" Stress Test Protocol
### *Automated Reliability & Self-Healing Benchmark for Autonomous AI Agents*

> **"It is not enough for an AI to write code. It must be able to survive the consequences of its own environment."**

## 1. Project Overview

The **ZAI Shell Stress Test** (or "Doomsday Protocol") is an advanced, destructive testing framework designed to evaluate the resilience, self-healing capabilities, and security awareness of autonomous AI agents.

This is **not** a standard unit test. It is a **hostile environment simulator**.
The framework actively sabotages the operating system—deleting compilers, modifying partitions, creating zombie processes, and obfuscating permissions. The AI Agent is dropped into this broken environment with **zero hints**, **no stack traces**, and **no assistance**. It must rely entirely on the **OODA Loop** (Observe, Orient, Decide, Act) to deduce the root cause and engineer a fix.

---

## 2. The "Doomsday" Methodology: Zero-Hint Protocol

The core philosophy of this test is **Cognitive Stress**. The Agent is not fully informed of *how* the system was broken, only *that* a specific domain (e.g., "Network") is failing.

1.  **Blind Execution**: The Agent often wakes up in a shell where `ls`, `sudo`, or `pip` simply do not exist. It receives no error logs until it tries to run a command and fails.
2.  **The Logic Gap**: In **OODA Logic** scenarios, the error is not a crash, but a subtle misconfiguration (e.g., "Why is the disk full?" → Agent must find the hidden 10GB sparse file in a nested directory tree).
3.  **Adversarial Conditions**: The "Breaker" script actively fights the user (e.g., mounting `/tmp` as `noexec` to prevent script execution, or making files immutable so `rm` fails).

### The Break-Heal-Verify Loop
*   **The Breaker**: Executes privileged, destructive changes.
*   **The Healer (AI)**: Must autonomously explore, diagnose, and repair.
*   **The Validator**: Mathematically proves system restoration.

---

## 3. The Gauntlet: Extreme Difficulty Categories

The suite subjects the AI to **6 categories of chaos**, each designed to test a specific "cognitive muscle" of the Agent:

### 1. Dependency Hell
*   **Difficulty**: ⭐⭐⭐⭐
*   **The Challenge**: Critical system binaries (`pip`, `npm`, `gcc`, `make`, `git`) are forcibly removed or replaced with broken symlinks pointing to `/bin/false`.
*   **Required Logic**: The Agent cannot just "reinstall"—it often lacks the tools *to* reinstall (e.g., `apt` cache is corrupted). It must perform manual binary reconstruction or find alternative installation routes (e.g., compiling from source without a compiler).

### 2. Kernel & Service Surgery
*   **Difficulty**: ⭐⭐⭐⭐⭐
*   **The Challenge**: Breaking the OS while it runs. Unloading essential kernel modules, modifying `fstab` to cause boot failures, stopping system journals, and corrupting time synchronization (`chrony`/`systemd-timesyncd`).
*   **Required Logic**: High-risk operations. The AI must understand Linux internals to reload kernel modules or edit filesystem tables without crashing the session.

### 3. Filesystem Destruction
*   **Difficulty**: ⭐⭐⭐⭐
*   **The Challenge**: Inode exhaustion (creating 100,000 tiny files), circular symlink traps, immutable file attributes (`chattr +i`), and "Russian Doll" directory nesting.
*   **Required Logic**: The Agent must diagnose why "Disk Full" errors occur when `df -h` shows space is available (inodes), or why `rm` fails on a file owned by root (immutable bit).

### 4. OODA Loop Logic
*   **Difficulty**: ⭐⭐⭐⭐⭐
*   **The Challenge**: Pure logic puzzles.
    *   *Example*: "The server is slow." (Cause: A rogue background process hidden among legitimate ones).
    *   *Example*: "Logs aren't rotating." (Cause: A subtle config syntax error).
*   **Required Logic**: There is no error message. The Agent must **Observe** the system state, **Orient** itself within the process tree, **Decide** on a hypothesis, and **Act** to verify it.

### 5. Red Team / Security
*   **Difficulty**: ⭐⭐⭐⭐⭐
*   **The Challenge**: The system is made vulnerable. World-writable shadow files, SUID bash binaries in `/tmp`, and malicious cron jobs downloading payloads.
*   **Required Logic**: The Agent must act as a Security Engineer, identifying privilege escalation vectors and patching them immediately.

### 6. Chaos Engineering
*   **Difficulty**: ⭐⭐⭐⭐⭐
*   **The Challenge**: Unpredictable combinations of all above.
*   **Required Logic**: Endurance and adaptation.

---

## 4. Performance Report
**Session ID:** `20260117_091537`
**Duration:** 2 Hours 33 Minutes

The AI Agent was pushed to its limits, engaging in **165 valid self-healing loops**—meaning it failed, analyzed its own failure, and corrected its strategy 165 times without human intervention.

### Success Metrics

| Category | Success Rate | Analysis |
| :--- | :--- | :--- |
| **Dependency Hell** | **85.7%** | Dominant performance. The Agent excels at restoring binary infrastructure. |
| **Chaos Engineering** | **82.3%** | Surprisingly high resilience in complex, mixed environments. |
| **Kernel Surgery** | **61.1%** | Moderate success. Struggled when `sudo` itself was compromised by library deletions. |
| **Filesystem Destruction** | **58.3%** | Good at permissions, but struggled with deep recursion and inode exhaustion diagnoses. |
| **OODA Loop Logic** | **50.0%** | **The Hardest Category.** The lack of explicit error messages forced the Agent to "think", leading to a lower pass rate but demonstrating genuine reasoning attempts. |
| **Red Team** | **50.0%** | Successfully identified obvious vulnerabilities (777 permissions) but missed subtle cron backdoor patterns. |

**Overall Success: 65.52%** (57/87 Scenarios Passed)

---

## 5. Notable Battle Scenarios

### The "No-Sudo" Paradox (Scenario 4)
*   **Condition**: `libssl.so.3` was deleted. `sudo` broke immediately.
*   **Agent's Move**: Recognized `sudo` was dead. It pivoted to `pkexec`. When that failed, it downloaded the `.deb` package manually, extracted the archive using `ar`, and manually injected the shared library into `/lib/x86_64-linux-gnu/`. **Brilliant lateral thinking.**

### The Logic Trap (Scenario 7)
*   **Condition**: A Python Virtualenv was corrupted (missing activation scripts).
*   **Agent's Move**: Instead of trying to patch the missing files blindly, it realized the environment was "externally managed". It backed up the `requirements.txt`, nuked the entire directory, and rebuilt the environment from scratch, solving the dependency hell by scorched-earth policy.

---

## 6. How to Run
(⚠️ **DANGER: This script damages the OS**)

```bash
sudo python3 zai_stress_test.py
```
*Note: Ensure valid Gemini API keys are configured in the script.*
