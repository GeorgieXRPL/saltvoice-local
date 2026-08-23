# Saltvoice Local

Standalone, **offline** voice front-end for Windows. Whisper runs on this PC. No API key.

## Easy commands (these are never pasted into Grok Bot)

- **Salt wake up** — start listening
- **Salt go on standby** — stop listening; talk freely, nothing is sent
- **Salt send to grok** — paste tasks into Grok Bot (default)
- **Salt send here** — paste into the app in front (browser, editor, Notepad)

Old phrases still work: “Salt open voice over”, “Salt stop voice over”. Prefer **wake up** / **go on standby** so Grok Bot never sees the word “stop”.

## Setup

```powershell
cd C:\Users\justa\saltvoice-local
git pull
.\run.bat
```

First run downloads Whisper. Keep the console open. Overlay title: **Saltvoice Local**.

Do not run this and API Saltvoice at the same time.

## Other applications

Two ways:

1. **Via Grok Bot (recommended for real work)** — default. You speak a task, it is pasted into Grok Bot, and Grok Bot can open folders, edit files, and drive other apps.
2. **Straight into the front window** — say **Salt send here**, then wake, then speak. Text is pasted where you are typing. Say **Salt send to grok** to switch back.

## Logs

`%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`
