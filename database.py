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
        
        # Create a table for storing prompts
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            content TEXT,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
        # Add column for tracking proposal submission timestamp
        if 'proposal_submitted_at' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN proposal_submitted_at TIMESTAMP')
            
        # Add column for tracking sent messages
        if 'message_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN message_sent BOOLEAN DEFAULT FALSE')
            
        # Add columns for tracking presentation follow-up emails
        if 'presentation_follow_up_sent' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent BOOLEAN DEFAULT FALSE')
            
        if 'presentation_follow_up_sent_at' not in column_names:
            cursor.execute('ALTER TABLE jobs ADD COLUMN presentation_follow_up_sent_at TIMESTAMP')
            
        conn.commit()
        
        # Initialize default prompts if needed
        self.initialize_default_prompts()
    
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
    
    def mark_proposal_submitted(self, job_id):
        """Mark a job as having had its proposal submitted to Useme"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update the job record to mark it as posted
            cursor.execute("""
                UPDATE jobs 
                SET proposal_posted = 1, 
                    proposal_submitted_at = ?
                WHERE job_id = ?
            """, (datetime.now().isoformat(), job_id))
            
            # Also store in the submitted_proposals table if it's not already there
            if not self.check_proposal_submitted(job_id):
                # Get the proposal text from the job record
                cursor.execute("SELECT proposal_text FROM jobs WHERE job_id = ?", (job_id,))
                job = cursor.fetchone()
                if job and job['proposal_text']:
                    self.store_submitted_proposal(
                        job_id, 
                        job['proposal_text'], 
                        status="success", 
                        submission_time=datetime.now().isoformat()
                    )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error marking proposal submitted: {str(e)}")
            return False
    
    def mark_message_sent(self, job_id):
        """Mark a job as having had a message sent through Useme"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE jobs 
                SET message_sent = 1
                WHERE job_id = ?
            ''', (job_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error marking message sent: {str(e)}")
            return False
            
    def get_prompts(self, prompt_type=None):
        """Get all prompts or prompts of a specific type"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if prompt_type:
                cursor.execute('''
                    SELECT * FROM prompts WHERE type = ? ORDER BY name
                ''', (prompt_type,))
            else:
                cursor.execute('SELECT * FROM prompts ORDER BY type, name')
                
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting prompts: {str(e)}")
            return []
            
    def get_prompt_by_id(self, prompt_id):
        """Get a prompt by its ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM prompts WHERE id = ?', (prompt_id,))
            prompt = cursor.fetchone()
            return dict(prompt) if prompt else None
        except Exception as e:
            print(f"Error getting prompt by ID: {str(e)}")
            return None
            
    def get_default_prompt(self, prompt_type):
        """Get the default prompt for a specific type"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM prompts 
                WHERE type = ? AND is_default = 1
                LIMIT 1
            ''', (prompt_type,))
            prompt = cursor.fetchone()
            return dict(prompt) if prompt else None
        except Exception as e:
            print(f"Error getting default prompt: {str(e)}")
            return None
            
    def save_prompt(self, name, prompt_type, content, prompt_id=None, is_default=False):
        """Save a new prompt or update an existing one"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # If this is set as default, unset any other defaults for this type
            if is_default:
                cursor.execute('''
                    UPDATE prompts SET is_default = 0 
                    WHERE type = ? AND id != ?
                ''', (prompt_type, prompt_id or -1))
            
            if prompt_id:
                # Update existing prompt
                cursor.execute('''
                    UPDATE prompts 
                    SET name = ?, type = ?, content = ?, is_default = ?, 
                        updated_at = ?
                    WHERE id = ?
                ''', (name, prompt_type, content, is_default, 
                      datetime.now().isoformat(), prompt_id))
            else:
                # Insert new prompt
                cursor.execute('''
                    INSERT INTO prompts 
                    (name, type, content, is_default, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, prompt_type, content, is_default, 
                      datetime.now().isoformat(), datetime.now().isoformat()))
                prompt_id = cursor.lastrowid
                
            conn.commit()
            return prompt_id
        except Exception as e:
            print(f"Error saving prompt: {str(e)}")
            return None
            
    def delete_prompt(self, prompt_id):
        """Delete a prompt by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if it's a default prompt
            cursor.execute('SELECT is_default, type FROM prompts WHERE id = ?', (prompt_id,))
            prompt = cursor.fetchone()
            
            if prompt:
                cursor.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
                conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error deleting prompt: {str(e)}")
            return False

    def initialize_default_prompts(self):
        """Initialize default prompts if they don't exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if we have any prompts
            cursor.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Add default proposal prompt
                proposal_prompt = """
                Nazywasz się Antoni Seba, jesteś menagerem projektów w Soft Synergy.

                Wygeneruj krótką, profesjonalną propozycję dla zlecenia o następujących parametrach:
                
                Opis zlecenia: {job_description}
                
                {client_info}
                {budget}
                {timeline}
                {additional_requirements}
                
                {research_info}
                
                Propozycja MUSI zawierać:
                1. Zwięzłe powitanie
                2. Krótkie podsumowanie zlecenia (max 2 zdania)
                3. Konkretną wycenę i termin realizacji (bazuj na wynikach researchu, jeśli są dostępne)
                4. Bardzo zwięzły opis metodologii (max 2 zdania)
                5. Krótkie uzasadnienie moich kompetencji (max 2 zdania)
                6. Informację, że przygotowaliśmy wizualną prezentację oferty dostępną pod linkiem: prezentacje.soft-synergy.com/{project_slug}
                7. Krótkie zakończenie z CTA
                
                ZASADY:
                - Pisz w języku polskim, profesjonalnie i przekonująco
                - Maksymalnie 200 słów
                - Wycena powinna być oparta na researchu rynkowym, jeśli jest dostępny, lub wynosić około 60% standardowej stawki rynkowej
                - Wycena musi być wyraźnie wyodrębniona w tekście (użyj **pogrubienia**)
                - Używaj formatowania tekstu: **pogrubienia**, *kursywy*, podkreślenia, listy, nowe linie
                - Dodaj przynajmniej 2-3 puste linie między sekcjami dla lepszej czytelności
                - Pamiętaj, że składasz propozycję na giełdzie zleceń, a nie odpowiadasz na bezpośrednie zapytanie
                - Zwracaj TYLKO treść propozycji bez żadnych dodatkowych komentarzy czy objaśnień
                - Nie używaj zwrotów sugerujących, że jesteś AI
                - KONIECZNIE umieść informację o przygotowanej prezentacji wizualnej z linkiem: prezentacje.soft-synergy.com/{project_slug}

                Dane kontaktowe (umieść je na końcu w osobnych liniach):
                Email: info@soft-synergy.com 
                Strona: https://soft-synergy.com
                Osoba kontaktowa: Antoni Seba
                Telefon: 576 205 389
                """
                
                # Add default email prompt
                email_prompt = """
                Wygeneruj krótki, profesjonalny email w języku polskim, który zostałby wysłany do klienta po złożeniu propozycji na giełdzie zleceń Useme.
                
                Opis zlecenia: {job_description}
                {client_info}
                
                Email powinien zawierać:
                1. Przywitanie + odniesienie się do ogłoszenia na Useme
                2. Propozycja rozwiązania – jak podejdziemy do projektu
                3. Social proof – link do portfolio (https://soft-synergy.com) + krótko o doświadczeniu
                4. Call to action – zaproszenie do kontaktu i link do przygotowanej prezentacji: prezentacje.soft-synergy.com/{project_slug}
                
                ZASADY:
                - Maksymalnie 150 słów
                - Email musi być w języku polskim
                - Używaj profesjonalnego, ale przyjaznego tonu
                - Podkreśl, że widział ogłoszenie na Useme
                - Podkreśl link do prezentacji: prezentacje.soft-synergy.com/{project_slug}
                - Nie używaj zwrotów sugerujących, że jesteś AI
                - Nie musisz dołączać nagłówka "Temat:" w treści maila
                - Pisz jako Antoni Seba, przedstawiciel firmy Soft Synergy
                
                Dane kontaktowe (umieść je na końcu w osobnych liniach):
                Z poważaniem,
                Antoni Seba
                Soft Synergy
                Tel: 576 205 389
                Email: info@soft-synergy.com
                """
                
                # Add default relevance prompt
                relevance_prompt = """
                Oceń na skali od 1 do 10, jak bardzo poniższe zlecenie jest odpowiednie dla software house'u specjalizującego się w tworzeniu stron internetowych, aplikacji webowych i mobilnych oraz systemów e-commerce.
                
                Opis zlecenia: {job_description}
                
                {client_info}
                {budget}
                {timeline}
                {additional_requirements}
                
                Gdzie:
                1 = Zupełnie nieodpowiednie dla software house'u (np. usługi fizyczne, niezwiązane z IT)
                5 = Częściowo odpowiednie (np. wymaga pewnych umiejętności IT, ale nie jest to główna specjalizacja software house'u)
                10 = Idealnie dopasowane do kompetencji software house'u (np. tworzenie zaawansowanych aplikacji webowych)
                
                Zwróć tylko liczbę od 1 do 10 bez żadnych dodatkowych komentarzy.
                """
                
                # Insert the default prompts
                cursor.execute(
                    "INSERT INTO prompts (name, type, content, is_default) VALUES (?, ?, ?, ?)",
                    ("Domyślny prompt propozycji", "proposal", proposal_prompt, True)
                )
                
                cursor.execute(
                    "INSERT INTO prompts (name, type, content, is_default) VALUES (?, ?, ?, ?)",
                    ("Domyślny prompt email", "email", email_prompt, True)
                )
                
                cursor.execute(
                    "INSERT INTO prompts (name, type, content, is_default) VALUES (?, ?, ?, ?)",
                    ("Domyślny prompt oceny", "relevance", relevance_prompt, True)
                )
                
                conn.commit()
                return True
            
            return False
        except Exception as e:
            print(f"Error initializing default prompts: {str(e)}")
            return False

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