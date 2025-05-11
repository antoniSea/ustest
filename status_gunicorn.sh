#!/bin/bash
# Script to check Gunicorn status and view logs

APP_DIR=$(dirname "$(readlink -f "$0")")
PID_FILE="$APP_DIR/gunicorn.pid"
LOG_DIR="$APP_DIR/logs"

echo "===== GUNICORN STATUS ====="

# Check if PID file exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "PID file found with process ID: $PID"
    
    # Check if process is running
    if ps -p "$PID" > /dev/null; then
        echo "Status: RUNNING"
        echo "Process info:"
        ps -p "$PID" -o pid,ppid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,command
        
        # Check for workers
        WORKERS=$(pgrep -P "$PID")
        WORKER_COUNT=$(echo "$WORKERS" | wc -w)
        echo "Worker processes: $WORKER_COUNT"
        if [ -n "$WORKERS" ]; then
            echo "Worker PIDs: $WORKERS"
            echo "Worker details:"
            ps -p "$WORKERS" -o pid,ppid,%cpu,%mem,vsz,rss,stat,start,time
        fi
    else
        echo "Status: NOT RUNNING (stale PID file)"
    fi
else
    echo "PID file not found."
    
    # Check if there are any gunicorn processes running anyway
    PIDS=$(pgrep -f "gunicorn.*app:app")
    if [ -n "$PIDS" ]; then
        echo "Found Gunicorn processes without PID file: $PIDS"
        echo "Process info:"
        ps -p "$PIDS" -o pid,ppid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,command
    else
        echo "Status: NOT RUNNING"
    fi
fi

# Check log files
echo ""
echo "===== LOG FILES ====="
if [ -d "$LOG_DIR" ]; then
    ACCESS_LOG="$LOG_DIR/gunicorn_access.log"
    ERROR_LOG="$LOG_DIR/gunicorn_error.log"
    
    if [ -f "$ACCESS_LOG" ]; then
        ACCESS_SIZE=$(du -h "$ACCESS_LOG" | cut -f1)
        echo "Access log: $ACCESS_LOG ($ACCESS_SIZE)"
        echo "Last 5 access log entries:"
        tail -n 5 "$ACCESS_LOG"
    else
        echo "Access log not found."
    fi
    
    echo ""
    
    if [ -f "$ERROR_LOG" ]; then
        ERROR_SIZE=$(du -h "$ERROR_LOG" | cut -f1)
        echo "Error log: $ERROR_LOG ($ERROR_SIZE)"
        echo "Last 5 error log entries:"
        tail -n 5 "$ERROR_LOG"
    else
        echo "Error log not found."
    fi
else
    echo "Log directory not found."
fi

echo ""
echo "===== COMMANDS ====="
echo "Start Gunicorn: ./start_gunicorn.sh"
echo "Stop Gunicorn: ./stop_gunicorn.sh"
echo "View real-time logs: tail -f $LOG_DIR/gunicorn_error.log" 