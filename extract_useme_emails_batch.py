#!/usr/bin/env python3
import sys
import csv
import argparse
from extract_useme_email import extract_employer_email, extract_job_id_from_url

def process_input_file(input_file, output_file):
    """
    Process a file containing job IDs or URLs, one per line.
    Extract employer emails and save results to CSV.
    """
    job_ids = []
    
    # Read job IDs from input file
    with open(input_file, 'r') as f:
        for line in f:
            job_id = line.strip()
            if job_id and not job_id.startswith('#'):  # Skip empty lines and comments
                job_ids.append(job_id)
    
    print(f"Found {len(job_ids)} job IDs in {input_file}")
    
    # Process each job ID and collect results
    results = []
    for i, job_id in enumerate(job_ids, 1):
        print(f"Processing {i}/{len(job_ids)}: {job_id}")
        
        # Extract job ID from URL if it's a URL
        original_id = job_id
        if job_id.startswith('http'):
            extracted_id = extract_job_id_from_url(job_id)
            if extracted_id:
                job_id = extracted_id
        
        # Extract employer email
        email = extract_employer_email(job_id)
        
        # Store result
        results.append({
            'job_id': job_id,
            'original_input': original_id,
            'email': email if email else ''
        })
        
        print(f"  Email: {email if email else 'Not found'}")
    
    # Write results to CSV
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['job_id', 'original_input', 'email']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results saved to {output_file}")
    
    # Print summary
    found_count = sum(1 for r in results if r['email'])
    print(f"Summary: Found {found_count} out of {len(results)} emails")

def main():
    parser = argparse.ArgumentParser(description='Extract employer emails from multiple Useme job IDs')
    parser.add_argument('input_file', help='Text file with job IDs or URLs, one per line')
    parser.add_argument('-o', '--output', default='useme_emails.csv', help='Output CSV file (default: useme_emails.csv)')
    
    args = parser.parse_args()
    
    process_input_file(args.input_file, args.output)

if __name__ == '__main__':
    main() 