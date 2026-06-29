#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
source venv/bin/activate
echo "Arrancando Thoth..."
python3 chat.py "$@"
