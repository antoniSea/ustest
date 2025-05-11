#!/usr/bin/env python3
"""
Script for posting proposals to Useme
"""

import os
import sys
import json
import time
import re
import base64
import logging
import traceback
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from database import Database

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Headers for requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': 'https://useme.com/',
    'Origin': 'https://useme.com',
    'Connection': 'keep-alive',
}

class UsemeProposalPoster:
    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.headers = headers.copy()
        self.employer_email = None
        self.db = Database()
        
        # Załaduj ciasteczka, jeśli są
        if cookies:
            self.session.cookies.update(cookies)
        else:
            # Załaduj ciasteczka z pliku
            self.load_cookies_from_file()
        
    def load_cookies_from_file(self, path='cookies.json'):
        """Load cookies from a JSON file"""
        try:
            with open(path, 'r') as f:
                cookies_data = json.load(f)
                
                # Sprawdź format ciasteczek (lista obiektów lub słownik)
                if isinstance(cookies_data, list):
                    # Format: lista obiektów [{"name": "key", "value": "val"}, ...]
                    for cookie in cookies_data:
                        self.session.cookies.set(cookie['name'], cookie['value'])
                elif isinstance(cookies_data, dict):
                    # Format: słownik {"key": "val", ...}
                    for name, value in cookies_data.items():
                        self.session.cookies.set(name, value)
            
            logger.info(f"Loaded cookies from {path}")
            return True
        except FileNotFoundError:
            logger.warning(f"Cookies file not found: {path}")
            return False
        except Exception as e:
            logger.error(f"Error loading cookies: {str(e)}")
            return False
            
    def store_submitted_proposal(self, job_id, proposal_text, status="submitted", response_message=""):
        """Store information about a submitted proposal"""
        # Current timestamp in ISO format
        submission_time = datetime.now().isoformat()
        
        # Use the database instance
        self.db.store_submitted_proposal(job_id, proposal_text, status, response_message)

    def get_csrf_token(self, url):
        """Get CSRF token and employer email from the job offer page."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # Try to extract from meta tag
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_csrf = soup.find('meta', attrs={'name': 'csrf-token'})
            
            # Also extract employer email
            email_input = soup.find('input', attrs={'name': '_employer_email'})
            if email_input and email_input.get('value'):
                encoded_email = email_input.get('value')
                self.employer_email = self.decode_employer_email(encoded_email)
            
            if meta_csrf and meta_csrf.get('content'):
                return meta_csrf.get('content')
            
            # Try to extract from form
            csrf_input = soup.find('input', attrs={'name': 'csrfmiddlewaretoken'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input.get('value')
            
            # Try to extract using regex as fallback
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
            if match:
                return match.group(1)
            
            raise Exception("Could not find CSRF token in the page")
        except Exception as e:
            print(f"Error getting CSRF token: {str(e)}")
            return None
            
    def decode_employer_email(self, encoded_value):
        """Decode the employer email from the encoded form value."""
        try:
            # Value format is typically: base64encoded_json:signature
            parts = encoded_value.split(':')
            if len(parts) < 2:
                return None
                
            # Get the base64 encoded part
            base64_part = parts[0]
            
            # Add padding if needed
            missing_padding = len(base64_part) % 4
            if missing_padding:
                base64_part += '=' * (4 - missing_padding)
            
            # Decode base64
            try:
                decoded_bytes = base64.b64decode(base64_part)
                decoded_json = decoded_bytes.decode('utf-8')
                
                # Parse JSON
                email_data = json.loads(decoded_json)
                
                # Extract email
                if 'employer_email' in email_data:
                    return email_data['employer_email']
                
                return None
            except Exception as e:
                # Try URL-safe base64 if standard base64 fails
                try:
                    decoded_bytes = base64.urlsafe_b64decode(base64_part)
                    decoded_json = decoded_bytes.decode('utf-8')
                    
                    # Parse JSON
                    email_data = json.loads(decoded_json)
                    
                    # Extract email
                    if 'employer_email' in email_data:
                        return email_data['employer_email']
                    
                    return None
                except Exception as e2:
                    print(f"Error decoding employer email with URL-safe base64: {str(e2)}")
                    return None
                
        except Exception as e:
            print(f"Error decoding employer email: {str(e)}")
            return None

    def convert_url_to_post_offer_format(self, url):
        """
        Przekształca URL oferty na format używany do wysyłania propozycji.
        Zwraca prawidłowy URL do wysyłania oferty w formacie: https://useme.com/pl/jobs/ID/post-offer/
        """
        try:
            # Najpierw wyodrębnij ID oferty
            job_id = self.extract_job_id_from_url(url)
            if not job_id:
                logger.error(f"Nie można przekształcić URL - nie znaleziono ID oferty: {url}")
                return url
                
            # Zwróć URL w standardowym formacie
            return f"https://useme.com/pl/jobs/{job_id}/post-offer/"
        except Exception as e:
            logger.error(f"Błąd podczas przekształcania URL: {str(e)}")
            return url

    def post_proposal(self, job_url, proposal_text, price=None, email_content=None, attachments=None, timeline_days=None):
        """Post a proposal to a job"""
        self.employer_email = None  # Reset employer email
        try:
            logger.info(f"Posting to URL: {job_url}")
            
            # Process price if provided
            clean_price = None
            if price:
                # Try to extract just the numeric part
                if isinstance(price, str):
                    # Remove currency, spaces and text like "PLN" or "netto"
                    price_str = price.strip()
                    # Extract first group of digits (possibly with decimal separator)
                    match = re.search(r'(\d[\d\s]*[\d,.]*\d)', price_str)
                    if match:
                        # Get the matched number and clean it up
                        clean_price_str = match.group(1)
                        # Remove spaces
                        clean_price_str = clean_price_str.replace(' ', '')
                        # Replace comma with dot for decimal
                        clean_price_str = clean_price_str.replace(',', '.')
                        # Try to convert to float and then to int (Useme requires integer amounts)
                        try:
                            clean_price = int(float(clean_price_str))
                            logger.info(f"Extracted price {clean_price} from '{price}'")
                        except ValueError:
                            logger.error(f"Could not convert price '{clean_price_str}' to number")
                            clean_price = 40  # Default price
                else:
                    # If already numeric, just use it
                    clean_price = price
            
            # Extract job ID from URL
            job_id = self.extract_job_id_from_url(job_url)
            if not job_id:
                return {
                    "success": False, 
                    "message": f"Nieprawidłowy format URL: {job_url}"
                }
            
            # Construct offer URL
            offer_post_url = self.convert_url_to_post_offer_format(job_url)
            logger.info(f"Przekształcono URL na: {offer_post_url}")
            
            # Get the page with form
            logger.info("Getting CSRF token...")
            response = self.session.get(offer_post_url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get offer page. Status code: {response.status_code}")
                debug_filename = f"debug_page_{job_id}.html"
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"Saved response to {debug_filename}")
                return {
                    "success": False, 
                    "message": f"Błąd pobierania strony oferty: Status {response.status_code}"
                }
            
            # Save the page content for debugging
            debug_filename = f"debug_page_{job_id}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"Saved page content to {debug_filename}")
            
            # Extract CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            
            if not csrf_token:
                # Try JavaScript variable
                csrf_match = re.search(r'csrfToken\s*=\s*["\']([^"\']+)["\']', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                else:
                    # Try meta tag
                    meta_csrf = soup.find('meta', attrs={'name': 'csrf-token'})
                    if meta_csrf and meta_csrf.get('content'):
                        csrf_token = meta_csrf.get('content')
                    else:
                        logger.error("No CSRF token found in the page")
                        return {
                            "success": False, 
                            "message": "Nie znaleziono tokenu CSRF"
                        }
            else:
                csrf_token = csrf_token.get('value')
            
            csrf_token_trimmed = csrf_token[:10] + "..." if len(csrf_token) > 10 else csrf_token
            logger.info(f"Got CSRF token: {csrf_token_trimmed}")
            
            # Extract employer email if available
            logger.info("Getting employer email...")
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', response.text)
            if email_match:
                self.employer_email = email_match.group(0)
                logger.info(f"Found employer email: {self.employer_email}")
            
            # Check if we're already logged in
            if "login" in response.text.lower() and "zaloguj się" in response.text.lower():
                logger.error("Not logged in. Please update cookies.")
                return {
                    "success": False,
                    "message": "Nie jesteś zalogowany na Useme. Zaktualizuj plik cookies.json."
                }
            
            # Look for the form and its fields
            form = soup.find('form', attrs={'method': 'post'})
            if not form:
                logger.error("Form not found on the page")
                return {
                    "success": False,
                    "message": "Nie znaleziono formularza na stronie"
                }
            
            # Prepare form data
            form_data = {
                'csrfmiddlewaretoken': csrf_token,
                'text': proposal_text,
                'description': proposal_text,  # Useme wymaga pola description
                'payment': str(clean_price) if clean_price is not None else "40",
                'work_days': str(timeline_days) if timeline_days else "7",
                'accept_regulations': 'on',
                'submit_offer': 'Wyślij propozycję',
                'copyright_transfer': 'protocol',
                'currency': 'PLN',
                'billing_calculator': 'GROSS',
                'license_duration': '15',
                'stages-TOTAL_FORMS': '5',
                'stages-INITIAL_FORMS': '0',
                'stages-MIN_NUM_FORMS': '0',
                'stages-MAX_NUM_FORMS': '1000'
            }
            
            # Dodaj pola _* z formularza
            for field_name in soup.find_all('input', {'name': re.compile(r'^_')}):
                name = field_name.get('name')
                value = field_name.get('value', '')
                form_data[name] = value
                logger.info(f"Added hidden field: {name}={value}")
                
            # Dodaj pola stages-*
            for i in range(5):
                form_data[f'stages-{i}-id'] = ''
                form_data[f'stages-{i}-name'] = ''
                form_data[f'stages-{i}-description'] = ''
                form_data[f'stages-{i}-payment'] = ''
                form_data[f'stages-{i}-work_days'] = ''
            
            # Add email content if provided
            if email_content and email_content.strip():
                form_data['email_content'] = email_content
                
            # Add attachments if provided
            files = {}
            if attachments:
                for idx, attachment in enumerate(attachments):
                    if 'local_path' in attachment and 'name' in attachment:
                        file_path = attachment['local_path']
                        file_name = attachment['name']
                        try:
                            files[f'attachment_{idx}'] = (file_name, open(file_path, 'rb'))
                            logger.info(f"Adding attachment: {file_name}")
                        except Exception as e:
                            logger.error(f"Failed to add attachment {file_name}: {str(e)}")
            
            # Submit the form
            logger.info("Submitting proposal form...")
            headers = self.headers.copy()
            headers['Referer'] = offer_post_url
            
            # Ustaw odpowiednie nagłówki dla żądania POST
            # Nie ustawiaj Content-Type jeśli załączamy pliki, requests zrobi to automatycznie
            if not files:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Origin'] = 'https://useme.com'
            
            # Log form data for debugging
            logger.info(f"Form data: {form_data}")
            logger.info(f"Post URL: {offer_post_url}")
            logger.info(f"Request method: POST")
            
            # Zapisz dane formularza do pliku dla debugowania
            with open(f"debug_form_data_{job_id}.json", 'w', encoding='utf-8') as f:
                json.dump(form_data, f, indent=4)
            
            # Wyślij żądanie z wyraźnie określoną metodą POST
            if files:
                # Jeśli mamy pliki, używamy multipart/form-data (określane automatycznie)
                response = self.session.post(
                    offer_post_url,
                    data=form_data,
                    files=files,
                    headers=headers,
                    allow_redirects=True
                )
            else:
                # Jeśli nie mamy plików, używamy application/x-www-form-urlencoded
                response = self.session.post(
                    offer_post_url, 
                    data=form_data,
                    headers=headers,
                    allow_redirects=True
                )
            
            # Close file handles if we opened any
            for file_obj in files.values():
                if isinstance(file_obj, tuple) and hasattr(file_obj[1], 'close'):
                    file_obj[1].close()
            
            logger.info(f"Got response. Status code: {response.status_code}, URL: {response.url}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            # Save response for debugging
            debug_response_filename = f"debug_response_{job_id}.html"
            with open(debug_response_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"Saved response to {debug_response_filename}")
            
            # Save job data for debugging
            job_data = {
                'job_id': job_id,
                'url': job_url,
                'response_status': response.status_code,
                'response_url': response.url,
                'csrf_token': csrf_token_trimmed
            }
            with open(f"job_{job_id}_data.json", 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=4)
            
            # Check for success (usually a redirect to the job page)
            if response.status_code == 200 and "post-offer" not in response.url:
                logger.info(f"Redirected to: {response.url} - assuming success")
                # Save the email and other data
                self.store_submitted_proposal(job_id, proposal_text)
                return {
                    "success": True, 
                    "message": "Propozycja została pomyślnie wysłana",
                    "employer_email": self.employer_email
                }
            # Sprawdź czy wiadomość sukcesu jest w odpowiedzi
            elif response.status_code == 200 and ("Dziękujemy za przesłanie propozycji" in response.text or 
                                                 "Twoja propozycja została przyjęta" in response.text or
                                                 "Dodaj usługę" in response.text or
                                                 "Oferta została wysłana" in response.text):
                logger.info("Znaleziono komunikat sukcesu w odpowiedzi!")
                print("SUKCES: Oferta została pomyślnie wysłana!")
                # Save the email and other data
                self.store_submitted_proposal(job_id, proposal_text)
                return {
                    "success": True, 
                    "message": "Propozycja została pomyślnie wysłana",
                    "employer_email": self.employer_email
                }
            elif response.status_code != 200:
                error_message = f"Serwer zwrócił błąd: {response.status_code}"
                self.store_submitted_proposal(job_id, proposal_text, status="failed", response_message=error_message)
                return {
                    "success": False, 
                    "message": error_message,
                    "employer_email": self.employer_email
                }
            else:
                # Check for error messages
                soup = BeautifulSoup(response.text, 'html.parser')
                error_msgs = soup.select('.errorlist li')
                if not error_msgs:
                    error_msgs = soup.select('.alert-danger')
                if not error_msgs:
                    error_msgs = soup.select('.error')
                errors = [msg.text for msg in error_msgs] if error_msgs else []
                
                if errors:
                    error_message = f"Błędy formularza: {', '.join(errors)}"
                    logger.error(error_message)
                else:
                    # Sprawdź czy jest jakiś komunikat w HTML
                    error_message = f"Nieznany błąd. Status: {response.status_code}, URL: {response.url}"
                    
                    # Spróbuj wyodrębnić jakikolwiek komunikat błędu z HTML
                    messages = soup.select('.messages li')
                    if messages:
                        error_message = f"Komunikat serwera: {', '.join([msg.text for msg in messages])}"
                    
                print(f"BŁĄD: {error_message}")
                self.store_submitted_proposal(job_id, proposal_text, status="failed", response_message=error_message)
                return {
                    "success": False, 
                    "message": error_message,
                    "employer_email": self.employer_email
                }
        
        except Exception as e:
            logger.error(f"Błąd podczas wysyłania propozycji: {str(e)}")
            traceback.print_exc()
            self.store_submitted_proposal(job_id, proposal_text, status="failed", response_message=str(e))
            return {
                "success": False, 
                "message": f"Wyjątek: {str(e)}",
                "employer_email": self.employer_email
            }

    def extract_job_id_from_url(self, url):
        """Extract job ID from Useme job URL."""
        try:
            # Usuń @ z początku URL, jeśli istnieje
            if url.startswith('@'):
                url = url[1:]
                
            # Try to extract job id from URL using regex
            # Pattern for URLs like https://useme.com/pl/jobs/123456/
            pattern = r'useme\.com/pl/jobs/(\d+)'
            match = re.search(pattern, url)
            
            if match:
                return match.group(1)
                
            # Format z nazwą projektu, np. jobs/nazwa-projektu,123456/
            format_with_name = r'jobs/[^,]+,(\d+)'
            match_with_name = re.search(format_with_name, url)
            if match_with_name:
                return match_with_name.group(1)
                
            # Alternative pattern for URLs without language prefix
            alt_pattern = r'useme\.com/jobs/(\d+)'
            match = re.search(alt_pattern, url)
            
            if match:
                return match.group(1)
                
            # If URL is just a job ID
            if url.isdigit():
                return url
                
            # Ostatnia próba - wyodrębnij dowolny 6-cyfrowy numer
            match_digits = re.search(r'(\d{6})', url)
            if match_digits:
                return match_digits.group(1)
                
            logger.error(f"Nie udało się wyodrębnić ID oferty z URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting job ID from URL {url}: {str(e)}")
            return None

def post_proposal_from_json(json_file, job_id=None, post_all=False):
    """
    Post proposals to Useme from a JSON file.
    
    Args:
        json_file (str): Path to the JSON file containing proposals
        job_id (str, optional): Specific job ID to post proposal for
        post_all (bool): Whether to post all proposals without asking
        
    Returns:
        bool: True if all operations were successful
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            proposals = json.load(f)
        
        print(f"\nFound {len(proposals)} proposals in {json_file}")
        
        poster = UsemeProposalPoster()
        success_count = 0
        
        for proposal in proposals:
            # If specific job_id is provided, skip other proposals
            if job_id and proposal.get('job_id') != job_id and proposal.get('job_id') != f"job_{job_id}":
                continue
                
            proposal_job_id = proposal.get('job_id', '').replace('job_', '')
            job_url = proposal.get('url') or f"https://useme.com/pl/jobs/{job_id}/post-offer/"
            
            print(f"\nProposal for job {proposal_job_id}:")
            print(f"Title: {proposal.get('title', 'No title')}")
            print(f"URL: {job_url}")
            
            # Extract price information
            price = proposal.get('price')
            timeline_days = proposal.get('timeline_days')
            
            # If proposal contains price information in its text, try to extract it
            proposal_text = proposal.get('proposal_text', '')
            if not price and proposal_text:
                # Look for price pattern in text
                price_match = re.search(r'(?:cena|kwota|koszt|wynagrodzenie|kwoty)(?:[^\d]*)(\d[\d\s]*[\d,.]*\d)[^\d]*(?:pln|zł|złotych|złote|zl)?', 
                                      proposal_text.lower())
                if price_match:
                    price = price_match.group(1)
                    print(f"Extracted price from proposal text: {price}")
                
                # Look for timeline pattern
                timeline_match = re.search(r'(?:czas|okres|terminie|dni|dniach)(?:[^\d]*)(\d+)[^\d]*(?:dni|dnia|dzień|robocz)', 
                                         proposal_text.lower())
                if timeline_match and not timeline_days:
                    timeline_days = int(timeline_match.group(1))
                    print(f"Extracted timeline from proposal text: {timeline_days} days")
            
            # Ask for confirmation if not post_all
            if not post_all:
                choice = input("Post this proposal? (y/n/q to quit): ").lower()
                if choice == 'q':
                    print("Quitting...")
                    break
                elif choice != 'y':
                    print("Skipping...")
                    continue
            
            # Post the proposal
            print(f"Posting proposal to {job_url}...")
            result = poster.post_proposal(
                job_url=job_url,
                proposal_text=proposal_text,
                price=price,
                email_content=proposal.get('email_content', ''),
                attachments=proposal.get('attachments', []),
                timeline_days=timeline_days
            )
            
            if result["success"]:
                print(f"Successfully posted proposal to job {proposal_job_id}")
                success_count += 1
            else:
                print(f"Failed to post proposal to job {proposal_job_id}: {result['message']}")
        
        print(f"\nFinished posting proposals. {success_count}/{len(proposals)} successful.")
        return True
        
    except Exception as e:
        print(f"Error posting proposals from JSON: {str(e)}")
        return False

