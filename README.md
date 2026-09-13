# Saltvoice Local

Standalone, **offline** voice front-end for Windows. Whisper runs on this PC. No API key.

## Easy commands (these are never pasted into Grok Bot)

- **Salt wake up** — start listening
- **Salt go on standby** — stop listening; talk freely, nothing is sent
- **Salt send to grok** — paste tasks into Grok Bot (default)
- **Salt send here** — paste into the app in front (browser, editor, Notepad)
- **Salt clip that** — save last ~20s of Streamlabs to Videos\\stream-clips (never pasted)

Streamlabs Replay Buffer must be on and Save Replay bound to Ctrl+Alt+C. Brand Studio / Spellbreaker watch that folder.

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

The window at the top of the screen shows **STANDBY** or **LISTENING**, what you said, and what was sent to Grok Bot.

**STANDBY** means tasks are not sent. Say **Salt wake up** to listen again (you do not have to click Wake). Kitchen chatter is not pasted. The app **starts listening** as soon as it opens. Say **Salt go to sleep** (or **bye**) for standby. If an old window is still running after git pull, `run.bat` closes it.

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

## Salt Bubble / phone HUD

The Android **Salt Bubble** overlay can POST 16 kHz WAV clips to this PC over Tailscale (HTTP, not HTTPS) and get a Whisper transcript.

- **remote_bridge** is on by default (`config.yaml` → `remote_bridge.enabled`)
- Binds the **Tailscale IPv4 only** (not Wi‑Fi / LAN). `host: tailscale` in config.
  - `POST /transcribe` → JSON `{"text":"..."}` (requires `X-Salt-Token`)
  - `POST /transcribe.txt` → plain text
  - `POST /pair` → pin this phone’s Tailscale IP (token required)
  - `GET /pair` → pair URL on **localhost only** (15 minutes). The phone uses the console `PAIR PHONE` link, not this GET.
  - `GET /health` → no token; after pair, only the pinned phone (plus localhost)
  - `POST /send-to-grok` → off when `allow_send_to_grok: false`
- Console prints `PAIR PHONE: saltbubble://bridge?…` — open that on the phone. Do not stream it. The raw token is not printed.
- After pair, `%LOCALAPPDATA%\SaltvoiceLocal\bridge.peers` holds the phone IP. A stolen token from another host gets 403.
- Windows Firewall: inbound TCP **8791** on the Tailscale adapter only. Keep Tailscale Funnel off.

## Logs

`%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`
