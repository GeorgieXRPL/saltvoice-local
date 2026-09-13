#!/data/data/com.termux/files/usr/bin/bash
# Termux: record -> MyPC Whisper (Tailscale) -> clipboard -> paste in Grok Bot
PC="${SALT_PC:-mypc.tailc2bc11.ts.net}"
PORT="${SALT_BRIDGE_PORT:-8791}"
OUT="$HOME/salt-call.wav"
WAV16="$HOME/salt-call-16k.wav"

echo "PC=$PC:$PORT"
echo "Listening... tap Enter when done (max 60s)."
termux-microphone-record -f "$OUT" -l 60 start
read -r _
termux-microphone-record -q
ffmpeg -y -loglevel error -i "$OUT" -ar 16000 -ac 1 "$WAV16" || cp "$OUT" "$WAV16"

TEXT=$(curl -sS --connect-timeout 10 -F "file=@${WAV16};type=audio/wav" "http://${PC}:${PORT}/transcribe.txt") || {
  echo "Call failed - Tailscale up? Bridge running on MyPC?"
  exit 1
}
echo "$TEXT"
printf '%s' "$TEXT" | termux-clipboard-set
termux-toast "Salt: copied - paste in Grok Bot" 2>/dev/null || true
