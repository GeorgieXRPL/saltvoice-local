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

## Update 2026-08-23 07:25 PT — full log for Cursor (VAD / Processing spam)

Session on MyPC, `C:\Users\justa\saltvoice-local`, tested at `4ce4af3`.
Raw log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log` (212 lines, 16.9 KB). No API keys.

### Counts (must fix)

- `INFO Processing audio with duration` : **55**
- `INFO VAD filter removed` : **55** (almost all `00:00.000` — empty/noise chunks still logged)
- `stt:` : 21
- handoff lines : 36
- HuggingFace HTTP chatter on every Whisper load (plus HF_TOKEN warning)

These two INFO lines fire about every 1–2 seconds even on **standby** (see 07:22:42–07:23:20). Cursor should:
1. Drop or demote `faster_whisper` / VAD library INFO to WARNING+ (or our own logger filter).
2. Do not log `Processing audio` / `VAD filter removed 00:00.000` at INFO.
3. On standby, stop feeding Whisper (mic still open = CPU + log flood).
4. Widen standby aliases: `Salt cut asleep` was pasted as a task.

### Full non-HTTP log (this session)

```
2026-08-23 06:57:39,409 INFO log file: C:\Users\justa\AppData\Local\SaltvoiceLocal\saltvoice-local.log
2026-08-23 06:58:23,080 INFO loading local Whisper tiny.en (cpu/int8)â€¦
2026-08-23 06:58:25,119 WARNING Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
2026-08-23 06:58:37,840 INFO Whisper ready
2026-08-23 06:58:50,975 INFO Processing audio with duration 00:01.280
2026-08-23 06:58:51,186 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:58:56,534 INFO Processing audio with duration 00:01.140
2026-08-23 06:58:56,536 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:02,934 INFO Processing audio with duration 00:01.060
2026-08-23 06:59:02,936 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:06,974 INFO Processing audio with duration 00:01.380
2026-08-23 06:59:06,976 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:11,014 INFO Processing audio with duration 00:01.480
2026-08-23 06:59:11,017 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:11,235 INFO stt: 'the pocket open voiceover.' wake=True â€” starting
2026-08-23 06:59:11,235 INFO armed â€” local Whisper will paste into Grok Bot
2026-08-23 06:59:18,654 INFO Processing audio with duration 00:01.600
2026-08-23 06:59:18,657 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:18,879 INFO stt: 'Can you hear me?' listening=True dur=1.6s
2026-08-23 06:59:18,879 INFO YOU: Can you hear me?
2026-08-23 06:59:18,881 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 06:59:19,512 INFO handoff pasted via win32 into 'Grok Bot' chars=16
2026-08-23 06:59:19,863 INFO HANDOFF window: Can you hear me?
2026-08-23 06:59:54,933 INFO Processing audio with duration 00:01.540
2026-08-23 06:59:54,937 INFO VAD filter removed 00:00.000 of audio
2026-08-23 06:59:55,149 INFO stt: 'Open the download folder.' listening=True dur=1.5s
2026-08-23 06:59:55,149 INFO YOU: Open the download folder.
2026-08-23 06:59:55,150 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 06:59:55,776 INFO handoff pasted via win32 into 'Grok Bot' chars=25
2026-08-23 06:59:56,127 INFO HANDOFF window: Open the download folder.
2026-08-23 07:00:03,734 INFO Processing audio with duration 00:01.260
2026-08-23 07:00:03,736 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:00:03,952 INFO stt: 'Close it down our tower.' listening=True dur=1.3s
2026-08-23 07:00:03,952 INFO YOU: Close it down our tower.
2026-08-23 07:00:03,955 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:00:04,600 INFO handoff pasted via win32 into 'Grok Bot' chars=24
2026-08-23 07:00:04,951 INFO HANDOFF window: Close it down our tower.
2026-08-23 07:00:10,974 INFO Processing audio with duration 00:01.760
2026-08-23 07:00:10,977 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:00:11,206 INFO stt: 'loads the download folder.' listening=True dur=1.8s
2026-08-23 07:00:11,206 INFO YOU: loads the download folder.
2026-08-23 07:00:11,206 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:00:11,855 INFO handoff pasted via win32 into 'Grok Bot' chars=26
2026-08-23 07:00:12,207 INFO HANDOFF window: loads the download folder.
2026-08-23 07:00:21,774 INFO Processing audio with duration 00:02.160
2026-08-23 07:00:21,778 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:00:21,995 INFO stt: 'close both download folders.' listening=True dur=2.2s
2026-08-23 07:00:21,995 INFO YOU: close both download folders.
2026-08-23 07:00:21,996 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:00:22,642 INFO handoff pasted via win32 into 'Grok Bot' chars=28
2026-08-23 07:00:22,994 INFO HANDOFF window: close both download folders.
2026-08-23 07:00:40,934 INFO Processing audio with duration 00:04.640
2026-08-23 07:00:40,940 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:00:41,179 INFO stt: 'Turn up the logs for the latest salt voice over AI.' wake=True â€” starting
2026-08-23 07:00:41,179 INFO armed â€” local Whisper will paste into Grok Bot
2026-08-23 07:00:53,733 INFO Processing audio with duration 00:03.760
2026-08-23 07:00:53,739 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:00:53,953 INFO stt: 'Pull up the log so the sole voice of AI.' listening=True dur=3.8s
2026-08-23 07:00:53,954 INFO YOU: Pull up the log so the sole voice of AI.
2026-08-23 07:00:53,956 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:00:54,586 INFO handoff pasted via win32 into 'Grok Bot' chars=40
2026-08-23 07:00:54,937 INFO HANDOFF window: Pull up the log so the sole voice of AI.
2026-08-23 07:01:16,093 INFO Processing audio with duration 00:01.860
2026-08-23 07:01:16,097 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:16,317 INFO stt: 'Stop salt for this over AI.' sleep=True â€” stopping
2026-08-23 07:01:16,317 INFO sleeping â€” waiting for Salt open voice over
2026-08-23 07:01:20,093 INFO Processing audio with duration 00:00.980
2026-08-23 07:01:20,095 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:23,093 INFO Processing audio with duration 00:01.000
2026-08-23 07:01:23,095 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:25,093 INFO Processing audio with duration 00:00.980
2026-08-23 07:01:25,094 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:27,893 INFO Processing audio with duration 00:01.800
2026-08-23 07:01:27,896 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:31,692 INFO Processing audio with duration 00:01.600
2026-08-23 07:01:31,696 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:38,373 INFO Processing audio with duration 00:01.900
2026-08-23 07:01:38,376 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:44,814 INFO Processing audio with duration 00:02.920
2026-08-23 07:01:44,818 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:45,011 INFO stt: 'salt voice over, salt open voice over.' wake=True â€” starting
2026-08-23 07:01:45,011 INFO armed â€” local Whisper will paste into Grok Bot
2026-08-23 07:01:58,333 INFO Processing audio with duration 00:02.640
2026-08-23 07:01:58,337 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:01:58,530 INFO stt: 'update the logs to GitHub.' listening=True dur=2.6s
2026-08-23 07:01:58,530 INFO YOU: update the logs to GitHub.
2026-08-23 07:01:58,531 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:01:59,164 INFO handoff pasted via win32 into 'Grok Bot' chars=26
2026-08-23 07:01:59,515 INFO HANDOFF window: update the logs to GitHub.
2026-08-23 07:03:59,611 INFO Processing audio with duration 00:00.640
2026-08-23 07:03:59,613 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:03:59,808 INFO stt: 'So.' listening=True dur=0.6s
2026-08-23 07:03:59,809 INFO YOU: So.
2026-08-23 07:03:59,810 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:04:00,454 INFO handoff pasted via win32 into 'Grok Bot' chars=3
2026-08-23 07:04:00,804 INFO HANDOFF window: So.
2026-08-23 07:04:15,532 INFO Processing audio with duration 00:01.400
2026-08-23 07:04:15,534 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:04:15,729 INFO stt: "So it's up voice over." listening=True dur=1.4s
2026-08-23 07:04:15,729 INFO YOU: So it's up voice over.
2026-08-23 07:04:15,731 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:04:16,378 INFO handoff pasted via win32 into 'Grok Bot' chars=22
2026-08-23 07:04:16,729 INFO HANDOFF window: So it's up voice over.
2026-08-23 07:04:21,331 INFO Processing audio with duration 00:01.660
2026-08-23 07:04:21,333 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:04:21,555 INFO stt: 'Soap, step voiceover.' listening=True dur=1.7s
2026-08-23 07:04:21,555 INFO YOU: Soap, step voiceover.
2026-08-23 07:04:21,556 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:04:22,198 INFO handoff pasted via win32 into 'Grok Bot' chars=21
2026-08-23 07:04:22,550 INFO HANDOFF window: Soap, step voiceover.
2026-08-23 07:04:27,611 INFO Processing audio with duration 00:02.080
2026-08-23 07:04:27,614 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:04:27,838 INFO stt: 'Stop voiceover.' sleep=True â€” stopping
2026-08-23 07:04:27,839 INFO sleeping â€” waiting for Salt open voice over
2026-08-23 07:19:35,695 INFO log file: C:\Users\justa\AppData\Local\SaltvoiceLocal\saltvoice-local.log
2026-08-23 07:19:35,905 INFO loading local Whisper tiny.en (cpu/int8)â€¦
2026-08-23 07:19:37,000 INFO Whisper ready
2026-08-23 07:20:33,626 INFO Processing audio with duration 00:00.980
2026-08-23 07:20:33,686 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:20:45,106 INFO Processing audio with duration 00:01.200
2026-08-23 07:20:45,108 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:20:49,906 INFO Processing audio with duration 00:01.340
2026-08-23 07:20:49,908 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:20:53,825 INFO Processing audio with duration 00:02.160
2026-08-23 07:20:53,829 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:20:55,826 INFO Processing audio with duration 00:01.080
2026-08-23 07:20:55,828 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:21:08,226 INFO Processing audio with duration 00:01.160
2026-08-23 07:21:08,228 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:21:10,546 INFO Processing audio with duration 00:00.960
2026-08-23 07:21:10,548 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:21:10,737 INFO stt: 'Wake up, salt.' wake â€” listening
2026-08-23 07:21:10,737 INFO armed â€” listening; say Salt go on standby when you are done
2026-08-23 07:21:18,106 INFO Processing audio with duration 00:01.160
2026-08-23 07:21:18,108 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:21:18,302 INFO stt: 'All right.' listening=True dur=1.2s
2026-08-23 07:21:18,303 INFO YOU: All right.
2026-08-23 07:21:18,306 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:21:18,933 INFO handoff pasted via win32 into 'Grok Bot' chars=10
2026-08-23 07:21:19,284 INFO HANDOFF window: All right.
2026-08-23 07:21:26,066 INFO Processing audio with duration 00:01.200
2026-08-23 07:21:26,068 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:21:26,273 INFO stt: 'Salt cut asleep.' listening=True dur=1.2s
2026-08-23 07:21:26,273 INFO YOU: Salt cut asleep.
2026-08-23 07:21:26,275 INFO handoff targeting window 'Grok Bot' hwnd=2425006
2026-08-23 07:21:26,904 INFO handoff pasted via win32 into 'Grok Bot' chars=16
2026-08-23 07:21:27,254 INFO HANDOFF window: Salt cut asleep.
2026-08-23 07:22:03,117 INFO log file: C:\Users\justa\AppData\Local\SaltvoiceLocal\saltvoice-local.log
2026-08-23 07:22:03,315 INFO loading local Whisper tiny.en (cpu/int8)â€¦
2026-08-23 07:22:04,481 INFO Whisper ready
2026-08-23 07:22:07,049 INFO Processing audio with duration 00:00.940
2026-08-23 07:22:07,108 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:09,209 INFO Processing audio with duration 00:01.000
2026-08-23 07:22:09,211 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:11,689 INFO Processing audio with duration 00:00.920
2026-08-23 07:22:11,690 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:13,208 INFO Processing audio with duration 00:00.800
2026-08-23 07:22:13,210 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:14,529 INFO Processing audio with duration 00:00.800
2026-08-23 07:22:14,530 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:15,849 INFO Processing audio with duration 00:00.880
2026-08-23 07:22:15,850 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:18,449 INFO Processing audio with duration 00:01.600
2026-08-23 07:22:18,452 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:18,659 INFO stt: 'Salt wake up.' wake â€” listening
2026-08-23 07:22:18,659 INFO armed â€” listening; say Salt go on standby when you are done
2026-08-23 07:22:30,209 INFO Processing audio with duration 00:01.800
2026-08-23 07:22:30,212 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:30,401 INFO stt: 'Salt go on standby.' standby â€” not sending to any app
2026-08-23 07:22:30,401 INFO standby â€” waiting for Salt wake up
2026-08-23 07:22:42,809 INFO Processing audio with duration 00:01.700
2026-08-23 07:22:42,812 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:42,999 INFO stt: 'salt go on standby' standby â€” not sending to any app
2026-08-23 07:22:42,999 INFO standby â€” waiting for Salt wake up
2026-08-23 07:22:48,089 INFO Processing audio with duration 00:01.340
2026-08-23 07:22:48,092 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:52,249 INFO Processing audio with duration 00:01.800
2026-08-23 07:22:52,252 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:22:56,408 INFO Processing audio with duration 00:01.580
2026-08-23 07:22:56,411 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:00,807 INFO Processing audio with duration 00:01.060
2026-08-23 07:23:00,810 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:04,209 INFO Processing audio with duration 00:01.220
2026-08-23 07:23:04,211 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:06,448 INFO Processing audio with duration 00:01.520
2026-08-23 07:23:06,451 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:09,169 INFO Processing audio with duration 00:01.880
2026-08-23 07:23:09,172 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:11,608 INFO Processing audio with duration 00:00.800
2026-08-23 07:23:11,610 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:13,687 INFO Processing audio with duration 00:00.880
2026-08-23 07:23:13,689 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:15,888 INFO Processing audio with duration 00:01.440
2026-08-23 07:23:15,891 INFO VAD filter removed 00:00.000 of audio
2026-08-23 07:23:17,968 INFO Processing audio with duration 00:01.080
2026-08-23 07:23:17,970 INFO VAD filter removed 00:01.080 of audio
2026-08-23 07:23:20,048 INFO Processing audio with duration 00:01.360
2026-08-23 07:23:20,050 INFO VAD filter removed 00:00.000 of audio
```

## Update 2026-08-23 07:45 PT — standby stops listening (3392a4d)

User report: **when it goes on standby it stops listening.** Wake-up cannot be heard until the process is restarted.

### After pull/restart (07:41–07:44)

VAD / `Processing audio` INFO is gone on this build (good). `So.` marked `filler — not pasted` (good).

```
07:42:43 stt: 'Hello, salt wake up.' wake — listening
07:43:10 navigate to Google.  HANDOFF
07:43:19 close Google.  HANDOFF
07:43:50 Suboperation.  HANDOFF
07:43:54 stop operation.  HANDOFF
07:44:04 So.  filler — not pasted
07:44:05 on standby.  HANDOFF (missing the word Salt — still pasted)
07:44:13 stt: 'Salt go on standby.' standby — not sending to any app
07:44:13 standby — waiting for Salt wake up
```

**No further stt/VAD/Processing lines after 07:44:13.** Log is dead until a manual restart. That matches the user: standby now mutes the wake listener, not just paste.

### Cursor fix

Standby should:
- stop pasting to Grok Bot
- **keep** a wake-only listener so `Salt wake up` works without killing the process
- not require Grok Bot to restart the app

Also still paste `on standby.` when the word Salt is dropped. Treat bare `standby` / `go on standby` as control.

No API keys. Log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`

