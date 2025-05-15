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
    """Get all pending tasks of the specified type that are due"""
    cursor = conn.cursor()
    
    # Get current time
    current_time = datetime.now()
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"Current time: {current_time_str}")
    
    # First, get all pending tasks of the specified type to inspect them
    cursor.execute("""
        SELECT id, task_type, scheduled_time, parameters 
        FROM scrape_queue 
        WHERE status = 'pending' 
        AND task_type = ?
    """, (task_type,))
    
    all_tasks = cursor.fetchall()
    
    tasks_to_process = []
    
    if all_tasks:
        logger.info(f"Found {len(all_tasks)} total pending tasks of type {task_type}")
        for task in all_tasks:
            task_id = task[0]
            scheduled_time_str = task[2]
            parameters = task[3]
            
            try:
                # Try to parse the datetime - handle both ISO format and standard format
                try:
                    # Try ISO format first (with T and possibly fractional seconds)
                    scheduled_time = datetime.fromisoformat(scheduled_time_str)
                except ValueError:
                    try:
                        # Try standard format (YYYY-MM-DD HH:MM:SS)
                        scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Last resort - try to parse with dateutil if available
                        try:
                            from dateutil import parser
                            scheduled_time = parser.parse(scheduled_time_str)
                        except (ImportError, ValueError):
                            logger.error(f"Could not parse date '{scheduled_time_str}' for task {task_id}")
                            continue
                
                time_diff = (scheduled_time - current_time).total_seconds()
                minutes_remaining = int(time_diff / 60)
                
                if time_diff <= 0:
                    # Task is due - add it to processing list
                    logger.info(f"Task {task_id} is DUE for processing (scheduled at {scheduled_time_str}, {abs(minutes_remaining)} minutes ago)")
                    tasks_to_process.append({
                        'id': task_id,
                        'parameters': parameters,
                        'task_type': task_type,
                        'scheduled_time': scheduled_time_str
                    })
                else:
                    logger.info(f"Task {task_id} is scheduled for the future (in {minutes_remaining} minutes)")
            except Exception as e:
                logger.error(f"Error parsing scheduled_time '{scheduled_time_str}' for task {task_id}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    if tasks_to_process:
        logger.info(f"{len(tasks_to_process)} tasks are due for processing now")
    else:
        logger.info("No tasks are due for processing yet")
    
    return tasks_to_process

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
        
        # IMPORTANT: For real production use with clients, remove this override
        # For testing purposes only:
        # email = "info@soft-synergy.com"
        
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

W załączniku przesyłamy wersję PDF oferty, którą mogli Państwo obejrzeć online.

Jesteśmy do Państwa dyspozycji w przypadku pytań lub potrzeby dodatkowych informacji.
Chętnie umówimy się na krótkie spotkanie, aby omówić szczegóły potencjalnej współpracy.

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
            
            # Update database to prevent duplicate emails for this presentation
            try:
                conn = get_connection()
                cursor = conn.cursor()
                # Mark any other pending tasks for this presentation as completed
                cursor.execute("""
                    UPDATE scrape_queue 
                    SET status = 'completed', last_run = ? 
                    WHERE task_type = 'send_pdf_email' 
                    AND status = 'pending' 
                    AND parameters LIKE ?
                    AND id != ?
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    f'%"presentation_slug": "{presentation_slug}"%',
                    task_id
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error updating related tasks: {str(e)}")
            
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
        
        # Get all pending tasks that are due
        tasks = get_pending_tasks(conn)
        
        if tasks:
            logger.info(f"Processing {len(tasks)} tasks that are due")
            
            # Process each task
            for task in tasks:
                # Debug the task
                logger.info(f"Task {task['id']} scheduled for {task['scheduled_time']}")
                
                # Process the task
                result = process_pdf_email_task(task)
                
                if result:
                    mark_task_completed(conn, task['id'])
                else:
                    mark_task_failed(conn, task['id'])
        else:
            logger.info("No tasks are due for processing yet")
        
    except Exception as e:
        logger.error(f"Error processing tasks: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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