def main():
    """Main function to run when executing the script directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Post proposals to Useme")
    parser.add_argument('--file', type=str, help='JSON file with proposals to post')
    parser.add_argument('--job', type=str, help='Specific job ID to post proposal for')
    parser.add_argument('--all', action='store_true', help='Post all proposals without asking for confirmation')
    parser.add_argument('--url', type=str, help='Direct URL to post a proposal to')
    parser.add_argument('--proposal', type=str, help='Text of the proposal to post (used with --url)')
    parser.add_argument('--payment', type=str, default='40', help='Payment amount in PLN (can include formatting like "1 500,00 PLN")')
    parser.add_argument('--days', type=int, default=7, help='Number of work days')
    parser.add_argument('--email', type=str, help='Email content to send to the client')
    parser.add_argument('--attachment', type=str, action='append', help='Path to attachment file (can be used multiple times)')
    
    args = parser.parse_args()
    
    if args.file:
        # Post proposals from a JSON file
        post_proposal_from_json(args.file, args.job, args.all)
    elif args.url and args.proposal:
        # Prepare attachments if provided
        attachments = []
        if args.attachment:
            for attachment_path in args.attachment:
                import os
                filename = os.path.basename(attachment_path)
                attachments.append({
                    'name': filename,
                    'local_path': attachment_path
                })
        
        # Post a single proposal
        poster = UsemeProposalPoster()
        result = poster.post_proposal(
            job_url=args.url,
            proposal_text=args.proposal,
            price=args.payment,
            email_content=args.email,
            attachments=attachments if attachments else None,
            timeline_days=args.days
        )
        print(f"{'Success' if result['success'] else 'Failed'} posting proposal to {args.url}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 