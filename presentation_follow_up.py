#!/usr/bin/env python3
"""
Presentation Follow-up System

This script tracks presentation views and sends follow-up emails with PDF attachments 
after clients have viewed a presentation for 30 minutes.
"""

import os
import time
import logging
import schedule
from datetime import datetime, timedelta
import json

from database import Database
from mailer import EmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("presentation_follow_up.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directory where presentation JSON files are stored
PRESENTATIONS_DIR = os.path.join("presentations")

def create_pdf_from_presentation(presentation_slug):
    """
    Generate a PDF from the presentation for email attachment.
    Returns the path to the created PDF file.
    """
    try:
        # Ensure the presentation filename has .json extension
        if not presentation_slug.endswith('.json'):
            json_filename = f"{presentation_slug}.json"
        else:
            json_filename = presentation_slug
            presentation_slug = presentation_slug[:-5]  # Remove .json extension
        
        # Check if the JSON file exists
        json_path = os.path.join(PRESENTATIONS_DIR, json_filename)
        if not os.path.exists(json_path):
            logger.error(f"Presentation file not found: {json_path}")
            return None
        
        # Load the presentation data
        with open(json_path, 'r', encoding='utf-8') as f:
            presentation_data = json.load(f)
        
        # Generate PDF file name based on the input JSON filename
        pdf_filename = os.path.splitext(json_filename)[0] + '.pdf'
        pdf_path = os.path.join(PRESENTATIONS_DIR, pdf_filename)
        
        # Import create_pdf_from_presentation from app.py
        from app import create_pdf_from_presentation as create_pdf
        
        # Create the PDF
        create_pdf(presentation_data, pdf_path)
        
        return pdf_path
    
    except Exception as e:
        logger.error(f"Error generating PDF for presentation {presentation_slug}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_email_content(client_name, presentation_slug):
    """
    Generate email content for the follow-up email.
    """
    # Basic email content
    subject = f"Podsumowanie naszej prezentacji dla {client_name}"
    
    body = f"""
    <html>
    <body>
        <p>Szanowni Państwo,</p>
        
        <p>Dziękujemy za zapoznanie się z naszą prezentacją.</p>
        
        <p>W załączniku przesyłamy plik PDF zawierający wszystkie informacje, 
        które zostały przedstawione w prezentacji, aby ułatwić Państwu dostęp 
        do tych materiałów w przyszłości.</p>
        
        <p>Jeżeli mają Państwo jakiekolwiek pytania lub potrzebują dodatkowych informacji, 
        prosimy o kontakt.</p>
        
        <p>Z poważaniem,<br>
        Antoni Seba<br>
        Soft Synergy</p>
    </body>
    </html>
    """
    
    return subject, body

def process_presentation_follow_ups():
    """
    Check for clients who have viewed presentations for at least 30 minutes 
    and send them follow-up emails with PDF attachments.
    """
    try:
        logger.info("Checking for presentations to follow up...")
        
        # Initialize database connection
        db = Database()
        
        # Get current time
        now = datetime.now()
        thirty_minutes_ago = now - timedelta(minutes=30)
        
        # Get presentation views from the database
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Query to find clients viewing presentations for at least 30 minutes
        # We'll check first view timestamp for a client/presentation to see if it was at least 30 minutes ago
        query = """
        SELECT 
            pv.presentation_slug,
            pv.job_id,
            pv.client_ip,
            MIN(pv.viewed_at) as first_view,
            j.username as client_name,
            j.employer_email
        FROM 
            presentation_views pv
        JOIN
            jobs j ON pv.job_id = j.job_id
        WHERE 
            j.employer_email IS NOT NULL
            AND (j.presentation_follow_up_sent IS NULL OR j.presentation_follow_up_sent = 0)
        GROUP BY 
            pv.presentation_slug, pv.client_ip
        HAVING 
            first_view <= ?
        """
        
        cursor.execute(query, (thirty_minutes_ago.isoformat(),))
        eligible_views = cursor.fetchall()
        
        logger.info(f"Found {len(eligible_views)} presentations eligible for follow-up")
        
        if not eligible_views:
            return 0
        
        # Initialize email sender
        email_sender = EmailSender()
        
        # Add column for tracking presentation follow-up emails if it doesn't exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'presentation_follow_up_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent BOOLEAN DEFAULT FALSE')
            
        if 'presentation_follow_up_sent_at' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent_at TIMESTAMP')
            
        conn.commit()
        
        # Process each eligible presentation view
        email_count = 0
        for view in eligible_views:
            presentation_slug = view['presentation_slug']
            job_id = view['job_id']
            client_name = view['client_name']
            recipient_email = view['employer_email']
            
            logger.info(f"Processing follow-up for presentation {presentation_slug}, job {job_id}, client {client_name}")
            
            # Generate PDF for the presentation
            pdf_path = create_pdf_from_presentation(presentation_slug)
            if not pdf_path:
                logger.error(f"Could not generate PDF for presentation {presentation_slug}")
                continue
            
            # Create email content
            subject, body = get_email_content(client_name, presentation_slug)
            
            # Send email with PDF attachment
            if email_sender.send_email(recipient_email, subject, body, attachments=[pdf_path]):
                # Update database to mark email as sent
                cursor.execute("""
                    UPDATE jobs 
                    SET presentation_follow_up_sent = 1, presentation_follow_up_sent_at = ? 
                    WHERE job_id = ?
                """, (now.isoformat(), job_id))
                conn.commit()
                
                email_count += 1
                logger.info(f"Sent presentation follow-up email to {recipient_email} for {presentation_slug}")
            else:
                logger.error(f"Failed to send follow-up email for presentation {presentation_slug}")
        
        logger.info(f"Sent {email_count} presentation follow-up emails")
        return email_count
        
    except Exception as e:
        logger.error(f"Error in process_presentation_follow_ups: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def main():
    """Main function to run the scheduler."""
    logger.info("Starting Presentation Follow-up Scheduler")
    
    # Schedule the job to run every 5 minutes
    schedule.every(5).minutes.do(process_presentation_follow_ups)
    
    # Run immediately at startup
    logger.info("Running initial check...")
    process_presentation_follow_ups()
    
    # Keep the script running and check for scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main() 