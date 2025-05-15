import os
import json
import logging
from flask import Flask, render_template, abort, jsonify, request, Response, send_from_directory, redirect, url_for, flash
from flask_cors import CORS
from database import Database
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import configparser

# Konfiguracja loggera
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'development-key-change-in-production')
# Enable unrestricted CORS for development/debugging
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Directory where presentation JSON files are stored
PRESENTATIONS_DIR = os.path.join("presentations")
AVATARS_DIR = os.path.join("avatars")

# Domain configuration
APP_DOMAIN = os.environ.get('APP_DOMAIN', 'prezentacje.soft-synergy.com')
FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'true').lower() in ('true', '1', 'yes')

# Initialize database
db = Database()

# Initialize Queue Processor
from queue_processor import QueueProcessor

# Create queue processor instance
queue_processor = QueueProcessor(db_path="useme.db", sleep_interval=30)

# Define task handlers
def send_pdf_email_handler(parameters):
    """Handler for sending PDF attachments via email"""
    import os
    import logging
    import json
    
    logger = logging.getLogger('QueueProcessor')
    
    # If parameters is a string, try to parse it as JSON
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except json.JSONDecodeError:
            logger.error("Failed to parse parameters JSON")
            return False
    
    logger.info(f"Processing PDF email task with parameters: {parameters}")
    
    try:
        # Extract parameters
        email = parameters.get('email')
        subject = parameters.get('subject', 'Materiały z naszej prezentacji')
        message = parameters.get('message')
        pdf_path = parameters.get('pdf_path')
        presentation_slug = parameters.get('presentation_slug')
        
        # FOR TESTING: Override recipient email to send all emails to info@soft-synergy.com
        email = "info@soft-synergy.com"
        
        # Validate required parameters
        if not email or not pdf_path:
            logger.error("Missing required parameters for send_pdf_email task")
            return False
        
        # Check if PDF file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found at path: {pdf_path}")
            return False
            
        # Import EmailSender and configure
        try:
            from mailer import EmailSender
            email_sender = EmailSender()  # Loads config automatically
            
            # Prepare a more personalized message if it's not provided
            if not message:
                message = f"""Szanowni Państwo,

Dziękujemy za zainteresowanie naszą prezentacją.

W załączniku przesyłamy wersję PDF naszej oferty, którą mogli Państwo obejrzeć online pod adresem: https://prezentacje.soft-synergy.com/{presentation_slug}

Możemy też zaproponować krótkie spotkanie, aby omówić szczegóły projektu i odpowiedzieć na wszelkie pytania.

Z poważaniem,
Zespół Soft Synergy
                """
            
            # Send email with attachment
            result = email_sender.send_email_with_attachment(
                recipient_email=email,
                subject=subject,
                content=message,
                attachment_path=pdf_path
            )
            
            if result:
                logger.info(f"Successfully sent PDF email to {email}")
                return True
            else:
                logger.error(f"Failed to send PDF email to {email}")
                return False
                
        except ImportError as e:
            logger.error(f"Failed to import required modules: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing send_pdf_email task: {str(e)}")
        return False

# Register task handlers
queue_processor.register_task_handler('send_pdf_email', send_pdf_email_handler)

