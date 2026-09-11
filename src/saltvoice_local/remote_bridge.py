from __future__ import annotations

"""HTTP bridge so Salt Bubble can POST WAV audio to local Whisper."""

import io
import json
import logging
import re
import socket
import threading
import time
import wave
from email.parser import Parser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

log = logging.getLogger("saltvoice_local")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8791
MAX_BODY = 32 * 1024 * 1024

TranscribeFn = Callable[[bytes, int, str], str]
GrokCallback = Callable[[str], Any]


def build_wav(
    pcm: bytes,
    sample_rate: int = 16_000,
    channels: int = 1,
    sampwidth: int = 2,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def encode_transcript(text: str, *, plain: bool) -> tuple[str, bytes]:
    text = text or ""
    if plain:
        return "text/plain; charset=utf-8", text.encode("utf-8")
    return "application/json", json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")


def _header_param(header_blob: str, header: str, param: str) -> str:
    parsed = Parser(policy=email_policy).parsestr(header_blob if ":" in header_blob else f"{header}: {header_blob}")
    raw = parsed.get_param(param, header=header)
    if raw is None:
        return ""
    if isinstance(raw, tuple):
        raw = raw[-1]
    return str(raw or "")


def _multipart_boundary(content_type: str) -> bytes:
    raw = _header_param(f"Content-Type: {content_type}\r\n", "content-type", "boundary")
    if not raw:
        match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type or "", re.I)
        if match:
            raw = (match.group(1) or match.group(2) or "").strip()
    if not raw:
        raise ValueError("bad multipart: missing boundary")
    return raw.encode("ascii", "replace")


def _part_field_name(header_bytes: bytes) -> str:
    text = header_bytes.decode("latin-1", "replace")
    name = _header_param(text + "\r\n", "content-disposition", "name")
    if name:
        return name
    match = re.search(r'name="([^"]+)"', text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"name=([^;\s]+)", text, re.I)
    return match.group(1) if match else ""


def parse_multipart_fields(content_type: str, body: bytes) -> dict[str, bytes]:
    boundary = _multipart_boundary(content_type)
    delim = b"--" + boundary
    fields: dict[str, bytes] = {}
    for chunk in body.split(delim):
        stripped = chunk.strip(b"\r\n")
        if not stripped or stripped == b"--":
            continue
        if chunk.startswith(b"--"):
            continue
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        elif chunk.startswith(b"\n"):
            chunk = chunk[1:]
        header_end = chunk.find(b"\r\n\r\n")
        sep = 4
        if header_end < 0:
            header_end = chunk.find(b"\n\n")
            sep = 2
        if header_end < 0:
            continue
        payload = chunk[header_end + sep :]
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        elif payload.endswith(b"\n"):
            payload = payload[:-1]
        name = _part_field_name(chunk[:header_end])
        if name:
            fields[name] = payload
    return fields


def audio_bytes_from_request(content_type: str, body: bytes) -> bytes:
    ctype_full = content_type or ""
    ctype = ctype_full.split(";")[0].strip().lower()
    if ctype.startswith("multipart/"):
        try:
            fields = parse_multipart_fields(ctype_full, body)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"bad multipart: {exc}") from exc
        for key in ("audio", "file"):
            blob = fields.get(key)
            if blob:
                return blob
        raise ValueError("bad multipart: missing audio/file field")
    if ctype in {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "application/octet-stream",
        "application/wav",
        "application/x-wav",
    }:
        if not body:
            raise ValueError("empty body")
        return body
    if body.startswith(b"RIFF"):
        return body
    raise ValueError("unsupported Content-Type")


def _pcm16le_downmix(frames: bytes, channels: int) -> bytes:
    if channels <= 1:
        return frames
    frame_bytes = 2 * channels
    nframes = len(frames) // frame_bytes
    out = bytearray(nframes * 2)
    for i in range(nframes):
        base = i * frame_bytes
        total = 0
        for ch in range(channels):
            off = base + ch * 2
            total += int.from_bytes(frames[off : off + 2], "little", signed=True)
        avg = total // channels
        if avg > 32767:
            avg = 32767
        elif avg < -32768:
            avg = -32768
        out[i * 2 : i * 2 + 2] = avg.to_bytes(2, "little", signed=True)
    return bytes(out)


def _u8_to_pcm16(frames: bytes) -> bytes:
    out = bytearray(len(frames) * 2)
    for i, sample in enumerate(frames):
        value = (int(sample) - 128) << 8
        out[i * 2 : i * 2 + 2] = value.to_bytes(2, "little", signed=True)
    return bytes(out)


def pcm_from_wav(wav_bytes: bytes) -> tuple[bytes, int]:
    if not wav_bytes:
        raise ValueError("empty audio")
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    except wave.Error as exc:
        raise ValueError(f"invalid WAV: {exc}") from exc
    if channels < 1 or rate < 1:
        raise ValueError("invalid WAV format")
    if sampwidth == 1:
        frames = _u8_to_pcm16(frames)
    elif sampwidth != 2:
        raise ValueError(f"unsupported WAV sample width {sampwidth}")
    return _pcm16le_downmix(frames, channels), rate


class _BridgeServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    bridge: RemoteBridge


