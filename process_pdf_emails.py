#!/usr/bin/env python3
"""
Process PDF email tasks in the queue continuously.
This script runs as a daemon, checking for new tasks every minute.
"""

import json
import logging
import os
import sys
import sqlite3
import time
from datetime import datetime

from mailer import EmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProcessPDFEmails')

def get_connection(db_path="useme.db"):
    """Get a connection to the database"""
    return sqlite3.connect(db_path)

def get_pending_tasks(conn, task_type="send_pdf_email"):
    """Get all pending tasks of the specified type"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, parameters, task_type FROM scrape_queue WHERE status = 'pending' AND task_type = ?",
        (task_type,)
    )
    
    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'id': row[0],
            'parameters': row[1],
            'task_type': row[2]
        })
    
    return tasks

def mark_task_completed(conn, task_id):
    """Mark a task as completed"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE scrape_queue SET status = 'completed', last_run = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id)
    )
    conn.commit()

def mark_task_failed(conn, task_id):
    """Mark a task as failed"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE scrape_queue SET status = 'failed', last_run = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id)
    )
    conn.commit()

def process_pdf_email_task(task):
    """Process a single PDF email task"""
    task_id = task['id']
    parameters_str = task['parameters']
    
    logger.info(f"Processing task {task_id} of type send_pdf_email")
    
    try:
        # Parse the parameters JSON
        parameters = json.loads(parameters_str)
        
        # Extract parameters
        email = parameters.get('email')
        subject = parameters.get('subject', 'Materiały z naszej prezentacji')
        message = parameters.get('message')
        pdf_path = parameters.get('pdf_path')
        presentation_slug = parameters.get('presentation_slug')
        
        # FOR TESTING: Override recipient email
        email = "info@soft-synergy.com"
        
        # Validate required parameters
        if not email or not pdf_path:
            logger.error("Missing required parameters for send_pdf_email task")
            return False
        
        # Check if PDF file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found at path: {pdf_path}")
            return False
            
        # Send email with attachment
        email_sender = EmailSender()  # Loads config automatically
        
        # Prepare a more personalized message if it's not provided
        if not message:
            message = f"""Szanowni Państwo,

Dziękujemy za zainteresowanie naszą prezentacją.

W załączniku przesyłamy wersję PDF naszej oferty, którą mogli Państwo obejrzeć online pod adresem: https://prezentacje.soft-synergy.com/{presentation_slug}

Z poważaniem,
Zespół Soft Synergy
            """
        
        # Send email with attachment
        result = email_sender.send_email_with_attachment(
            recipient_email=email,
            subject=subject,
            content=message,
            attachment_path=pdf_path
        )
        
        if result:
            logger.info(f"Successfully sent PDF email to {email}")
            return True
        else:
            logger.error(f"Failed to send PDF email to {email}")
            return False
                
    except Exception as e:
        logger.error(f"Error processing send_pdf_email task: {str(e)}")
        return False

def process_tasks():
    """Process all pending tasks"""
    try:
        # Connect to the database
        conn = get_connection()
        
        # Get all pending tasks
        tasks = get_pending_tasks(conn)
        
        if tasks:
            logger.info(f"Found {len(tasks)} pending tasks")
            
            # Process each task
            for task in tasks:
                result = process_pdf_email_task(task)
                
                if result:
                    mark_task_completed(conn, task['id'])
                else:
                    mark_task_failed(conn, task['id'])
        else:
            logger.debug("No pending tasks found")
            
    except Exception as e:
        logger.error(f"Error processing tasks: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to continuously process PDF email tasks"""
    logger.info("Starting PDF email processor daemon...")
    
    try:
        # Run continuously
        while True:
            # Process pending tasks
            process_tasks()
            
            # Log status
            logger.debug("Waiting for new tasks...")
            
            # Sleep for 60 seconds
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Process terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 