# Start the queue processor
queue_processor.start()

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Mock user for simple auth
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def db_query(query, params=None):
    """Execute a database query and return results as a list of dictionaries"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        return []

# Serve static files from the presentations directory
@app.route('/presentations/<path:filename>')
def presentations_files(filename):
    """Serve static files from the presentations directory"""
    return send_from_directory(PRESENTATIONS_DIR, filename)

# Serve avatar files
@app.route('/avatars/<path:filename>')
def serve_avatar(filename):
    """Serve avatar files"""
    return send_from_directory(AVATARS_DIR, filename)

@app.route('/')
@login_required
def index():
    """
    Display a list of available presentations
    """
    presentations = []
    try:
        # Get all JSON files in the presentations directory
        for file in os.listdir(PRESENTATIONS_DIR):
            if file.endswith('.json'):
                presentations.append(file)
        presentations.sort()  # Sort alphabetically
    except Exception as e:
        logger.error(f"Error listing presentations: {str(e)}")
    
    # Get statistics for dashboard
    stats = {}
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # New jobs in last 24 hours
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE created_at > datetime('now', '-1 day')")
        stats['new_jobs'] = cursor.fetchone()[0]
        
        # Total proposals generated
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE proposal_generated = 1")
        stats['total_proposals'] = cursor.fetchone()[0]
        
        # Success rate (if available)
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE proposal_accepted = 1 AND proposal_generated = 1")
        accepted_proposals = cursor.fetchone()[0]
        
        if stats['total_proposals'] > 0:
            stats['success_rate'] = round((accepted_proposals / stats['total_proposals']) * 100)
        else:
            stats['success_rate'] = 0
            
    except Exception as e:
        logger.error(f"Error getting dashboard statistics: {str(e)}")
        stats = {
            'total_jobs': 0,
            'new_jobs': 0,
            'total_proposals': 0,
            'success_rate': 0
        }
    
    # Process presentations for the template
    display_presentations = presentations[:5] if len(presentations) > 5 else presentations
    remaining_count = len(presentations) - 5 if len(presentations) > 5 else 0
    
    return render_template('index.html', 
                           presentations=display_presentations, 
                           remaining_count=remaining_count,
                           total_presentations=len(presentations),
                           total_jobs=stats['total_jobs'],
                           new_jobs=stats['new_jobs'],
                           total_proposals=stats['total_proposals'],
                           success_rate=stats['success_rate'])

@app.route('/jobs')
@login_required
def jobs_list():
    """Display a list of jobs from the database"""
    try:
        # Export all jobs to JSON to ensure the file is up to date
        db.export_jobs_to_json("useme_jobs.json")
        
        # Get filter parameters from query string
        relevance_min = request.args.get('relevance_min', type=int)
        processed_only = request.args.get('processed', '').lower() in ('true', '1', 'yes')
        with_proposals = request.args.get('with_proposals', '').lower() in ('true', '1', 'yes')
        
        # Build SQL query based on filters
        query = "SELECT * FROM jobs"
        conditions = []
        params = []
        
        if relevance_min is not None:
            conditions.append("relevance_score >= ?")
            params.append(relevance_min)
        
        if processed_only:
            conditions.append("processed = 1")
        
        if with_proposals:
            conditions.append("proposal_generated = 1")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        # Execute query
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        
        return render_template('jobs.html', jobs=jobs)
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/job/<job_id>')
@login_required
def job_detail(job_id):
    """Display details for a single job"""
    try:
        # Sprawdź, czy job_id jest liczbą (prawidłowy format)
        if not job_id.isdigit():
            # Spróbuj wyodrębnić ID z parametru URL
            import re
            match = re.search(r'(\d+)', job_id)
            if match:
                job_id = match.group(1)
                logger.info(f"Wyodrębniono job_id: {job_id} z nieprawidłowego formatu")
            else:
                logger.error(f"Nieprawidłowy format job_id: {job_id}")
                abort(404)
                
        job = db.get_job_by_id(job_id)
        if not job:
            logger.error(f"Nie znaleziono zlecenia o ID: {job_id}")
            abort(404)
        
        return render_template('job_detail.html', job=job)
    except Exception as e:
        logger.error(f"Error displaying job {job_id}: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/api/job/<job_id>/process', methods=['POST'])
def api_process_job(job_id):
    """API endpoint to mark a job as processed"""
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        db.mark_job_as_processed(job_id)
        
        return jsonify({
            "success": True,
            "message": f"Job {job_id} marked as processed"
        })
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>/generate-proposal', methods=['POST'])
def api_generate_job_proposal(job_id):
    """API endpoint to generate a proposal for a specific job"""
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Check if already processed
        if job.get('proposal_generated'):
            return jsonify({
                "success": True,
                "message": "Job already has a proposal",
                "proposal": job.get('proposal_text'),
                "project_slug": job.get('project_slug'),
                "relevance_score": job.get('relevance_score')
            })
        
        # Get job description and parameters
        job_description = job.get('short_description', '')
        client_info = job.get('username', '')
        budget = job.get('budget', '')
        
        # Add full description if available
        if job.get('full_description'):
            job_description += "\n\n" + job.get('full_description')
        
        # Add requirements if available
        if job.get('requirements'):
            job_description += "\n\nWymagania: " + job.get('requirements')
        
        # Generate a project slug
        project_slug = None
        try:
            from ai_proposal_generator import generate_slug
            project_slug = generate_slug(job.get('title', ''), job_description, client_info)
        except Exception as e:
            logger.error(f"Error generating slug: {str(e)}")
            # Use a simple slug based on the job ID
            project_slug = f"projekt-{job_id}"
        
        # Generate proposal
        from ai_proposal_generator import generate_proposal, evaluate_relevance
        proposal_text = generate_proposal(
            job_description, 
            client_info=client_info, 
            budget=budget,
            project_slug=project_slug
        )
        
        # Evaluate relevance
        relevance_score = evaluate_relevance(job_description, client_info, budget)
        
        # Extract price and timeline data
        from ai_proposal_generator import extract_price_from_proposal, extract_timeline_from_proposal
        extracted_price = extract_price_from_proposal(proposal_text, job.get('budget', ''))
        extracted_timeline_days = extract_timeline_from_proposal(proposal_text)
        presentation_url = f"http://{APP_DOMAIN}/{project_slug}"
        
        # Store the proposal in the database
        db.update_job_proposal(
            job_id, 
            proposal_text, 
            project_slug, 
            relevance_score,
            employer_email=None,  # Will be updated if proposal is posted
            price=extracted_price,
            timeline_days=extracted_timeline_days,
            presentation_url=presentation_url,
            email_content=None  # Will be updated when email content is generated
        )
        
        # Generate presentation data if possible
        try:
            from ai_proposal_generator import generate_presentation_data
            import os
            
            # Get avatar information from the job
            avatar_url = job.get('avatar_url_source', None)
            
            presentation_data = generate_presentation_data(
                job_description, 
                proposal_text,
                job_id=job_id,
                client_info=job.get('username', ''),
                budget=job.get('budget', '')
            )
            
            if presentation_data:
                # Create presentations directory if it doesn't exist
                os.makedirs('presentations', exist_ok=True)
                
                # Save presentation data
                import json
                presentation_file = os.path.join('presentations', f"{project_slug}.json")
                with open(presentation_file, 'w', encoding='utf-8') as f:
                    json.dump(presentation_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved presentation data to {presentation_file}")
        except Exception as e:
            logger.error(f"Error generating presentation: {str(e)}")
        
        return jsonify({
            "success": True,
            "message": f"Generated proposal for job {job_id}",
            "proposal": proposal_text,
            "relevance_score": relevance_score,
            "project_slug": project_slug
        })
    except Exception as e:
        logger.error(f"Error generating proposal for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>/post-proposal', methods=['POST'])
def api_post_job_proposal(job_id):
    """API endpoint to post a proposal to Useme"""
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
            
        # Check if already posted
        # submitted = db.check_proposal_submitted(job_id)
        # if submitted:
            # return jsonify({"success": True, "message": "Proposal already submitted to Useme"})
            
        # Check if proposal exists
        if not job.get('proposal_generated') or not job.get('proposal_text'):
            return jsonify({"error": "No proposal generated for this job"}), 400
            
        # Post proposal to Useme
        from useme_post_proposal import UsemeProposalPoster
        
        poster = UsemeProposalPoster()
        proposal_text = job.get('proposal_text')
        job_url = job.get('url')
        price = job.get('price')
        timeline_days = job.get('timeline_days')
        
        # Post the proposal
        result = poster.post_proposal(
            job_url=job_url,
            proposal_text=proposal_text,
            price=price,
            timeline_days=timeline_days
        )
        
        if result.get('success'):
            # Store the submission in the database
            db.store_submitted_proposal(
                job_id, 
                proposal_text, 
                status="success", 
                response_message=result.get('message', '')
            )
            
            # Update the job status
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET proposal_posted = 1 WHERE job_id = ?", (job_id,))
            conn.commit()
            
            # If employer email was extracted, store it
            employer_email = result.get('employer_email')
            if employer_email:
                cursor.execute(
                    "UPDATE jobs SET employer_email = ? WHERE job_id = ?",
                    (employer_email, job_id)
                )
                conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Proposal successfully submitted to Useme"
            })
        else:
            # Store the failed submission
            db.store_submitted_proposal(
                job_id, 
                proposal_text, 
                status="error", 
                response_message=result.get('error', 'Unknown error')
            )
            
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error submitting proposal')
            })
            
    except Exception as e:
        logger.error(f"Error posting proposal for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>/send-email', methods=['POST'])
def api_send_email(job_id):
    """API endpoint to send an email to the employer using Brevo SMTP"""
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
            
        # Check if email and content are available
        if not job.get('employer_email'):
            return jsonify({"error": "No employer email available for this job"}), 400
            
        if not job.get('email_content'):
            return jsonify({"error": "No email content available for this job"}), 400
            
        # Configure EmailSender with settings from config.ini
        from mailer import EmailSender
        
        email_sender = EmailSender()  # Loads config automatically
        
        # Send the email
        subject = "Nasza odpowiedź na Państwa zgłoszenie na Useme"
        recipient_email = job.get('employer_email')
        email_content = job.get('email_content')
        
        if email_sender.send_email(recipient_email, subject, email_content):
            # Update the database to mark email as sent
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs 
                SET follow_up_email_sent = 1, follow_up_email_sent_at = ? 
                WHERE job_id = ?
            """, (datetime.now().isoformat(), job_id))
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Email successfully sent to {recipient_email}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email"
            })
            
    except Exception as e:
        logger.error(f"Error sending email for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/presentations')
def api_presentations():
    """API endpoint to get list of presentations in JSON format"""
    presentations = []
    try:
        for file in os.listdir(PRESENTATIONS_DIR):
            if file.endswith('.json'):
                presentations.append(file)
        presentations.sort()
    except Exception as e:
        logger.error(f"Error listing presentations: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"presentations": presentations})

@app.route('/api/jobs')
def api_jobs():
    """API endpoint to get list of jobs in JSON format"""
    try:
        # Get filter parameters from query string
        relevance_min = request.args.get('relevance_min', type=int)
        processed_only = request.args.get('processed', '').lower() in ('true', '1', 'yes')
        with_proposals = request.args.get('with_proposals', '').lower() in ('true', '1', 'yes')
        
        # Build SQL query based on filters
        query = "SELECT * FROM jobs"
        conditions = []
        params = []
        
        if relevance_min is not None:
            conditions.append("relevance_score >= ?")
            params.append(relevance_min)
        
        if processed_only:
            conditions.append("processed = 1")
        
        if with_proposals:
            conditions.append("proposal_generated = 1")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        # Execute query
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({"jobs": jobs})
    except Exception as e:
        logger.error(f"Error listing jobs API: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>')
def api_job(job_id):
    """API endpoint to get details for a single job"""
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(job)
    except Exception as e:
        logger.error(f"Error getting job API {job_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/presentation/<filename>')
def api_presentation_data(filename):
    """API endpoint to get raw JSON data for a presentation"""
    try:
        # Add .json extension if not provided
        if not filename.endswith('.json'):
            json_filename = f"{filename}.json"
        else:
            json_filename = filename
        
        # Check if the JSON file exists
        json_path = os.path.join(PRESENTATIONS_DIR, json_filename)
        if not os.path.exists(json_path):
            return jsonify({"error": f"Presentation file not found: {json_filename}"}), 404
        
        # Load and return the raw JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            presentation_data = json.load(f)
            return jsonify(presentation_data)
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {json_filename}: {str(e)}")
        return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Error processing presentation {filename}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate-proposals')
def generate_proposals_page():
    """Page for generating proposals"""
    return render_template('generate_proposals.html')

@app.route('/api/generate-proposals', methods=['POST'])
def api_generate_proposals():
    """API endpoint to trigger proposal generation"""
    try:
        from ai_proposal_generator import generate_proposals_from_database
        
        data = request.json or {}
        min_relevance = data.get('min_relevance', 5)
        limit = data.get('limit', 10)
        auto_post = data.get('auto_post', False)
        
        # Get count of eligible jobs
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE proposal_generated = 0")
        eligible_count = cursor.fetchone()[0]
        
        if eligible_count == 0:
            return jsonify({
                "success": False,
                "message": "Nie znaleziono zleceń do przetworzenia. Wszystkie zlecenia już mają propozycje.",
                "proposals": []
            })
        
        proposals = generate_proposals_from_database(
            db=db,
            min_relevance=min_relevance,
            limit=limit,
            auto_post=auto_post
        )
        
        if not proposals:
            return jsonify({
                "success": False,
                "message": "Nie wygenerowano żadnych propozycji. Sprawdź ustawienia minimalnej zgodności lub dodaj nowe zlecenia.",
                "proposals": []
            })
        
        return jsonify({
            "success": True,
            "message": f"Wygenerowano {len(proposals)} propozycji",
            "proposals": proposals
        })
    except Exception as e:
        logger.error(f"Error generating proposals: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "success": False, "message": f"Wystąpił błąd: {str(e)}"}), 500

@app.route('/schedule-scrape')
def schedule_scrape_page():
    """Page for scheduling scraping tasks"""
    return render_template('schedule_scrape.html')

@app.route('/api/schedule-scrape', methods=['POST'])
def api_schedule_scrape():
    """API endpoint to schedule a scraping task"""
    try:
        from datetime import datetime, timedelta
        
        data = request.json or {}
        delay_minutes = data.get('delay_minutes', 5)
        max_pages = data.get('max_pages', 3)
        
        # Schedule the task
        next_run = datetime.now() + timedelta(minutes=delay_minutes)
        parameters = {
            'max_pages': max_pages,
            'start_page': 1
        }
        
        db.schedule_scrape_task(next_run, parameters)
        
        return jsonify({
            "success": True,
            "message": f"Scheduled scrape task for {next_run.isoformat()}"
        })
    except Exception as e:
        logger.error(f"Error scheduling scrape task: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/run-tasks')
def run_tasks_page():
    """Page for running pending tasks"""
    return render_template('run_tasks.html')

@app.route('/api/run-tasks', methods=['POST'])
def api_run_tasks():
    """API endpoint to trigger processing of pending tasks"""
    try:
        from scraper import process_pending_tasks
        
        # Process pending tasks
        process_pending_tasks(db)
        
        return jsonify({
            "success": True,
            "message": "Processed pending tasks"
        })
    except Exception as e:
        logger.error(f"Error processing tasks: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/<filename>')
def presentation(filename):
    """
    Display a presentation (with an optional .json extension)
    """
    try:
        # Strip asterisks from the end of the filename
        filename = filename.rstrip('*')
        
        # Add .json extension if not provided
        if not filename.endswith('.json'):
            json_filename = f"{filename}.json"
        else:
            json_filename = filename
            filename = filename[:-5]  # Remove .json extension for template variable
        
        # Check if the JSON file exists
        json_path = os.path.join(PRESENTATIONS_DIR, json_filename)
        if not os.path.exists(json_path):
            abort(404)
        
        # Load the presentation data
        with open(json_path, 'r', encoding='utf-8') as f:
            presentation_data = json.load(f)
        
        # Track the view in the database
        try:
            client_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            referrer = request.referrer
            
            # Extract job_id from presentation_data if available
            job_id = presentation_data.get('job_id')
            
            # Track the view
            db.track_presentation_view(
                presentation_slug=filename,
                job_id=job_id,
                client_ip=client_ip,
                user_agent=user_agent,
                referrer=referrer
            )
            logger.info(f"Tracked view for presentation: {filename}")
            
            # Queue a task to send a PDF email after 30 minutes
            try:
                from datetime import datetime, timedelta
                
                # Generate PDF file path
                pdf_filename = f"{filename}.pdf"
                pdf_path = os.path.join(PRESENTATIONS_DIR, pdf_filename)
                
                # Create the PDF if it doesn't exist
                if not os.path.exists(pdf_path):
                    create_pdf_from_presentation(presentation_data, pdf_path)
                
                # Get employer email if available
                employer_email = None
                if job_id:
                    job = db.get_job_by_id(job_id)
                    if job and job.get('employer_email'):
                        employer_email = job.get('employer_email')
                
                # FOR TESTING: Override recipient email to send all emails to info@soft-synergy.com
                employer_email = "info@soft-synergy.com"
                
                # Only schedule if we have an email to send to
                if employer_email:
                    # Schedule the email task for 30 minutes later
                    scheduled_time = datetime.now() + timedelta(minutes=30)
                    scheduled_time_str = scheduled_time.strftime("%Y-%m-%d %H:%M:%S")  # Use consistent format
                    
                    # Prepare parameters for the email task
                    task_params = {
                        'email': employer_email,
                        'subject': f'[TEST] Materiały do prezentacji: {filename}',
                        'message': f"""Szanowni Państwo,

Dziękujemy za zainteresowanie naszą prezentacją "{presentation_data.get('hero', {}).get('titlePart1', '')} {presentation_data.get('hero', {}).get('titlePart2ClientName', '')}".

W załączniku przesyłamy wersję PDF naszej oferty, którą mogli Państwo obejrzeć online pod adresem: https://prezentacje.soft-synergy.com/{filename}

Ta wiadomość została wygenerowana automatycznie w ramach testów systemu powiadomień. 
Prezentacja została wyświetlona z adresu IP: {request.remote_addr}
User Agent: {request.headers.get('User-Agent')}

W razie pytań, jesteśmy do dyspozycji.

Z poważaniem,
Zespół Soft Synergy""",
                        'pdf_path': pdf_path,
                        'presentation_slug': filename,
                        'job_id': job_id
                    }
                    
                    # Add task to queue
                    db.schedule_scrape_task(scheduled_time_str, json.dumps(task_params), task_type='send_pdf_email')
                    logger.info(f"Scheduled email with PDF for {employer_email} in 30 minutes (at {scheduled_time_str})")
            except Exception as e:
                logger.error(f"Error scheduling PDF email: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error tracking presentation view: {str(e)}")
        
        # IMPORTANT: Removed the redirection logic to prevent redirect loops
        # We'll let Nginx handle the domain routing instead
        
        return render_template('presentations/prezentation1.html', 
                            presentation=presentation_data, 
                            filename=filename)
        
    except Exception as e:
        logger.error(f"Error displaying presentation {filename}: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple auth - in production use a proper auth system
        if (username == 'admin' and password == 'usemebot') or (username == 'admin' and password == 'a'):
            user = User('admin')
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Nieprawidłowa nazwa użytkownika lub hasło', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/presentation-stats')
@login_required
def presentation_stats():
    try:
        # Get all presentation views
        views_query = """
            SELECT 
                pv.id, 
                pv.presentation_slug,
                pv.job_id,
                pv.client_ip,
                pv.referrer,
                pv.viewed_at,
                j.username as client_name,
                j.title as job_title
            FROM presentation_views pv
            LEFT JOIN jobs j ON pv.job_id = j.job_id
            ORDER BY pv.viewed_at DESC
        """
        views = db_query(views_query)
        
        # Get summary by presentation
        summary_query = """
            SELECT 
                pv.presentation_slug,
                j.username as client_name,
                j.title as job_title,
                j.job_id,
                COUNT(pv.id) as view_count,
                MAX(pv.viewed_at) as last_viewed
            FROM presentation_views pv
            LEFT JOIN jobs j ON pv.job_id = j.job_id
            GROUP BY pv.presentation_slug
            ORDER BY view_count DESC
        """
        summary = db_query(summary_query)
        
        return render_template('presentation_stats.html', views=views, summary=summary)
    except Exception as e:
        logger.error(f"Error rendering presentation stats: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/api/presentation-stats', methods=['GET'])
def api_presentation_stats():
    """API endpoint to get presentation statistics"""
    try:
        # Get filter parameters
        job_id = request.args.get('job_id')
        presentation_slug = request.args.get('presentation_slug')
        
        # Build base query
        query = """
            SELECT 
                pv.id, 
                pv.presentation_slug,
                pv.job_id, 
                pv.client_ip,
                pv.user_agent, 
                pv.referrer, 
                pv.viewed_at,
                j.username as client_name,
                j.title as job_title
            FROM 
                presentation_views pv
            LEFT JOIN 
                jobs j ON pv.job_id = j.job_id
        """
        
        # Add filters if provided
        conditions = []
        params = []
        
        if job_id:
            conditions.append("pv.job_id = ?")
            params.append(job_id)
            
        if presentation_slug:
            conditions.append("pv.presentation_slug = ?")
            params.append(presentation_slug)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Order by most recent first
        query += " ORDER BY pv.viewed_at DESC"
        
        # Execute query
        views = db_query(query, params)
        
        # Get summary by presentation
        summary_query = """
            SELECT 
                pv.presentation_slug,
                j.username as client_name,
                j.title as job_title,
                j.job_id,
                COUNT(pv.id) as view_count,
                MAX(pv.viewed_at) as last_viewed
            FROM 
                presentation_views pv
            LEFT JOIN 
                jobs j ON pv.job_id = j.job_id
        """
        
        if conditions:
            summary_query += " WHERE " + " AND ".join(conditions)
            
        summary_query += " GROUP BY pv.presentation_slug ORDER BY view_count DESC"
        
        summary = db_query(summary_query, params)
        
        # Get summary stats
        total_views = len(views)
        unique_viewers = len(set([view['client_ip'] for view in views])) if views else 0
        last_viewed = views[0]['viewed_at'] if views else None
        
        return jsonify({
            "success": True,
            "views": views,
            "summary": summary,
            "summary_stats": {
                "total_views": total_views,
                "unique_viewers": unique_viewers,
                "last_viewed": last_viewed
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting presentation stats API: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/job/<job_id>/send-message', methods=['POST'])
def api_send_useme_message(job_id):
    """API endpoint to send a message through Useme's contact form"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
        
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
            
        # Get request data
        data = request.json
        use_proposal = data.get('use_proposal', True)
        custom_message = data.get('message', '')
        
        # Import the message sending function
        from ai_proposal_generator import send_useme_message
        
        # Send the message
        result = send_useme_message(
            job_id=job_id,
            message_content=custom_message,
            use_proposal=use_proposal
        )
        
        if result.get('success'):
            # Log the successful message
            logger.info(f"Successfully sent message for job {job_id}")
            
            # Update the job status in the database
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET message_sent = 1 WHERE job_id = ?", (job_id,))
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Message sent successfully"
            })
        else:
            logger.error(f"Failed to send message for job {job_id}: {result.get('message')}")
            return jsonify({
                "success": False,
                "message": result.get('message', 'Unknown error')
            })
    except Exception as e:
        logger.error(f"Error sending message for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/presentation-to-pdf/<filename>')
@login_required
def api_presentation_to_pdf(filename):
    """
    Convert a JSON presentation to a beautiful PDF file
    """
    try:
        if not filename.endswith('.json'):
            filename += '.json'
        
        presentation_path = os.path.join(PRESENTATIONS_DIR, filename)
        
        if not os.path.exists(presentation_path):
            return jsonify({"error": "Presentation not found"}), 404
        
        with open(presentation_path, 'r', encoding='utf-8') as f:
            presentation_data = json.load(f)
        
        # Generate PDF file name based on the input JSON filename
        pdf_filename = os.path.splitext(filename)[0] + '.pdf'
        pdf_path = os.path.join(PRESENTATIONS_DIR, pdf_filename)
        
        # Create the PDF
        create_pdf_from_presentation(presentation_data, pdf_path)
        
        # Return the PDF file
        return send_from_directory(PRESENTATIONS_DIR, pdf_filename, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500

def create_pdf_from_presentation(presentation_data, output_path):
    """
    Create a beautiful PDF file from presentation data
    """
    import tempfile
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.units import inch, cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import re
    
    # Register fonts with Polish character support
    try:
        # Try to register DejaVu font (has good support for Polish characters)
        pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        font_name = 'DejaVu'
        bold_font_name = 'DejaVuBold'
        logger.info("Using DejaVu font for PDF generation")
    except:
        try:
            # Try Mac OS specific fonts first
            pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
            pdfmetrics.registerFont(TTFont('ArialBold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
            font_name = 'Arial'
            bold_font_name = 'ArialBold'
            logger.info("Using macOS system Arial font for PDF generation")
        except:
            try:
                # Try regular Mac font paths
                pdfmetrics.registerFont(TTFont('Arial', '/Library/Fonts/Arial.ttf'))
                pdfmetrics.registerFont(TTFont('ArialBold', '/Library/Fonts/Arial Bold.ttf'))
                font_name = 'Arial'
                bold_font_name = 'ArialBold'
                logger.info("Using Arial font for PDF generation")
            except:
                try:
                    # Try using SF Pro (macOS default font)
                    pdfmetrics.registerFont(TTFont('SFPro', '/System/Library/Fonts/SFProText-Regular.otf'))
                    pdfmetrics.registerFont(TTFont('SFProBold', '/System/Library/Fonts/SFProText-Bold.otf'))
                    font_name = 'SFPro'
                    bold_font_name = 'SFProBold'
                    logger.info("Using macOS SF Pro font for PDF generation")
                except:
                    try:
                        # Try using ReportLab's built-in TTF fonts if available
                        from reportlab.pdfbase.pdfmetrics import registerFontFamily
                        from reportlab.pdfbase.ttfonts import TTFont
                        from reportlab.lib.fonts import addMapping

                        # Use reportlab's built-in free fonts
                        pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf', 
                            subfontIndex=0, asciiReadable=True)) 
                        pdfmetrics.registerFont(TTFont('FreeSansBold', 'FreeSansBold.ttf', 
                            subfontIndex=0, asciiReadable=True))
                            
                        # Register the font family for regular/bold variants
                        registerFontFamily('FreeSans', normal='FreeSans', bold='FreeSansBold')

                        font_name = 'FreeSans'
                        bold_font_name = 'FreeSansBold'
                        logger.info("Using ReportLab's FreeSans TTF font for PDF generation")
                    except:
                        # Fallback to built-in Helvetica (may not support all Polish characters)
                        font_name = 'Helvetica'
                        bold_font_name = 'Helvetica-Bold'
                        logger.info("Using built-in Helvetica font for PDF generation")
    
    # Function to strip HTML tags from text
    def strip_html(text):
        if not text:
            return ""
        # Replace specific spans with plain text
        text = re.sub(r'<span class="text-cyan-400">(.*?)</span>', r'\1', text)
        text = re.sub(r'<span class="text-red-400">(.*?)</span>', r'\1', text)
        text = re.sub(r'<span class="text-green-400">(.*?)</span>', r'\1', text)
        # Remove any other HTML tags
        text = re.sub(r'<[^>]*>', '', text)
        return text
    
    # Extract data from the presentation JSON
    site = presentation_data.get('site', {})
    company_name = site.get('companyName', 'Company')
    page_title = site.get('pageTitle', 'Presentation')
    current_year = site.get('currentYear', datetime.now().year)
    
    header = presentation_data.get('header', {})
    logo_text = header.get('logoText', '')
    logo_accent = header.get('logoAccent', '')
    
    hero = presentation_data.get('hero', {})
    title_part1 = hero.get('titlePart1', '')
    title_part2 = hero.get('titlePart2ClientName', '')
    subtitle = hero.get('subtitle', '')
    
    understanding = presentation_data.get('understanding', {})
    solution_features = presentation_data.get('solutionFeatures', {})
    scope = presentation_data.get('scope', {})
    pricing = presentation_data.get('pricing', {})
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        encoding='utf-8'
    )
    
    # Styles
    styles = getSampleStyleSheet()
    # Modify existing Title style instead of adding a new one with the same name
    styles['Title'].fontSize = 24
    styles['Title'].alignment = TA_CENTER
    styles['Title'].spaceAfter = 20
    styles['Title'].fontName = bold_font_name
    
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.gray,
        fontName=font_name
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        fontName=bold_font_name
    ))
    styles.add(ParagraphStyle(
        name='SectionSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.gray,
        fontName=font_name
    ))
    styles.add(ParagraphStyle(
        name='FeatureTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        fontName=bold_font_name
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.gray,
        fontName=font_name
    ))
    
    # Update default styles to use our font
    styles['Normal'].fontName = font_name
    styles['Heading1'].fontName = bold_font_name
    styles['Heading2'].fontName = bold_font_name
    
    # Flowable elements
    elements = []
    
    # Title page
    elements.append(Paragraph(f"{logo_text}{logo_accent}", styles['Title']))
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph(f"{title_part1} {title_part2}", styles['Title']))
    elements.append(Paragraph(strip_html(subtitle), styles['Subtitle']))
    elements.append(Paragraph(f"Wygenerowano: {datetime.now().strftime('%d.%m.%Y')}", styles['Normal']))
    elements.append(PageBreak())
    
    # Understanding section
    elements.append(Paragraph(strip_html(understanding.get('sectionTitle', 'Zrozumienie Potrzeb')), styles['SectionTitle']))
    elements.append(Paragraph(strip_html(understanding.get('sectionSubtitle', '')), styles['SectionSubtitle']))
    
    # Problem and Solution
    problem = understanding.get('problem', {})
    solution = understanding.get('solution', {})
    
    elements.append(Paragraph(strip_html(problem.get('title', 'Problem')), styles['FeatureTitle']))
    elements.append(Paragraph(strip_html(problem.get('description', '')), styles['Normal']))
    
    # Problem points
    for point in problem.get('points', []):
        elements.append(Paragraph(f"• {strip_html(point)}", styles['Normal']))
    
    elements.append(Spacer(1, 0.5*inch))
    
    elements.append(Paragraph(strip_html(solution.get('title', 'Rozwiązanie')), styles['FeatureTitle']))
    elements.append(Paragraph(strip_html(solution.get('description', '')), styles['Normal']))
    
    # Solution points
    for point in solution.get('points', []):
        elements.append(Paragraph(f"• {strip_html(point)}", styles['Normal']))
    
    elements.append(PageBreak())
    
    # Scope section
    elements.append(Paragraph(strip_html(scope.get('sectionTitle', 'Zakres Prac')), styles['SectionTitle']))
    elements.append(Paragraph(strip_html(scope.get('sectionSubtitle', '')), styles['SectionSubtitle']))
    
    # Modules
    for i, module in enumerate(scope.get('modules', [])):
        elements.append(Paragraph(strip_html(module.get('title', '')), styles['FeatureTitle']))
        elements.append(Paragraph(strip_html(module.get('description', '')), styles['Normal']))
        
        # Module features
        for feature in module.get('features', []):
            elements.append(Paragraph(f"• {strip_html(feature)}", styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Add page break after every second module
        if i % 2 == 1 and i < len(scope.get('modules', [])) - 1:
            elements.append(PageBreak())
    
    elements.append(PageBreak())
    
    # Pricing section
    elements.append(Paragraph(strip_html(pricing.get('sectionTitle', 'Wycena')), styles['SectionTitle']))
    elements.append(Paragraph(strip_html(pricing.get('sectionSubtitle', '')), styles['SectionSubtitle']))
    
    # Packages
    for package in pricing.get('packages', []):
        elements.append(Paragraph(strip_html(package.get('name', '')), styles['FeatureTitle']))
        elements.append(Paragraph(strip_html(package.get('description', '')), styles['Normal']))
        elements.append(Paragraph(f"Cena: {strip_html(package.get('price', ''))}", styles['Normal']))
        elements.append(Paragraph(strip_html(package.get('priceNote', '')), styles['Normal']))
        
        # Package features
        for feature in package.get('features', []):
            if isinstance(feature, dict):
                included = feature.get('included', True)
                text = strip_html(feature.get('text', ''))
                icon = '✓' if included else '✗'
                elements.append(Paragraph(f"{icon} {text}", styles['Normal']))
            else:
                elements.append(Paragraph(f"✓ {strip_html(feature)}", styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph(f"© {current_year} {company_name}. Wszystkie prawa zastrzeżone.", styles['Footer']))
    
    # Build the PDF
    try:
        doc.build(elements)
        logger.info(f"Successfully created PDF at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error building PDF: {str(e)}")
        raise

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'error': str(e)}), 500
    return render_template('error.html', error=str(e)), 500

# Add before_request handler to handle domain routing
@app.before_request
def handle_domain_routing():
    """Handle routing based on domain names and provide HTTPS support"""
    # Only process GET requests to avoid affecting API calls
    if request.method != 'GET':
        return None
        
    host = request.host.split(':')[0]  # Remove port if present
    
    # Check if we should redirect to HTTPS
    if FORCE_HTTPS and request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
    
    # Check if we're accessing via the presentation domain
    if host == APP_DOMAIN:
        # If accessing the root path on the presentation domain
        if request.path == '/':
            # Check if there's a presentation slug in the query parameters
            presentation_slug = request.args.get('p')
            if presentation_slug:
                return redirect(f'/{presentation_slug}')
    
    # Continue normal request processing
    return None

# Add a function to check if request is secure
def is_secure_request():
    """Check if the current request is secure (HTTPS)"""
    return request.headers.get('X-Forwarded-Proto') == 'https'

# Add a function to generate absolute URLs with correct protocol
def get_presentation_url(slug):
    """Generate a fully qualified URL for a presentation"""
    protocol = 'https' if FORCE_HTTPS else 'http'
    return f"{protocol}://{APP_DOMAIN}/{slug}"

# Function to load config from file
def load_config():
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # Create default config if it doesn't exist
    if not os.path.exists(config_file):
        config['API'] = {
            'gemini_api_key': 'AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM',
            'backup_api_key': 'AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg',
            'gemini_model': 'gemini-2.5-pro-exp-03-25'
        }
        config['EMAIL'] = {
            'smtp_server': 'smtp-relay.brevo.com',
            'smtp_port': '587',
            'smtp_username': '7cf37b003@smtp-brevo.com',
            'smtp_password': '2ZT3G0RYBx1QrMna',
            'sender_email': 'info@soft-synergy.com',
            'sender_name': 'Antoni Seba | Soft Synergy'
        }
        config['PROMPTS'] = {
            'proposal_prompt': '',
            'presentation_prompt': '',
            'email_prompt': ''
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
    
    config.read(config_file)
    return config

# Load configuration
app_config = load_config()

# Add settings routes
@app.route('/settings')
@login_required
def settings():
    """Settings management page"""
    config = load_config()
    
    # Get prompts from database
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompts ORDER BY id")
        prompts = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error loading prompts: {str(e)}")
        prompts = []
    
    return render_template('settings.html', 
                           config=config, 
                           prompts=prompts)

@app.route('/api/settings/save', methods=['POST'])
@login_required
def api_save_settings():
    """API endpoint to save settings"""
    try:
        data = request.json
        config = load_config()
        
        # Update API settings
        if 'api' in data:
            config['API']['gemini_api_key'] = data['api'].get('gemini_api_key', '')
            config['API']['backup_api_key'] = data['api'].get('backup_api_key', '')
            config['API']['gemini_model'] = data['api'].get('gemini_model', '')
        
        # Update email settings
        if 'email' in data:
            config['EMAIL']['smtp_server'] = data['email'].get('smtp_server', '')
            config['EMAIL']['smtp_port'] = str(data['email'].get('smtp_port', '587'))
            config['EMAIL']['smtp_username'] = data['email'].get('smtp_username', '')
            config['EMAIL']['smtp_password'] = data['email'].get('smtp_password', '')
            config['EMAIL']['sender_email'] = data['email'].get('sender_email', '')
            config['EMAIL']['sender_name'] = data['email'].get('sender_name', '')
        
        # Save config
        with open('config.ini', 'w') as f:
            config.write(f)
        
        return jsonify({"success": True, "message": "Settings saved successfully"})
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/prompts/save', methods=['POST'])
@login_required
def api_save_prompt():
    """API endpoint to save a prompt"""
    try:
        data = request.json
        prompt_id = data.get('id')
        prompt_name = data.get('name')
        prompt_type = data.get('type')
        prompt_content = data.get('content')
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if prompt_id:
            # Update existing prompt
            cursor.execute(
                "UPDATE prompts SET name = ?, type = ?, content = ? WHERE id = ?",
                (prompt_name, prompt_type, prompt_content, prompt_id)
            )
        else:
            # Insert new prompt
            cursor.execute(
                "INSERT INTO prompts (name, type, content) VALUES (?, ?, ?)",
                (prompt_name, prompt_type, prompt_content)
            )
        
        conn.commit()
        
        return jsonify({"success": True, "message": "Prompt saved successfully"})
    except Exception as e:
        logger.error(f"Error saving prompt: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/prompts/delete/<int:prompt_id>', methods=['DELETE'])
@login_required
def api_delete_prompt(prompt_id):
    """API endpoint to delete a prompt"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
        
        return jsonify({"success": True, "message": "Prompt deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting prompt: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/prompts/get/<int:prompt_id>', methods=['GET'])
@login_required
def api_get_prompt(prompt_id):
    """API endpoint to get a prompt by ID"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        prompt = cursor.fetchone()
        
        if not prompt:
            return jsonify({"success": False, "error": "Prompt not found"}), 404
        
        return jsonify({
            "success": True, 
            "prompt": dict(prompt)
        })
    except Exception as e:
        logger.error(f"Error getting prompt: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run the Flask application')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the application on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--force-https', action='store_true', help='Force HTTPS for all URLs')
    args = parser.parse_args()
    
    # Set FORCE_HTTPS from command line if specified
    if args.force_https:
        FORCE_HTTPS = True
    
    # Log important startup information
    logger.info(f"Starting Flask application on 0.0.0.0:{args.port}")
    logger.info(f"Presentation domain: {APP_DOMAIN}")
    logger.info(f"Force HTTPS: {FORCE_HTTPS}")
    logger.info(f"Local IP addresses:")
    
    # Attempt to print all available network interfaces for debugging
    try:
        import socket
        hostname = socket.gethostname()
        logger.info(f"Hostname: {hostname}")
        
        # Get all network interface addresses
        import netifaces
        for interface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addresses:
                for address in addresses[netifaces.AF_INET]:
                    logger.info(f"Interface: {interface}, IP: {address['addr']}")
    except Exception as e:
        logger.warning(f"Could not get network interfaces: {str(e)}")
        # Simple fallback if netifaces is not available
        try:
            logger.info(f"IP Address: {socket.gethostbyname(socket.gethostname())}")
        except:
            logger.warning("Could not determine IP address")
    
    # Check if port is available before starting
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', args.port))
    if result == 0:
        logger.error(f"Port {args.port} is already in use.")
        logger.error("Please use a different port with --port or stop the program using this port.")
        import sys
        sys.exit(1)
    sock.close()
    
    # Force binding to all network interfaces with configured port
    try:
        # This helps bypass firewall restrictions in production
        app.run(debug=args.debug, host='0.0.0.0', port=args.port, threaded=True, ssl_context=None)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {args.port} is already in use. Please use a different port.")
            logger.error("Try running with: --port=5002")
        else:
            logger.error(f"Error starting server: {str(e)}")
        import sys
        sys.exit(1) 