import time
import json
import logging
import threading
from datetime import datetime, timedelta
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QueueProcessor')

class QueueProcessor:
    def __init__(self, db_path="useme.db", sleep_interval=1):
        """
        Initialize the Queue Processor
        
        Args:
            db_path (str): Path to the SQLite database
            sleep_interval (int): Time in seconds to sleep between processing cycles
        """
        self.db = Database(db_path)
        self.sleep_interval = sleep_interval
        self.running = False
        self.thread = None
        self.task_handlers = {}
        
    def register_task_handler(self, task_type, handler_function):
        """
        Register a handler function for a specific task type
        
        Args:
            task_type (str): The type of task
            handler_function (callable): Function to call for this task type
        """
        self.task_handlers[task_type] = handler_function
        logger.info(f"Registered handler for task type: {task_type}")
        
    def process_task(self, task):
        """
        Process a single task from the queue
        
        Args:
            task (dict): Task data from the database
        
        Returns:
            bool: True if task was processed successfully, False otherwise
        """
        task_id = task['id']
        task_type = task['task_type']
        parameters = json.loads(task['parameters'] or '{}')
        
        logger.info(f"Processing task {task_id} of type {task_type}")
        
        # Update task status to 'processing'
        self.db.update_task_status(task_id, 'processing', datetime.now().isoformat())
        
        try:
            # Check if we have a handler for this task type
            if task_type in self.task_handlers:
                handler = self.task_handlers[task_type]
                result = handler(parameters)
                
                # Update task status to 'completed'
                self.db.update_task_status(task_id, 'completed', datetime.now().isoformat())
                logger.info(f"Task {task_id} completed successfully")
                return True
            else:
                logger.warning(f"No handler registered for task type: {task_type}")
                self.db.update_task_status(task_id, 'failed', datetime.now().isoformat())
                return False
                
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            self.db.update_task_status(task_id, 'failed', datetime.now().isoformat())
            return False
    
    def process_queue(self):
        """Process all pending tasks in the queue"""
        current_time = datetime.now().isoformat()
        pending_tasks = self.db.get_pending_tasks(current_time)
        
        if pending_tasks:
            logger.info(f"Found {len(pending_tasks)} pending tasks")
            for task in pending_tasks:
                self.process_task(task)
        else:
            logger.debug("No pending tasks found")
    
    def start(self):
        """Start the queue processor in a separate thread"""
        if self.running:
            logger.warning("Queue processor is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Queue processor started")
    
    def stop(self):
        """Stop the queue processor"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Queue processor stopped")
    
    def _run_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                self.process_queue()
            except Exception as e:
                logger.error(f"Error in queue processing loop: {str(e)}")
            
            # Sleep before the next cycle
            time.sleep(self.sleep_interval)
    
    def add_task(self, task_type, parameters=None, scheduled_time=None):
        """
        Add a new task to the queue
        
        Args:
            task_type (str): Type of task
            parameters (dict): Task parameters
            scheduled_time (datetime): When to execute the task
        
        Returns:
            int: Task ID
        """
        if scheduled_time is None:
            scheduled_time = datetime.now()
            
        parameters_json = json.dumps(parameters or {})
        return self.db.schedule_scrape_task(scheduled_time, parameters_json, task_type)

# Example of how to use the queue processor
if __name__ == "__main__":
    # Create a queue processor instance
    processor = QueueProcessor()
    
    # Define some example task handlers
    def scrape_jobs_handler(parameters):
        print(f"Scraping jobs with parameters: {parameters}")
        # Here you would implement the actual scraping logic
        return True
    
    def send_emails_handler(parameters):
        print(f"Sending emails with parameters: {parameters}")
        # Here you would implement the email sending logic
        return True
    
    def send_pdf_email_handler(parameters):
        """Handler for sending PDF attachments via email"""
        import os
        import logging
        
        logger = logging.getLogger('QueueProcessor')
        logger.info(f"Processing PDF email task with parameters: {parameters}")
        
        try:
            # Extract parameters
            email = parameters.get('email')
            subject = parameters.get('subject', 'Materiały z naszej prezentacji')
            message = parameters.get('message')
            pdf_path = parameters.get('pdf_path')
            presentation_slug = parameters.get('presentation_slug')
            
            
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
    
    # Register the task handlers
    processor.register_task_handler('scrape_jobs', scrape_jobs_handler)
    processor.register_task_handler('send_emails', send_emails_handler)
    processor.register_task_handler('send_pdf_email', send_pdf_email_handler)
    
    # Add tasks to the queue
    processor.add_task('scrape_jobs', {'category': 'programming'})
    processor.add_task('send_emails', {'template': 'follow_up'}, 
                      scheduled_time=datetime.now() + timedelta(minutes=5))
    
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