## Update 2026-08-23 08:25 PT — e46b9dd wake-on-standby test (MyPC)

Pulled `e46b9dd`, restarted 08:21:06. Whisper tiny.en. User asked to push these logs to GitHub.

### Wake-on-standby works if the phrase is exact

After `Salt, go on standby.` the process stayed up and still transcribed:

```
08:22:55 standby — not pasting; still listening for Salt wake up
08:23:03 ignored 'So wake up.'
08:23:18 ignored 'Oh my god.'
08:23:30 ignored 'Soak, wake up.'
08:24:39 ignored 'So wake up.'
08:24:43 stt: 'Salt wake up.' wake — listening
```

So standby no longer goes deaf. Restart is not required.

### Cursor tweaks (tiny.en + phrase matching)

1. **Wake is too strict.** While on standby it ignored `So wake up.`, `Soak, wake up.`, `out wake up.`, `So, wait the fuck up.` User had to land exact `Salt wake up.`
2. **Standby is too strict.** `Soat go on standby.` was pasted into Grok Bot (Soat ≠ Salt). Exact `Salt, go on standby.` worked.
3. Fragments still paste when armed: `layers chrome.`, `flows from`, `So go and say bye.`
4. Earlier on this build, standby ignored `in her.` and still listened (`08:20:32`) — good.

