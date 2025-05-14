import requests
import json
import logging
import os
import configparser
import re
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_thinking_tags(text):
    """Remove <thinking> tags and their content from the response."""
    if not text:
        return ""
    return re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)

def test_proxy_with_deepseek(proxy, prompt, api_key, max_retries=3):
    """
    Send a request to DeepSeek through the proxy with retry logic.
    
    Args:
        proxy: The proxy to use
        prompt: The prompt to send
        api_key: The OpenRouter API key
        max_retries: Maximum number of retry attempts
        
    Returns:
        The response text or None if all retries failed
    """
    retry_count = 0
    backoff_time = 2  # Initial backoff time in seconds
    
    while retry_count <= max_retries:
        try:
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count}/{max_retries} after {backoff_time}s")
                time.sleep(backoff_time)
                # Add jitter and increase backoff time for next retry
                backoff_time = backoff_time * 1.5 + random.uniform(0, 1)
            
            api_url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer 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",
                "HTTP-Referer": "http://localhost:3000"
            }
            
            data = {
                "model": "deepseek/deepseek-r1:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,  # Lower temperature for more focused responses
                "max_tokens": 3000,  # Ensure enough token space for complete responses
                "top_p": 0.1,  # More focused sampling from token distribution
                "frequency_penalty": 0.5,  # Discourage repetition
                "presence_penalty": 0.5  # Discourage topic wandering
            }
            
            logger.info(f"Sending request to OpenRouter API via proxy (attempt {retry_count+1}/{max_retries+1})")
            response = requests.post(
                api_url,       
                headers=headers,
                json=data,
                proxies={"http": proxy, "https": proxy},
                timeout=200
            )
            
            if response.ok:
                content = response.json()
                if 'choices' in content and len(content['choices']) > 0:
                    if 'message' in content['choices'][0]:
                        text_response = content['choices'][0]['message'].get('content', '')
                        
                        # Check if response is empty or just whitespace
                        if not text_response or text_response.isspace():
                            logger.warning(f"Received empty response from DeepSeek (attempt {retry_count+1})")
                            retry_count += 1
                            continue
                            
                        # Remove thinking tags
                        text_response = remove_thinking_tags(text_response)
                        # Additional post-processing to clean responses
                        text_response = re.sub(r'(^|\n)Temat:.*?\n', '', text_response, flags=re.IGNORECASE)  # Remove any subject lines
                        text_response = re.sub(r'(As an AI|I am an AI|As a language model|I\'m an AI|I\'m just an AI)', '', text_response, flags=re.IGNORECASE)
                        
                        if text_response.strip():  # Final check to ensure response isn't empty after processing
                            logger.info("Successfully received and processed response from DeepSeek")
                            return text_response
                        else:
                            logger.warning("Response was empty after processing, retrying")
                            retry_count += 1
                            continue
                
                logger.warning(f"Proxy {proxy} connected but couldn't parse DeepSeek response: {response.text[:200]}...")
            else:
                logger.error(f"Proxy {proxy} failed with OpenRouter API. Status code: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}...")
            
            retry_count += 1
            
        except Exception as e:
            logger.error(f"Error occurred while testing proxy {proxy} with DeepSeek: {e}")
            retry_count += 1
    
    # If we've exhausted all retries
    logger.error(f"Failed to get a valid response after {max_retries+1} attempts")
    return None

def get_gemini_response(prompt):
    """
    Get response from DeepSeek through Open Router API via proxy.
    Returns the raw text response string, not a response object.
    """
    # Add explicit instructions to reduce confabulation
    enhanced_prompt = f"""INSTRUKCJE:
1. Odpowiedz BEZPOŚREDNIO na pytanie bez dodatkowych wyjaśnień
2. NIE KONFABULUJ - odpowiadaj tylko na podstawie faktów
3. NIE używaj sformułowań typu "jako AI", "jako model językowy" itp.
4. NIE dodawaj informacji, o które nie pytano

PYTANIE/ZADANIE:
{prompt}"""
    
    # Load configuration
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
        api_key = config['API'].get('openrouter_api_key', "your_default_openrouter_key_here")
    else:
        api_key = "your_default_openrouter_key_here"
    
    proxy = "http://fmwytxzp:042mq93wiwm1@198.23.239.134:6540"
    
    # Get response with retry logic
    response = test_proxy_with_deepseek(proxy, enhanced_prompt, api_key)
    
    # If response is None after all retries, return a fallback message
    if response is None:
        logger.error("Using fallback response due to API failure")
        return "Przepraszamy, wystąpił problem z połączeniem do API. Proszę spróbować ponownie później."
    
    return response
