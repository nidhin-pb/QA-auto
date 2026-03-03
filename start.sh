#!/bin/bash
echo "=========================================="
echo " CVA QA Testing Automation Platform"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    exit 1
fi

echo "[1/5] Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt

echo "[2/5] Installing Playwright browsers..."
python3 -m playwright install chromium

echo "[3/5] Installing frontend dependencies..."
cd ../frontend
npm install

echo "[4/5] Building frontend..."
npm run build 2>/dev/null || echo "WARNING: Build failed, using dev server"

echo "[5/5] Starting servers..."
cd ../backend

# Start backend in background
python3 main.py &
BACKEND_PID=$!

# Wait a moment then start frontend
sleep 3
cd ../frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo " Backend: http://localhost:8000"
echo " Frontend: http://localhost:3000"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