No VAD/Processing INFO in this stretch. No API keys.
Log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`

## Update 2026-08-23 08:28 PT — “bye” is not standby (MyPC)

User said they cannot “say bye” to put Saltvoice Local on standby.

Current standby phrases that work: `Salt go on standby` / `Salt, go on standby.` (exact). `Salt cut asleep` still pastes. `Soat go on standby.` still pastes.

**Ask Cursor:** treat these as standby (do not paste):
- `bye`
- `say bye`
- `Salt say bye`
- `Salt go to sleep` / `Salt cut asleep` (already requested)

tiny.en often hears `So go and say bye.` when the user means standby. Fuzzy-match “say bye” / “bye” after Salt-ish wake word, and also bare `bye` if that is the whole utterance.

## Update 2026-08-23 18:14 PT — evening session (MyPC)

Restarted Saltvoice Local 17:41 and 17:54. tiny.en. User asked to upload these logs.

### Standby still too exact

Pasted into Grok Bot (should have been standby):
- `So let's go on standby.`
- `Soat, go on, standby.`
- `Stop going same boy.` (user meant standby)

Exact `Salt go on standby.` then worked (17:43:22). Wake-on-standby still works; ignored `So wake up.` until `You salt wake up.` armed it.

### Wake still too exact

Ignored on standby: `So wake up.` (twice). Accepted: `Salt wake up.` and `You salt wake up.`

