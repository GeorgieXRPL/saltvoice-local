#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saltvoice_local.pcm import resample_pcm16, rms_int16
from saltvoice_local.phrases import (
    classify_utterance,
    is_filler_utterance,
    is_sleep_phrase,
    is_wake_phrase,
    remainder_after_wake,
)
from saltvoice_local.state import Hub, Phase


def test_resample() -> None:
    silence = b"\x00\x00" * 240
    out = resample_pcm16(silence, 24000, 48000)
    assert len(out) == 480 * 2
    assert rms_int16(silence) == 0.0


def test_phrases() -> None:
    assert classify_utterance("Salt wake up") == "wake"
    assert classify_utterance("Salt, go on standby") == "standby"
    assert classify_utterance("Salt go on stand by") == "standby"
    assert classify_utterance("Salt send here") == "target_here"
    assert classify_utterance("Salt send to Grok Bot") == "target_grok"
    assert classify_utterance("Open the download folder") == "task"
    assert classify_utterance("Salt, open the download folder") == "task"
    assert is_wake_phrase("Salt, open voice over")
    assert is_wake_phrase("hey salt")
    assert is_sleep_phrase("Stop, stop voiceover.")
    assert is_sleep_phrase("salt stop")
    assert not is_wake_phrase("please pass the salt")
    assert classify_utterance("Salt stop voice over") == "standby"
    assert classify_utterance("stop salt voice over") == "standby"
    assert classify_utterance("Stop, salt, voiceover") == "standby"
    assert classify_utterance("stop salt") == "standby"
    assert classify_utterance("Salt, open the downloads") == "task"
    # Real Windows log lines
    assert classify_utterance("the pocket open voiceover.") == "wake"
    assert classify_utterance("Wake up, salt.") == "wake"
    assert classify_utterance("Salt cut asleep.") == "standby"
    assert classify_utterance("Soap, step voiceover.") == "standby"
    assert classify_utterance("Stop voiceover.") == "standby"
    assert classify_utterance("Turn up the logs for the latest salt voice over AI.") == "task"
    assert classify_utterance("Can you hear me?") == "task"
    assert is_filler_utterance("So.")
    assert is_filler_utterance("All right.")
    assert not is_filler_utterance("Can you hear me?")
    assert remainder_after_wake("Salt wake up open the download folder") == "open the download folder"
    assert classify_utterance("on standby.") == "standby"
    assert classify_utterance("go on standby") == "standby"
    assert classify_utterance("Hello, salt wake up.") == "wake"
    assert classify_utterance("put chrome on standby") == "task"
    assert classify_utterance("soat wake up") == "wake"
    assert classify_utterance("soat go on standby") == "standby"
    assert classify_utterance("So wake up.") == "wake"
    assert classify_utterance("Soak, wake up.") == "wake"
    assert classify_utterance("Soat go on standby.") == "standby"
    # Evening Windows log (tiny.en)
    assert classify_utterance("So wake up.") == "wake"
    assert classify_utterance("Soak, wake up.") == "wake"
    assert classify_utterance("You salt wake up.") == "wake"
    assert classify_utterance("So let's go on standby.") == "standby"
    assert classify_utterance("Soat, go on, standby.") == "standby"
    assert classify_utterance("Stop going same boy.") == "standby"
    assert classify_utterance("bye") == "standby"
    assert classify_utterance("say bye") == "standby"
    assert classify_utterance("Salt say bye") == "standby"
    assert classify_utterance("So go and say bye.") == "standby"
    assert classify_utterance("Salt go to sleep") == "standby"
    assert classify_utterance("Salt cut asleep.") == "standby"
    assert classify_utterance("put chrome on standby") == "task"
    from saltvoice_local.phrases import is_incomplete_utterance, is_noise_utterance, normalize, polish_task

    assert polish_task("Open crime.") == "Open Chrome."
    assert is_noise_utterance("Fuck, fuck, fuck, fuck!")
    assert is_noise_utterance("a")
    assert not is_noise_utterance("purple.")
    assert not is_noise_utterance("Are you online?")
    assert not is_noise_utterance("That's it.")
    assert not is_noise_utterance("G-I-F.")
    from saltvoice_local.phrases import is_incomplete_utterance, normalize

    assert normalize("soat") == "salt"
    assert is_incomplete_utterance("soat")
    assert is_incomplete_utterance("so")
    assert is_incomplete_utterance("So.")
    assert not is_incomplete_utterance("Open the download folder")
    assert not is_incomplete_utterance("Are you online?")
    assert not is_incomplete_utterance("That's it.")
    assert not is_incomplete_utterance("Can you hear me?")
    assert not is_incomplete_utterance("G-I-F.")
    assert not is_filler_utterance("Are you online?")
    assert not is_filler_utterance("That's it.")
    assert not is_filler_utterance("G-I-F.")
    assert not is_filler_utterance("Can you hear me?")
    from saltvoice_local.phrases import set_command_aliases, set_user_corrections

    set_user_corrections({"bork": "salt"})
    assert classify_utterance("bork wake up") == "wake"
    set_user_corrections({})
    set_command_aliases({"thats enough": "standby"})
    assert classify_utterance("that's enough") == "standby"
    set_command_aliases({})


