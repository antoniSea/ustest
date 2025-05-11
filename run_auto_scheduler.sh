#!/bin/bash

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to the script directory
cd "$DIR"

# Check if a virtual environment exists
if [ -d "venv" ]; then
    # Activate the virtual environment
    source venv/bin/activate
else
    echo "No virtual environment found. Please create one with 'python -m venv venv' and install requirements."
    exit 1
fi

# Run the scheduler in the background
echo "Starting auto proposal scheduler..."
nohup python auto_proposal_scheduler.py > auto_scheduler.out 2>&1 &

# Get the PID of the background process
PID=$!
echo "Scheduler started with PID: $PID"
echo $PID > scheduler.pid

echo "Scheduler is running in the background. Check auto_scheduler.out and auto_proposal_scheduler.log for output."
echo "To stop the scheduler, run: kill $(cat scheduler.pid)" 