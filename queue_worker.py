#!/usr/bin/env python3
"""
Queue worker for processing scraping and proposal generation tasks.
This script can be run periodically via cron or manually.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from database import Database
from scraper import process_pending_tasks
from ai_proposal_generator import generate_proposals_from_database
from mailer import send_followup_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('queue_worker.log')
    ]
)
logger = logging.getLogger(__name__)

def process_scrape_queue(db):
    """Process pending scrape tasks"""
    logger.info("Processing scrape queue...")
    process_pending_tasks(db)

def process_proposal_queue(db, min_relevance=5, limit=10, auto_post=False):
    """Process proposal generation for new jobs"""
    logger.info("Processing proposal generation queue...")
    proposals = generate_proposals_from_database(
        db=db,
        min_relevance=min_relevance,
        limit=limit,
        auto_post=auto_post
    )
    logger.info(f"Generated {len(proposals)} proposals")

def process_followup_emails(db, min_relevance=7):
    """Process follow-up emails for submitted proposals with high relevance scores"""
    logger.info("Processing follow-up emails...")
    sent_count = send_followup_email(db, min_relevance)
    logger.info(f"Sent {sent_count} follow-up emails")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Queue worker for Useme automation")
    parser.add_argument('--scrape', action='store_true', help='Process scrape queue')
    parser.add_argument('--proposals', action='store_true', help='Process proposal generation')
    parser.add_argument('--min-relevance', type=int, default=5, help='Minimum relevance score for proposals')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of proposals to generate')
    parser.add_argument('--auto-post', action='store_true', help='Automatically post generated proposals')
    parser.add_argument('--followup-emails', action='store_true', help='Send follow-up emails to high relevance proposals')
    parser.add_argument('--followup-min-relevance', type=int, default=7, help='Minimum relevance score for follow-up emails')
    
    args = parser.parse_args()
    
    # Connect to database
    db = Database()
    
    try:
        # Process scrape queue
        if args.scrape:
            process_scrape_queue(db)
        
        # Process proposal generation
        if args.proposals:
            process_proposal_queue(
                db, 
                min_relevance=args.min_relevance,
                limit=args.limit,
                auto_post=args.auto_post
            )
        
        # Process follow-up emails
        if args.followup_emails:
            process_followup_emails(db, min_relevance=args.followup_min_relevance)
        
        # If no arguments were provided, process all queues
        if not (args.scrape or args.proposals or args.followup_emails):
            logger.info("No specific tasks specified, processing all queues...")
            process_scrape_queue(db)
            process_proposal_queue(db)
            process_followup_emails(db)
    
    except Exception as e:
        logger.error(f"Error in queue worker: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 