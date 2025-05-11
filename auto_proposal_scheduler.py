import time
import logging
import schedule
from datetime import datetime
from ai_proposal_generator import generate_proposals_from_database
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_proposal_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_proposal_generation():
    """Run the proposal generation process automatically."""
    try:
        logger.info(f"Starting scheduled proposal generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize database
        db = Database()
        
        # Generate proposals with these settings:
        # - minimum relevance score of 6
        # - limit to 5 proposals per run
        # - automatically save to database
        # - automatically post to Useme for relevant jobs
        result = generate_proposals_from_database(
            db=db,
            min_relevance=6,
            limit=5,
            auto_save=True,
            auto_post=True
        )
        
        # Log the results
        logger.info(f"Proposal generation completed: {result['message']}")
        logger.info(f"Generated {result['count']} proposals, posted {result['proposals_posted']} to Useme")
        
        return result
    except Exception as e:
        logger.error(f"Error during scheduled proposal generation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "count": 0,
            "proposals_posted": 0,
            "emails_sent": 0,
            "message": f"Error: {str(e)}"
        }

def main():
    """Main function to run the scheduler."""
    logger.info("Starting Auto Proposal Scheduler")
    
    # Schedule the job to run every 5 minutes
    schedule.every(5).minutes.do(run_proposal_generation)
    
    # Also run immediately when started
    logger.info("Running initial proposal generation...")
    run_proposal_generation()
    
    # Keep the script running and check for scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main() 