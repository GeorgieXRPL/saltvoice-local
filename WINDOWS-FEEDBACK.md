# Windows feedback (fill this on the Windows PC, then commit and push)

Grok Bot: fill this file from what you see. Do not paste API keys. Then:

```
git add WINDOWS-FEEDBACK.md
git commit -m "Report Windows Saltvoice Local test results"
git push
```

## Environment

- Windows version: Microsoft Windows 11 (MyPC, user justa)
- Python version (`python --version`): Python 3.12.10
- Saltvoice Local commit (`git rev-parse --short HEAD`): 52f8fb0 at test time
- Clone path: C:\Users\justa\saltvoice-local
- Grok Bot app running? (yes/no): yes
- Exact Grok Bot window title: Grok Bot
- PC / user: MyPC / justa
- No .env / no XAI_API_KEY (offline Whisper)

## What appeared

- Black log window? (yes/no): process started via python -m saltvoice_local (venv + child)
- Window titled `Saltvoice Local` at the top of the screen? (yes/no): not confirmed in this pass
- First log lines (copy, no secrets):

```
2026-08-23 06:57:39 INFO log file: ...\SaltvoiceLocal\saltvoice-local.log
2026-08-23 06:58:23 INFO loading local Whisper tiny.en (cpu/int8)
2026-08-23 06:58:37 INFO Whisper ready
```

First start downloaded Systran/faster-whisper-tiny.en from Hugging Face (unauthenticated). Then offline.

## Wake / stop

- Said "Salt open voice over": yes. STT heard: `the pocket open voiceover.` (wake=True) then later `salt voice over, salt open voice over.` (wake=True)
- Overlay changed to LISTENING? (yes/no): not checked; log said armed
- Said "Salt stop voice over": no (not tested in this session)

## Handoff to Grok Bot

- Spoke a task: yes. Several lines pasted into this chat.
- Did that text appear in Grok Bot? (yes/no): yes
- Console showed `HANDOFF window:` : yes, `handoff pasted via win32 into 'Grok Bot'`

Examples:

```
06:59:18 stt: 'Can you hear me?'  HANDOFF window: Can you hear me?
06:59:55 stt: 'Open the download folder.'
07:00:03 stt: 'Close it down our tower.'
07:00:11 stt: 'loads the download folder.'
07:00:21 stt: 'close both download folders.'
07:00:53 stt: 'Pull up the log so the sole voice of AI.'
07:01:58 stt: 'update the logs to GitHub.'
```

hwnd=2425006 every time.

## Errors

- Whisper / ctranslate2 / VC++: loaded OK (cpu/int8 tiny.en)
- Microphone: working. tiny.en mishears wake phrase
- Other: HF Hub warning about missing HF_TOKEN (rate limit only). No API keys used.

## Log path

- %LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log
