#!/bin/bash

echo "🛑 Stopping TIPQIC RAG Chatbot Services..."

# Kill processes by PID if files exist
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "Backend stopped (PID: $BACKEND_PID)" || echo "Backend not running"
    rm -f logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "Frontend stopped (PID: $FRONTEND_PID)" || echo "Frontend not running"
    rm -f logs/frontend.pid
fi

# Kill by process name as backup
pkill -f "uvicorn.*api.main" && echo "Killed remaining backend processes" || true
pkill -f "streamlit.*app.py" && echo "Killed remaining frontend processes" || true

echo "✅ All services stopped"
