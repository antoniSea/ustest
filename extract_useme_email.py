import sys
import requests
from bs4 import BeautifulSoup
import json
import base64
import re
import argparse

# Cookies for authentication - replace with your own cookies
COOKIES = {
    "_tt_enable_cookie": "1",
    "_ttp": "01JTK1Z3W2P39XPQMJW90KPCYF_.tt.1",
    "__hs_cookie_cat_pref": "1:true_2:true_3:true",
    "hubspotutk": "515cce126ad5caf802db8247db388010",
    "__hssrc": "1",
    "_ga": "GA1.1.439587260.1746543818",
    "_fbp": "fb.1.1746543818646.834346703319431092",
    "_hjSessionUser_661614": "eyJpZCI6ImExZThkYWQ5LTQyNGEtNTA3MS1iNWJmLWIwYWVmZjA2M2VhOSIsImNyZWF0ZWQiOjE3NDY1NDM4MTg3NTMsImV4aXN0aW5nIjp0cnVlfQ==",
    "csrftoken": "a9ALgB78whmkgLDATzfZRZadmTU7ktju",
    "sessionid": "hnkqglxgfnnjkzcpq5u67mknt512bx17",
    "user_id": "219122",
    "_hjSession_661614": "eyJpZCI6IjE4ZTA0NDIzLTg5ODctNDhmNC1hMzkyLTBlNTBlNzdiMzU1ZCIsImMiOjE3NDY3ODc0MzUyNzEsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=",
    "__hstc": "194865778.515cce126ad5caf802db8247db388010.1746543810753.1746683931433.1746787438927.9",
    "__hssc": "194865778.7.1746787438927",
    "_ga_3MHM4HVMF1": "GS2.1.s1746787435$o11$g1$t1746787604$j40$l1$h1876547645",
    "ttcsid": "1746787436250::vWyMA_GcTled6TUv86TL.9.1746787604780",
    "ttcsid_CUU466RC77U7F7KCJ8F0": "1746787436250::se-oNq9jvkTaRU6urbi_.9.1746787604783",
    "_gcl_au": "1.1.2064432027.1746543814.1335018212.1746787454.1746787604"
}

def extract_job_id_from_url(url):
    """Extract job ID from a Useme URL."""
    # Match patterns like: 
    # https://useme.com/pl/jobs/projekt-ulotki,115348/
    # https://useme.com/pl/jobs/115348/
    # https://useme.com/pl/jobs/projekt-nazwa/115348/
    patterns = [
        r'jobs/[^,/]+,(\d+)',  # Format: jobs/nazwa,123/
        r'jobs/(\d+)',         # Format: jobs/123/
        r'/(\d+)(?:/|$)'       # Format: anything/123/ or anything/123
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def extract_employer_email(job_id, cookies=None):
    """
    Extract employer email from a Useme job post-offer page.
    
    Args:
        job_id (str): The Useme job ID or complete URL
        cookies (dict, optional): Custom cookies for authentication
    
    Returns:
        str or None: The employer email if found, None otherwise
    """
    # Use provided cookies or default ones
    request_cookies = cookies if cookies else COOKIES
    
    # Check if job_id is a URL and extract the ID if needed
    if job_id.startswith('http'):
        extracted_id = extract_job_id_from_url(job_id)
        if extracted_id:
            job_id = extracted_id
        else:
            print(f"Error: Could not extract job ID from the URL: {job_id}")
            return None
    
    # Construct the post-offer URL
    url = f"https://useme.com/pl/jobs/{job_id}/post-offer/"
    
    try:
        # Send GET request to the URL
        response = requests.get(url, cookies=request_cookies)
        
        if response.status_code != 200:
            print(f"Error: Failed to access the URL. Status code: {response.status_code}")
            return None
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the hidden input field with the employer email
        hidden_input = soup.find('input', {'name': '_employer_email'})
        
        if not hidden_input:
            print("Error: Could not find the employer email field in the page.")
            return None
        
        # Extract the value
        encoded_value = hidden_input.get('value', '')
        
        # The value is in the format "eyJ....:1uD..."
        if ':' in encoded_value:
            encoded_data = encoded_value.split(':')[0]
            
            try:
                # Add padding if needed for base64 decoding
                padding_needed = len(encoded_data) % 4
                if padding_needed:
                    encoded_data += '=' * (4 - padding_needed)
                
                # Decode the base64 data
                decoded_bytes = base64.b64decode(encoded_data)
                decoded_str = decoded_bytes.decode('utf-8')
                
                # Parse the JSON data
                try:
                    email_data = json.loads(decoded_str)
                    if 'employer_email' in email_data:
                        return email_data['employer_email']
                    else:
                        print(f"Error: employer_email key not found in decoded data: {decoded_str}")
                        return None
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {str(e)}")
                    
                    # Fallback to regex if JSON parsing fails
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', decoded_str)
                    if email_match:
                        return email_match.group(0)
                    else:
                        print(f"Could not extract email with regex from: {decoded_str}")
                        return None
            except Exception as e:
                print(f"Error decoding the email: {str(e)}")
                return None
        else:
            print(f"Warning: Expected encoded value format 'part1:part2', got: {encoded_value}")
            return None
    except Exception as e:
        print(f"Error accessing Useme: {str(e)}")
        return None

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description='Extract employer email from Useme job post-offer page')
    parser.add_argument('job_id', help='Useme job ID or complete URL')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    email = extract_employer_email(args.job_id)
    
    if args.json:
        result = {"job_id": args.job_id, "email": email if email else None}
        print(json.dumps(result, ensure_ascii=False))
    else:
        if email:
            print(f"Employer email: {email}")
        else:
            print("Failed to extract employer email.")

if __name__ == "__main__":
    main() 