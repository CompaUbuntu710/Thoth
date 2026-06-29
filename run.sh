#!/bin/bash
source venv/bin/activate
export GROQ_API_KEY=$(grep GROQ_API_KEY .env | cut -d= -f2)
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
