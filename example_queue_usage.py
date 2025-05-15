#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime, timedelta
from queue_processor import QueueProcessor
from scraper import UsemeScraper
from mailer import Mailer
from extract_useme_email import extract_emails_for_job
from auto_proposal_scheduler import process_job_for_proposal
from useme_post_proposal import post_proposal_to_useme
from database import Database

def main():
    """
    Example of integrating the queue processor with existing functionality
    """
    # Initialize database
    db = Database()
    
    # Create a queue processor
    processor = QueueProcessor()
    
    # Define task handlers that use existing functionality
    
    # 1. Task handler for scraping new jobs
    def scrape_jobs_handler(parameters):
        print(f"Starting job scraping with parameters: {parameters}")
        categories = parameters.get('categories', [])
        max_pages = parameters.get('max_pages', 3)
        
        # Initialize the scraper
        scraper = UsemeScraper()
        scraper.login()
        
        # Scrape jobs from specified categories
        if categories:
            for category in categories:
                scraper.scrape_category(category, max_pages=max_pages)
        else:
            # Scrape all available categories
            scraper.scrape_all_categories(max_pages=max_pages)
            
        return True
    
    # 2. Task handler for extracting employer emails
    def extract_emails_handler(parameters):
        print(f"Starting email extraction with parameters: {parameters}")
        job_id = parameters.get('job_id')
        if job_id:
            # Extract email for a specific job
            extract_emails_for_job(job_id)
        else:
            # Extract emails for all unprocessed jobs
            limit = parameters.get('limit', 5)
            jobs = db.get_unprocessed_jobs(limit=limit)
            for job in jobs:
                extract_emails_for_job(job['job_id'])
        return True
    
    # 3. Task handler for generating proposals
    def generate_proposals_handler(parameters):
        print(f"Starting proposal generation with parameters: {parameters}")
        job_id = parameters.get('job_id')
        if job_id:
            # Generate proposal for a specific job
            process_job_for_proposal(job_id)
        else:
            # Generate proposals for eligible jobs
            limit = parameters.get('limit', 5)
            min_relevance = parameters.get('min_relevance', 7)
            jobs = db.get_jobs_for_proposal_generation(min_relevance=min_relevance, limit=limit)
            for job in jobs:
                process_job_for_proposal(job['job_id'])
        return True
    
    # 4. Task handler for posting proposals to Useme
    def post_proposals_handler(parameters):
        print(f"Starting proposal posting with parameters: {parameters}")
        job_id = parameters.get('job_id')
        if job_id:
            # Post proposal for a specific job
            post_proposal_to_useme(job_id)
        else:
            # Find jobs with generated proposals that haven't been posted yet
            limit = parameters.get('limit', 3)
            jobs = db.get_conn().execute("""
                SELECT job_id FROM jobs 
                WHERE proposal_generated = TRUE 
                AND proposal_posted = FALSE 
                LIMIT ?
            """, (limit,)).fetchall()
            
            for job in jobs:
                post_proposal_to_useme(job['job_id'])
        return True
    
    # 5. Task handler for sending follow-up emails
    def send_follow_up_emails_handler(parameters):
        print(f"Starting follow-up email sending with parameters: {parameters}")
        days_threshold = parameters.get('days_threshold', 3)
        
        # Find jobs that need follow-up emails
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        cutoff_date_str = cutoff_date.isoformat()
        
        jobs = db.get_conn().execute("""
            SELECT job_id, employer_email, title, username 
            FROM jobs 
            WHERE proposal_posted = TRUE 
            AND proposal_submitted_at < ? 
            AND follow_up_email_sent = FALSE
            AND employer_email IS NOT NULL
        """, (cutoff_date_str,)).fetchall()
        
        # Initialize mailer
        mailer = Mailer()
        
        for job in jobs:
            try:
                job_id = job['job_id']
                email = job['employer_email']
                title = job['title']
                username = job['username']
                
                # Compose and send email
                subject = f"Follow-up: Your job posting '{title}'"
                body = f"""Hello {username},

I wanted to follow up regarding my proposal for the job: {title}

I'm excited about the opportunity to work on this project and would love to discuss it further.

Best regards,
Your Name
"""
                mailer.send_email(email, subject, body)
                
                # Update database
                db.get_conn().execute("""
                    UPDATE jobs 
                    SET follow_up_email_sent = TRUE, 
                        follow_up_email_sent_at = ? 
                    WHERE job_id = ?
                """, (datetime.now().isoformat(), job_id))
                db.get_conn().commit()
                
                print(f"Sent follow-up email for job {job_id} to {email}")
            except Exception as e:
                print(f"Error sending follow-up email for job {job_id}: {e}")
        
        return True
    
    # Register all task handlers
    processor.register_task_handler('scrape_jobs', scrape_jobs_handler)
    processor.register_task_handler('extract_emails', extract_emails_handler)
    processor.register_task_handler('generate_proposals', generate_proposals_handler)
    processor.register_task_handler('post_proposals', post_proposals_handler)
    processor.register_task_handler('send_follow_up_emails', send_follow_up_emails_handler)
    
    # Schedule some example tasks
    
    # Scrape jobs every day at 8:00 AM
    tomorrow_morning = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    if tomorrow_morning < datetime.now():
        tomorrow_morning += timedelta(days=1)
    
    processor.add_task('scrape_jobs', 
                      {'categories': ['programming', 'graphics'], 'max_pages': 5},
                      scheduled_time=tomorrow_morning)
    
    # Extract emails for new jobs in 30 minutes
    processor.add_task('extract_emails', 
                      {'limit': 10}, 
                      scheduled_time=datetime.now() + timedelta(minutes=30))
    
    # Generate proposals in 1 hour
    processor.add_task('generate_proposals', 
                      {'min_relevance': 7, 'limit': 5}, 
                      scheduled_time=datetime.now() + timedelta(hours=1))
    
    # Post proposals in 2 hours
    processor.add_task('post_proposals', 
                      {'limit': 3}, 
                      scheduled_time=datetime.now() + timedelta(hours=2))
    
    # Send follow-up emails for proposals sent 3+ days ago
    processor.add_task('send_follow_up_emails', 
                      {'days_threshold': 3}, 
                      scheduled_time=datetime.now() + timedelta(hours=3))
    
    # Start the processor
    processor.start()
    
    try:
        # Keep the main thread alive
        print("Queue processor running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the processor when Ctrl+C is pressed
        processor.stop()
        print("Queue processor stopped.")

if __name__ == "__main__":
    main() 