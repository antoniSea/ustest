#!/usr/bin/env python3
"""
Script to mark unprocessed jobs as processed to prepare them for proposal generation.
"""

import argparse
import logging
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def mark_jobs_as_processed(limit=None, min_relevance=None):
    """Mark unprocessed jobs as processed"""
    db = Database()
    
    # Get unprocessed jobs
    unprocessed_jobs = db.get_unprocessed_jobs(limit=100 if limit is None else limit)
    
    if not unprocessed_jobs:
        logger.info("Brak nieprzetworzonych zleceń w bazie danych.")
        return 0
    
    logger.info(f"Znaleziono {len(unprocessed_jobs)} nieprzetworzonych zleceń.")
    
    # Count of jobs that were marked as processed
    processed_count = 0
    
    for job in unprocessed_jobs:
        job_id = job.get('job_id')
        
        # Skip if job_id is None
        if job_id is None:
            logger.warning(f"Pomijam zlecenie bez ID: {job.get('title', 'Brak tytułu')}")
            continue
        
        # Debug info
        logger.info(f"Przetwarzanie zlecenia: {job_id} - {job.get('title', 'Brak tytułu')}")
        
        # If min_relevance is specified, evaluate job relevance
        if min_relevance is not None:
            # Import the function locally to avoid circular imports
            from ai_proposal_generator import evaluate_relevance
            
            # Create combined job description
            job_description = f"{job.get('title', '')}. {job.get('full_description', '')}"
            if job.get('requirements'):
                job_description += f"\n\nWymagania: {job.get('requirements')}"
            
            # Evaluate relevance
            relevance_score = evaluate_relevance(
                job_description, 
                client_info=job.get('username', ''),
                budget=job.get('budget', '')
            )
            
            # Skip if below minimum relevance
            if relevance_score < min_relevance:
                logger.info(f"Pomijam zlecenie {job_id} (relevance: {relevance_score} < {min_relevance})")
                continue
        
        # Mark job as processed
        db.mark_job_as_processed(job_id)
        logger.info(f"Oznaczono zlecenie {job_id} jako przetworzone")
        processed_count += 1
    
    logger.info(f"Zakończono przetwarzanie. Oznaczono {processed_count} zleceń jako przetworzone.")
    return processed_count

def main():
    parser = argparse.ArgumentParser(description="Mark unprocessed jobs as processed")
    parser.add_argument('--limit', type=int, help='Limit the number of jobs to process')
    parser.add_argument('--min-relevance', type=int, help='Only process jobs with minimum relevance score')
    
    args = parser.parse_args()
    
    mark_jobs_as_processed(limit=args.limit, min_relevance=args.min_relevance)

if __name__ == "__main__":
    main() 