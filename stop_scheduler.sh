#!/bin/bash

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to the script directory
cd "$DIR"

# Check if PID file exists
if [ -f "scheduler.pid" ]; then
    PID=$(cat scheduler.pid)
    
    # Check if process is running
    if ps -p $PID > /dev/null; then
        echo "Stopping scheduler with PID: $PID"
        kill $PID
        
        # Wait a bit and check if it's still running
        sleep 2
        if ps -p $PID > /dev/null; then
            echo "Process still running, forcing termination..."
            kill -9 $PID
        fi
        
        echo "Scheduler stopped."
    else
        echo "Scheduler process with PID $PID is not running."
    fi
    
    # Remove the PID file
    rm scheduler.pid
    echo "Removed PID file."
else
    echo "No scheduler seems to be running (scheduler.pid not found)."
fi 