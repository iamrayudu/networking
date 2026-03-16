#!/bin/bash
# JobFlow OS V2 — Start Script
# Run from the jobflow_os/ root directory

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "========================================="
echo "  JobFlow OS V2"
echo "========================================="

# 1. Check venv
if [ ! -d "venv" ]; then
    echo "[setup] Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Install backend deps
echo "[backend] Installing dependencies..."
venv/bin/pip install -r requirements.txt -q

# 3. Check API key
if grep -q "YOUR_KEY_HERE" config.yaml; then
    echo ""
    echo "  ⚠  Set your Anthropic API key in config.yaml before running."
    echo "     claude.api_key: 'YOUR_KEY_HERE'  ← replace this"
    echo ""
fi

# 4. Init database
echo "[backend] Initialising database..."
venv/bin/python3 -c "from backend.memory.database import init_db; init_db(); print('  DB ready')"

# 5. Start backend (background)
echo "[backend] Starting FastAPI on http://localhost:8000 ..."
venv/bin/uvicorn backend.main:app --host localhost --port 8000 --reload &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"

sleep 2

# 6. Start frontend
echo "[frontend] Starting Vite on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!
echo "  PID: $FRONTEND_PID"
cd "$ROOT"

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  API docs → http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
