import requests
import json
import logging
import os
import configparser

def test_proxy_with_gemini(proxy, prompt, api_key, model="gemini-2.5-pro-exp-03-25"):
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        url = f"{api_url}?key={api_key}"
        
        response = requests.post(
            url,
            headers=headers,
            json=data,
            proxies={"http": proxy, "https": proxy},
            timeout=200
        )
        
        if response.ok:
            content = response.json()
            if 'candidates' in content and len(content['candidates']) > 0:
                if 'content' in content['candidates'][0]:
                    content_data = content['candidates'][0]['content']
                    if 'parts' in content_data and len(content_data['parts']) > 0:
                        text_response = content_data['parts'][0].get('text', '')
                        return text_response
            
            print(f"Proxy {proxy} connected but couldn't parse Gemini response: {response.text[:100]}...")
        else:
            print(f"Proxy {proxy} failed with Gemini API. Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Error occurred while testing proxy {proxy} with Gemini: {e}")

def get_gemini_response(prompt):
    """
    Get response from Gemini API through proxy.
    Returns the raw text response string, not a response object.
    """
    # Load configuration
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
        api_key = config['API'].get('gemini_api_key', "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM")
        model = config['API'].get('gemini_model', "gemini-2.5-pro-exp-03-25")
    else:
        api_key = "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM"
        model = "gemini-2.5-pro-exp-03-25"
    
    proxy = "http://8c5906b99fbd1c0bcd0f916d545c565ad4a39b7f89ce737b59fe3b50f1a001f69c62459f79f743615cd889172872cf5d4e30038ec896a33b99b244eab73adf15347c77cc26480843748c75b893647fb2:qcqao80vou9s@proxy.toolip.io:31111"
    
    # This already returns text, so no need to do response.text or similar in the caller
    return test_proxy_with_gemini(proxy, prompt, api_key, model)
