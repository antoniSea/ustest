import requests
import json
import logging
import os
import configparser
import re

def remove_thinking_tags(text):
    """Remove <thinking> tags and their content from the response."""
    return re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)

def test_proxy_with_deepseek(proxy, prompt, api_key):
    try:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer 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",
            "HTTP-Referer": "http://localhost:3000"
        }
        
        data = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [{"role": "user", "content": prompt}]
        }
        
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
                    # Remove thinking tags
                    text_response = remove_thinking_tags(text_response)
                    return text_response
            
            print(f"Proxy {proxy} connected but couldn't parse DeepSeek response: {response.text[:100]}...")
        else:
            print(f"Proxy {proxy} failed with Open Router API. Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Error occurred while testing proxy {proxy} with DeepSeek: {e}")

def get_gemini_response(prompt):
    """
    Get response from DeepSeek through Open Router API via proxy.
    Returns the raw text response string, not a response object.
    """
    # Load configuration
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
        api_key = config['API'].get('openrouter_api_key', "your_default_openrouter_key_here")
    else:
        api_key = "your_default_openrouter_key_here"
    
    proxy = "http://fmwytxzp:042mq93wiwm1@198.23.239.134:6540"
    
    # This already returns text, so no need to do response.text or similar in the caller
    return test_proxy_with_deepseek(proxy, prompt, api_key)

print(get_gemini_response("Explain how AI works"))