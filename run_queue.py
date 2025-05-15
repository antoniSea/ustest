#!/usr/bin/env python3
"""
This script runs the queue processor to handle pending tasks including send_pdf_email tasks.
Run this script to process queued emails and other scheduled tasks.
"""

import time
import json
import logging
import os
from datetime import datetime, timedelta

from queue_processor import QueueProcessor
from database import Database
from mailer import EmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('RunQueue')

def main():
    """Main function to run the queue processor"""
    logger.info("Starting queue processor...")
    
    # Create database instance
    db = Database()
    
    # Create queue processor instance
    processor = QueueProcessor(db_path="useme.db", sleep_interval=10)
    
    # Define send_pdf_email handler
    def send_pdf_email_handler(parameters):
        """Handler for sending PDF attachments via email"""
        logger.info(f"Processing PDF email task with parameters: {parameters}")
        
        try:
            # Extract parameters
            email = parameters.get('email')
            subject = parameters.get('subject', 'Materiały z naszej prezentacji')
            message = parameters.get('message')
            pdf_path = parameters.get('pdf_path')
            presentation_slug = parameters.get('presentation_slug')
            
            # FOR TESTING: Override recipient email to send all emails to info@soft-synergy.com
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
            try:
                email_sender = EmailSender()  # Loads config automatically
                
                # Prepare a more personalized message if it's not provided
                if not message:
                    message = f"""Szanowni Państwo,

Dziękujemy za zainteresowanie naszą prezentacją.

W załączniku przesyłamy wersję PDF naszej oferty, którą mogli Państwo obejrzeć online pod adresem: https://prezentacje.soft-synergy.com/{presentation_slug}

Możemy też zaproponować krótkie spotkanie, aby omówić szczegóły projektu i odpowiedzieć na wszelkie pytania.

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
                    
            except ImportError as e:
                logger.error(f"Failed to import required modules: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing send_pdf_email task: {str(e)}")
            return False
    
    # Register task handlers
    processor.register_task_handler('send_pdf_email', send_pdf_email_handler)
    
    # Process any pending tasks immediately
    logger.info("Processing pending tasks...")
    processor.process_queue()
    
    # Start the processor
    processor.start()
    
    try:
        # Keep the script running
        logger.info("Queue processor is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle keyboard interrupt
        logger.info("Stopping queue processor...")
        processor.stop()
        logger.info("Queue processor stopped.")

if __name__ == "__main__":
    main() 