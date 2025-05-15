#!/usr/bin/env python3
"""
Process all pending PDF email tasks in the queue.
This script is a one-time tool to handle pending tasks that haven't been processed.
"""

import json
import logging
import os
import sys
import sqlite3
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
        "SELECT id, parameters, task_type FROM tasks WHERE status = 'pending' AND task_type = ?",
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
        "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id)
    )
    conn.commit()

def mark_task_failed(conn, task_id):
    """Mark a task as failed"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'failed', completed_at = ? WHERE id = ?",
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

def main():
    """Main function to process all pending PDF email tasks"""
    logger.info("Starting PDF email processor...")
    
    # Connect to the database
    conn = get_connection()
    
    # Get all pending tasks
    tasks = get_pending_tasks(conn)
    
    if not tasks:
        logger.info("No pending tasks found.")
        return
    
    logger.info(f"Found {len(tasks)} pending tasks")
    
    # Process each task
    for task in tasks:
        result = process_pdf_email_task(task)
        
        if result:
            mark_task_completed(conn, task['id'])
        else:
            mark_task_failed(conn, task['id'])
    
    logger.info("Finished processing tasks")

if __name__ == "__main__":
    main() 