### Armed paste noise

tiny.en split one request into junk pastes: `I'm... Soka.` / `about Soka.` / `purple.` / `Thought to pull over.` / `Fuck, fuck, fuck, fuck!` / `bucket photo.` before the real line `Not Bucket Photo Football. Build me a one page website about football.`

Also pasted `Open crime.` (Chrome).

### Still requested

Fuzzy Salt (So/Soat/Salts), `bye` / `say bye` as standby, hold-to-finish so a long command is one paste not six.

No API keys. Log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`

## Update 2026-08-23 21:02 PT — ded969b night session (MyPC)

Pulled `ded969b` (fuzzy wake/standby, hold until speech finishes, Settings on overlay) and restarted 20:45. tiny.en. User asked to upload these logs.

### Hold-until-finish works

Long lines stayed one paste, e.g. overlay request (40 chars), Streamlabs, FF7 gifts line, and the 156-char “have a look at the overlays…” line. Draft + 2.2s wait then `finished speaking`.

### Filler is a bit hungry

`Are you online?` and `That's it.` and `G-I-F.` were `filler (not pasted)`. The follow-up `All you run on.` (meant “are you online / running”) did paste. Fine for junk, bad if the user is asking a short status question.

### Wake / standby

Exact `Salt wake up.` armed twice. Later `standby` then `Salt wake up.` again at 21:01. No Soat/So wake samples in this stretch.

