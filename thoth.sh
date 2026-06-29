#!/bin/bash
cd ~/Thoth
source venv/bin/activate
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
echo "Arrancando Thoth..."
sleep 5
python3 ~/Thoth/chat.py
