import google.generativeai as genai
import configparser
import os
import logging
import time
import random
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.ini file"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # Create default config if it doesn't exist
    if not os.path.exists(config_file):
        config['API'] = {
            'gemini_api_key': 'AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM',
            'backup_api_key': 'AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg',
            'gemini_model': 'gemini-2.5-pro-exp-03-25'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
    
    config.read(config_file)
    return config

def get_gemini_response(prompt, max_retries=3, retry_delay=2, use_backup=False):
    """
    Get a response from the Gemini API, with retry logic
    
    Args:
        prompt: The prompt to send to the API
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        use_backup: Whether to use the backup API key
        
    Returns:
        String response from the API
    """
    # Load API configuration
    config = load_config()
    
    # Use backup key if specified or primary key if not
    if use_backup:
        api_key = config['API'].get('backup_api_key', 'AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg')
        logger.info("Using backup API key")
    else:
        api_key = config['API'].get('gemini_api_key', 'AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM')
    
    model_name = config['API'].get('gemini_model', 'gemini-2.5-pro-exp-03-25')
    
    # Configure the API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            # Call the API
            response = model.generate_content(prompt)
            
            # Check if response exists and has text
            if response and hasattr(response, 'text'):
                return response.text
            else:
                logger.warning(f"Empty response from Gemini API on attempt {attempt+1}")
                
        except Exception as e:
            # Log the error
            error_str = str(e)
            logger.error(f"Error calling Gemini API on attempt {attempt+1}: {error_str}")
            
            # Check if this is a quota exceeded error (429)
            if "429" in error_str and not use_backup:
                logger.info("Quota exceeded. Trying with backup API key...")
                return get_gemini_response(prompt, max_retries, retry_delay, use_backup=True)
            
            # If this was the last attempt, re-raise the exception
            if attempt == max_retries - 1:
                raise
            
            # Calculate delay with exponential backoff and jitter
            jitter = random.uniform(0, 1)
            delay = (retry_delay * (2 ** attempt)) + jitter
            logger.info(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    # This should not be reached due to the raise in the exception handler
    return "Error: Failed to get response after maximum retries"
