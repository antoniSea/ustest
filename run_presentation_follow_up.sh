#!/bin/bash
# Script to run the presentation follow-up scheduler
# Sends emails with PDF attachments after clients view presentations for 30 minutes

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create pid file to track process
echo $$ > presentation_follow_up.pid

# Set up log file
LOG_FILE="presentation_follow_up.out"
touch "$LOG_FILE"

# Check if Python virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the scheduler in the background with all output redirected to log file
echo "Starting presentation follow-up scheduler..."
echo "$(date): Starting presentation follow-up scheduler" >> "$LOG_FILE"

python presentation_follow_up.py >> "$LOG_FILE" 2>&1 &

# Save the PID of the background process
PID=$!
echo $PID > presentation_follow_up.pid
echo "Presentation follow-up scheduler started with PID $PID"
echo "Log file: $LOG_FILE" 