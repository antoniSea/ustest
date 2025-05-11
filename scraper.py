# scraper.py

import argparse
import csv
import json
import os
import time
import sys
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import hashlib
from database import Database
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UsemeScraper:
    def __init__(self, base_url="https://useme.com/pl/jobs/", output_format="csv", avatars_base_dir="avatars", db=None):
        self.base_url = base_url
        self.output_format = output_format
        self.jobs = []
        self.db = db or Database()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        # Utwórz katalog na avatary, jeśli nie istnieje
        self.avatars_dir = avatars_base_dir # Use the passed directory for avatars
        if not os.path.exists(self.avatars_dir):
            os.makedirs(self.avatars_dir)
            logger.info(f"Utworzono katalog '{self.avatars_dir}' na avatary")

    def fetch_page(self, url):
        """Pobiera zawartość strony HTML."""
        max_retries = 3
        retry_count = 0
        retry_delay = 2
        
        while retry_count < max_retries:
            try:
                logger.info(f"Próba {retry_count + 1} pobrania strony: {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # Check if we got a valid HTML response
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type.lower():
                    logger.warning(f"Ostrzeżenie: Nieoczekiwany typ zawartości: {content_type}")
                
                # Check if the response actually contains HTML content
                if not response.text or len(response.text) < 1000:
                    logger.warning(f"Ostrzeżenie: Podejrzanie krótka odpowiedź ({len(response.text)} bajtów)")
                    # If empty or suspiciously short, retry
                    if len(response.text) < 500:
                        retry_count += 1
                        time.sleep(retry_delay)
                        continue
                
                return response.text
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Błąd połączenia podczas pobierania strony {url}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ponowna próba za {retry_delay} sekundy...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout podczas pobierania strony {url}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ponowna próba za {retry_delay} sekundy...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except requests.RequestException as e:
                logger.error(f"Błąd podczas pobierania strony {url}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ponowna próba za {retry_delay} sekundy...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd podczas pobierania strony {url}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ponowna próba za {retry_delay} sekundy...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        logger.error(f"Nie udało się pobrać strony {url} po {max_retries} próbach.")
        return None

    def download_avatar(self, avatar_url, username):
        """Pobiera avatar użytkownika i zapisuje go na dysku. Zwraca względną ścieżkę."""
        if not avatar_url or "empty-neutral.svg" in avatar_url:
            return None
        
        try:
            filename_hash = hashlib.md5((username + avatar_url).encode()).hexdigest()
            parsed_url = urlparse(avatar_url)
            path = unquote(parsed_url.path)
            extension = os.path.splitext(path)[1]
            if not extension or len(extension) > 5: # Basic check for valid extension
                extension = ".jpg"
            
            avatar_filename = f"{username.replace(' ', '_').replace('/', '_')}_{filename_hash}{extension}"
            # Ensure avatar_filename is filesystem-safe
            avatar_filename = re.sub(r'[^\w\.-]', '_', avatar_filename)

            avatar_path_on_disk = os.path.join(self.avatars_dir, avatar_filename)
            # Relative path for web display (assuming avatars_dir is served at /avatars by Flask)
            # The web path will be just the filename, as Flask will serve it from the AVATARS_FULL_PATH
            avatar_web_path_segment = avatar_filename # This will be used in url_for('serve_avatar', filename=...)

            if os.path.exists(avatar_path_on_disk):
                logger.info(f"Avatar dla {username} już istnieje: {avatar_path_on_disk}")
                return avatar_web_path_segment # Return filename for web path
            
            response = requests.get(avatar_url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(avatar_path_on_disk, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Zapisano avatar dla {username}: {avatar_path_on_disk}")
            return avatar_web_path_segment # Return filename for web path
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania avatara dla {username} ({avatar_url}): {e}")
            return None

    def download_attachment(self, attachment_url, filename):
        """Pobiera załącznik i zapisuje go na dysku. Zwraca względną ścieżkę."""
        if not attachment_url:
            return None
        
        try:
            # Przygotuj nazwę pliku (użyj oryginalnej nazwy, jeśli to możliwe)
            if not filename or len(filename) < 3:
                parsed_url = urlparse(attachment_url)
                path = unquote(parsed_url.path)
                filename = os.path.basename(path)
            
            # Usuń niebezpieczne znaki z nazwy pliku
            safe_filename = re.sub(r'[^\w\.-]', '_', filename)
            
            # Zapewnij unikalność nazwy pliku
            filename_hash = hashlib.md5(attachment_url.encode()).hexdigest()[:8]
            attachment_filename = f"{filename_hash}_{safe_filename}"
            
            # Stwórz katalog attachments, jeśli nie istnieje
            attachments_dir = "attachments"
            os.makedirs(attachments_dir, exist_ok=True)
            
            attachment_path_on_disk = os.path.join(attachments_dir, attachment_filename)
            attachment_web_path = os.path.join(attachments_dir, attachment_filename)
            
            # Sprawdź, czy plik już istnieje
            if os.path.exists(attachment_path_on_disk):
                logger.info(f"Załącznik już istnieje: {attachment_path_on_disk}")
                return attachment_web_path
            
            # Pobierz plik
            logger.info(f"Pobieranie załącznika: {attachment_url}")
            response = requests.get(attachment_url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Zapisz plik
            with open(attachment_path_on_disk, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Zapisano załącznik: {attachment_path_on_disk}")
            return attachment_web_path
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania załącznika ({attachment_url}): {e}")
            return None

    def parse_job_listings(self, html):
        """Parsuje ogłoszenia z HTML."""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        new_jobs = []
        
        job_articles = soup.find_all('article', class_='job')
        logger.info(f"Znaleziono {len(job_articles)} ogłoszeń na stronie")
        
        for article in job_articles:
            try:
                username_elem = article.find('strong')
                username = username_elem.get_text().strip() if username_elem else "Nieznany"
                
                avatar_elem = article.select_one('.user_avatar img')
                avatar_url_source = None
                avatar_filename_for_web = None # Will store just the filename
                if avatar_elem:
                    avatar_url_source = avatar_elem.get('src') or avatar_elem.get('data-src')
                    if avatar_url_source:
                        if avatar_url_source.startswith('//'):
                            avatar_url_source = 'https:' + avatar_url_source
                        elif avatar_url_source.startswith('/'):
                            # Correctly form absolute URL if relative
                            if not avatar_url_source.startswith("https://useme.com"):
                                avatar_url_source = 'https://useme.com' + avatar_url_source
                        
                        avatar_filename_for_web = self.download_avatar(avatar_url_source, username)
                
                title_elem = article.find('a', class_='job__title-link')
                title = title_elem.get_text().strip() if title_elem else "Brak tytułu"
                job_url_path = title_elem['href'] if title_elem and title_elem.has_attr('href') else ""
                
                description_elem = article.select_one('.job__content p')
                description = description_elem.get_text().strip() if description_elem else "Brak opisu"
                
                budget_elem = article.select_one('.job__budget-value')
                budget = budget_elem.get_text().strip() if budget_elem else "Brak budżetu"
                
                category_elem = article.select_one('.job__category p')
                category = category_elem.get_text().strip() if category_elem else "Brak kategorii"
                
                offers_elem = article.select_one('.job__header-details--offers span:nth-of-type(2)')
                offers = offers_elem.get_text().strip() if offers_elem else "0"
                
                date_elem = article.select_one('.job__header-details--date span:nth-of-type(2) span')
                expiry_date = date_elem.get_text().strip() if date_elem else "Nieznana"
                
                full_url = "https://useme.com" + job_url_path if job_url_path.startswith('/') else job_url_path
                
                job = {
                    "username": username,
                    "title": title,
                    "short_description": description,
                    "budget": budget,
                    "category": category,
                    "offers": offers,
                    "expiry_date": expiry_date,
                    "url": full_url,
                    "avatar_url_source": avatar_url_source,
                    "avatar_filename_for_web": avatar_filename_for_web # Store just the filename
                }
                
                # Check if job already exists in database before adding
                job_id = self.db.extract_job_id_from_url(full_url)
                if job_id:
                    existing_job = self.db.get_job_by_id(job_id)
                    if not existing_job:
                        new_jobs.append(job)
                    else:
                        logger.info(f"Pominięto duplikat zlecenia: {title} (ID: {job_id})")
                else:
                    # If we can't extract an ID, add it anyway
                    new_jobs.append(job)
                
            except Exception as e:
                logger.error(f"Błąd podczas parsowania ogłoszenia: {e}")
        
        return new_jobs

    def get_job_details(self, job):
        """Pobiera szczegóły ogłoszenia."""
        logger.info(f"Pobieranie szczegółów dla: {job['title']}")
        
        html = self.fetch_page(job['url'])
        if not html:
            logger.error(f"Nie udało się pobrać szczegółów dla: {job['title']}")
            return job
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Get full description
            full_desc_elem = soup.select_one('.job-details__main-desc .text')
            full_description = ""
            
            if full_desc_elem:
                # Get all paragraphs in the text div
                paragraphs = full_desc_elem.find_all('p')
                full_description = "\n".join([p.get_text().strip() for p in paragraphs])
            
            # Get extra details
            extra_details = {}
            extra_section = soup.select_one('.job-details__main-desc .extra')
            if extra_section:
                detail_blocks = extra_section.select('.block')
                for block in detail_blocks:
                    title_elem = block.select_one('.title')
                    answer_elem = block.select_one('.answer')
                    if title_elem and answer_elem:
                        title = title_elem.get_text().strip().rstrip(':')
                        answer = answer_elem.get_text().strip()
                        extra_details[title] = answer
            
            # Get requirements if available
            requirements_elem = soup.select_one('.requirements')
            requirements = requirements_elem.get_text().strip() if requirements_elem else ""
            
            # Check for attachments
            attachments = []
            attachments_section = soup.select_one('.job-attachments')
            if attachments_section:
                attachment_links = attachments_section.select('a')
                for link in attachment_links:
                    href = link.get('href', '')
                    name = link.get_text().strip()
                    if href and name:
                        # Pobierz załącznik
                        local_path = self.download_attachment(href, name)
                        attachments.append({
                            "name": name, 
                            "url": href,
                            "local_path": local_path
                        })
            
            # Update job with additional details
            job.update({
                "full_description": full_description,
                "requirements": requirements,
                "attachments": attachments,
                "extra_details": json.dumps(extra_details, ensure_ascii=False) if extra_details else "{}"
            })
            
            # Store job in the database using the enhanced method
            self.save_job_with_details(job)
            
            return job
        except Exception as e:
            logger.error(f"Błąd podczas pobierania szczegółów dla {job['title']}: {e}")
            import traceback
            traceback.print_exc()
            return job

    def get_total_pages(self):
        """Pobiera liczbę dostępnych stron z ogłoszeniami."""
        try:
            html = self.fetch_page(self.base_url)
            if not html:
                logger.error("Nie udało się pobrać strony głównej.")
                return 1  # Assume at least one page
            
            soup = BeautifulSoup(html, 'html.parser')
            pagination = soup.select_one('.pagination-component')
            
            if not pagination:
                logger.warning("Nie znaleziono komponentu paginacji.")
                return 1  # Assume at least one page
            
            # Look for the last page number
            last_page = 1
            page_links = pagination.find_all('a')
            
            for link in page_links:
                href = link.get('href', '')
                if 'page=' in href:
                    page_num_match = re.search(r'page=(\d+)', href)
                    if page_num_match:
                        page_num = int(page_num_match.group(1))
                        last_page = max(last_page, page_num)
            
            logger.info(f"Znaleziono {last_page} stron z ogłoszeniami.")
            return last_page
        except Exception as e:
            logger.error(f"Błąd podczas określania liczby stron: {e}")
            return 1  # Assume at least one page

    def scrape(self, max_pages=None, start_page=1, last_n_pages=None, fetch_details=True):
        """
        Scrapuje ogłoszenia z Useme.
        
        Args:
            max_pages (int, optional): Maksymalna liczba stron do przejrzenia.
            start_page (int, optional): Strona początkowa. Domyślnie 1.
            last_n_pages (int, optional): Scrapuj tylko ostatnie N stron.
            fetch_details (bool, optional): Czy pobierać szczegóły ogłoszeń. Domyślnie True.
        """
        self.jobs = []  # Reset jobs list
        total_pages = 10
        
        if last_n_pages:
            start_page = max(1, total_pages - last_n_pages + 1)
            logger.info(f"Pobieranie ostatnich {last_n_pages} stron, począwszy od strony {start_page}.")
        
        if max_pages:
            end_page = min(total_pages, start_page + max_pages - 1)
        else:
            end_page = total_pages
    
        logger.info(f"Rozpoczynam scrapowanie stron od {start_page} do {end_page}.")
        new_jobs_count = 0
        
        for page in range(start_page, end_page + 1):
            try:
                page_url = f"{self.base_url}?page={page}"
                logger.info(f"Pobieram stronę {page} z {end_page}: {page_url}")
                
                html = self.fetch_page(page_url)
                if not html:
                    logger.error(f"Nie udało się pobrać strony {page}. Przechodzę do następnej.")
                    continue
                
                # Parse job listings
                page_jobs = self.parse_job_listings(html)
                
                if fetch_details:
                    # Get details for each job
                    for i, job in enumerate(page_jobs):
                        logger.info(f"Pobieranie szczegółów {i+1}/{len(page_jobs)} dla strony {page}")
                        self.get_job_details(job)
                        
                        # Store job in database
                        job_id = self.db.extract_job_id_from_url(job['url'])
                        if job_id and self.db.store_job(job):
                            new_jobs_count += 1
                        
                        # Avoid overloading the server
                        time.sleep(1)
                else:
                    # Store basic job information without details
                    for job in page_jobs:
                        job_id = self.db.extract_job_id_from_url(job['url'])
                        if job_id and self.db.store_job(job):
                            new_jobs_count += 1
                    
                # Add jobs to the list
                self.jobs.extend(page_jobs)
                
                logger.info(f"Zakończono przetwarzanie strony {page}. Znaleziono {len(page_jobs)} nowych ogłoszeń.")
                
                # Small delay between pages
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Błąd podczas scrapowania strony {page}: {e}")
        
        logger.info(f"Zakończono scrapowanie. Dodano {new_jobs_count} nowych ogłoszeń.")
        
        # Export data to JSON (for presentation purposes)
        if self.jobs:
            self.export_data()
            
        return new_jobs_count

    def export_to_csv(self, filename="useme_jobs.csv"):
        """Eksportuje dane do pliku CSV."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if not filename.endswith('.csv'):
            filename = f"{filename}_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Define CSV headers
                fieldnames = [
                    'username', 'title', 'short_description', 'budget', 
                    'category', 'offers', 'expiry_date', 'url', 
                    'avatar_url_source', 'avatar_filename_for_web',
                    'full_description', 'requirements'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for job in self.jobs:
                    writer.writerow(job)
                
            logger.info(f"Dane zostały wyeksportowane do {filename}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas eksportu do CSV: {e}")
            return False

    def export_to_json(self, filename="useme_jobs.json"):
        """Eksportuje dane do pliku JSON."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.jobs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dane zostały wyeksportowane do {filename}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas eksportu do JSON: {e}")
            return False

    def export_data(self, filename=None):
        """Eksportuje dane w wybranym formacie."""
        if not self.jobs:
            logger.warning("Brak danych do wyeksportowania.")
            return False
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            if self.output_format.lower() == 'csv':
                filename = f"useme_jobs_{timestamp}.csv"
            else:
                filename = "useme_jobs.json"  # For presentation, keep a consistent name
        
        if self.output_format.lower() == 'csv':
            return self.export_to_csv(filename)
        else:
            return self.export_to_json(filename)

    def save_job_with_details(self, job):
        """Zapisuje zlecenie w bazie danych z dodatkowym logowaniem."""
        try:
            # Extract job ID from URL for better logging
            job_id = self.db.extract_job_id_from_url(job.get('url', ''))
            if job_id:
                job['job_id'] = job_id
                logger.info(f"Znaleziono ID zlecenia: {job_id} dla {job.get('title', '')}")
            else:
                logger.warning(f"Nie można wyodrębnić ID zlecenia z URL: {job.get('url', '?')}")
            
            # Try to store the job
            result = self.db.store_job(job)
            if result:
                logger.info(f"Zapisano nowe zlecenie w bazie: {job.get('title', '?')} (ID: {job_id})")
            else:
                logger.info(f"Zlecenie już istnieje w bazie: {job.get('title', '?')} (ID: {job_id})")
            
            return result
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania zlecenia do bazy danych: {str(e)}")
            return None

def schedule_next_scrape(db):
    """Schedule the next scrape 5 minutes from now"""
    next_run_time = datetime.now() + timedelta(minutes=5)
    db.schedule_scrape_task(next_run_time)
    logger.info(f"Zaplanowano kolejne scrapowanie na {next_run_time.isoformat()}")

def process_pending_tasks(db):
    """Process any pending tasks in the queue"""
    current_time = datetime.now()
    pending_tasks = db.get_pending_tasks(current_time)
    
    if not pending_tasks:
        logger.info("Brak zadań do wykonania")
        return
    
    for task in pending_tasks:
        try:
            task_id = task['id']
            task_type = task['task_type']
            parameters = json.loads(task['parameters']) if task['parameters'] else {}
            
            logger.info(f"Wykonywanie zadania {task_id} typu {task_type}")
            
            if task_type == 'scrape':
                # Update task status to 'processing'
                db.update_task_status(task_id, 'processing', current_time)
                
                # Create scraper and run it
                max_pages = parameters.get('max_pages', 3)
                start_page = parameters.get('start_page', 1)
                
                scraper = UsemeScraper(db=db)
                scraper.scrape(max_pages=max_pages, start_page=start_page)
                
                # Update task status to 'completed'
                db.update_task_status(task_id, 'completed', datetime.now())
                
                # Schedule next task
                schedule_next_scrape(db)
            else:
                logger.warning(f"Nieznany typ zadania: {task_type}")
                db.update_task_status(task_id, 'failed', current_time)
                
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania zadania {task['id']}: {e}")
            try:
                db.update_task_status(task['id'], 'failed', current_time)
            except Exception as db_error:
                logger.error(f"Nie można zaktualizować statusu zadania: {db_error}")

def main():
    """Główna funkcja programu."""
    parser = argparse.ArgumentParser(description="Useme Job Scraper")
    parser.add_argument('--output', choices=['csv', 'json'], default='json',
                       help='Format pliku wyjściowego (csv lub json). Domyślnie: json')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maksymalna liczba stron do scrapowania')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Strona początkowa. Domyślnie: 1')
    parser.add_argument('--last-pages', type=int, default=None,
                       help='Scrapuj tylko ostatnie N stron')
    parser.add_argument('--no-details', action='store_true',
                       help='Nie pobieraj szczegółów ogłoszeń')
    parser.add_argument('--avatars-dir', type=str, default='avatars',
                       help='Katalog na avatary. Domyślnie: avatars')
    parser.add_argument('--schedule', action='store_true',
                       help='Zaplanuj zadanie scrapowania co 5 minut')
    parser.add_argument('--process-queue', action='store_true',
                       help='Przetwórz zaplanowane zadania z kolejki')
    
    args = parser.parse_args()
    
    # Connect to database
    db = Database()
    
    if args.schedule:
        # Schedule a scraping task
        next_run_time = datetime.now() + timedelta(minutes=5)
        parameters = {
            'max_pages': args.max_pages,
            'start_page': args.start_page
        }
        db.schedule_scrape_task(next_run_time, parameters)
        logger.info(f"Zaplanowano zadanie scrapowania na {next_run_time.isoformat()}")
        return
    
    if args.process_queue:
        # Process pending tasks in the queue
        process_pending_tasks(db)
        return
    
    # Regular scraping
    try:
        # Create and run scraper
        scraper = UsemeScraper(
            output_format=args.output,
            avatars_base_dir=args.avatars_dir,
            db=db
        )
        
        logger.info("Rozpoczynam scrapowanie ofert z Useme...")
        scraper.scrape(
            max_pages=args.max_pages,
            start_page=args.start_page,
            last_n_pages=args.last_pages,
            fetch_details=not args.no_details
        )
        
        logger.info(f"Znaleziono {len(scraper.jobs)} ogłoszeń.")
        
        # Schedule next scrape if this was a regular run
        schedule_next_scrape(db)
        
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika. Kończenie pracy...")
    except Exception as e:
        logger.error(f"Wystąpił błąd: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()