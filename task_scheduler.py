#!/usr/bin/env python3
"""
Task scheduler for Useme scraper.
This script is meant to be run as a daemon/service to periodically process tasks.
"""

import time
import logging
import os
import sys
import signal
from datetime import datetime, timedelta
from database import Database
from scraper import process_pending_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

# Global flag to determine if the script should continue running
running = True

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Received termination signal. Shutting down...")
    running = False

def schedule_next_task(db):
    """Schedule the next scraping task if none exists"""
    # Check if there are any pending tasks
    current_time = datetime.now()
    end_time = current_time + timedelta(days=1)  # Look ahead 1 day
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) as count FROM scrape_queue 
        WHERE status = 'pending' AND scheduled_time BETWEEN ? AND ?
        """,
        (current_time.isoformat(), end_time.isoformat())
    )
    result = cursor.fetchone()
    
    # If no pending tasks in the next day, schedule one
    if result['count'] == 0:
        # Schedule for 5 minutes from now
        next_run = current_time + timedelta(minutes=5)
        parameters = {
            'max_pages': 3,  # Default to 3 pages
            'start_page': 1
        }
        db.schedule_scrape_task(next_run, parameters)
        logger.info(f"Scheduled next scrape task for {next_run.isoformat()}")

def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting task scheduler")
    
    # Connect to database
    db = Database()
    
    # Schedule an initial task if none exists
    schedule_next_task(db)
    
    try:
        # Main loop
        while running:
            try:
                logger.info("Checking for pending tasks...")
                
                # Process any pending tasks
                process_pending_tasks(db)
                
                # Schedule next task if needed
                schedule_next_task(db)
                
                # Sleep for 1 minute before checking again
                for _ in range(60):
                    if not running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                # Sleep for 30 seconds before retrying after an error
                time.sleep(30)
    
    finally:
        logger.info("Task scheduler stopped")

if __name__ == "__main__":
    main() 