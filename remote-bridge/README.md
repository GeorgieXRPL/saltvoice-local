# Salt Remote Bridge (phone → MyPC Whisper → transcript)

Call Salt’s Whisper brain from Android on the go. Audio goes to MyPC over Tailscale; transcript comes back to your phone for paste into Grok Bot.

## Why this shape
Salt Local is Windows-only (mic → Whisper → paste into a desktop Grok Bot *window*).
On the phone you need the **text in this chat**, so the bridge returns the transcript to Android instead of only pasting on the PC.

## Stack
- MyPC: Tailscale + this bridge (`server.py`) using the same faster-whisper model as Salt Local
- Android: Termux + Termux:API (mic) + one tap script
- Network: Tailscale only (no public port)

## MyPC once
1. Install Tailscale, sign in (same account as the phone).
2. Copy this folder to `C:\Users\justa\saltvoice-local\remote-bridge\` (or next to saltvoice-local).
3. `pip install fastapi uvicorn python-multipart faster-whisper` (if not already from Salt).
4. Run: `python server.py` (or `run-bridge.bat`).
5. Note your Tailscale IP / MagicDNS name (e.g. `mypc.tailXXXX.ts.net`).

Prefer the in-app `remote_bridge` (binds Tailscale IPv4 only, pair URL, peer allowlist). This folder is a stand-alone fallback. Do not bind `0.0.0.0` on a café LAN. Firewall: TCP 8791 on the Tailscale adapter only. Keep Funnel off.

## Android once (Termux from F-Droid)
```bash
pkg install termux-api curl ffmpeg
# put call-salt.sh in ~/bin and chmod +x
```
Edit `PC=...` in the script to your Tailscale host.

## Call it
```bash
~/bin/call-salt.sh
```
Speak → stop → transcript lands on clipboard. Open Grok Bot and paste (or long-press paste).

Optional: keep Salt Local’s desktop overlay running at home for desk use; this bridge is the on-the-go path.
