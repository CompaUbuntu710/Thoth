#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
source venv/bin/activate

cleanup() {
    echo -e "\nDeteniendo Thoth..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

echo "Arrancando Thoth..."
for i in $(seq 1 10); do
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

python3 chat.py "$@"
cleanup
