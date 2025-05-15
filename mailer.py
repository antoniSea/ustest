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
import configparser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load email configuration from config.ini file"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if not os.path.exists(config_file):
        config['EMAIL'] = {
            'smtp_server': 'smtp-relay.brevo.com',
            'smtp_port': '587',
            'smtp_username': '7cf37b003@smtp-brevo.com',
            'smtp_password': '2ZT3G0RYBx1QrMna',
            'sender_email': 'info@soft-synergy.com',
            'sender_name': 'Antoni Seba | Soft Synergy'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
    
    config.read(config_file)
    return config

class EmailSender:
    def __init__(self, config=None):
        """Initialize EmailSender with configuration"""
        if config is None:
            # Load from config.ini if not provided
            config_parser = load_config()
            self.config = {
                'smtp_server': config_parser['EMAIL'].get('smtp_server'),
                'smtp_port': int(config_parser['EMAIL'].get('smtp_port', 587)),
                'smtp_username': config_parser['EMAIL'].get('smtp_username'),
                'smtp_password': config_parser['EMAIL'].get('smtp_password'),
                'sender_email': config_parser['EMAIL'].get('sender_email'),
                'sender_name': config_parser['EMAIL'].get('sender_name')
            }
        else:
            self.config = config
            
        logger.info(f"EmailSender initialized with SMTP server: {self.config['smtp_server']}:{self.config['smtp_port']}")
    
    def send_email(self, recipient_email, subject, body, attachments=None):
        """Send an email to the specified recipient."""
        if not self.config['smtp_password']:
            logger.error("Cannot send email: SMTP password not set")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['sender_name']} <{self.config['sender_email']}>"
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
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
                
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False
    
    def send_email_with_attachment(self, recipient_email, subject, content, attachment_path=None):
        """
        Send an email with a single attachment.
        
        Args:
            recipient_email (str): Email address of the recipient
            subject (str): Email subject
            content (str): Email body content
            attachment_path (str): Path to the attachment file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not attachment_path:
            # If no attachment, use regular send_email method
            return self.send_email(recipient_email, subject, content)
            
        if not os.path.exists(attachment_path):
            logger.error(f"Attachment file not found: {attachment_path}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['sender_name']} <{self.config['sender_email']}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Determine if content is HTML
            is_html = '<html>' in content.lower()
            
            # Add body
            msg.attach(MIMEText(content, 'html' if is_html else 'plain'))
            
            # Add the attachment
            with open(attachment_path, 'rb') as file:
                attachment_filename = os.path.basename(attachment_path)
                part = MIMEApplication(file.read(), Name=attachment_filename)
                part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
                msg.attach(part)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
                
            logger.info(f"Email with attachment '{attachment_filename}' sent to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email with attachment to {recipient_email}: {str(e)}")
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

# Example usage
if __name__ == "__main__":
    # Example email
    config = load_config()
    
    email_config = {
        'smtp_server': config['EMAIL'].get('smtp_server'),
        'smtp_port': int(config['EMAIL'].get('smtp_port', 587)),
        'smtp_username': config['EMAIL'].get('smtp_username'),
        'smtp_password': config['EMAIL'].get('smtp_password'),
        'sender_email': config['EMAIL'].get('sender_email'),
        'sender_name': config['EMAIL'].get('sender_name')
    }
    
    sender = EmailSender(email_config)
    
    test_recipient = "test@example.com"
    test_subject = "Test Email from EmailSender"
    test_body = """
    <html>
    <body>
        <h1>Test Email</h1>
        <p>This is a test email from the EmailSender class.</p>
        <p>If you're seeing this, the email system is working correctly.</p>
    </body>
    </html>
    """
    
    print(f"Sending test email to {test_recipient}...")
    result = sender.send_email(test_recipient, test_subject, test_body)
    
    if result:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email. Check logs for details.")



