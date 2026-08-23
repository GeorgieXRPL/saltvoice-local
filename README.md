# Saltvoice Local

Standalone, **offline** voice front-end for **Grok Bot** on Windows.

This is **not** the API Saltvoice repo. That project still uses an xAI key and lives in `Saltvoice`. This folder talks to no cloud STT: Whisper runs on your PC, then the same paste path puts the text into Grok Bot.

## What it does

1. Listens for **Salt open voice over**.
2. Transcribes your speech with local Whisper (`tiny.en` by default).
3. Pastes that text into the **Grok Bot** window.
4. Stops on **Salt stop voice over**.

No `.env`. No `XAI_API_KEY`.

## Setup (Windows)

Copy this whole `saltvoice-local` folder to the PC (next to `Saltvoice` is fine). Keep **Grok Bot open**. Do not run API Saltvoice and this at the same time.

```powershell
cd C:\Users\justa\saltvoice-local
.\run.bat
```

First start downloads the Whisper model into `%LOCALAPPDATA%\SaltvoiceLocal\models` (about 75 MB for `tiny.en`). Later starts are offline.

If `ctranslate2` fails to load, install the [VC++ redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

## Phrases

- Start: **Salt open voice over** (also “Salt start voice over”, “hey salt”)
- Stop: **Salt stop voice over**
- Backup: **Ctrl+Alt+G**

## Accuracy vs speed

In `config.yaml`:

```yaml
stt:
  model: tiny.en      # fastest
  # model: base.en    # clearer, slower
  device: cpu
  compute_type: int8
```

## Logs

`%LOCALAPPDATA%\SaltvoiceLocal\saltvoice-local.log`
