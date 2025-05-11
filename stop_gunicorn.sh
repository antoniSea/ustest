#!/bin/bash
# Script to stop Gunicorn daemon process

APP_DIR=$(dirname "$(readlink -f "$0")")
PID_FILE="$APP_DIR/gunicorn.pid"

echo "===== STOPPING GUNICORN ====="

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found. Gunicorn might not be running."
    
    # Check if there are any gunicorn processes running anyway
    PIDS=$(pgrep -f "gunicorn.*app:app")
    if [ -n "$PIDS" ]; then
        echo "Found Gunicorn processes without PID file: $PIDS"
        echo "Killing these processes..."
        for PID in $PIDS; do
            kill -9 "$PID"
            echo "Killed process $PID"
        done
        echo "All Gunicorn processes killed."
    else
        echo "No Gunicorn processes found."
    fi
    exit 0
fi

# Read PID from file
PID=$(cat "$PID_FILE")
echo "Found PID file with process ID: $PID"

# Check if process is running
if ps -p "$PID" > /dev/null; then
    echo "Stopping Gunicorn with PID $PID..."
    kill "$PID"
    
    # Wait for process to terminate
    echo "Waiting for process to terminate..."
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null; then
            echo "Process stopped."
            break
        fi
        sleep 1
    done
    
    # Force kill if process is still running
    if ps -p "$PID" > /dev/null; then
        echo "Process didn't terminate gracefully. Sending SIGKILL..."
        kill -9 "$PID"
        sleep 1
    fi
else
    echo "Process $PID not found. Gunicorn might have crashed or been stopped."
fi

# Remove PID file
rm -f "$PID_FILE"
echo "PID file removed."

# Check for any remaining gunicorn processes
PIDS=$(pgrep -f "gunicorn.*app:app")
if [ -n "$PIDS" ]; then
    echo "Found other Gunicorn processes: $PIDS"
    echo "Killing these processes..."
    for PID in $PIDS; do
        kill -9 "$PID"
        echo "Killed process $PID"
    done
fi

echo "===== GUNICORN STOPPED =====" 