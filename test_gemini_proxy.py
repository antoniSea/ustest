#!/usr/bin/env python3
"""
Test if proxy is being used with Gemini API
"""

import google.generativeai as genai
import requests
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_with_proxy():
    """Test Gemini API using our proxy setup."""
    logger.info("Testing Gemini API with proxy...")
    
    # Gemini API configuration
    API_KEY = "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM"
    
    # Known working proxy
    PROXY_URL = "http://43.167.167.192:13001"
    
    # Configure proxy session
    custom_session = requests.Session()
    custom_session.proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL
    }
    
    # Test the proxy by checking IP
    try:
        logger.info("Checking proxy IP...")
        response = custom_session.get('https://ipinfo.io/json', timeout=5)
        ip_info = response.json()
        logger.info(f"Proxy IP: {ip_info.get('ip')}")
        logger.info(f"Location: {ip_info.get('city')}, {ip_info.get('region')}, {ip_info.get('country')}")
    except Exception as e:
        logger.error(f"Proxy IP check failed: {str(e)}")
        logger.info("Trying with a different proxy service...")
        try:
            response = custom_session.get('https://api.ipify.org?format=json', timeout=5)
            ip_info = response.json()
            logger.info(f"Proxy IP: {ip_info.get('ip')}")
        except Exception as e:
            logger.error(f"Alternate proxy check failed: {str(e)}")
            return False
    
    # Configure Gemini with the proxy session
    logger.info("Configuring Gemini API with proxy session...")
    genai.configure(api_key=API_KEY)
    
    # Create a simple model with the transport option
    model = genai.GenerativeModel(
        "gemini-pro",
        transport=custom_session
    )
    
    # Try a simple API call
    try:
        logger.info("Attempting API call with proxy...")
        start_time = time.time()
        response = model.generate_content("Say hello in Polish")
        end_time = time.time()
        
        # Log success and response
        logger.info(f"API call successful (took {end_time - start_time:.2f}s)")
        logger.info(f"Response: {response.text}")
        return True
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return False

def test_without_proxy():
    """Test Gemini API without proxy for comparison."""
    logger.info("Testing Gemini API without proxy...")
    
    # Gemini API configuration
    API_KEY = "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM"
    
    # Configure direct connection session
    direct_session = requests.Session()
    
    # Test direct connection by checking IP
    try:
        logger.info("Checking direct IP...")
        response = direct_session.get('https://ipinfo.io/json', timeout=5)
        ip_info = response.json()
        logger.info(f"Direct IP: {ip_info.get('ip')}")
        logger.info(f"Location: {ip_info.get('city')}, {ip_info.get('region')}, {ip_info.get('country')}")
    except Exception as e:
        logger.error(f"Direct IP check failed: {str(e)}")
        return False
    
    # Configure Gemini with direct connection
    logger.info("Configuring Gemini API with direct connection...")
    genai.configure(api_key=API_KEY)
    
    # Create a simple model (not passing transport here for direct connection)
    model = genai.GenerativeModel("gemini-pro")
    
    # Try a simple API call
    try:
        logger.info("Attempting API call without proxy...")
        start_time = time.time()
        response = model.generate_content("Say hello in Polish")
        end_time = time.time()
        
        # Log success and response
        logger.info(f"API call successful (took {end_time - start_time:.2f}s)")
        logger.info(f"Response: {response.text}")
        return True
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Running proxy tests for Gemini API...")
    
    # Test with proxy
    proxy_success = test_with_proxy()
    
    # Add a separator
    logger.info("\n" + "-" * 50 + "\n")
    
    # Test without proxy
    direct_success = test_without_proxy()
    
    # Summary
    logger.info("\n--- Test Results ---")
    logger.info(f"Proxy connection test: {'SUCCESS' if proxy_success else 'FAILED'}")
    logger.info(f"Direct connection test: {'SUCCESS' if direct_success else 'FAILED'}")
    
    # Recommendation
    if proxy_success:
        logger.info("\nRecommendation: Use the proxy configuration for Gemini API requests")
    elif direct_success:
        logger.info("\nRecommendation: Use direct connection as proxy failed but direct connection works")
    else:
        logger.info("\nRecommendation: Check your API key and internet connection as both methods failed") 