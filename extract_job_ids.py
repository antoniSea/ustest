#!/usr/bin/env python3
"""
Script to extract job_ids from URLs and update the database
"""

import re
import logging
import sqlite3
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_job_id_from_url(url):
    """Extract job ID from URL"""
    if not url:
        return None
    
    # Match patterns like /jobs/123456/
    match = re.search(r'/jobs/(\d+)/', url)
    if match:
        return match.group(1)
    
    # Also try to match format like "projekt-ulotki,115348/"
    match = re.search(r',(\d+)/?$', url)
    if match:
        return match.group(1)
    
    return None

def update_job_ids():
    """Update job_ids in the database based on URLs"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all jobs
    cursor.execute("SELECT id, job_id, url, title FROM jobs")
    jobs = [dict(row) for row in cursor.fetchall()]
    
    if not jobs:
        logger.info("Brak zleceń w bazie danych.")
        return 0
    
    logger.info(f"Znaleziono {len(jobs)} zleceń.")
    
    # Count of jobs that were updated
    updated_count = 0
    duplicates_count = 0
    
    for job in jobs:
        internal_id = job['id']
        current_job_id = job['job_id']
        url = job['url']
        title = job['title']
        
        # Skip if job already has a job_id
        if current_job_id:
            continue
        
        # Extract job_id from URL
        job_id = extract_job_id_from_url(url)
        
        if not job_id:
            logger.warning(f"Nie można wyciągnąć job_id z URL: {url} dla zlecenia: {title}")
            continue
        
        try:
            # Update job with extracted job_id
            cursor.execute(
                "UPDATE jobs SET job_id = ? WHERE id = ?",
                (job_id, internal_id)
            )
            conn.commit()
            
            logger.info(f"Zaktualizowano job_id dla zlecenia {title}: {job_id}")
            updated_count += 1
            
        except sqlite3.IntegrityError:
            # Handle duplicate job_id (UNIQUE constraint violation)
            logger.warning(f"Znaleziono duplikat job_id: {job_id} dla zlecenia: {title}")
            
            # Option 1: Remove the duplicate
            cursor.execute("DELETE FROM jobs WHERE id = ?", (internal_id,))
            conn.commit()
            logger.info(f"Usunięto duplikat zlecenia: {title}")
            duplicates_count += 1
            
            # Option 2 (alternative): Make the job_id unique by adding a suffix
            # cursor.execute(
            #     "UPDATE jobs SET job_id = ? WHERE id = ?",
            #     (f"{job_id}_duplicate", internal_id)
            # )
            # conn.commit()
            # logger.info(f"Zaktualizowano zduplikowany job_id dla zlecenia {title}: {job_id}_duplicate")
            # updated_count += 1
    
    logger.info(f"Zakończono aktualizację. Zaktualizowano {updated_count} zleceń, usunięto {duplicates_count} duplikatów.")
    return updated_count

def fix_duplicate_jobs():
    """Find and fix duplicate jobs in the database"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Find jobs with duplicate job_ids
    cursor.execute("""
        SELECT job_id, COUNT(*) as count 
        FROM jobs 
        WHERE job_id IS NOT NULL 
        GROUP BY job_id 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        logger.info("Nie znaleziono zduplikowanych job_id w bazie danych.")
        return 0
    
    logger.info(f"Znaleziono {len(duplicates)} zduplikowanych job_id.")
    
    # Count of removed duplicates
    removed_count = 0
    
    for duplicate in duplicates:
        job_id = duplicate['job_id']
        count = duplicate['count']
        
        logger.info(f"Usuwanie duplikatów dla job_id: {job_id} (znaleziono {count})")
        
        # Get all instances of this job_id
        cursor.execute("SELECT id, title, created_at FROM jobs WHERE job_id = ? ORDER BY created_at DESC", (job_id,))
        instances = cursor.fetchall()
        
        # Keep the newest one, remove the rest
        if len(instances) > 1:
            # Skip the first one (the newest) and delete the rest
            for instance in instances[1:]:
                cursor.execute("DELETE FROM jobs WHERE id = ?", (instance['id'],))
                logger.info(f"Usunięto duplikat: {instance['title']} (id: {instance['id']})")
                removed_count += 1
            
            conn.commit()
    
    logger.info(f"Zakończono usuwanie duplikatów. Usunięto {removed_count} zduplikowanych zleceń.")
    return removed_count

if __name__ == "__main__":
    # First fix any existing duplicates
    fix_duplicate_jobs()
    
    # Then update job_ids for remaining jobs
    update_job_ids() 