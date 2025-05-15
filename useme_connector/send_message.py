import logging

logger = logging.getLogger(__name__)

def send_useme_message(job_id, message_content, use_proposal=False):
    """
    Send a message through Useme's contact form for a specific job.
    
    Args:
        job_id (str): The Useme job ID.
        message_content (str): The message to send.
        use_proposal (bool): If True, use the saved proposal text as the message.
        
    Returns:
        dict: Success status and message.
    """
    logger.info(f"Sending message for job {job_id}")
    try:
        # Initialize the Useme poster (which has the cookies)
        poster = UsemeProposalPoster()
        
        # If use_proposal is True, get the proposal text from the database
        if use_proposal:
            db = Database()
            job = db.get_job_by_id(job_id)
            if job and job.get('proposal_text'):
                message_content = job.get('proposal_text')
                logger.info("Using saved proposal text as message content")
            else:
                logger.warning("No proposal found for this job, using provided message")
        
        # First, we need to visit the job page to extract the correct message URL
        # Useme uses two URL formats:
        # 1. /pl/jobs/ID/ 
        # 2. /pl/jobs/title,ID/ (comma format)
        
        # Try the comma format first as it's more common
        job_url = None
        
        # Check if we have the job data in the database to get the full URL
        db = Database()
        job_data = db.get_job_by_id(job_id)
        if job_data and job_data.get('url'):
            job_url = job_data.get('url')
            logger.info(f"Using URL from database: {job_url}")
        else:
            # Try to get the job title from the database to construct the URL
            if job_data and job_data.get('title'):
                # Create a slug from the title
                title_slug = job_data.get('title', '').lower().replace(' ', '-')
                # Remove any special characters
                import re
                title_slug = re.sub(r'[^a-z0-9-]', '', title_slug)
                job_url = f"https://useme.com/pl/jobs/{title_slug},{job_id}/"
                logger.info(f"Constructed URL with title: {job_url}")
            else:
                # Fallback to basic URL without title
                job_url = f"https://useme.com/pl/jobs/{job_id}/"
                logger.info(f"Using basic URL: {job_url}")
        
        logger.info(f"Visiting job page to find message link: {job_url}")
        
        job_response = poster.session.get(job_url, headers=poster.headers)
        if job_response.status_code != 200:
            # If the first URL format fails, try the second format
            if ',' in job_url:
                # Try without the title part
                job_url = f"https://useme.com/pl/jobs/{job_id}/"
            else:
                # Try with a generic title
                job_url = f"https://useme.com/pl/jobs/zlecenie,{job_id}/"
            
            logger.info(f"First URL failed, trying alternative: {job_url}")
            job_response = poster.session.get(job_url, headers=poster.headers)
            
            if job_response.status_code != 200:
                logger.error(f"Failed to access job page. Status code: {job_response.status_code}")
                return {
                    "success": False,
                    "message": f"Error accessing job page: Status {job_response.status_code}"
                }
        
        # Extract the message link from the job page
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(job_response.text, 'html.parser')
        
        # Look for the "Zapytaj o szczegóły" button/link
        message_link = None
        
        # Method 1: Look for the "Zapytaj o szczegóły" text in links
        ask_links = soup.find_all('a', text=lambda t: t and "Zapytaj o szczegóły" in t)
        if ask_links:
            message_link = ask_links[0]['href']
            logger.info(f"Found message link via button text: {message_link}")
        
        # Method 2: Look for links with the compose pattern in href
        if not message_link:
            compose_pattern = re.compile(r'/pl/mesg/compose/\d+/\d+/')
            compose_links = soup.find_all('a', href=compose_pattern)
            if compose_links:
                message_link = compose_links[0]['href']
                logger.info(f"Found message link via href pattern: {message_link}")
        
        # Method 3: Look for text pattern in the HTML if Methods 1 & 2 fail
        if not message_link:
            compose_match = re.search(r'href="(/pl/mesg/compose/\d+/\d+/)"', job_response.text)
            if compose_match:
                message_link = compose_match.group(1)
                logger.info(f"Found message link via regex: {message_link}")
        
        # Method 4: Look for specific button class/text
        if not message_link:
            for link in soup.find_all('a', {'class': 'button'}):
                if 'Zapytaj o szczegóły' in link.text or 'mesg/compose' in link.get('href', ''):
                    message_link = link.get('href')
                    logger.info(f"Found message link via button class: {message_link}")
                    break
                    
        # Method 5: Try fixed pattern as last resort
        if not message_link:
            # Try a direct format that might work based on the example
            employer_id = None
            employer_match = re.search(r'/pl/mesg/compose/\d+/(\d+)/', job_response.text)
            if employer_match:
                employer_id = employer_match.group(1)
                message_link = f"/pl/mesg/compose/{job_id}/{employer_id}/"
                logger.info(f"Found employer ID {employer_id} and constructed message link: {message_link}")
            else:
                return ' '
                logger.warning(f"Using fallback message link format: {message_link}")
        
        if not message_link:
            logger.error("Could not find message link on job page")
            # Save debug information
            with open(f"job_page_debug_{job_id}.html", "w", encoding="utf-8") as f:
                f.write(job_response.text)
            logger.info(f"Saved job page HTML to job_page_debug_{job_id}.html for debugging")
            return {
                "success": False,
                "message": "Could not find message link on job page"
            }
        
        # Construct the full message URL
        if message_link.startswith('/'):
            message_url = f"https://useme.com{message_link}"
        else:
            message_url = message_link
            
        logger.info(f"Using message URL: {message_url}")
        
        # Get the page with the form
        response = poster.session.get(message_url, headers=poster.headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get message form. Status code: {response.status_code}")
            return {
                "success": False,
                "message": f"Error accessing message form: Status {response.status_code}"
            }
        
        # Save debug information
        with open(f"message_form_debug_{job_id}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Saved message form HTML to message_form_debug_{job_id}.html for debugging")
        
        # Extract CSRF token
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            logger.error("No CSRF token found in the page")
            return {
                "success": False,
                "message": "No CSRF token found"
            }
        
        csrf_token = csrf_token.get('value')
        
        # Check if we're logged in
        if "login" in response.text.lower() and "zaloguj się" in response.text.lower():
            logger.error("Not logged in. Please update cookies.")
            return {
                "success": False,
                "message": "Not logged in. Please update cookies."
            }
        
        # Prepare form data
        form_data = {
            'csrfmiddlewaretoken': csrf_token,
            'content': message_content,
        }
        
        # Check if there's a subject field that needs to be included
        subject_input = soup.find('input', {'name': 'subject'})
        if subject_input and subject_input.get('value'):
            form_data['subject'] = subject_input.get('value')
        
        # Add required formset fields for file attachments
        formset_fields = [
            ('files-TOTAL_FORMS', '0'),
            ('files-INITIAL_FORMS', '0'),
            ('files-MIN_NUM_FORMS', '0'),
            ('files-MAX_NUM_FORMS', '1000')
        ]
        
        # Check if these fields exist in the form and add them
        for field_name, default_value in formset_fields:
            input_field = soup.find('input', {'name': field_name})
            if input_field:
                form_data[field_name] = input_field.get('value', default_value)
            else:
                # Add it anyway as it's likely required
                form_data[field_name] = default_value
                
        # Look for any other hidden inputs that might be required
        for hidden_input in soup.find_all('input', {'type': 'hidden'}):
            name = hidden_input.get('name')
            if name and name not in form_data and name != 'csrfmiddlewaretoken':
                form_data[name] = hidden_input.get('value', '')
        
        # Submit the form
        logger.info("Submitting message form...")
        headers = poster.headers.copy()
        headers['Referer'] = message_url
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Origin'] = 'https://useme.com'
        
        response = poster.session.post(
            message_url,
            data=form_data,
            headers=headers,
            allow_redirects=True
        )
        
        logger.info(f"Got response. Status code: {response.status_code}, URL: {response.url}")
        
        # Save response for debugging
        with open(f"message_response_debug_{job_id}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Saved response HTML to message_response_debug_{job_id}.html for debugging")
        
        # Check for success (usually a redirect to the thread page)
        if response.status_code == 200 and ("thread" in response.url or "threads" in response.url) and "compose" not in response.url:
            logger.info(f"Redirected to: {response.url} - message sent successfully")
            return {
                "success": True,
                "message": "Message sent successfully"
            }
        # Check for success by redirection to main messages page
        elif response.status_code == 200 and response.url == "https://useme.com/pl/mesg/":
            logger.info(f"Redirected to main messages page - This usually means the message was sent successfully")
            return {
                "success": True,
                "message": "Message sent successfully"
            }
        # Check for success message in response
        elif response.status_code == 200 and ("Wiadomość została wysłana" in response.text or "message has been sent" in response.text):
            logger.info("Found success message in response!")
            return {
                "success": True,
                "message": "Message sent successfully"
            }
        else:
            # Check for error messages
            soup = BeautifulSoup(response.text, 'html.parser')
            error_msgs = soup.select('.errorlist li')
            if not error_msgs:
                error_msgs = soup.select('.alert-danger')
            errors = [msg.text for msg in error_msgs] if error_msgs else []
            
            if errors:
                error_message = f"Form errors: {', '.join(errors)}"
                logger.error(error_message)
            else:
                error_message = f"Unknown error. Status: {response.status_code}, URL: {response.url}"
            
            logger.error(f"ERROR: {error_message}")
            return {
                "success": False,
                "message": error_message
            }
    
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Exception: {str(e)}"
        }
