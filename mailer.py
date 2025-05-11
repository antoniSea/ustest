#!/usr/bin/env python3
"""
Email sending functionality for the Useme automation system.
Used to send follow-up emails to employers after a proposal is submitted.
"""

import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, config=None):
        """Initialize email sender with configuration."""
        self.config = config or {}
        
        # Get SMTP settings from environment variables or config
        self.smtp_server = os.environ.get('SMTP_SERVER', self.config.get('smtp_server', 'smtp.gmail.com'))
        self.smtp_port = int(os.environ.get('SMTP_PORT', self.config.get('smtp_port', 587)))
        self.smtp_username = os.environ.get('SMTP_USERNAME', self.config.get('smtp_username', 'info@soft-synergy.com'))
        self.smtp_password = os.environ.get('SMTP_PASSWORD', self.config.get('smtp_password', ''))
        self.sender_email = os.environ.get('SENDER_EMAIL', self.config.get('sender_email', 'info@soft-synergy.com'))
        self.sender_name = os.environ.get('SENDER_NAME', self.config.get('sender_name', 'Antoni Seba | Soft Synergy'))
        
        if not self.smtp_password:
            logger.warning("SMTP password not set! Email sending will not work.")
    
    def send_email(self, recipient_email, subject, body, attachments=None):
        """Send an email to the specified recipient."""
        if not self.smtp_password:
            logger.error("Cannot send email: SMTP password not set")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    if os.path.exists(attachment):
                        with open(attachment, 'rb') as file:
                            part = MIMEApplication(file.read(), Name=os.path.basename(attachment))
                            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment)}"'
                            msg.attach(part)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False

def send_followup_email(db, min_relevance=7):
    """
    Send follow-up emails to employers one hour after a proposal was submitted,
    only for proposals with relevance score >= the minimum.
    """
    logger.info(f"Processing follow-up emails for proposals with relevance >= {min_relevance}")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get the current time
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Find submitted proposals from one hour ago with high relevance
        cursor.execute("""
            SELECT j.job_id, j.title, j.employer_email, j.email_content, sp.submission_time
            FROM jobs j
            JOIN submitted_proposals sp ON j.job_id = sp.job_id
            WHERE j.relevance_score >= ?
            AND sp.submission_time <= ?
            AND sp.submission_time >= ?
            AND (j.follow_up_email_sent IS NULL OR j.follow_up_email_sent = 0)
            AND j.employer_email IS NOT NULL
        """, (min_relevance, one_hour_ago.isoformat(), (now - timedelta(hours=2)).isoformat()))
        
        eligible_proposals = cursor.fetchall()
        logger.info(f"Found {len(eligible_proposals)} eligible proposals for follow-up emails")
        
        if not eligible_proposals:
            return 0
            
        # Initialize email sender
        email_sender = EmailSender()
        
        email_count = 0
        for proposal in eligible_proposals:
            job_id = proposal['job_id']
            recipient_email = proposal['employer_email']
            email_content = proposal['email_content']
            job_title = proposal['title']
            
            # Send the follow-up email
            subject = "Nasza odpowiedź na Państwa zgłoszenie na Useme"
            
            if email_sender.send_email(recipient_email, subject, email_content):
                # Update database to mark email as sent
                cursor.execute("""
                    UPDATE jobs 
                    SET follow_up_email_sent = 1, follow_up_email_sent_at = ? 
                    WHERE job_id = ?
                """, (now.isoformat(), job_id))
                conn.commit()
                
                email_count += 1
                logger.info(f"Sent follow-up email for job {job_id} - {job_title}")
                
        logger.info(f"Sent {email_count} follow-up emails")
        return email_count
        
    except Exception as e:
        logger.error(f"Error in send_followup_email: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0