class _BridgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    timeout = 120

    def log_message(self, fmt: str, *args: Any) -> None:
        log.info("bridge %s %s", self.address_string(), fmt % args)

    def _path(self) -> str:
        path = urlparse(self.path).path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path or "/"

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def _write(self, code: int, content_type: str, payload: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self._cors()
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._write(code, "application/json", body)

    def _error(self, code: int, message: str) -> None:
        self._json(code, {"error": message})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self._path()
        if path in {"/", "/health"}:
            bridge: RemoteBridge = self.server.bridge  # type: ignore[attr-defined]
            self._json(
                200,
                {"ok": True, "service": "salt-remote-bridge", "port": bridge.port},
            )
            return
        self._error(404, "not found")

    def do_POST(self) -> None:  # noqa: N802
        path = self._path()
        try:
            body = self._read_body()
        except ValueError as exc:
            self._error(400, str(exc))
            return
        if path == "/send-to-grok":
            self._handle_send_to_grok(body)
            return
        if path in {"/transcribe", "/transcribe.txt"}:
            self._handle_transcribe(path, body)
            return
        self._error(404, "not found")

    def _read_body(self) -> bytes:
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise ValueError("missing Content-Length")
        try:
            length = int(raw)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0:
            raise ValueError("invalid Content-Length")
        if length > MAX_BODY:
            raise ValueError("body too large")
        if length == 0:
            return b""
        return self.rfile.read(length)

    def _handle_transcribe(self, path: str, body: bytes) -> None:
        bridge: RemoteBridge = self.server.bridge  # type: ignore[attr-defined]
        client = self.address_string()
        nbytes = len(body)
        try:
            wav = audio_bytes_from_request(self.headers.get("Content-Type") or "", body)
            pcm, rate = pcm_from_wav(wav)
            if not pcm:
                text = ""
            else:
                text = bridge.transcribe(pcm, rate)
        except ValueError as exc:
            log.info("bridge %s %s bytes=%s error=%s", client, path, nbytes, exc)
            self._error(400, str(exc))
            return
        except Exception as exc:
            log.exception("bridge transcribe failed")
            self._error(500, str(exc))
            return
        text = text or ""
        log.info(
            "bridge %s %s bytes=%s transcript_len=%s",
            client,
            path,
            nbytes,
            len(text),
        )
        ctype, payload = encode_transcript(text, plain=path.endswith(".txt"))
        self._write(200, ctype, payload)

    def _handle_send_to_grok(self, body: bytes) -> None:
        bridge: RemoteBridge = self.server.bridge  # type: ignore[attr-defined]
        if bridge.grok_callback is None:
            self._error(501, "send-to-grok is not configured")
            return
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            self._error(400, "invalid JSON")
            return
        if not isinstance(data, dict):
            self._error(400, "invalid JSON")
            return
        text = str(data.get("text") or "")
        try:
            result = bridge.grok_callback(text)
        except Exception as exc:
            log.exception("bridge send-to-grok failed")
            self._error(500, str(exc))
            return
        if not isinstance(result, dict):
            result = {"status": "ok", "result": result}
        log.info(
            "bridge %s /send-to-grok bytes=%s transcript_len=%s",
            self.address_string(),
            len(body),
            len(text),
        )
        self._json(200, result)


class RemoteBridge:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        language: str = "en",
        grok_callback: GrokCallback | None = None,
        transcribe_fn: TranscribeFn | None = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.language = language or "en"
        self.grok_callback = grok_callback
        self._transcribe_fn = transcribe_fn
        self._httpd: _BridgeServer | None = None
        self._thread: threading.Thread | None = None

    def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        if self._transcribe_fn is not None:
            return self._transcribe_fn(pcm, sample_rate, self.language) or ""
        from saltvoice_local.stt import model_loaded, transcribe_pcm

        if not model_loaded():
            raise RuntimeError("Whisper model is not loaded")
        return transcribe_pcm(pcm, sample_rate=sample_rate, language=self.language, force=True) or ""

    def start(self) -> RemoteBridge:
        if self._httpd is not None:
            return self
        httpd = _BridgeServer((self.host, self.port), _BridgeHandler)
        httpd.bridge = self
        self._httpd = httpd
        self.port = int(httpd.server_address[1])
        self._thread = threading.Thread(
            target=httpd.serve_forever,
            name="salt-remote-bridge",
            daemon=True,
        )
        self._thread.start()
        self._wait_listening()
        log.info("remote bridge listening on http://%s:%s", self.host, self.port)
        return self

    def _wait_listening(self, timeout: float = 2.0) -> None:
        probe = "127.0.0.1" if self.host in {"0.0.0.0", "", "::"} else self.host
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._thread is not None and not self._thread.is_alive():
                raise RuntimeError("remote bridge thread exited")
            try:
                with socket.create_connection((probe, self.port), timeout=0.15):
                    return
            except OSError:
                time.sleep(0.02)
        raise RuntimeError("remote bridge did not start listening")

    def stop(self) -> None:
        httpd = self._httpd
        thread = self._thread
        self._httpd = None
        self._thread = None
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                log.debug("remote bridge shutdown", exc_info=True)
            try:
                httpd.server_close()
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            thread.join(timeout=8.0)
            if thread.is_alive():
                log.warning("remote bridge thread still running after stop")


_bridge: RemoteBridge | None = None
_bridge_lock = threading.Lock()


def start_bridge(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    language: str = "en",
    grok_callback: GrokCallback | None = None,
    transcribe_fn: TranscribeFn | None = None,
) -> RemoteBridge:
    global _bridge
    with _bridge_lock:
        if _bridge is not None:
            return _bridge
        bridge = RemoteBridge(
            host=host,
            port=port,
            language=language,
            grok_callback=grok_callback,
            transcribe_fn=transcribe_fn,
        )
        try:
            bridge.start()
        except Exception:
            try:
                bridge.stop()
            except Exception:
                pass
            raise
        _bridge = bridge
        return bridge


def stop_bridge() -> None:
    global _bridge
    with _bridge_lock:
        bridge = _bridge
        _bridge = None
    if bridge is not None:
        bridge.stop()
