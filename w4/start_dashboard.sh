#!/bin/bash

# Start script for GeekBrain AI Dashboard
# This script starts all required services

set -e

echo "=========================================="
echo "GeekBrain AI — Starting All Services"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "geekbrain.db" ]; then
    echo "❌ Error: geekbrain.db not found"
    echo "   Please run this script from the w4 directory"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if .env exists in parent directory
if [ ! -f "../.env" ]; then
    echo "⚠️  Warning: .env file not found in parent directory"
    echo "   Some features may not work without proper configuration"
fi

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 1
    fi
    return 0
}

# Function to kill process on port
kill_port() {
    echo "   Killing existing process on port $1..."
    lsof -ti:$1 | xargs kill -9 2>/dev/null || true
    sleep 1
}

# Check and clean ports
echo "🔍 Checking ports..."
if ! check_port 8000; then
    echo "⚠️  Port 8000 is in use"
    kill_port 8000
fi
if ! check_port 8001; then
    echo "⚠️  Port 8001 is in use"
    kill_port 8001
fi
if ! check_port 8002; then
    echo "⚠️  Port 8002 is in use"
    kill_port 8002
fi
echo "✅ All ports are free"
echo ""

# Start monitoring API in background
echo "🚀 Starting Monitoring API (port 8000)..."
nohup python3 monitoring_api.py > logs/monitoring_api.log 2>&1 &
MONITORING_PID=$!
echo "   PID: $MONITORING_PID"

# Wait for monitoring API to be ready
echo "   Waiting for Monitoring API to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "   ✅ Monitoring API is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ⚠️  Monitoring API took longer than expected"
    fi
    sleep 1
done
echo ""

# Start main API (which auto-starts dashboard)
echo "🚀 Starting Main API (port 8001) + Dashboard (port 8002)..."
cd src
nohup python3 main.py > ../logs/main_api.log 2>&1 &
MAIN_PID=$!
cd ..
echo "   PID: $MAIN_PID"

# Wait for main API to be ready
echo "   Waiting for Main API to start..."
for i in {1..15}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "   ✅ Main API is ready"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "   ⚠️  Main API took longer than expected"
    fi
    sleep 1
done
echo ""

# Wait for dashboard to be ready
echo "   Waiting for Dashboard to start..."
for i in {1..10}; do
    if curl -s http://localhost:8002 > /dev/null 2>&1; then
        echo "   ✅ Dashboard is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ⚠️  Dashboard took longer than expected"
    fi
    sleep 1
done
echo ""

# Final health check
echo "🔍 Final health check..."
MONITORING_OK=false
MAIN_OK=false
DASHBOARD_OK=false

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Monitoring API is running"
    MONITORING_OK=true
else
    echo "❌ Monitoring API failed to start"
    echo "   Check logs: tail -f logs/monitoring_api.log"
fi

if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Main API is running"
    MAIN_OK=true
else
    echo "❌ Main API failed to start"
    echo "   Check logs: tail -f logs/main_api.log"
fi

if curl -s http://localhost:8002 > /dev/null 2>&1; then
    echo "✅ Dashboard is running"
    DASHBOARD_OK=true
else
    echo "❌ Dashboard failed to start"
    echo "   Check logs: tail -f logs/main_api.log"
fi

echo ""

# Check if all services are running
if [ "$MONITORING_OK" = true ] && [ "$MAIN_OK" = true ] && [ "$DASHBOARD_OK" = true ]; then
    echo "=========================================="
    echo "✅ All Services Started Successfully!"
    echo "=========================================="
else
    echo "=========================================="
    echo "⚠️  Some Services Failed to Start"
    echo "=========================================="
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs in logs/ directory"
    echo "  2. Verify .env configuration"
    echo "  3. Ensure Python dependencies installed"
    echo "  4. Check AWS credentials"
    echo ""
fi

echo ""
echo "📊 Service URLs:"
echo "   Monitoring API:  http://localhost:8000"
echo "   Main API:        http://localhost:8001"
echo "   Dashboard:       http://localhost:8002"
echo ""
echo "📝 Logs:"
echo "   Monitoring: logs/monitoring_api.log"
echo "   Main API:   logs/main_api.log"
echo ""
echo "🛑 To stop services:"
echo "   bash stop_dashboard.sh"
echo "   OR: kill $MONITORING_PID $MAIN_PID"
echo ""
echo "💡 Test the dashboard:"
echo "   python test_dashboard.py"
echo "   python test_dashboard_comprehensive.py"
echo ""

# Save PIDs to file for easy cleanup
echo "$MONITORING_PID" > .pids
echo "$MAIN_PID" >> .pids

# Keep script running and show logs
echo "=========================================="
echo "📋 Tailing logs (Ctrl+C to stop)..."
echo "=========================================="
echo ""

# Trap Ctrl+C to cleanup
trap "echo ''; echo '🛑 Stopping services...'; kill $MONITORING_PID $MAIN_PID 2>/dev/null; rm -f .pids; echo '✅ Services stopped'; exit 0" INT

# Tail logs from both services
tail -f logs/monitoring_api.log logs/main_api.log
