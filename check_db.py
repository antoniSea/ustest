#!/usr/bin/env python3
"""
Utility to check the database status.
"""

import argparse
import sys
import json
from database import Database
from datetime import datetime

def print_table_stats(db, table_name):
    """Print statistics for a table"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get record count
    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    count = cursor.fetchone()['count']
    
    print(f"Table '{table_name}': {count} records")
    
    # Get sample data if records exist
    if count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = dict(cursor.fetchone())
        print(f"Sample record fields: {', '.join(sample.keys())}")

def list_jobs(db, limit=10, as_json=False, filters=None):
    """List jobs from the database"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM jobs"
    params = []
    
    # Apply filters if provided
    if filters:
        conditions = []
        
        if 'processed' in filters:
            conditions.append("processed = ?")
            params.append(int(filters['processed']))
        
        if 'proposal_generated' in filters:
            conditions.append("proposal_generated = ?")
            params.append(int(filters['proposal_generated']))
            
        if 'min_relevance' in filters:
            conditions.append("relevance_score >= ?")
            params.append(int(filters['min_relevance']))
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    jobs = [dict(row) for row in cursor.fetchall()]
    
    if as_json:
        print(json.dumps(jobs, indent=2, default=str))
    else:
        for job in jobs:
            print(f"ID: {job['job_id']}, Title: {job['title']}")
            print(f"  User: {job['username']}, Budget: {job['budget']}")
            print(f"  Status: {'Processed' if job['processed'] else 'Unprocessed'}, " + 
                  f"Proposal: {'Generated' if job['proposal_generated'] else 'Not Generated'}")
            print(f"  Relevance: {job['relevance_score']}")
            print(f"  Created: {job['created_at']}")
            print("-" * 80)

def list_queue(db, as_json=False):
    """List scheduled tasks from the queue"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM scrape_queue ORDER BY scheduled_time")
    tasks = [dict(row) for row in cursor.fetchall()]
    
    if as_json:
        print(json.dumps(tasks, indent=2, default=str))
    else:
        for task in tasks:
            print(f"Task {task['id']}: {task['task_type']}")
            print(f"  Status: {task['status']}")
            print(f"  Scheduled: {task['scheduled_time']}")
            print(f"  Last run: {task['last_run'] or 'Never'}")
            print(f"  Parameters: {task['parameters']}")
            print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Database Inspection Tool")
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--jobs', action='store_true', help='List jobs')
    parser.add_argument('--queue', action='store_true', help='List tasks in the queue')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of records')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--processed', action='store_true', help='Filter to processed jobs only')
    parser.add_argument('--with-proposals', action='store_true', help='Filter to jobs with proposals only')
    parser.add_argument('--min-relevance', type=int, help='Filter by minimum relevance score')
    
    args = parser.parse_args()
    
    # Connect to database
    db = Database()
    
    # Default to stats if no specific action is requested
    if not (args.stats or args.jobs or args.queue):
        args.stats = True
    
    if args.stats:
        print("=== Database Statistics ===")
        print_table_stats(db, "jobs")
        print_table_stats(db, "scrape_queue")
        print_table_stats(db, "submitted_proposals")
    
    if args.jobs:
        print("\n=== Jobs ===")
        filters = {}
        if args.processed:
            filters['processed'] = 1
        if args.with_proposals:
            filters['proposal_generated'] = 1
        if args.min_relevance is not None:
            filters['min_relevance'] = args.min_relevance
            
        list_jobs(db, limit=args.limit, as_json=args.json, filters=filters)
    
    if args.queue:
        print("\n=== Task Queue ===")
        list_queue(db, as_json=args.json)

if __name__ == "__main__":
    sys.exit(main()) 