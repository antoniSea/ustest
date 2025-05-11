from fp.fp import FreeProxy
import requests
import os
import certifi
import time
import logging
import json

# Set SSL certificate path
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Max number of retries and timeout settings
MAX_RETRIES = 5  # Increased retries to find working proxy
TIMEOUT = 60
BACKOFF_FACTOR = 1.5

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_proxy():
    """Get a free proxy from the FreeProxy service."""
    for _ in range(3):  # Try up to 3 times to get a proxy
        try:
            proxy = FreeProxy(rand=True).get()
            logger.info(f"Found proxy: {proxy}")
            return proxy
        except Exception as e:
            logger.error(f"Failed to get proxy: {e}")
            time.sleep(1)
    return None

def save_working_proxy(proxy):
    """Save working proxy to a file."""
    try:
        with open('working_proxy.json', 'w') as f:
            json.dump({'proxy': proxy, 'timestamp': time.time()}, f)
        logger.info(f"Saved working proxy to working_proxy.json: {proxy}")
    except Exception as e:
        logger.error(f"Failed to save working proxy: {e}")

def load_working_proxy():
    """Load a previously saved working proxy if it exists and is recent."""
    try:
        if os.path.exists('working_proxy.json'):
            with open('working_proxy.json', 'r') as f:
                data = json.load(f)
                proxy = data.get('proxy')
                timestamp = data.get('timestamp', 0)
                
                # Check if proxy is not too old (less than 1 hour old)
                if proxy and time.time() - timestamp < 3600:
                    logger.info(f"Loaded previously working proxy: {proxy}")
                    return proxy
                else:
                    logger.info("Saved proxy is too old or invalid, getting a new one")
    except Exception as e:
        logger.error(f"Error loading working proxy: {e}")
    
    return None

# Try to load a previously working proxy first
proxy = load_working_proxy()

# If no working proxy found, get a new one
if not proxy:
    logger.info("No recent working proxy found, getting a new one")
    proxy = get_proxy()

# Ensure we have a proxy before proceeding
if not proxy:
    logger.error("No proxy available. Exiting.")
    exit(1)

logger.info(f"Using proxy: {proxy}")
working_proxy_found = False

for attempt in range(MAX_RETRIES):
    try:
        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25:generateContent?key=AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM',
            headers={'Content-Type': 'application/json'},
            json={
                "contents": [{
                    "parts": [{"text": "Explain how AI works"}]
                }]
            },
            proxies={'http': proxy, 'https': proxy},
            timeout=TIMEOUT,
            verify=True
        )
        
        # Check if response is successful
        if response.status_code == 200:
            logger.info("Request successful")
            print(response.text)
            working_proxy_found = True
            save_working_proxy(proxy)
            break  # Success, exit the retry loop
        else:
            logger.warning(f"Request failed with status code: {response.status_code}")
            raise Exception(f"Request failed with status code: {response.status_code}")
            
    except (requests.exceptions.ProxyError, 
            requests.exceptions.ReadTimeout, 
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError) as e:
        logger.error(f"Proxy error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        if attempt < MAX_RETRIES - 1:
            # Get a new proxy for the next attempt
            logger.info("Getting new proxy...")
            proxy = get_proxy()
            if not proxy:
                logger.error("Failed to get a new proxy. Exiting.")
                exit(1)
            logger.info(f"Switching to new proxy: {proxy}")
            
            # Calculate backoff time
            backoff_time = BACKOFF_FACTOR ** attempt
            logger.info(f"Retrying in {backoff_time:.1f} seconds...")
            time.sleep(backoff_time)
    except Exception as e:
        logger.error(f"Error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        if attempt < MAX_RETRIES - 1:
            # Get a new proxy for the next attempt
            logger.info("Getting new proxy...")
            proxy = get_proxy()
            if not proxy:
                logger.error("Failed to get a new proxy. Exiting.")
                exit(1)
            logger.info(f"Switching to new proxy: {proxy}")
            
            backoff_time = BACKOFF_FACTOR ** attempt
            logger.info(f"Retrying in {backoff_time:.1f} seconds...")
            time.sleep(backoff_time)

if working_proxy_found:
    logger.info(f"Successfully found working proxy: {proxy}")
else:
    logger.error("Failed to find a working proxy after all attempts")

logger.info(f"Used proxy: {proxy}")