def test_hub() -> None:
    hub = Hub()
    hub.emit("ready", phase=Phase.LISTENING, status_line="hi")
    assert hub.phase is Phase.LISTENING


def _multipart(field: str, data: bytes, filename: str = "clip.wav") -> tuple[str, bytes]:
    boundary = "----SaltTestBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("ascii") + data + f"\r\n--{boundary}--\r\n".encode("ascii")
    return f"multipart/form-data; boundary={boundary}", body


def _http_open(req: urllib.request.Request, timeout: float = 3.0):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(req, timeout=timeout)


def test_remote_bridge_wav() -> None:
    from saltvoice_local.remote_bridge import build_wav, pcm_from_wav

    pcm = b"\x00\x00" * 160
    wav = build_wav(pcm, sample_rate=16_000, channels=1)
    assert wav.startswith(b"RIFF")
    out, rate = pcm_from_wav(wav)
    assert rate == 16_000
    assert out == pcm

    stereo = b"".join(struct.pack("<hh", 1000, 2000) for _ in range(8))
    stereo_wav = build_wav(stereo, sample_rate=16_000, channels=2)
    mono, rate = pcm_from_wav(stereo_wav)
    assert rate == 16_000
    assert struct.unpack("<h", mono[:2])[0] == 1500
    assert len(mono) == 8 * 2


def test_remote_bridge_multipart() -> None:
    from saltvoice_local.remote_bridge import audio_bytes_from_request, build_wav, parse_multipart_fields

    wav = build_wav(b"\x00\x00" * 32)
    ctype, body = _multipart("audio", wav)
    fields = parse_multipart_fields(ctype, body)
    assert fields["audio"] == wav
    assert audio_bytes_from_request(ctype, body) == wav

    ctype, body = _multipart("file", wav)
    assert audio_bytes_from_request(ctype, body) == wav

    both_boundary = "----SaltBoth"
    both = (
        f"--{both_boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="a.wav"\r\n\r\n'
    ).encode("ascii") + wav + (
        f"\r\n--{both_boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="b.wav"\r\n\r\n'
    ).encode("ascii") + b"NOPE" + f"\r\n--{both_boundary}--\r\n".encode("ascii")
    assert audio_bytes_from_request(f"multipart/form-data; boundary={both_boundary}", both) == wav


def test_remote_bridge_format() -> None:
    from saltvoice_local.remote_bridge import encode_transcript

    ctype, body = encode_transcript("hello", plain=False)
    assert ctype.startswith("application/json")
    assert json.loads(body.decode("utf-8")) == {"text": "hello"}
    ctype, body = encode_transcript("hello", plain=True)
    assert ctype.startswith("text/plain")
    assert body == b"hello"
    ctype, body = encode_transcript("", plain=False)
    assert json.loads(body.decode("utf-8")) == {"text": ""}


def test_transcribe_force_skips_gate() -> None:
    from saltvoice_local import stt

    class _Seg:
        text = "forced"

    class _Dummy:
        def transcribe(self, audio, **kwargs):
            return [_Seg()], None

    prev_on = stt._stt_on
    prev_model = stt._model
    pcm = b"\x00\x7f" * 8000
    try:
        stt._stt_on = False
        stt._model = _Dummy()
        assert stt.transcribe_pcm(pcm, 16_000, min_rms=0.0, force=False) == ""
        assert stt.transcribe_pcm(pcm, 16_000, min_rms=0.0, force=True) == "forced"

        from saltvoice_local.remote_bridge import RemoteBridge

        seen: dict[str, object] = {}
        orig = stt.transcribe_pcm

        def _spy(pcm_arg, sample_rate=24000, language="en", min_rms=0.008, force=False):
            seen["force"] = force
            return "spy"

        stt.transcribe_pcm = _spy  # type: ignore[method-assign]
        try:
            assert RemoteBridge().transcribe(pcm, 16_000) == "spy"
            assert seen.get("force") is True
        finally:
            stt.transcribe_pcm = orig
    finally:
        stt._stt_on = prev_on
        stt._model = prev_model


