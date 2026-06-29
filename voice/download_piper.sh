#!/bin/bash
# Descarga la voz Piper para español (voz natural, local)
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/piper_voices"
cd "$DIR/piper_voices"

VOICE="es_ES-carlfm-x_low"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/$VOICE"

echo "Descargando voz Piper: $VOICE"
wget -q --show-progress "$BASE_URL/$VOICE.onnx?download=true" -O "$VOICE.onnx"
wget -q --show-progress "$BASE_URL/$VOICE.onnx.json?download=true" -O "$VOICE.onnx.json"
echo "Voz Piper lista en voice/piper_voices/"
