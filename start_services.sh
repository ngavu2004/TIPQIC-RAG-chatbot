#!/bin/bash
set -e

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "IP_NOT_FOUND")

echo "🚀 Starting TIPQIC RAG Chatbot Services..."
echo "🌐 Detected Public IP: $PUBLIC_IP"

# Navigate to project directory
cd /home/ec2-user/TIPQIC-RAG-chatbot

# Activate virtual environment
source .venv/bin/activate

# Kill any existing processes
pkill -f "uvicorn.*api.main" || true
pkill -f "streamlit.*app.py" || true

# Wait a moment
sleep 2

# Start backend
echo "Starting backend API..."
nohup python api/main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start frontend with environment variables
echo "Starting frontend..."
export API_HOST=$PUBLIC_IP
export API_PORT=8000
export EC2_PUBLIC_IP=$PUBLIC_IP

nohup streamlit run frontend/app.py --server.port 8501 > logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Create logs directory if it doesn't exist
mkdir -p logs

# Save PIDs for later management
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo "✅ Services started successfully!"
echo ""
echo "🌐 Access URLs:"
echo "   Backend API: http://$PUBLIC_IP:8000"
echo "   Frontend: http://$PUBLIC_IP:8501"
echo "   API Docs: http://$PUBLIC_IP:8000/docs"
echo ""
echo "📊 Process Information:"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "📝 View Logs:"
echo "   Backend: tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 Stop Services:"
echo "   ./stop_services.sh"