#!/usr/bin/env python3
"""
Script to help update Useme cookies in useme_post_proposal.py
"""

import argparse
import json
import re
import requests
from bs4 import BeautifulSoup

def extract_cookies_from_browser_string(cookie_string):
    """Extract cookies from a copy-pasted browser string"""
    cookies = {}
    
    # Split by lines or semicolons
    if '\n' in cookie_string:
        parts = cookie_string.strip().split('\n')
    else:
        parts = cookie_string.strip().split('; ')
    
    for part in parts:
        if '=' in part:
            name, value = part.split('=', 1)
            cookies[name.strip()] = value.strip()
    
    return cookies

def test_cookies(cookies):
    """Test if the cookies work by checking if we're logged in"""
    session = requests.Session()
    # Add -dns-result-order=ipv6first parameter to session
    session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, pool_block=False))
    session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, pool_block=False))
    setattr(session, 'dns_result_order', 'ipv6first')
    session.cookies.update(cookies)
    
    # Try to access the dashboard
    response = session.get("https://useme.com/pl/account/dashboard/")
    
    if response.status_code != 200:
        print(f"ERROR: Got status code {response.status_code}")
        return False
    
    # Check if we're redirected to login
    if "Zaloguj się" in response.text and "Odzyskaj hasło" in response.text:
        print("ERROR: Not logged in. Cookies are invalid or expired.")
        return False
    
    # Try to extract username
    soup = BeautifulSoup(response.text, 'html.parser')
    username_elem = soup.select_one('.navbar-username')
    username = username_elem.text.strip() if username_elem else "Unknown User"
    
    print(f"Successfully logged in as {username}")
    return True

def update_cookies_in_file(file_path, cookies):
    """Update the COOKIES dictionary in the given file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the COOKIES dictionary
        cookies_pattern = r"COOKIES\s*=\s*\{[^}]+\}"
        match = re.search(cookies_pattern, content, re.DOTALL)
        
        if not match:
            print(f"ERROR: Could not find COOKIES dictionary in {file_path}")
            return False
        
        # Format the new cookies
        cookies_str = "COOKIES = {\n"
        for key, value in cookies.items():
            cookies_str += f'    "{key}": "{value}",\n'
        cookies_str += "}"
        
        # Replace the old cookies with new ones
        new_content = content[:match.start()] + cookies_str + content[match.end():]
        
        # Write the updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Successfully updated cookies in {file_path}")
        return True
    
    except Exception as e:
        print(f"ERROR: Failed to update cookies: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Update Useme cookies in the project")
    parser.add_argument('--cookies', type=str, help='Cookie string from browser')
    parser.add_argument('--file', type=str, default='useme_post_proposal.py', 
                        help='Path to the file containing COOKIES dictionary')
    parser.add_argument('--input-file', type=str, help='Path to a JSON file containing cookies')
    
    args = parser.parse_args()
    
    cookies = {}
    
    if args.input_file:
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load cookies from {args.input_file}: {str(e)}")
            return
    elif args.cookies:
        cookies = extract_cookies_from_browser_string(args.cookies)
    else:
        print("Please provide cookies using --cookies or --input-file")
        print("\nExample usage:")
        print("1. From browser string:")
        print('   python update_cookies.py --cookies "cookie1=value1; cookie2=value2"')
        print("\n2. From file:")
        print('   python update_cookies.py --input-file cookies.json')
        print("\nTo get cookies from your browser:")
        print("1. Open Useme.com and log in")
        print("2. Open developer tools (F12)")
        print("3. Go to the Network tab")
        print("4. Refresh the page")
        print("5. Click on any request to useme.com")
        print("6. Find the 'Cookie' header in the request headers")
        print("7. Copy the entire cookie string")
        return
    
    if not cookies:
        print("ERROR: No cookies found")
        return
    
    print(f"Got {len(cookies)} cookies")
    
    # Test the cookies
    if test_cookies(cookies):
        # Save cookies to a backup file
        with open('useme_cookies_backup.json', 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        print("Saved cookies to useme_cookies_backup.json")
        
        # Update the file
        update_cookies_in_file(args.file, cookies)
    else:
        print("ERROR: Cookie test failed. Not updating files.")

if __name__ == "__main__":
    main() 