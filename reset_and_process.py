import sqlite3
import os
import time
import logging
import subprocess
from database import Database
from scraper import UsemeScraper
from ai_proposal_generator import generate_proposals_from_database
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def reset_database():
    """Reset the database by deleting all data"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    # # Delete data from each table
    # for table in tables:
    #     table_name = table[0]
    #     if table_name != 'sqlite_sequence':  # Skip internal SQLite tables
    #         logger.info(f"Clearing table: {table_name}")
    #         cursor.execute(f"DELETE FROM {table_name}")
    
    conn.commit()
    logger.info("Database reset complete")

def scrape_latest_jobs():
    """Scrape the latest jobs from Useme"""
    logger.info("Starting scraper for the latest Useme jobs")
    scraper = UsemeScraper(db=Database())
    
    # Only scrape the first page
    num_pages = 10
    scraper.scrape(max_pages=num_pages, start_page=1)
    
    # Get jobs from the scraper
    jobs = scraper.jobs
    
    logger.info(f"Scraped {len(jobs)} jobs from Useme")
    return jobs

def generate_proposals(min_relevance=5):
    """Generate proposals for jobs with relevance score above threshold"""
    logger.info(f"Generating proposals for jobs with relevance >= {min_relevance}")
    
    result = generate_proposals_from_database(
        min_relevance=min_relevance,
        limit=20,  # Increase limit to process more jobs
        auto_save=True,
        auto_post=False  # We'll post them separately in the next step
    )
    
    logger.info(f"Generated proposals: {result}")
    return result

def post_proposals(min_relevance=5):
    """Post generated proposals to Useme for jobs with relevance score above threshold"""
    logger.info(f"Posting proposals for jobs with relevance >= {min_relevance}")
    
    # Get database connection
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get jobs with proposals and relevance above threshold
    cursor.execute(
        """
        SELECT job_id, proposal_text, price, timeline_days, email_content, project_slug, relevance_score
        FROM jobs
        WHERE proposal_generated = 1
        AND relevance_score >= ?
        AND job_id NOT IN (SELECT job_id FROM submitted_proposals)
        """,
        (min_relevance,)
    )
    jobs = cursor.fetchall()
    
    logger.info(f"Found {len(jobs)} proposals to post")
    
    # Post each proposal
    from useme_post_proposal import UsemeProposalPoster
    poster = UsemeProposalPoster()
    
    success_count = 0
    
    for job in jobs:
        job_id = job['job_id']
        proposal_text = job['proposal_text']
        price = job['price'] or 40  # Default to minimum if not set
        
        # Get job URL
        cursor.execute("SELECT url FROM jobs WHERE job_id = ?", (job_id,))
        job_url = cursor.fetchone()['url']
        
        if not job_url:
            logger.warning(f"No URL found for job {job_id}, skipping")
            continue
        
        logger.info(f"Posting proposal for job {job_id} with relevance {job['relevance_score']}")
        
        # Get email content if available
        email_content = job['email_content']
        
        # Post the proposal
        result = poster.post_proposal(
            job_url=job_url,
            proposal_text=proposal_text,
            price=price,
            email_content=email_content
        )
        
        if result["success"]:
            # Store the submission in the database
            db.store_submitted_proposal(job_id, proposal_text, submission_time=datetime.now().isoformat())
            
            # If employer email was found, update the job record
            employer_email = result.get("employer_email")
            if employer_email:
                cursor.execute(
                    "UPDATE jobs SET employer_email = ? WHERE job_id = ?",
                    (employer_email, job_id)
                )
                conn.commit()
                
                # Also update the presentation if it exists
                if job['project_slug']:
                    try:
                        import json
                        presentation_file = os.path.join('presentations', f"{job['project_slug']}.json")
                        if os.path.exists(presentation_file):
                            with open(presentation_file, 'r', encoding='utf-8') as f:
                                presentation_data = json.load(f)
                            
                            # Add employer_email to presentation data
                            presentation_data['employer_email'] = employer_email
                            
                            with open(presentation_file, 'w', encoding='utf-8') as f:
                                json.dump(presentation_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(f"Error updating presentation with employer email: {str(e)}")
            
            success_count += 1
            logger.info(f"Successfully posted proposal for job {job_id}")
        else:
            logger.error(f"Failed to post proposal for job {job_id}")
        
        # Sleep briefly to avoid rate limiting
        time.sleep(2)
    
    logger.info(f"Posted {success_count} out of {len(jobs)} proposals")
    return success_count

def run_full_process(min_relevance=5):
    """Run the full process: reset DB, scrape, generate proposals, post proposals"""
    try:
        # Step 1: Reset database
        logger.info("STEP 1: Resetting database")
        reset_database()
        
        # Step 2: Scrape latest jobs
        logger.info("STEP 2: Scraping latest jobs")
        jobs = scrape_latest_jobs()
        
        # if not jobs or len(jobs) == 0:
            # logger.error("No jobs scraped. Aborting process.")
            # return
        
        # Step 3: Generate proposals
        logger.info("STEP 3: Generating proposals")
        generate_result = generate_proposals(min_relevance)
        
        # Step 4: Post proposals
        logger.info("STEP 4: Posting proposals")
        post_result = post_proposals(min_relevance)
        
        # Final summary
        logger.info(f"PROCESS COMPLETE: Scraped {len(jobs)} jobs, generated and posted proposals for jobs with relevance >= {min_relevance}")
        
    except Exception as e:
        logger.error(f"Error during process: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset database and process Useme jobs")
    parser.add_argument(
        "--min-relevance", 
        type=int, 
        default=5, 
        help="Minimum relevance score (1-10) for generating and posting proposals"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting continuous process with minimum relevance: {args.min_relevance}")
    
    try:
        while True:
            logger.info("Starting iteration")
            run_full_process(min_relevance=args.min_relevance)
            logger.info("Sleeping for 5 seconds before next iteration...")
            time.sleep(300)
    except KeyboardInterrupt:
        logger.info("Process stopped by user") 