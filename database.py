import sqlite3
import os
import json
from datetime import datetime
import threading

# Thread-local storage for database connections
local = threading.local()

class Database:
    def __init__(self, db_path="useme.db"):
        self.db_path = db_path
        self.initialize_db()
    
    def get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(local, "connection"):
            local.connection = sqlite3.connect(self.db_path)
            local.connection.row_factory = sqlite3.Row
        return local.connection
    
    def initialize_db(self):
        """Create database tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create jobs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            job_id TEXT UNIQUE,
            username TEXT,
            title TEXT,
            short_description TEXT,
            budget TEXT,
            category TEXT,
            offers TEXT,
            expiry_date TEXT,
            url TEXT,
            avatar_url_source TEXT,
            avatar_filename_for_web TEXT,
            full_description TEXT,
            requirements TEXT,
            attachments TEXT,
            extra_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE,
            proposal_generated BOOLEAN DEFAULT FALSE,
            proposal_text TEXT,
            project_slug TEXT,
            relevance_score INTEGER,
            employer_email TEXT,
            price INTEGER,
            timeline_days INTEGER,
            presentation_url TEXT,
            email_content TEXT
        )
        ''')
        
        # Create queue table for scheduled tasks
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scrape_queue (
            id INTEGER PRIMARY KEY,
            task_type TEXT,
            status TEXT DEFAULT 'pending',
            scheduled_time TIMESTAMP,
            last_run TIMESTAMP,
            parameters TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create a table for tracking submitted proposals
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS submitted_proposals (
            id INTEGER PRIMARY KEY,
            job_id TEXT UNIQUE,
            proposal_text TEXT,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            response_message TEXT
        )
        ''')
        
        # Create a table for tracking presentation views
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS presentation_views (
            id INTEGER PRIMARY KEY,
            presentation_slug TEXT,
            job_id TEXT,
            client_ip TEXT,
            user_agent TEXT,
            referrer TEXT,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(job_id)
        )
        ''')
        
        # Check if extra_details column exists, add it if it doesn't
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'extra_details' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN extra_details TEXT')
            
        if 'email_content' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN email_content TEXT')
            
        if 'proposal_accepted' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN proposal_accepted BOOLEAN DEFAULT FALSE')
            
        # Add columns for tracking follow-up emails
        if 'follow_up_email_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN follow_up_email_sent BOOLEAN DEFAULT FALSE')
            
        if 'follow_up_email_sent_at' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN follow_up_email_sent_at TIMESTAMP')
            
        # Add column for tracking posted proposals
        if 'proposal_posted' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN proposal_posted BOOLEAN DEFAULT FALSE')
            
        # Add column for tracking sent messages
        if 'message_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN message_sent BOOLEAN DEFAULT FALSE')
            
        # Add columns for tracking presentation follow-up emails
        if 'presentation_follow_up_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent BOOLEAN DEFAULT FALSE')
            
        if 'presentation_follow_up_sent_at' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent_at TIMESTAMP')
            
        conn.commit()
    
    def store_job(self, job):
        """Store a job in the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Convert any dictionary/list fields to JSON strings
        if isinstance(job.get('attachments'), (list, dict)):
            job['attachments'] = json.dumps(job['attachments'])
            
        # Handle extra_details
        if isinstance(job.get('extra_details'), (dict, list)):
            job['extra_details'] = json.dumps(job['extra_details'], ensure_ascii=False)
        
        # Extract the job_id from the URL
        job_id = self.extract_job_id_from_url(job['url'])
        
        # Check if job exists
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", (job_id,))
        existing_job = cursor.fetchone()
        
        if existing_job:
            # Update existing job
            cursor.execute('''
            UPDATE jobs SET 
                username = ?, 
                title = ?, 
                short_description = ?, 
                budget = ?, 
                category = ?, 
                offers = ?, 
                expiry_date = ?, 
                url = ?, 
                avatar_url_source = ?, 
                avatar_filename_for_web = ?, 
                full_description = ?, 
                requirements = ?, 
                attachments = ?,
                extra_details = ?
            WHERE job_id = ?
            ''', (
                job.get('username', ''),
                job.get('title', ''),
                job.get('short_description', ''),
                job.get('budget', ''),
                job.get('category', ''),
                job.get('offers', ''),
                job.get('expiry_date', ''),
                job.get('url', ''),
                job.get('avatar_url_source', ''),
                job.get('avatar_filename_for_web', ''),
                job.get('full_description', ''),
                job.get('requirements', ''),
                job.get('attachments', ''),
                job.get('extra_details', '{}'),
                job_id
            ))
            conn.commit()
            return existing_job[0]
        else:
            # Insert new job
            try:
                cursor.execute('''
                INSERT INTO jobs 
                (job_id, username, title, short_description, budget, category, offers, 
                expiry_date, url, avatar_url_source, avatar_filename_for_web, 
                full_description, requirements, attachments, extra_details, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_id,
                    job.get('username', ''),
                    job.get('title', ''),
                    job.get('short_description', ''),
                    job.get('budget', ''),
                    job.get('category', ''),
                    job.get('offers', ''),
                    job.get('expiry_date', ''),
                    job.get('url', ''),
                    job.get('avatar_url_source', ''),
                    job.get('avatar_filename_for_web', ''),
                    job.get('full_description', ''),
                    job.get('requirements', ''),
                    job.get('attachments', ''),
                    job.get('extra_details', '{}'),
                    datetime.now().isoformat()
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Job already exists (due to UNIQUE constraint)
                return None
    
    def extract_job_id_from_url(self, url):
        """Extract job ID from URL"""
        if not url:
            return None
        
        # Usuń @ z początku URL, jeśli istnieje
        if url.startswith('@'):
            url = url[1:]
        
        import re
        # Dopasowanie do kilku możliwych formatów URL Useme
        # Format 1: /jobs/nazwa-projektu,123456/
        match1 = re.search(r'/jobs/[^,]+,(\d+)/', url)
        if match1:
            return match1.group(1)
            
        # Format 2: /jobs/123456/
        match2 = re.search(r'/jobs/(\d+)/', url)
        if match2:
            return match2.group(1)
            
        # Format 3: jobs/nazwa-projektu,123456 (bez slash na końcu)
        match3 = re.search(r'/jobs/[^,]+,(\d+)', url)
        if match3:
            return match3.group(1)
            
        # Format 4: po prostu liczba w URL
        match4 = re.search(r'(\d{5,6})', url)  # Szukamy 5-6 cyfrowego numeru
        if match4:
            return match4.group(1)
            
        return None
    
    def get_job_by_id(self, job_id):
        """Get a job by its ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_unprocessed_jobs(self, limit=10):
        """Get jobs that haven't been processed yet"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE processed = 0 ORDER BY created_at DESC LIMIT ?", 
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_job_as_processed(self, job_id):
        """Mark a job as processed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET processed = 1 WHERE job_id = ?", 
            (job_id,)
        )
        conn.commit()
    
    def update_job_proposal(
        self, 
        job_id, 
        proposal_text, 
        project_slug,
        relevance_score=None,
        employer_email=None,
        price=None,
        timeline_days=None,
        presentation_url=None,
        email_content=None,
        attachments=None
    ):
        """
        Aktualizuje ofertę pracy o wygenerowany tekst propozycji.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Przygotowanie atrybutów do aktualizacji
            update_attrs = {
                "proposal_text": proposal_text,
                "project_slug": project_slug,
                "proposal_generated": True
            }
            
            # Dodanie opcjonalnych atrybutów, jeśli są dostępne
            if relevance_score is not None:
                update_attrs["relevance_score"] = relevance_score
            
            if employer_email:
                update_attrs["employer_email"] = employer_email
            
            if price is not None:
                update_attrs["price"] = price
            
            if timeline_days is not None:
                update_attrs["timeline_days"] = timeline_days
            
            if presentation_url:
                update_attrs["presentation_url"] = presentation_url
            
            if email_content:
                update_attrs["email_content"] = email_content
            
            if attachments:
                import json
                if isinstance(attachments, list):
                    update_attrs["attachments"] = json.dumps(attachments)
                else:
                    update_attrs["attachments"] = attachments
            
            # Budowanie zapytania SQL
            set_clauses = [f"{key} = ?" for key in update_attrs.keys()]
            query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
            
            # Wykonanie zapytania
            params = list(update_attrs.values()) + [job_id]
            cursor.execute(query, params)
            conn.commit()
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji propozycji oferty {job_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_jobs_for_proposal_generation(self, min_relevance=5, limit=10):
        """Get jobs that haven't had proposals generated"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM jobs 
            WHERE proposal_generated = 0 
            ORDER BY created_at DESC 
            LIMIT ?
            """, 
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def schedule_scrape_task(self, scheduled_time, parameters=None):
        """Schedule a scrape task"""
        conn = self.get_connection()
        cursor = conn.cursor()
        params_json = json.dumps(parameters) if parameters else '{}'
        
        cursor.execute(
            """
            INSERT INTO scrape_queue (task_type, status, scheduled_time, parameters)
            VALUES (?, ?, ?, ?)
            """,
            ('scrape', 'pending', scheduled_time.isoformat(), params_json)
        )
        conn.commit()
    
    def get_pending_tasks(self, current_time):
        """Get pending tasks that should be executed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM scrape_queue 
            WHERE status = 'pending' AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            """,
            (current_time.isoformat(),)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_task_status(self, task_id, status, last_run):
        """Update task status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE scrape_queue 
            SET status = ?, last_run = ? 
            WHERE id = ?
            """,
            (status, last_run.isoformat(), task_id)
        )
        conn.commit()
    
    def store_submitted_proposal(self, job_id, proposal_text, status="submitted", response_message="", submission_time=None):
        """Store information about a submitted proposal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if submission_time is None:
            submission_time = datetime.now().isoformat()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO submitted_proposals 
            (job_id, proposal_text, status, response_message, submission_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, proposal_text, status, response_message, submission_time)
        )
        conn.commit()
    
    def check_proposal_submitted(self, job_id):
        """Check if a proposal has already been submitted for this job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM submitted_proposals WHERE job_id = ?", 
            (job_id,)
        )
        return cursor.fetchone() is not None
    
    def export_jobs_to_json(self, filename="useme_jobs.json"):
        """Export all jobs to JSON file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs")
        jobs = [dict(row) for row in cursor.fetchall()]
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
            
        return len(jobs)
    
    def track_presentation_view(self, presentation_slug, job_id=None, client_ip=None, user_agent=None, referrer=None):
        """Track a presentation view"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # First, if job_id is not provided but presentation_slug is available,
            # try to find the job_id from existing records
            if not job_id and presentation_slug:
                cursor.execute(
                    "SELECT job_id FROM jobs WHERE project_slug = ?", 
                    (presentation_slug,)
                )
                result = cursor.fetchone()
                if result:
                    job_id = result[0]
            
            # Insert the view record
            cursor.execute('''
            INSERT INTO presentation_views 
            (presentation_slug, job_id, client_ip, user_agent, referrer, viewed_at) 
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (
                presentation_slug,
                job_id,
                client_ip,
                user_agent,
                referrer
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error tracking presentation view: {str(e)}")
            return None
            
    def get_presentation_views(self, presentation_slug=None, job_id=None, limit=100):
        """Get presentation view statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM presentation_views"
        params = []
        conditions = []
        
        if presentation_slug:
            conditions.append("presentation_slug = ?")
            params.append(presentation_slug)
            
        if job_id:
            conditions.append("job_id = ?")
            params.append(job_id)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY viewed_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_message_sent(self, job_id):
        """Mark a job as having a message sent through Useme"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE jobs SET message_sent = 1 WHERE job_id = ?
        """, (job_id,))
        
        conn.commit() 