#!/bin/bash

# Stop script for GeekBrain AI Dashboard

echo "🛑 Stopping GeekBrain AI services..."
echo ""

# Function to kill process by PID
kill_pid() {
    if ps -p $1 > /dev/null 2>&1; then
        echo "   Stopping process $1..."
        kill $1 2>/dev/null
        sleep 1
        # Force kill if still running
        if ps -p $1 > /dev/null 2>&1; then
            echo "   Force killing process $1..."
            kill -9 $1 2>/dev/null
        fi
    fi
}

# Read PIDs from file if exists
if [ -f ".pids" ]; then
    echo "📋 Stopping services from PID file..."
    while read pid; do
        kill_pid $pid
    done < .pids
    rm -f .pids
    echo "✅ Services from PID file stopped"
    echo ""
fi

# Also kill by port (in case PID file is missing)
echo "🔍 Checking ports..."

for port in 8000 8001 8002; do
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "   Killing processes on port $port..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
done

echo "✅ All ports cleared"
echo ""

# Verify services are stopped
echo "🔍 Verifying services are stopped..."
STOPPED=true

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use"
    STOPPED=false
else
    echo "✅ Port 8000 is free"
fi

if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8001 still in use"
    STOPPED=false
else
    echo "✅ Port 8001 is free"
fi

if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8002 still in use"
    STOPPED=false
else
    echo "✅ Port 8002 is free"
fi

echo ""

if [ "$STOPPED" = true ]; then
    echo "=========================================="
    echo "✅ All Services Stopped Successfully"
    echo "=========================================="
else
    echo "=========================================="
    echo "⚠️  Some ports are still in use"
    echo "=========================================="
    echo ""
    echo "Try running again or manually kill:"
    echo "  lsof -ti:8000,8001,8002 | xargs kill -9"
fi

echo ""