def test_remote_bridge_http() -> None:
    from saltvoice_local.config import Settings, describe_setup
    from saltvoice_local.remote_bridge import RemoteBridge, build_wav

    settings = Settings()
    assert settings.remote_bridge_enabled is True
    assert settings.remote_bridge_port == 8791
    assert any("Remote bridge: ON" in line for line in describe_setup(settings))

    def fake_transcribe(pcm: bytes, sample_rate: int, language: str) -> str:
        return "hello phone"

    grok_got: dict[str, str] = {}

    def grok_cb(text: str) -> dict:
        grok_got["text"] = text
        return {"status": "ok"}

    wav = build_wav(b"\x00\x00" * 160)
    ctype, body = _multipart("audio", wav)
    bridge = RemoteBridge(
        host="127.0.0.1",
        port=0,
        transcribe_fn=fake_transcribe,
        grok_callback=None,
    )
    bridge.start()
    try:
        base = f"http://127.0.0.1:{bridge.port}"
        with _http_open(urllib.request.Request(f"{base}/health")) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            assert resp.status == 200
            assert health["ok"] is True
            assert health["service"] == "salt-remote-bridge"
            assert health["port"] == bridge.port
            assert health["auth"] is False
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"

        with _http_open(urllib.request.Request(base)) as resp:
            root = json.loads(resp.read().decode("utf-8"))
            assert root["ok"] is True

        opt = urllib.request.Request(f"{base}/transcribe", method="OPTIONS")
        with _http_open(opt) as resp:
            assert resp.status == 204
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"

        req = urllib.request.Request(
            f"{base}/transcribe",
            data=body,
            method="POST",
            headers={"Content-Type": ctype},
        )
        with _http_open(req) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {"text": "hello phone"}
            assert resp.headers.get("Content-Type", "").startswith("application/json")

        req = urllib.request.Request(
            f"{base}/transcribe.txt",
            data=body,
            method="POST",
            headers={"Content-Type": ctype},
        )
        with _http_open(req) as resp:
            assert resp.status == 200
            assert resp.read() == b"hello phone"
            assert resp.headers.get("Content-Type", "").startswith("text/plain")

        req = urllib.request.Request(
            f"{base}/transcribe",
            data=wav,
            method="POST",
            headers={"Content-Type": "audio/wav"},
        )
        with _http_open(req) as resp:
            assert json.loads(resp.read().decode("utf-8")) == {"text": "hello phone"}

        req = urllib.request.Request(
            f"{base}/send-to-grok",
            data=json.dumps({"text": "open notepad"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            _http_open(req)
            raise AssertionError("expected 501")
        except urllib.error.HTTPError as exc:
            assert exc.code == 501
            assert "error" in json.loads(exc.read().decode("utf-8"))

        silent = build_wav(b"")
        req = urllib.request.Request(
            f"{base}/transcribe",
            data=silent,
            method="POST",
            headers={"Content-Type": "audio/wav"},
        )
        with _http_open(req) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {"text": ""}

        req = urllib.request.Request(
            f"{base}/transcribe",
            data=b"not-a-wav",
            method="POST",
            headers={"Content-Type": "audio/wav"},
        )
        try:
            _http_open(req)
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            assert "error" in json.loads(exc.read().decode("utf-8"))
    finally:
        bridge.stop()

    bridge = RemoteBridge(
        host="127.0.0.1",
        port=0,
        transcribe_fn=fake_transcribe,
        grok_callback=grok_cb,
    )
    bridge.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{bridge.port}/send-to-grok",
            data=json.dumps({"text": "open notepad"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with _http_open(req) as resp:
            assert json.loads(resp.read().decode("utf-8")) == {"status": "ok"}
            assert grok_got["text"] == "open notepad"
    finally:
        bridge.stop()


def test_remote_bridge_auth_and_rate() -> None:
    import tempfile
    from pathlib import Path

    from saltvoice_local.remote_bridge import (
        RemoteBridge,
        build_wav,
        extract_token,
        load_or_create_token,
        tokens_match,
    )

    assert tokens_match("", "anything")
    assert tokens_match("secret", "secret")
    assert not tokens_match("secret", "nope")
    assert not tokens_match("secret", "")
    assert extract_token({"Authorization": "Bearer abc"}) == "abc"
    assert extract_token({"X-Salt-Token": "xyz"}) == "xyz"

    folder = Path(tempfile.mkdtemp())
    first = load_or_create_token("", folder)
    second = load_or_create_token("", folder)
    assert first == second
    assert load_or_create_token("from-config", folder) == "from-config"

    def fake_transcribe(pcm: bytes, sample_rate: int, language: str) -> str:
        return "ok"

    wav = build_wav(b"\x00\x00" * 160)
    bridge = RemoteBridge(
        host="127.0.0.1",
        port=0,
        transcribe_fn=fake_transcribe,
        token="test-token",
        rate_max=2,
        rate_window=60.0,
    )
    bridge.start()
    try:
        base = f"http://127.0.0.1:{bridge.port}"
        with _http_open(urllib.request.Request(f"{base}/health")) as resp:
            assert json.loads(resp.read().decode("utf-8"))["auth"] is True

        req = urllib.request.Request(
            f"{base}/transcribe",
            data=wav,
            method="POST",
            headers={"Content-Type": "audio/wav"},
        )
        try:
            _http_open(req)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        ok = urllib.request.Request(
            f"{base}/transcribe",
            data=wav,
            method="POST",
            headers={"Content-Type": "audio/wav", "X-Salt-Token": "test-token"},
        )
        with _http_open(ok) as resp:
            assert json.loads(resp.read().decode("utf-8")) == {"text": "ok"}
        with _http_open(ok) as resp:
            assert resp.status == 200
        try:
            _http_open(ok)
            raise AssertionError("expected 429")
        except urllib.error.HTTPError as exc:
            assert exc.code == 429
    finally:
        bridge.stop()


def test_remote_bridge_bind_and_pair() -> None:
    import tempfile
    from pathlib import Path

    from saltvoice_local.remote_bridge import (
        RemoteBridge,
        build_pair_url,
        peer_ip,
        resolve_bind_host,
    )

    assert resolve_bind_host("192.0.2.10") == "192.0.2.10"
    assert resolve_bind_host("tailscale") in {"127.0.0.1"} or resolve_bind_host("tailscale").startswith("100.")
    assert resolve_bind_host("0.0.0.0") in {"127.0.0.1"} or resolve_bind_host("0.0.0.0").startswith("100.")
    assert peer_ip("100.64.1.8:41234") == "100.64.1.8"
    assert peer_ip("[fd7a::1]:80") == "fd7a::1"
    raw = build_pair_url("mypc.tailc2bc11.ts.net", 8791, "secret", 1_800_000_000)
    assert raw.startswith("saltbubble://bridge?")
    assert "token=secret" in raw
    assert "host=mypc.tailc2bc11.ts.net" in raw

    peers = Path(tempfile.mkdtemp()) / "bridge.peers"
    peers.write_text("203.0.113.9\n", encoding="utf-8")
    bridge = RemoteBridge(
        host="127.0.0.1",
        port=0,
        token="pair-token",
        peers_path=peers,
        pair_ttl=0,
    )
    assert not bridge.peer_allowed("203.0.113.8")
    assert bridge.peer_allowed("203.0.113.9")
    assert bridge.peer_allowed("127.0.0.1")
    assert not bridge.pair_open()
    assert not bridge.can_pair("203.0.113.8")
    assert bridge.can_pair("203.0.113.9")

    open_bridge = RemoteBridge(
        host="127.0.0.1",
        port=0,
        token="pair-token",
        peers_path=peers,
        pair_ttl=60,
        advertised_host="mypc.tailc2bc11.ts.net",
    )
    assert open_bridge.can_pair("198.51.100.4")
    open_bridge.start()
    try:
        base = f"http://127.0.0.1:{open_bridge.port}"
        with _http_open(urllib.request.Request(f"{base}/pair")) as resp:
            pair_body = json.loads(resp.read().decode("utf-8"))
            assert pair_body["ok"] is True
            assert str(pair_body["deep"]).startswith("saltbubble://bridge?")
        locked = RemoteBridge(
            host="127.0.0.1",
            port=0,
            token="pair-token",
            allow_send_to_grok=False,
            grok_callback=lambda text: {"status": "ok", "visible_windows": ["Secret"]},
        )
        locked.start()
        try:
            denied = urllib.request.Request(
                f"http://127.0.0.1:{locked.port}/send-to-grok",
                data=json.dumps({"text": "open notepad"}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json", "X-Salt-Token": "pair-token"},
            )
            try:
                _http_open(denied)
                raise AssertionError("expected 403")
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
        finally:
            locked.stop()
        req = urllib.request.Request(
            f"{base}/pair",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json", "X-Salt-Token": "pair-token"},
        )
        with _http_open(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            assert body["ok"] is True
            assert body["peer"] == "127.0.0.1"
        assert open_bridge.allowed_ips == {"127.0.0.1"}
        assert not open_bridge.pair_open()
    finally:
        open_bridge.stop()


if __name__ == "__main__":
    test_resample()
    test_phrases()
    test_hub()
    test_remote_bridge_wav()
    test_remote_bridge_multipart()
    test_remote_bridge_format()
    test_transcribe_force_skips_gate()
    test_remote_bridge_http()
    test_remote_bridge_auth_and_rate()
    test_remote_bridge_bind_and_pair()
    print("ok")
