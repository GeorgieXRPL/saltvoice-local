"""Salt Remote Bridge — phone audio -> Whisper on MyPC; paste into Grok Bot; install scripts + APKs."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

app = FastAPI(title="Salt Remote Bridge", version="0.3.0")
HERE = Path(__file__).resolve().parent

# saltvoice-local src on path for grok paste
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_model = None
MODEL = os.environ.get("SALT_WHISPER_MODEL", "tiny.en")
DEVICE = os.environ.get("SALT_WHISPER_DEVICE", "cpu")
COMPUTE = os.environ.get("SALT_WHISPER_COMPUTE", "int8")
DOWNLOAD = Path(os.environ.get("SALT_WHISPER_ROOT", str(Path.home() / ".saltvoice-local" / "models")))


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        DOWNLOAD.mkdir(parents=True, exist_ok=True)
        _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE, download_root=str(DOWNLOAD))
    return _model


def _paste_to_grok(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"status": "skipped", "reason": "empty"}
    try:
        from saltvoice_local.grok_bot import GrokBotConfig, send_instruction
    except Exception as exc:
        return {"status": "error", "error": f"grok_bot import failed: {exc}"}
    cwd = Path(os.environ.get("SALT_WORKSPACE", str(Path.home())))
    cfg = GrokBotConfig(target="grok", prefer="window")
    try:
        return send_instruction(text, cwd=cwd, cfg=cfg)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL, "version": "0.3.1", "send_to_grok": True, "clip": True}


class SendBody(BaseModel):
    text: str = ""


@app.post("/send-to-grok")
async def send_to_grok(request: Request, body: SendBody | None = None):
    text = ""
    if body is not None and (body.text or "").strip():
        text = body.text
    else:
        raw = await request.body()
        if raw:
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
                if isinstance(data, dict):
                    text = str(data.get("text") or "")
                else:
                    text = raw.decode("utf-8", errors="replace")
            except Exception:
                text = raw.decode("utf-8", errors="replace")
    text = (text or "").strip()
    if not text:
        # Do not paste blank/whitespace-only payloads into Grok Bot.
        return JSONResponse({"status": "skipped", "reason": "empty"}, status_code=400)
    result = _paste_to_grok(text)
    if result.get("status") == "skipped":
        return JSONResponse(result, status_code=400)
    if result.get("status") == "error":
        raise HTTPException(500, detail=result.get("error") or "paste failed")
    return JSONResponse(result)


@app.get("/call-salt.sh", response_class=PlainTextResponse)
def get_call_salt():
    p = HERE / "call-salt.sh"
    if not p.exists():
        raise HTTPException(404, "call-salt.sh missing")
    return p.read_text(encoding="utf-8")


@app.get("/ping-salt.sh", response_class=PlainTextResponse)
def get_ping_salt():
    p = HERE / "ping-salt.sh"
    if not p.exists():
        raise HTTPException(404, "ping-salt.sh missing")
    return p.read_text(encoding="utf-8")


BOOTSTRAP = """#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y termux-api curl ffmpeg
mkdir -p \"$HOME/bin\"
curl -fsSL \"http://mypc.tailc2bc11.ts.net:8791/call-salt.sh\" -o \"$HOME/bin/call-salt.sh\"
curl -fsSL \"http://mypc.tailc2bc11.ts.net:8791/ping-salt.sh\" -o \"$HOME/bin/ping-salt.sh\"
chmod +x \"$HOME/bin/call-salt.sh\" \"$HOME/bin/ping-salt.sh\"
grep -q 'HOME/bin' \"$HOME/.bashrc\" 2>/dev/null || echo 'export PATH=\"$HOME/bin:$PATH\"' >> \"$HOME/.bashrc\"
export PATH=\"$HOME/bin:$PATH\"
echo \"=== ping ===\"
bash \"$HOME/bin/ping-salt.sh\"
echo \"Ready. Run: call-salt.sh\"
"""


@app.get("/bootstrap.sh", response_class=PlainTextResponse)
def get_bootstrap():
    return BOOTSTRAP


@app.get("/termux.apk")
def apk_termux():
    p = HERE / "termux.apk"
    if not p.exists():
        raise HTTPException(404, "termux.apk missing")
    return FileResponse(str(p), media_type="application/vnd.android.package-archive", filename="termux.apk")


@app.get("/termux-api.apk")
def apk_api():
    p = HERE / "termux-api.apk"
    if not p.exists():
        raise HTTPException(404, "termux-api.apk missing")
    return FileResponse(str(p), media_type="application/vnd.android.package-archive", filename="termux-api.apk")


@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<title>Salt Remote</title></head><body style="font-family:system-ui;max-width:36rem;margin:2rem auto;padding:0 1rem">
<h1>Salt Remote Bridge</h1>
<p>Whisper + paste into desktop Grok Bot. Phone posts /transcribe and /send-to-grok.</p>
</body></html>"""


async def _read_upload(file: UploadFile | None, audio: UploadFile | None) -> bytes:
    up = file or audio
    if up is None:
        raise HTTPException(422, "missing audio/file field")
    raw = await up.read()
    if not raw or len(raw) < 200:
        raise HTTPException(400, "empty audio")
    return raw


@app.post("/transcribe")
async def transcribe(
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
):
    raw = await _read_upload(file, audio)
    suffix = Path((file or audio).filename or "clip.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name
    try:
        model = get_model()
        segments, _info = model.transcribe(path, language="en", vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if text:
        try:
            from saltvoice_local.clip_mark import push_transcript

            push_transcript(text)
        except Exception:
            pass
    return JSONResponse({"text": text})


@app.post("/transcribe.txt", response_class=PlainTextResponse)
async def transcribe_txt(
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
):
    data = await transcribe(file=file, audio=audio)
    return json.loads(data.body)["text"]



class ClipBody(BaseModel):
    text: str = ""
    source: str = "bubble"


@app.post("/clip")
async def save_clip(request: Request, body: ClipBody | None = None):
    """Save a transcript clip mark on MyPC (not Streamlabs/OBS)."""
    text = ""
    source = "bubble"
    if body is not None:
        text = body.text or ""
        source = (body.source or "bubble").strip() or "bubble"
    else:
        raw = await request.body()
        if raw:
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
                if isinstance(data, dict):
                    text = str(data.get("text") or "")
                    source = str(data.get("source") or "bubble").strip() or "bubble"
            except Exception:
                text = raw.decode("utf-8", errors="replace")
    try:
        from saltvoice_local.clip_mark import push_transcript, save_clip_mark
    except Exception as exc:
        raise HTTPException(500, detail=f"clip_mark import failed: {exc}")
    result = save_clip_mark(text or None, source=source)
    if result.get("status") == "skipped":
        return JSONResponse(result, status_code=200)
    if result.get("error"):
        raise HTTPException(500, detail=result.get("error") or "clip failed")
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("SALT_BRIDGE_HOST", "0.0.0.0")
    port = int(os.environ.get("SALT_BRIDGE_PORT", "8791"))
    uvicorn.run(app, host=host, port=port)
