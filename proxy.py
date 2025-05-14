import requests
import json
import logging
import os
import configparser
import re

def remove_thinking_tags(text):
    """Remove <thinking> tags and their content from the response."""
    return re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)

def test_proxy_with_gemini(proxy, prompt, api_key=None):
    try:
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25:generateContent"
        
        # Add a strong system prompt to reduce hallucinations
        system_prompt = """Jesteś asystentem AI, który zawsze udziela dokładnych, konkretnych odpowiedzi na podstawie pytań.
        NIE wymyślaj informacji, NIE konfabuluj.
        NIE generuj treści fikcyjnych, chyba że zostaniesz wyraźnie o to poproszony.
        Jeśli nie znasz odpowiedzi, przyznaj to.
        ZAWSZE dokładnie wykonuj otrzymane polecenia, nie dodając własnych interpretacji.
        Tworzysz treści przeznaczone dla PRAWDZIWYCH klientów, więc unikaj konfabulacji.
        
        BARDZO WAŻNE: Zawsze odpowiadaj TYLKO tym, o co jesteś pytany. Nie dodawaj "Oto treść..." ani komentarzy meta na początku lub końcu odpowiedzi.
        """
        
        # Default API key if none provided
        if not api_key:
            api_key = "AIzaSyBPWhJ4w3IbcOLcAMXmz-jcWQPSRaCnBOM"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Rozumiem. Będę udzielać dokładnych, konkretnych odpowiedzi bez konfabulacji i zbędnych komentarzy."}]
                },
                {
                    "role": "user", 
                    "parts": [{"text": prompt}]
                }
            ],
            "generation_config": {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40
            }
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
                        # Remove thinking tags
                        text_response = remove_thinking_tags(text_response)
                        return text_response
            
            print(f"Proxy {proxy} connected but couldn't parse Gemini response: {response.text[:100]}...")
        else:
            print(f"Proxy {proxy} failed with Gemini API. Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Error occurred while testing proxy {proxy} with Gemini: {e}")

def get_gemini_response(prompt):
    """
    Get response from Gemini through API via proxy.
    Returns the raw text response string, not a response object.
    """
    # Load configuration
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
        api_key = config['API'].get('gemini_api_key', "AIzaSyBPWhJ4w3IbcOLcAMXmz-jcWQPSRaCnBOM")
    else:
        api_key = "AIzaSyBPWhJ4w3IbcOLcAMXmz-jcWQPSRaCnBOM"
    
    proxy = "http://fmwytxzp:042mq93wiwm1@198.23.239.134:6540"
    
    # This already returns text, so no need to do response.text or similar in the caller
    return test_proxy_with_gemini(proxy, prompt, api_key)

if __name__ == "__main__":
    print(get_gemini_response("Explain how AI works"))