### Still requested

Do not treat short status questions (`are you online`, `are you running`) as filler. Keep hold-to-finish. Fuzzy Salt still wanted for So/Soat.

No API keys. Log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`

## Update 2026-08-24 04:35 PT — sleep still runs STT (MyPC)

On `9669246` / `ded969b`. User asked to upload logs: **Salt is still listening when he goes to sleep.**

### What happened

`Salt go to sleep.` correctly becomes standby (04:34:04, 04:35:28):

```
standby — not pasting; still listening for Salt wake up
```

Then STT keeps transcribing room talk and holding phrases:

- ignored `Gotta find somebody to love.`
- holding: `Salt.`, `It's done!`, `Let's go!`, `Salt go on.`, kitchen talk (`Add a little bit of salt.`, `It's yummy.`)
- Overnight 21:09–04:14 the process never went deaf

User does **not** want a wake listener on sleep. Sleep should stop STT (no holding, no ignored lines). Wake can be a hotkey (Ctrl+Alt+G) or a process restart until a true low-power wake-word exists.

`Salt go to sleep.` should mean sleep/deaf, not “standby but still hearing the kitchen.”

No API keys. Log: `%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`

## Update 2026-08-24 05:27 PT — more STT-on-sleep proof (MyPC)

User: upload to GitHub so they can **fix the STT**. Still on `5dc3b84` (no new app code). Restarted Saltvoice ~05:24 (second start hit `ERROR another Saltvoice Local process is already running`).

### Sleep / standby still runs Whisper

After `Salt go on standby.` at 05:26:17:

```
standby — not pasting; still listening for Salt wake up
stt: "It's so listening." holding (waiting for Salt wake up)
ignored "It's still listening, all right. Fucking, don't do the simplest thing when you get a sleep."
```

Same as overnight: `Salt go to sleep.` / standby does not stop STT. Room audio still transcribed (`Gotta find somebody to live.`, `Is that everything?`, `Alright, let's go.`).

### Ask Cursor

Deaf sleep: no `holding`, no `ignored`, no Whisper until hotkey or an explicit wake that is not always-on STT. User is fixing STT from this log.

No API keys.
