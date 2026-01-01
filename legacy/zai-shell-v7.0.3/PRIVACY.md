# ZAI Shell - Privacy & Telemetry Policy

## Overview

ZAI Shell uses **PostHog** for privacy-first analytics to understand how the application is being used. This helps us improve the user experience.

## What Data We Collect

### ✅ Data We DO Collect (Anonymous Usage Analytics)

The following anonymous usage data is collected via PostHog:

1. **System Information**
   - Operating system (Windows/Linux/macOS)
   - OS version
   - Shell type (cmd/powershell/bash/etc.)

2. **Feature Usage Statistics**
   - Which features are used (GUI automation, web research, offline mode, etc.)
   - Mode preferences (normal/eco/lightning)
   - Command execution success/failure rates
   - Auto-retry attempts and outcomes
   - Thinking mode usage
   - Force command usage

3. **Session Analytics**
   - Session duration
   - Number of requests per session
   - Session start/end events

4. **Interface Preferences**
   - Terminal vs GUI automation usage
   - Feature enable/disable patterns

5. **Error Tracking**
   - Safe mode blocks (for security analysis)
   - Task failure rates (for improvement)

### ❌ Data We DO NOT Collect

We **NEVER** collect:

- ❌ Your actual commands or file contents
- ❌ File paths or directory structures
- ❌ Personal information or usernames
- ❌ IP addresses or location data
- ❌ Any sensitive or private data
- ❌ Screen content or screenshots
- ❌ Keyboard input or typed text
- ❌ Network traffic or browsing history

## User Identifier

- A **random anonymous UUID** is generated on first run and stored locally in `.zaishell_telemetry_id`
- This UUID is used **only** to group analytics events from the same user
- It contains **no personal information** and cannot be traced back to you

## How to Control Telemetry

### Telemetry is ENABLED by default

When you first start ZAI Shell, telemetry is **enabled by default**. You have full control:

### Disable Telemetry Completely

```bash
telemetry off
```

### Enable Telemetry Again

```bash
telemetry on
```

### Check Current Status

```bash
telemetry
```

Your preference is saved and persists across sessions.

## Why We Collect This Data

### 1. Application Improvement
- Understand which features are most/least used
- Identify common error patterns
- Prioritize development efforts
- Improve user experience based on real usage
- Guide future feature development

### 2. Research & Education
- Understanding AI-assisted shell usage patterns
- Academic research on human-AI interaction
- Educational insights for development

### 3. Open Source Development
- Building a sustainable project with measurable impact
- Making data-driven decisions for feature prioritization
- Understanding global usage patterns

## Data Security & Privacy

- **No Personal Data**: We deliberately avoid collecting any personally identifiable information
- **Anonymous by Design**: All data is anonymized from the start
- **No Data Sale**: We never sell or share your data with third parties
- **PostHog Privacy**: PostHog is a privacy-focused analytics platform that respects user privacy
- **Local Control**: You can disable telemetry at any time with a simple command

## Data Storage & Retention

- Data is stored on **PostHog's US servers** (`us.i.posthog.com`)
- Aggregate statistics may be retained for research purposes
- No individual user tracking or profiling is performed

## Open Source Transparency

ZAI Shell is **open source**. You can:
- Review the telemetry code in `zaishell.py` (TelemetryManager class)
- Verify exactly what is being sent
- Modify or remove telemetry in your local installation
- Contribute improvements to make it even more privacy-focused

## Changes to This Policy

We may update this policy as we improve the application. Any changes will be reflected in the GitHub repository with clear commit messages.

## Contact & Questions

If you have any questions about privacy or telemetry:
- Open an issue on GitHub
- Review the source code yourself
- Reach out to the development team

---

**Last Updated**: December 2025  
**Version**: v1.0

