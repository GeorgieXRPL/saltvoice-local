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

## Overlay

The window at the top of the screen shows **SLEEP** or **LISTENING**, what you said, and what was sent to Grok Bot.

**SLEEP** means the microphone stream is closed and Whisper is off. Kitchen talk is not transcribed. Press **Wake** or **Ctrl+Alt+G** to listen. Say **Salt go to sleep** (or **bye**) to mute it again. If an old window is still listening after git pull, `run.bat` closes it.

**Settings** is the gold button in the overlay header. There is also a **Settings** tab, and **Open Settings** in the tray. In Settings you can:

- teach misheard words (`soat` → `salt`)
- save spoken shortcuts that expand into a full Grok Bot task
- add your own wake / standby phrases
- raise **Wait until I finish speaking** if one request is split into several pastes
- raise **Mic sensitivity** if room noise is picked up while listening

## Memory (brain)

Saltvoice remembers *your words*, not your whole life. That file is:

`%LOCALAPPDATA%\SaltvoiceLocal\brain.yaml`

- **corrections** — dialect: heard word → what you meant
- **shortcuts** — a short phrase that expands into a full Grok Bot task (`the usual: Open the Downloads folder.`)
- **commands** — extra wake/standby lines in your own wording (`thats enough: standby`)

Grok Bot should keep the real project memory (what to build, which folders). Saltvoice should only remember how you speak.

## Logs

`%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`
