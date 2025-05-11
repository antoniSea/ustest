#!/usr/bin/env python3
"""
Test script for proxy functionality
"""

import requests
from fp.fp import FreeProxy
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_polish_proxy():
    """Get a free proxy from Poland."""
    try:
        # Try to get a Polish proxy
        proxy = FreeProxy(country_id=['PL'], rand=True).get()
        if proxy:
            logger.info(f"Found Polish proxy: {proxy}")
            return proxy
        
        # Fallback to European proxies if no Polish proxies available
        proxy = FreeProxy(country_id=['PL', 'DE', 'CZ', 'SK'], rand=True).get()
        if proxy:
            logger.info(f"Found European proxy: {proxy}")
            return proxy
            
        # Fallback to any proxy if no European proxies available
        proxy = FreeProxy(rand=True).get()
        logger.info(f"Fallback to random proxy: {proxy}")
        return proxy
    except Exception as e:
        logger.warning(f"Error getting proxy: {str(e)}. Using direct connection.")
        return None

def test_proxy(proxy_url=None):
    """Test if proxy is working by checking IP information."""
    try:
        session = requests.Session()
        if proxy_url:
            session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            logger.info(f"Testing proxy: {proxy_url}")
        else:
            logger.info("Testing direct connection (no proxy)")
            
        # Check IP info to verify proxy is working
        response = session.get('https://ipinfo.io/json', timeout=10)
        ip_info = response.json()
        
        logger.info(f"Connection successful via {'proxy' if proxy_url else 'direct connection'}")
        logger.info(f"IP: {ip_info.get('ip')}")
        logger.info(f"Location: {ip_info.get('city')}, {ip_info.get('region')}, {ip_info.get('country')}")
        
        return ip_info
    except Exception as e:
        logger.error(f"Proxy test failed: {str(e)}")
        return None

def get_multiple_proxies(count=5):
    """Get multiple proxies and test them."""
    working_proxies = []
    
    logger.info(f"Attempting to find {count} working proxies...")
    
    # Try to find specified number of working proxies
    for i in range(count * 2):  # Try twice as many to account for failures
        if len(working_proxies) >= count:
            break
            
        proxy = get_polish_proxy()
        if not proxy:
            logger.warning("Couldn't get a proxy, continuing...")
            continue
            
        # Test the proxy
        ip_info = test_proxy(proxy)
        if ip_info:
            country = ip_info.get('country', '')
            proxy_info = {
                'url': proxy,
                'ip': ip_info.get('ip'),
                'country': country,
                'location': f"{ip_info.get('city', '')}, {ip_info.get('region', '')}"
            }
            working_proxies.append(proxy_info)
            logger.info(f"Found working proxy #{len(working_proxies)}: {proxy} ({country})")
        else:
            logger.warning(f"Proxy {proxy} is not working, skipping...")
            
        # Small delay between attempts
        time.sleep(1)
        
    return working_proxies

if __name__ == "__main__":
    # Get multiple proxies
    working_proxies = get_multiple_proxies(3)
    
    if working_proxies:
        logger.info(f"\nFound {len(working_proxies)} working proxies:")
        for i, proxy in enumerate(working_proxies, 1):
            logger.info(f"{i}. {proxy['url']} - {proxy['ip']} ({proxy['country']}, {proxy['location']})")
        
        # Compare with direct connection
        logger.info("\nComparing with direct connection:")
        direct_ip_info = test_proxy()
        
        logger.info("\nProxy implementation instructions for ai_proposal_generator.py:")
        logger.info(f"1. Use the best proxy: {working_proxies[0]['url']}")
        logger.info("2. Configure the requests session with this proxy")
        logger.info("3. Pass the session to Google Generative AI API")
    else:
        logger.warning("No working proxies found. Consider using a direct connection or premium proxy service.") 