import requests
import json
import logging
import os
import configparser

def test_proxy_with_gemini(proxy, prompt, api_key, model="gemini-2.5-flash-preview-04-17", backup_api_key=None):
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent"
        
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
        url = f"{api_url}?key=AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg"
        
        response = requests.post(
            url,       
            headers=headers,
            json=data,
            proxies={"http": proxy, "https": proxy},
            timeout=200
        )
        
        # # Check for rate limit error (429) and retry with backup key if available
        # if response.status_code == 429 and backup_api_key:
        #     print(f"Rate limit exceeded (429). Trying with backup API key...")
        #     url = f"{api_url}?key=AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg"
        #     response = requests.post(
        #         url,
        #         headers=headers,
        #         json=data,
        #         proxies={"http": proxy, "https": proxy},
        #         timeout=200
        #     )


        
        if response.ok:
            content = response.json()
            if 'candidates' in content and len(content['candidates']) > 0:
                if 'content' in content['candidates'][0]:
                    content_data = content['candidates'][0]['content']
                    if 'parts' in content_data and len(content_data['parts']) > 0:
                        text_response = content_data['parts'][0].get('text', '')
                        return text_response
            
            print(f"Proxy {proxy} connected but couldn't parse Gemini response: {response.text}...")
        else:
            print(f"Proxy {proxy} failed with Gemini API. Status code: {response.status_code}")
            print(f"Response: {response.text}...")
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
        api_key = config['API'].get('gemini_api_key', "AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg")
        model = config['API'].get('gemini_model', "gemini-2.5-pro-exp-03-25")
        backup_api_key = config['API'].get('backup_api_key', None)
    else:
        api_key = "AIzaSyC_ibblijbVhr0EXFoVX04fZi71z3mB7Kg"
        model = "gemini-2.5-pro-exp-03-25"
        backup_api_key = None
    
    proxy = "http://fmwytxzp:042mq93wiwm1@198.23.239.134:6540"
    
    # This already returns text, so no need to do response.text or similar in the caller
    return test_proxy_with_gemini(proxy, prompt, api_key, model, backup_api_key)


