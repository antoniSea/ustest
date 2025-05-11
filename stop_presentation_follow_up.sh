#!/bin/bash
# Script to stop the presentation follow-up scheduler

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PID_FILE="presentation_follow_up.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    echo "Stopping presentation follow-up scheduler (PID: $PID)..."
    
    # Check if process exists
    if ps -p $PID > /dev/null; then
        # Kill the process
        kill $PID
        
        # Wait for it to terminate
        for i in {1..5}; do
            if ! ps -p $PID > /dev/null; then
                echo "Process stopped."
                break
            fi
            echo "Waiting for process to terminate..."
            sleep 1
        done
        
        # Force kill if still running
        if ps -p $PID > /dev/null; then
            echo "Process did not terminate gracefully. Forcing termination..."
            kill -9 $PID
        fi
    else
        echo "Process is not running."
    fi
    
    # Remove the PID file
    rm -f "$PID_FILE"
    echo "PID file removed."
else
    echo "PID file not found. The scheduler may not be running."
fi

echo "Presentation follow-up scheduler stopped." 