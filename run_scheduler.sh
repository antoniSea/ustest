#!/bin/bash

# Script to run the task scheduler as a background service
# Usage: ./run_scheduler.sh [start|stop|status]

PID_FILE="scheduler.pid"
LOG_FILE="scheduler.log"

start_scheduler() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null; then
            echo "Scheduler is already running with PID $pid"
            return 0
        else
            echo "PID file exists but process is not running. Removing stale PID file."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "Starting task scheduler..."
    python3 task_scheduler.py > "$LOG_FILE" 2>&1 &
    
    # Store the PID
    pid=$!
    echo $pid > "$PID_FILE"
    echo "Scheduler started with PID $pid"
}

stop_scheduler() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        echo "Stopping scheduler with PID $pid..."
        kill $pid
        rm -f "$PID_FILE"
        echo "Scheduler stopped"
    else
        echo "Scheduler is not running"
    fi
}

status_scheduler() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null; then
            echo "Scheduler is running with PID $pid"
        else
            echo "Scheduler is not running (stale PID file)"
        fi
    else
        echo "Scheduler is not running"
    fi
}

case "$1" in
    start)
        start_scheduler
        ;;
    stop)
        stop_scheduler
        ;;
    restart)
        stop_scheduler
        sleep 2
        start_scheduler
        ;;
    status)
        status_scheduler
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0 