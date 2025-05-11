#!/bin/bash
# Script to start Gunicorn as a background daemon process

# Configuration
APP_DIR=$(dirname "$(readlink -f "$0")")
NUM_WORKERS=4
PORT=5001
LOG_DIR="$APP_DIR/logs"
PID_FILE="$APP_DIR/gunicorn.pid"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "===== STARTING GUNICORN IN BACKGROUND ====="
echo "Application directory: $APP_DIR"
echo "Workers: $NUM_WORKERS"
echo "Port: $PORT"
echo "PID file: $PID_FILE"
echo "Logs: $LOG_DIR/gunicorn_access.log and $LOG_DIR/gunicorn_error.log"

# Check if Gunicorn is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "Gunicorn is already running with PID $PID"
        echo "To stop it, run: ./stop_gunicorn.sh"
        exit 0
    else
        echo "Stale PID file found. Removing..."
        rm "$PID_FILE"
    fi
fi

# Install gunicorn if not installed
if ! command -v gunicorn &> /dev/null; then
    echo "Gunicorn not found. Installing..."
    pip install gunicorn
fi

# Start Gunicorn in the background
echo "Starting Gunicorn..."
export APP_DOMAIN="prezentacje.soft-synergy.com"
export FORCE_HTTPS="true"

cd "$APP_DIR"
gunicorn --workers=$NUM_WORKERS \
         --bind=0.0.0.0:$PORT \
         --access-logfile="$LOG_DIR/gunicorn_access.log" \
         --error-logfile="$LOG_DIR/gunicorn_error.log" \
         --pid="$PID_FILE" \
         --daemon \
         --timeout=120 \
         "app:app"

# Check if Gunicorn started successfully
sleep 2
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "===== GUNICORN STARTED SUCCESSFULLY ====="
        echo "PID: $PID"
        echo "To check logs: tail -f $LOG_DIR/gunicorn_error.log"
        echo "To stop: ./stop_gunicorn.sh"
    else
        echo "Failed to start Gunicorn. Check logs for details."
        exit 1
    fi
else
    echo "Failed to start Gunicorn. PID file not created."
    exit 1
fi 