#!/bin/bash
# Descarga el modelo Vosk para español (STT local)
cd "$(dirname "$0")"
wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip -q vosk-model-small-es-0.42.zip
rm vosk-model-small-es-0.42.zip
echo "Modelo Vosk español descargado en voice/vosk-model-small-es-0.42/"
