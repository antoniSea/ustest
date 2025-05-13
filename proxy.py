import requests
import json
import logging
import os
import configparser
import re

def test_proxy_with_openrouter(proxy, prompt, api_key):
    try:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8000"
        }
        
        data = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "user", "content": prompt}
            ]
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
                    message = content['choices'][0]['message']
                    if 'content' in message:
                        text_response = message['content']
                        # Remove thinking tags
                        text_response = re.sub(r'<thinking>.*?</thinking>', '', text_response, flags=re.DOTALL)
                        return text_response
            
            print(f"Proxy {proxy} connected but couldn't parse OpenRouter response: {response.text[:100]}...")
        else:
            print(f"Proxy {proxy} failed with OpenRouter API. Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Error occurred while testing proxy {proxy} with OpenRouter: {e}")

def get_gemini_response(prompt):
    """
    Get response from OpenRouter API through proxy.
    Returns the raw text response string with thinking tags removed.
    """
    # Load configuration
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # if os.path.exists(config_file):
    #     config.read(config_file)
    #     api_key = config['API'].get('openrouter_api_key', "YOUR_DEFAULT_OPENROUTER_API_KEY")
    # else:
    api_key = "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"
    
    proxy = "http://fmwytxzp:042mq93wiwm1@198.23.239.134:6540"
    
    return test_proxy_with_openrouter(proxy, prompt, api_key)

# print(get_openrouter_response("Explain how AI works"))