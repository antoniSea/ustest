#!/usr/bin/env python3
"""
Simple test for proxy implementation with Gemini API
"""

import google.generativeai as genai
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_KEY = "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM"
MODEL = "gemini-1.5-pro"
PROXY = "http://43.167.167.192:13001"

def test_with_proxy():
    """Test with a known working proxy."""
    try:
        # Setup proxy session
        session = requests.Session()
        session.proxies = {
            'http': PROXY,
            'https': PROXY
        }
        
        # Test IP address first
        logger.info(f"Testing connection through proxy {PROXY}...")
        try:
            response = session.get('https://api.ipify.org?format=json', timeout=10)
            ip_info = response.json()
            logger.info(f"Connected through IP: {ip_info.get('ip')}")
        except Exception as e:
            logger.error(f"IP check failed: {str(e)}")
            return
        
        # Configure Gemini with the proxy
        genai.configure(api_key=API_KEY, transport=session)
        
        # Create model
        logger.info("Creating Gemini model...")
        model = genai.GenerativeModel(MODEL)
        
        # Make a simple request
        logger.info("Generating content...")
        response = model.generate_content("Hello, say something in Polish")
        
        # Check response
        if response and hasattr(response, 'text'):
            logger.info(f"Response from API: {response.text}")
            return True
        else:
            logger.error("Empty or invalid response")
            return False
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Running simple proxy test...")
    result = test_with_proxy()
    
    if result:
        logger.info("TEST PASSED! Proxy is working correctly with Gemini API")
    else:
        logger.error("TEST FAILED! Proxy is not working with Gemini API") 