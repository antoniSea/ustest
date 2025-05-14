import os
import json
import csv
import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
import time
from datetime import datetime
import re
import unicodedata
from useme_post_proposal import UsemeProposalPoster
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from urllib.parse import quote_plus
from database import Database
import logging
from extract_useme_email import extract_employer_email
from proxy import get_gemini_response
import configparser


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # Create default config if it doesn't exist
    if not os.path.exists(config_file):
        config['API'] = {
            'gemini_api_key': 'AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM',
            'gemini_model': 'gemini-2.5-pro-exp-03-25'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
    
    config.read(config_file)
    return config

# Get API config
config = load_config()
API_KEY = config['API'].get('gemini_api_key', "AIzaSyDh3EMORXEvvVpeuT9QKVUlKe1_uBvwkpM")
MODEL = config['API'].get('gemini_model', "gemini-2.5-pro-exp-03-25")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

console = Console()

def get_prompt_from_db(prompt_type):
    """Get the appropriate prompt from the database"""
    db = Database()
    prompt_data = db.get_default_prompt(prompt_type)
    
    if prompt_data and prompt_data.get('content'):
        return prompt_data.get('content')
    
    return None

def generate_proposal(job_description, client_info="", budget="", timeline="", additional_requirements="", project_slug="", research_data=None):
    """Generate a proposal for a job based on the provided information and research data."""
    # Include research data in the prompt if available
    research_info = ""
    if research_data:
        research_info = f"""
        Wyniki researchu rynkowego:
        - Typowy zakres cenowy: {research_data.get('market_price_range', 'Brak danych')}
        - Typowy czas realizacji: {research_data.get('typical_timeline', 'Brak danych')}
        - Rekomendowane technologie: {research_data.get('recommended_technologies', 'Brak danych')}
        - Potencjalne wyzwania: {research_data.get('potential_challenges', 'Brak danych')}
        - Podsumowanie: {research_data.get('summary', 'Brak danych')}
        """
    
    # Try to get prompt from database first
    custom_prompt = get_prompt_from_db('proposal')
    
    if custom_prompt:
        # Replace placeholders in the custom prompt
        prompt = custom_prompt
        prompt = prompt.replace("{job_description}", job_description)
        prompt = prompt.replace("{client_info}", client_info or "")
        prompt = prompt.replace("{budget}", budget or "")
        prompt = prompt.replace("{timeline}", timeline or "")
        prompt = prompt.replace("{additional_requirements}", additional_requirements or "")
        prompt = prompt.replace("{project_slug}", project_slug or "")
        prompt = prompt.replace("{research_info}", research_info)
    else:
        # Use default prompt
        prompt = f"""
        Nazywasz się Antoni Seba, jesteś menagerem projektów w Soft Synergy, specjalizującym się w skutecznym dostarczaniu rozwiązań IT, które zwiększają przychody klientów.

        technologie które używamy: 
        - React
        - Woocomerce
        - Elementor
        - PHP
        - MySQL
        - Docker
        - Linux
        - Nginx
        - flutter
        - react native
        - python
        - django
        
        Wygeneruj wyjątkowo przekonującą, profesjonalną propozycję dla zlecenia poniżej. Użyj strategii persuazji zaczerpniętych z METODY SPIN SELLING oraz metodologii AIDA (Attention, Interest, Desire, Action):
        
        Opis zlecenia: {job_description}
        
        {f"Informacje o kliencie: {client_info}" if client_info else ""}
        {f"Budżet: {budget}" if budget else ""}
        {f"Harmonogram: {timeline}" if timeline else ""}
        {f"Dodatkowe wymagania: {additional_requirements}" if additional_requirements else ""}
        
        {research_info}
        
        Propozycja MUSI zawierać:
        1. Magnetyzujące powitanie, które NATYCHMIAST wywołuje zainteresowanie (1-2 krótkie zdania)
        2. Szczegółową diagnozę problemów, które klient próbuje rozwiązać (dopasuj do opisu zlecenia)
        3. Podkreślenie konsekwencji NIE rozwiązania tych problemów (budowanie pilności i wykazanie głębokiego zrozumienia)
        4. Konkretną propozycję rozwiązania zawierającą wycenę i termin (bold: **3000 PLN, czas realizacji: 14 dni**)
        5. Precyzyjne uzasadnienie WARTOŚCI oferty (nie ceny) - pokaż ROI
        6. Silne elementy budujące zaufanie i ograniczające postrzegane ryzyko
        7. Link do wizualnej prezentacji: prezentacje.soft-synergy.com/{project_slug}
        8. Bezpośrednie wezwanie do działania z przejawami ograniczoności czasowej (techniki scarcity)
        
        KLUCZOWE ZASADY PSYCHOLOGII SPRZEDAŻY:
        - Pisz w języku polskim, zawsze odnoszącym się do KORZYŚCI klienta
        - Maksymalnie 200 słów podzielonych krótkimi paragrafami
        - Używaj elementów social proof (np. "97% naszych klientów zgłasza wzrost konwersji o minimum 23%")
        - Stosuj zasadę wzajemności oferując KONKRETNĄ wartość już w propozycji
        - Wdrażaj fundamenty neuromarketingu - użyj zwrotów aktywujących obszary mózgu odpowiedzialne za decyzje zakupowe
        - Wykorzystaj FOMO (Fear Of Missing Out) i ograniczoną dostępność terminu
        - Wycena musi być wyraźnie wyodrębniona w tekście (użyj **pogrubienia**)
        - Format musi być łatwo skanowalny wzrokiem - krótkie paragrafy, punktory, pogrubienia
        - Podkreśl unikalny charakter oferty - dlaczego to TY powinieneś realizować to zlecenie
        - KONIECZNIE umieść informację o przygotowanej prezentacji wizualnej z linkiem: prezentacje.soft-synergy.com/{project_slug}
        - Wzbudź natychmiastową wiarygodność używając konkretnych liczb, a nie zaokrągleń (np. "zwiększyliśmy konwersje o 27.3%" zamiast "około 30%")
        - Stosuj techniki NLP i framingu emocjonalnego, dopasowując ton do charakteru zlecenia

        Dane kontaktowe (umieść je na końcu w osobnych liniach):
        Email: info@soft-synergy.com 
        Strona: https://soft-synergy.com
        Osoba kontaktowa: Antoni Seba
        Telefon: 576 205 389
        
        """
        
        # Apply industry-specific enhancements to the prompt
        prompt = apply_industry_specific_prompt(job_description, additional_requirements, prompt)
    
    try:
        return get_gemini_response(prompt)
        
    except Exception as e:
        logger.error(f"Błąd generowania propozycji: {str(e)}")
        return f"Błąd generowania propozycji: {str(e)}"

def generate_industry_specific_prompt(industry, job_description):
    """
    Generate industry-specific prompt enhancements based on the job's industry/category.
    This helps tailor the AI's responses to specific industries for better conversion rates.
    """
    # Try to get custom industry prompt from database first
    custom_industry_prompt = get_prompt_from_db(f'industry_{industry.lower()}')
    if custom_industry_prompt:
        return custom_industry_prompt
    
    # Default industry-specific prompts
    industry_prompts = {
        "e-commerce": f"""
        Dla tego projektu e-commerce zastosuj następujące podejście:
        
        1. Podkreśl DOŚWIADCZENIE w zwiększaniu konwersji sklepów online (min. +35%)
        2. Wymień kluczowe metryki, które monitorujemy (CAC, LTV, AOV, CR)
        3. Odnieś się do optymalizacji ścieżki zakupowej i redukcji porzuceń koszyka
        4. Wspomnij o WooCommerce/Shopify jako sprawdzonych platformach
        5. Podkreśl nasze doświadczenie w integracji z systemami płatności i logistyki
        6. Zaproponuj analizę koszyków i zachowań użytkowników za pomocą heatmap
        7. Zaznacz rozumienie procesów zwiększania średniej wartości zamówienia
        8. Podkreśl umiejętność wdrożenia programów lojalnościowych
        
        Kluczowe korzyści do podkreślenia: wzrost sprzedaży, optymalizacja konwersji, zwiększenie ruchu organicznego.
        """,
        
        "landing_page": f"""
        Dla tego projektu landing page zastosuj następujące podejście:
        
        1. Podkreśl nasze doświadczenie w ZWIĘKSZANIU KONWERSJI stron docelowych (+50-120%)
        2. Zaznacz wiedzę z zakresu psychologii decyzji i neuromarketingu
        3. Odnieś się do technik A/B testowania dla optymalizacji CTA
        4. Wspomnij o projektowaniu pod kątem maksymalizacji współczynnika konwersji
        5. Podkreśl rozumienie lejków sprzedażowych i mechanizmów lead generation
        6. Zaproponuj analizę User Experience i optymalizację czasu ładowania (<1.5s)
        7. Wspomnij o strategiach budowania zaufania (social proof, testimonials)
        8. Podkreśl umiejętność integracji z narzędziami analitycznymi i marketingowymi
        
        Kluczowe korzyści do podkreślenia: wzrost konwersji, lepszy ROI z kampanii, więcej jakościowych leadów.
        """,
        
        "aplikacja_mobilna": f"""
        Dla tego projektu aplikacji mobilnej zastosuj następujące podejście:
        
        1. Podkreśl nasze doświadczenie w tworzeniu ANGAŻUJĄCYCH aplikacji z wysokimi ocenami (4.8+)
        2. Zaznacz wiedzę z zakresu Flutter i React Native dla wieloplatformowego rozwoju
        3. Odnieś się do procesu projektowania UX/UI dla maksymalnej retencji użytkowników
        4. Wspomnij o strategiach monetyzacji aplikacji i analityce zachowań
        5. Podkreśl rozumienie procesów publikacji w App Store i Google Play
        6. Zaproponuj implementację funkcji offline i optymalizację wydajności
        7. Wspomnij o zabezpieczeniach RODO/GDPR i bezpieczeństwie danych
        8. Podkreśl doświadczenie w tworzeniu aplikacji, które się skalują z rosnącą bazą użytkowników
        
        Kluczowe korzyści do podkreślenia: wysokie oceny użytkowników, niski współczynnik odrzuceń, efektywna monetyzacja.
        """,
        
        "system_crm": f"""
        Dla tego projektu systemu CRM/ERP zastosuj następujące podejście:
        
        1. Podkreśl nasze doświadczenie w AUTOMATYZACJI procesów biznesowych (+40% efektywności)
        2. Zaznacz wiedzę z zakresu integracji systemów i przepływu danych
        3. Odnieś się do tworzenia intuicyjnych interfejsów dla złożonych systemów
        4. Wspomnij o dostosowywaniu systemów do specyficznych procesów klienta
        5. Podkreśl rozumienie bezpieczeństwa danych i zgodności z regulacjami
        6. Zaproponuj implementację raportowania i dashboardów biznesowych
        7. Wspomnij o skalowalności rozwiązania wraz z rozwojem firmy
        8. Podkreśl doświadczenie w szkoleniach i onboardingu nowych użytkowników
        
        Kluczowe korzyści do podkreślenia: oszczędność czasu pracowników, lepsza analiza danych, automatyzacja powtarzalnych zadań.
        """,
        
        "strona_firmowa": f"""
        Dla tego projektu strony firmowej zastosuj następujące podejście:
        
        1. Podkreśl nasze doświadczenie w budowaniu WIZERUNKOWYCH stron zwiększających wiarygodność
        2. Zaznacz wiedzę z zakresu SEO i pozycjonowania lokalnego
        3. Odnieś się do projektowania zgodnego z identyfikacją wizualną klienta
        4. Wspomnij o responsywności i dostosowaniu do urządzeń mobilnych
        5. Podkreśl umiejętność tworzenia angażujących treści i zrozumiałej architektury informacji
        6. Zaproponuj integrację z mediami społecznościowymi i narzędziami analitycznymi
        7. Wspomnij o optymalizacji szybkości ładowania i SEO technicznym
        8. Podkreśl umiejętność wdrożenia systemu CMS dla samodzielnej aktualizacji
        
        Kluczowe korzyści do podkreślenia: wzmocnienie marki, wyższa pozycja w Google, wzrost zapytań od klientów.
        """
    }
    
    # Try to match industry or return a default enhancement
    for key, prompt in industry_prompts.items():
        if key.lower() in industry.lower() or key.lower() in job_description.lower():
            return prompt
    
    # Default general enhancement if no specific industry matched
    return f"""
    Dla tego projektu zastosuj następujące podejście:
    
    1. Podkreśl nasze doświadczenie w podobnych projektach i technologiach
    2. Zaznacz konkretne mierzalne rezultaty osiągnięte dla poprzednich klientów
    3. Odnieś się do unikalnych wyzwań tego typu projektów i jak je przezwyciężamy
    4. Wspomnij o metodologii, która zapewnia terminowe dostarczenie i wysoką jakość
    5. Podkreśl wartość naszego rozwiązania w kontekście ROI dla klienta
    6. Zaproponuj dodatkową wartość, która wyróżnia naszą ofertę
    7. Wspomnij o procesie współpracy i komunikacji podczas projektu
    8. Podkreśl elastyczność i gotowość do dostosowania rozwiązania do konkretnych potrzeb
    
    Kluczowe korzyści do podkreślenia: efektywność kosztowa, wysokiej jakości rezultaty, przewaga konkurencyjna.
    """

def apply_industry_specific_prompt(job_description, category, prompt):
    """
    Apply industry-specific prompt enhancement to the main prompt based on job category
    """
    # Determine industry/category from job data
    industry = category.lower() if category else ""
    
    # If no clear category, try to infer from job description
    if not industry:
        # Common industry keywords to look for
        industry_keywords = {
            "e-commerce": ["sklep", "e-commerce", "ecommerce", "woocommerce", "shopify", "sprzedaż online", "koszyk"],
            "landing_page": ["landing page", "strona docelowa", "leadowa", "konwersja", "lead generation"],
            "aplikacja_mobilna": ["aplikacja mobilna", "aplikacja na telefon", "android", "ios", "flutter", "react native"],
            "system_crm": ["crm", "erp", "system zarządzania", "system dla firmy", "automatyzacja procesów"],
            "strona_firmowa": ["strona www", "strona internetowa", "wizytówka", "firma", "wizytówka internetowa"]
        }
        
        # Check for keywords in job description
        for key, keywords in industry_keywords.items():
            if any(keyword.lower() in job_description.lower() for keyword in keywords):
                industry = key
                break
    
    # Get industry-specific enhancements
    industry_enhancements = generate_industry_specific_prompt(industry, job_description)
    
    # Add industry-specific enhancements to the main prompt
    enhanced_prompt = f"{prompt}\n\nDODATKOWE WSKAZÓWKI DLA BRANŻY:\n{industry_enhancements}"
    
    return enhanced_prompt

def evaluate_relevance(job_description, client_info="", budget="", timeline="", additional_requirements=""):
    """Evaluate the relevance of a job for a software house on a scale from 1 to 10."""
    # Try to get prompt from database first
    custom_prompt = get_prompt_from_db('relevance')
    
    if custom_prompt:
        # Replace placeholders in the custom prompt
        prompt = custom_prompt
        prompt = prompt.replace("{job_description}", job_description)
        prompt = prompt.replace("{client_info}", client_info or "")
        prompt = prompt.replace("{budget}", budget or "")
        prompt = prompt.replace("{timeline}", timeline or "")
        prompt = prompt.replace("{additional_requirements}", additional_requirements or "")
    else:
        # Use default prompt
        prompt = f"""
        Dokonaj strategicznej analizy biznesowej poniższego zlecenia pod kątem potencjalnej wartości dla software house'u specjalizującego się w aplikacjach webowych, mobilnych i systemach e-commerce.
        
        Opis zlecenia: {job_description}
        
        {f"Informacje o kliencie: {client_info}" if client_info else ""}
        {f"Budżet: {budget}" if budget else ""}
        {f"Harmonogram: {timeline}" if timeline else ""}
        {f"Dodatkowe wymagania: {additional_requirements}" if additional_requirements else ""}
        
        KRYTERIA OCENY WARTOŚCI BIZNESOWEJ (skala 1-10):
        
        1. DOPASOWANIE TECHNOLOGICZNE - czy projekt pasuje do naszych kompetencji w React, PHP, Flutter, Python, WooCommerce?
        2. POTENCJAŁ DŁUGOTERMINOWY - czy zlecenie może prowadzić do stałej współpracy lub rozszerzeń projektu?
        3. PRESTIŻ I WARTOŚĆ REFERENCYJNA - czy projekt będzie atrakcyjnym case study dla przyszłych klientów?
        4. MARŻA I RENTOWNOŚĆ - czy budżet pozwala na wypracowanie satysfakcjonującej marży (min. 40%)?
        5. CZAS REALIZACJI VS. ZYSKOWNOŚĆ - czy stosunek wymaganego nakładu pracy do oczekiwanego wynagrodzenia jest korzystny?
        6. SKALOWALNOŚĆ TECHNOLOGII - czy technologia pozwala na efektywne wykorzystanie istniejących komponentów lub bibliotek?
        7. POTENCJAŁ POWTARZALNOŚCI - czy z projektu można wyprowadzić powtarzalne rozwiązanie dla innych klientów?
        8. RYZYKO WDROŻENIA - czy projekt niesie nadzwyczajne ryzyko opóźnień lub komplikacji?
        
        Przypisz wagę każdemu kryterium, uwzględniając specyfikę zlecenia, następnie oblicz średnią ważoną, gdzie:
        1 = Zlecenie kompletnie nieopłacalne lub niedopasowane
        5 = Zlecenie przeciętnie opłacalne, wymaga dokładnej kalkulacji
        10 = Zlecenie idealnie dopasowane, wysokomarżowe, o dużym potencjale długoterminowym
        
        UWAGA: Zwróć WYŁĄCZNIE finalną ocenę w postaci liczby całkowitej od 1 do 10, bez żadnych komentarzy czy wyjaśnień.
        """
    
    try:
        response = get_gemini_response(prompt)
        # Próba wyodrębnienia liczby z odpowiedzi
        relevance_score = re.search(r'\b([1-9]|10)\b', response)
        if relevance_score:
            return int(relevance_score.group(1))
        else:
            return 5  # Domyślna wartość w przypadku problemu z parsowaniem
    except Exception as e:
        logger.error(f"Błąd oceny relevance: {str(e)}")
        return 5  # Domyślna wartość w przypadku błędu

def generate_initials_avatar(client_info):
    """Generate a URL for an avatar with the client's initials when no real avatar is available."""
    if not client_info or client_info.strip() == "":
        # Default if no client info is provided
        return f"https://via.placeholder.com/150/4F46E5/FFFFFF?text=SS"
    
    # Extract initials (up to 2 characters)
    words = client_info.split()
    if len(words) >= 2:
        initials = words[0][0] + words[1][0]
    else:
        # If only one word, use first two letters or pad with a space
        if len(words[0]) >= 2:
            initials = words[0][:2]
        else:
            initials = words[0] + " "
    
    # Make uppercase
    initials = initials.upper()
    
    # URL encode the initials
    encoded_initials = quote_plus(initials)
    
    # Generate a placeholder with initials (blue background with white text)
    return f"https://via.placeholder.com/150/4F46E5/FFFFFF?text={encoded_initials}"

def generate_presentation_data(job_description, proposal, job_id="", client_info="", budget="", timeline="", additional_requirements="", client_logo_path="", research_data=None, employer_email=None):
    """Generate presentation data in JSON format for a job."""
    # Read the template data structure for presentations
    default_data = {}
    try:
        with open("templates/presentations/data.json", "r", encoding="utf-8") as f:
            default_data = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Błąd podczas wczytywania szablonu prezentacji: {str(e)}[/bold red]")
        # Create a minimal default structure based on the expected format
        default_data = {
            "site": {
                "companyName": "Soft Synergy",
                "pageTitle": "Propozycja Projektu",
                "currentYear": datetime.now().strftime("%Y")
            },
            "header": {
                "logoText": "Soft",
                "logoAccent": "Synergy",
                "navLinks": []
            },
            "hero": {
                "clientLogoSrc": generate_initials_avatar(client_info),
                "clientLogoAlt": "Logo Klienta",
                "titlePart1": "Propozycja Projektu dla",
                "titlePart2ClientName": client_info or "Klienta",
                "subtitle": "Opis projektu",
                "ctaButtonText": "Zobacz Szczegóły Oferty",
                "ctaButtonLink": "#understanding"
            }
        }

    # Check if this job has an avatar URL in the database
    avatar_url = None
    if job_id:
        try:
            # Import database here to avoid circular imports
            from database import Database
            db = Database()
            job = db.get_job_by_id(job_id)
            if job and job.get('avatar_url_source') and job.get('avatar_url_source') != "https://cdn.useme.com/1.20.4/images/avatar/empty-neutral.svg?v=1.20.4":
                avatar_url = job.get('avatar_url_source')
                console.print(f"[green]✓[/green] Znaleziono avatar klienta: {avatar_url}")
            else:
                # Generate an avatar with client initials
                avatar_url = generate_initials_avatar(client_info)
                console.print(f"[blue]ℹ[/blue] Wygenerowano avatar z inicjałami: {avatar_url}")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Nie udało się pobrać avatara klienta: {str(e)}")
            # Generate an avatar with client initials as fallback
            avatar_url = generate_initials_avatar(client_info)
            console.print(f"[blue]ℹ[/blue] Wygenerowano fallback avatar z inicjałami: {avatar_url}")
    else:
        # No job_id, generate avatar with client initials
        avatar_url = generate_initials_avatar(client_info)
        console.print(f"[blue]ℹ[/blue] Wygenerowano domyślny avatar z inicjałami: {avatar_url}")
    
    # Try to get prompt from database first
    custom_prompt = get_prompt_from_db('presentation')
    
    if custom_prompt:
        # Replace placeholders in the custom prompt
        prompt = custom_prompt
        prompt = prompt.replace("{job_description}", job_description)
        prompt = prompt.replace("{client_info}", client_info or "")
        prompt = prompt.replace("{budget}", budget or "")
        prompt = prompt.replace("{additional_requirements}", additional_requirements or "")
        prompt = prompt.replace("{employer_email}", employer_email or "")
        prompt = prompt.replace("{proposal}", proposal or "")
        prompt = prompt.replace("{job_id}", job_id or "")
        prompt = prompt.replace("{default_data}", json.dumps(default_data, ensure_ascii=False))
    else:
        # Use default prompt
        prompt = f"""
        Wygeneruj wysoce perswazyjne dane do prezentacji projektu, wykorzystujące naukowe badania neuromarketingowe i psychologię decyzji zakupowych. Dane muszą być w formacie JSON, zgodnie z podaną strukturą.
        
        Opis zlecenia: {job_description}
        {f"Informacje o kliencie: {client_info}" if client_info else ""}
        {f"Budżet: {budget}" if budget else ""}
        {f"Dodatkowe wymagania: {additional_requirements}" if additional_requirements else ""}
        {f"Email klienta: {employer_email}" if employer_email else ""}
        
        Propozycja, którą już przygotowaliśmy:
        {proposal}
        
        WYMAGANE ELEMENTY PSYCHOLOGICZNE W PREZENTACJI:
        1. KONTRASTUJĄCE SEKCJE PROBLEMÓW I ROZWIĄZAŃ - użyj języka bólu i przyjemności (pain vs. pleasure)
        2. SPOŁECZNY DOWÓD SŁUSZNOŚCI - zawrzyj przynajmniej dwa konkretne przykłady z liczbami/statystykami
        3. ZASADA AUTORYTETU - podkreśl ekspertyzę i doświadczenie zespołu
        4. STRATEGIA WYRAŹNYCH KORZYŚCI - formułuj wartość w kategoriach ROI i przewagi konkurencyjnej
        5. ELIMINACJA RYZYKA - uwzględnij gwarancję, jasny harmonogram i przewidywalne rezultaty
        6. BEZPOŚREDNI WPŁYW NA BIZNES - podkreśl jak rozwiązanie zwiększa przychody/obniża koszty
        7. WIZUALIZACJA SUKCESU - zawrzyj sekcje opisujące wyobrażalny scenariusz po wdrożeniu
        
        STRUKTURA ARGUMENTACJI:
        - Użyj formatu PROBLEM > IMPLIKACJE > ROZWIĄZANIE > WARTOŚĆ dla każdej kluczowej sekcji
        - Zastosuj strukturę social proof HISTORIA > LICZBY > WYNIK
        - Dodaj elementy wizualne wzmacniające przekaz w sekcji "features" i "benefits"
        - Stwórz złożone, wielopoziomowe pakiety cenowe zwiększające postrzeganą wartość
        - W sekcji "pricing" unikaj okrągłych kwot - użyj precyzyjnych liczb (np. 4999 zamiast 5000)
        
        WAŻNE STRATEGIE KONWERSJI:
        - Użyj konkretnych, mierzalnych liczb we wszystkich kluczowych sekcjach (wzrost konwersji o X%)
        - Wstaw przynajmniej jedno porównanie "przed i po" w sekcji zalet lub korzyści
        - Umieść minimum dwa pytania retoryczne wzmacniające zaangażowanie
        - Zastosuj techniki decoy pricing dla zwiększenia atrakcyjności głównej oferty
        - Wycena musi być wyrażona jako inwestycja z oczekiwanym zwrotem, nie jako koszt
        - Struktura zawiera trzy pakiety cenowe o różnej wartości, z wyraźnie oznaczonym pakietem rekomendowanym
        
        Zwróć kompletny, poprawny JSON zgodny DOKŁADNIE z podaną strukturą, zachowując wszystkie klucze i typy wartości.
        
        Przykładowy JSON (zachowaj dokładnie tę strukturę): {json.dumps(default_data, ensure_ascii=False)}
        """
    
    try:
        response = get_gemini_response(prompt)
        print(response)
        return 'sadasdadasd'
        # The response is already a string, no need to call .strip() on it
        response_text = response
        
        # First attempt: try to parse the whole response as JSON
        try:
            json_data = json.loads(response_text)
            console.print("[green]✓[/green] Poprawnie sparsowano JSON z odpowiedzi")
        except json.JSONDecodeError:
            console.print("[yellow]⚠[/yellow] Niepoprawny format JSON w odpowiedzi, próbuję wyodrębnić")
            
            # Second attempt: try to extract JSON from the response
            json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response_text)
            if not json_match:
                json_match = re.search(r'({[\s\S]*})', response_text)
                
            if json_match:
                try:
                    json_text = json_match.group(1).strip()
                    json_data = json.loads(json_text)
                    console.print("[green]✓[/green] Poprawnie wyodrębniono i sparsowano JSON z odpowiedzi")
                except json.JSONDecodeError:
                    console.print("[red]✗[/red] Nie udało się sparsować wyodrębnionego JSON")
                    # Create a customized structure based on content extraction from AI response
                    json_data = create_presentation_from_text(response_text, default_data, client_info, job_description, proposal)
                    console.print("[yellow]⚠[/yellow] Wygenerowano strukturę z tekstu odpowiedzi AI")
            else:
                console.print("[red]✗[/red] Nie znaleziono JSON w odpowiedzi")
                # Create a customized structure based on content extraction from AI response
                json_data = create_presentation_from_text(response_text, default_data, client_info, job_description, proposal)
                console.print("[yellow]⚠[/yellow] Wygenerowano strukturę z tekstu odpowiedzi AI")
        
        # Extract numeric price and timeline values for metadata only
        extracted_price = extract_price_from_proposal(proposal, budget)
        extracted_timeline_days = extract_timeline_from_proposal(proposal)
        
        # Add metadata fields for useme_id, price and timelineDays
        if 'useme_id' not in json_data and job_id:
            json_data['useme_id'] = job_id
            
        # Add metadata price as a simple number (for Useme proposal)
        json_data['price'] = extracted_price
            
        # Add metadata timelineDays as a simple number (for Useme proposal)
        json_data['timelineDays'] = extracted_timeline_days
            
        # Add employer_email if provided
        if employer_email and 'employer_email' not in json_data:
            json_data['employer_email'] = employer_email
            
        # Make sure price in pricing section is formatted as string with PLN
        if 'pricing' in json_data and 'packages' in json_data['pricing'] and len(json_data['pricing']['packages']) > 0:
            for package in json_data['pricing']['packages']:
                if isinstance(package.get('price'), (int, float)):
                    package['price'] = f"{package['price']},00 PLN brutto"
                
        # Make sure timeline section exists and has the proper structure
        if 'timeline' not in json_data or not isinstance(json_data['timeline'], dict):
            console.print("[yellow]⚠[/yellow] Brak lub nieprawidłowa sekcja timeline w wygenerowanym JSON, używam domyślnej")
            json_data['timeline'] = generate_timeline_section(proposal, job_description)
        
        # Ensure client name is set in hero section
        if 'hero' in json_data and client_info and not json_data['hero'].get('titlePart2ClientName'):
            json_data['hero']['titlePart2ClientName'] = client_info
        
        # If we have an avatar URL, update the clientLogoSrc in the hero section
        if avatar_url and 'hero' in json_data:
            json_data['hero']['clientLogoSrc'] = avatar_url
            json_data['hero']['clientLogoAlt'] = f"Logo {client_info or 'Klienta'}"
            console.print(f"[green]✓[/green] Ustawiono avatar klienta w prezentacji")
            
        return json_data
        
    except Exception as e:
        console.print(f"[bold red]Błąd generowania danych prezentacji: {str(e)}[/bold red]")
        # In case of any error, create a customized fallback structure with available data
        custom_fallback = create_presentation_from_text("", default_data, client_info, job_description, proposal)
        custom_fallback["useme_id"] = job_id
        custom_fallback["price"] = extract_price_from_proposal(proposal, budget)
        custom_fallback["timelineDays"] = extract_timeline_from_proposal(proposal)
        if employer_email:
            custom_fallback["employer_email"] = employer_email
        
        # If we have an avatar URL, update the clientLogoSrc in the hero section even for the custom fallback
        if avatar_url and 'hero' in custom_fallback:
            custom_fallback['hero']['clientLogoSrc'] = avatar_url
            custom_fallback['hero']['clientLogoAlt'] = f"Logo {client_info or 'Klienta'}"
            console.print(f"[green]✓[/green] Ustawiono avatar klienta w domyślnej prezentacji")
            
        return custom_fallback

def create_presentation_from_text(ai_response, template_data, client_info, job_description, proposal):
    """
    Create a customized presentation structure by extracting key information from AI response text.
    This is used as a fallback when JSON parsing fails.
    """
    # Start with a copy of the template
    custom_data = template_data.copy()
    
    # Set personalized hero section
    if 'hero' in custom_data:
        custom_data['hero']['titlePart2ClientName'] = client_info or "Klienta"
        
        # Extract subtitle/description from response or job_description
        if len(job_description) > 150:
            custom_data['hero']['subtitle'] = job_description[:147] + "..."
        else:
            custom_data['hero']['subtitle'] = job_description
    
    # Extract pricing information from the proposal
    extracted_price = extract_price_from_proposal(proposal)
    price_text = f"{extracted_price},00 PLN brutto"
    
    # Get timeline information
    timeline_days = extract_timeline_from_proposal(proposal)
    
    # Create a custom pricing section
    if 'pricing' not in custom_data:
        custom_data['pricing'] = {
            "title": "Pakiety Cenowe",
            "subtitle": "Wybierz pakiet dopasowany do Twoich potrzeb",
            "packages": []
        }
    
    # Create customized packages based on the extracted price
    package_base = int(extracted_price * 0.8)
    package_premium = int(extracted_price * 1.2)
    
    # Build packages with appropriate descriptions
    custom_data['pricing']['packages'] = [
        {
            "name": "Pakiet Podstawowy",
            "price": f"{package_base},00 PLN brutto",
            "description": "Realizacja podstawowego zakresu projektu",
            "features": ["Podstawowa funkcjonalność", "Wdrożenie rozwiązania", "Testy jakościowe"],
            "isPopular": False
        },
        {
            "name": "Pakiet Standardowy",
            "price": price_text,
            "description": "Kompletne rozwiązanie dostosowane do Twoich potrzeb",
            "features": ["Pełna funkcjonalność", "Wsparcie techniczne", "Testy i optymalizacja", "Dokumentacja"],
            "isPopular": True
        },
        {
            "name": "Pakiet Premium",
            "price": f"{package_premium},00 PLN brutto",
            "description": "Rozszerzona wersja z dodatkowymi funkcjami i wsparciem",
            "features": ["Wszystkie funkcje pakietu Standardowego", "Priorytetowe wsparcie", "Dodatkowe funkcje", "Szkolenie i wdrożenie"],
            "isPopular": False
        }
    ]
    
    # Create understanding section if needed
    if 'understanding' not in custom_data:
        custom_data['understanding'] = {
            "title": "Nasze Podejście",
            "subtitle": "Rozumiemy Twoje potrzeby",
            "content": extract_understanding(job_description, ai_response)
        }
    
    # Create benefits section if needed
    if 'benefits' not in custom_data:
        custom_data['benefits'] = {
            "title": "Korzyści Współpracy",
            "subtitle": "Co zyskujesz wybierając naszą ofertę",
            "items": extract_benefits(job_description, ai_response, proposal)
        }
    
    # Create testimonials if needed
    if 'testimonials' not in custom_data:
        custom_data['testimonials'] = {
            "title": "Opinie Klientów",
            "subtitle": "Co mówią o nas klienci",
            "items": [
                {
                    "quote": "Zespół Soft Synergy dostarczył rozwiązanie, które znacząco zwiększyło efektywność naszej firmy. Profesjonalizm i terminowość to ich znaki rozpoznawcze.",
                    "author": "Marta Kowalska",
                    "company": "Tech Solutions"
                },
                {
                    "quote": "Współpraca na najwyższym poziomie. Polecam każdemu, kto szuka rzetelnego partnera IT.",
                    "author": "Tomasz Nowak",
                    "company": "Marketing Plus"
                }
            ]
        }
    
    # Create features section if needed
    if 'features' not in custom_data:
        custom_data['features'] = {
            "title": "Funkcjonalności",
            "subtitle": "Co oferujemy w ramach projektu",
            "items": extract_features(job_description, ai_response)
        }
    
    # Create timeline section
    custom_data['timeline'] = generate_timeline_section(proposal, job_description)
    
    return custom_data

def extract_understanding(job_description, ai_response):
    """Extract or generate understanding content from job description and AI response"""
    description_excerpt = job_description[:min(len(job_description), 300)]
    
    understanding = (
        f"Dokładnie przeanalizowaliśmy Twoje potrzeby i rozumiemy, że kluczowe dla Ciebie są: "
        f"wydajność, niezawodność i terminowość realizacji. Na podstawie Twojego opisu projektu "
        f"zidentyfikowaliśmy główne wyzwania i przygotowaliśmy rozwiązanie, które w pełni odpowiada na Twoje oczekiwania. "
        f"\n\nNasz zespół ma doświadczenie w realizacji podobnych projektów, dzięki czemu możemy zagwarantować "
        f"wysoką jakość wykonania i terminową realizację."
    )
    return understanding

def extract_benefits(job_description, ai_response, proposal):
    """Extract or generate benefits from job description, AI response and proposal"""
    basic_benefits = [
        {
            "title": "Wzrost Efektywności",
            "description": "Nasze rozwiązanie zwiększa efektywność operacyjną o minimum 30%, co przekłada się na realne oszczędności"
        },
        {
            "title": "Przewaga Konkurencyjna",
            "description": "Zyskasz rozwiązanie, które wyróżni Cię na tle konkurencji i przyciągnie nowych klientów"
        },
        {
            "title": "Wsparcie Techniczne",
            "description": "Zapewniamy pełne wsparcie techniczne i bieżące aktualizacje systemu"
        },
        {
            "title": "Terminowa Realizacja",
            "description": f"Gwarantujemy terminową realizację projektu w ciągu {extract_timeline_from_proposal(proposal)} dni"
        }
    ]
    return basic_benefits

def extract_features(job_description, ai_response):
    """Extract or generate features from job description and AI response"""
    if "strona" in job_description.lower() or "website" in job_description.lower():
        return [
            {
                "title": "Responsywny Design",
                "description": "Strona dostosowana do wszystkich urządzeń - desktop, tablet, mobile"
            },
            {
                "title": "Optymalizacja SEO",
                "description": "Implementacja najlepszych praktyk SEO dla lepszej widoczności w wyszukiwarkach"
            },
            {
                "title": "Intuicyjny CMS",
                "description": "Prosty system zarządzania treścią, który pozwoli na samodzielną aktualizację strony"
            },
            {
                "title": "Bezpieczeństwo",
                "description": "Implementacja zaawansowanych zabezpieczeń chroniących przed atakami"
            }
        ]
    elif "aplikacja" in job_description.lower() or "app" in job_description.lower():
        return [
            {
                "title": "Intuicyjny Interfejs",
                "description": "Aplikacja z prostym i intuicyjnym interfejsem użytkownika"
            },
            {
                "title": "Tryb Offline",
                "description": "Możliwość korzystania z kluczowych funkcji nawet bez dostępu do internetu"
            },
            {
                "title": "Szybkość Działania",
                "description": "Zoptymalizowany kod zapewniający płynne działanie aplikacji"
            },
            {
                "title": "Integracje",
                "description": "Możliwość integracji z popularnymi serwisami i API"
            }
        ]
    else:
        return [
            {
                "title": "Jakość Wykonania",
                "description": "Gwarancja wysokiej jakości wykonania zgodnie z najlepszymi praktykami"
            },
            {
                "title": "Wsparcie Techniczne",
                "description": "Pełne wsparcie techniczne w trakcie i po zakończeniu projektu"
            },
            {
                "title": "Skalowalność",
                "description": "Rozwiązanie, które rośnie wraz z Twoim biznesem"
            },
            {
                "title": "Bezpieczeństwo",
                "description": "Implementacja zaawansowanych zabezpieczeń i zgodność z RODO"
            }
        ]

def generate_timeline_section(proposal, job_description):
    """Generate timeline section based on proposal text and job description"""
    timeline_days = extract_timeline_from_proposal(proposal)
    
    # Default timeline steps
    timeline_steps = [
        {
            "title": "Analiza Wymagań",
            "description": "Dokładna analiza Twoich potrzeb i oczekiwań",
            "days": max(2, int(timeline_days * 0.2))
        },
        {
            "title": "Projektowanie",
            "description": "Opracowanie koncepcji i projektu rozwiązania",
            "days": max(3, int(timeline_days * 0.3))
        },
        {
            "title": "Implementacja",
            "description": "Wdrożenie rozwiązania zgodnie z projektem",
            "days": max(5, int(timeline_days * 0.4))
        },
        {
            "title": "Testy i Finalizacja",
            "description": "Testy jakościowe i przekazanie finalnego produktu",
            "days": max(2, int(timeline_days * 0.1))
        }
    ]
    
    # Customize timeline based on job type
    if "strona" in job_description.lower() or "website" in job_description.lower():
        timeline_steps = [
            {
                "title": "Analiza i Projektowanie",
                "description": "Analiza wymagań i przygotowanie projektu graficznego",
                "days": max(2, int(timeline_days * 0.2))
            },
            {
                "title": "Akceptacja Projektu",
                "description": "Prezentacja i akceptacja projektu graficznego",
                "days": max(2, int(timeline_days * 0.1))
            },
            {
                "title": "Kodowanie",
                "description": "Implementacja strony zgodnie z projektem",
                "days": max(5, int(timeline_days * 0.5))
            },
            {
                "title": "Testy i Wdrożenie",
                "description": "Testy funkcjonalne i wdrożenie na serwer produkcyjny",
                "days": max(2, int(timeline_days * 0.2))
            }
        ]
    elif "aplikacja" in job_description.lower() or "app" in job_description.lower():
        timeline_steps = [
            {
                "title": "Analiza Wymagań",
                "description": "Określenie funkcjonalności i architektury aplikacji",
                "days": max(3, int(timeline_days * 0.15))
            },
            {
                "title": "Projekt UX/UI",
                "description": "Zaprojektowanie interfejsu użytkownika",
                "days": max(4, int(timeline_days * 0.2))
            },
            {
                "title": "Rozwój Aplikacji",
                "description": "Implementacja funkcjonalności aplikacji",
                "days": max(8, int(timeline_days * 0.5))
            },
            {
                "title": "Testy i Publikacja",
                "description": "Testy, poprawki i publikacja aplikacji",
                "days": max(3, int(timeline_days * 0.15))
            }
        ]
    
    return {
        "title": "Harmonogram Realizacji",
        "subtitle": f"Projekt zostanie zrealizowany w ciągu {timeline_days} dni",
        "totalDays": timeline_days,
        "steps": timeline_steps
    }

# Helper functions to extract price and timeline from proposal
def extract_price_from_proposal(proposal, budget=""):
    """Extract price from proposal text."""
    price = 40  # Minimalna cena dla Useme
    
    # Try to extract from proposal
    price_matches = re.findall(r'(\d+(?:[.,]\d+)?(?:\s*\d+)*)\s*(?:zł|PLN|złotych)(?:\s*netto)?', proposal, re.IGNORECASE)
    if price_matches:
        for price_match in price_matches:
            price_str = re.sub(r'\s+', '', price_match)
            price_str = price_str.replace(',', '.')
            try:
                extracted_price = float(price_str)
                extracted_price = int(extracted_price)
                if extracted_price >= 40:
                    price = extracted_price
                    break
            except ValueError:
                continue
    
    # Check for price range
    price_range_match = re.search(r'(\d+(?:[.,]\d+)?(?:\s*\d+)*)(?:\s*[-–]\s*)(\d+(?:[.,]\d+)?(?:\s*\d+)*)\s*(?:zł|PLN|złotych)(?:\s*netto)?', proposal, re.IGNORECASE)
    if price_range_match:
        try:
            price_str = re.sub(r'\s+', '', price_range_match.group(1))
            price_str = price_str.replace(',', '.')
            lower_price = float(price_str)
            lower_price = int(lower_price)
            if lower_price >= 40:
                price = lower_price
        except ValueError:
            pass
    
    # Check budget from CSV if provided
    if budget:
        budget_str = budget
        budget_str = budget_str.replace(',', '.')
        budget_match = re.search(r'(\d+(?:\.\d+)?)', budget_str)
        if budget_match:
            try:
                budget_value = float(budget_match.group(1))
                budget_int = int(budget_value)
                if budget_int >= 40 and (price == 40 or budget_int < price):
                    price = budget_int
            except ValueError:
                pass
    
    return int(price)

def extract_timeline_from_proposal(proposal):
    """Extract timeline (in days) from proposal text."""
    timeline = 7  # Minimalny czas wykonania
    
    # Check for "X dni roboczych" format
    timeline_matches = re.findall(r'(\d+)(?:\s*(?:dni|dniach|dniowy|dni\s+robocz(?:ych|e)|dniach\s+robocz(?:ych|e)))', proposal, re.IGNORECASE)
    if timeline_matches:
        for timeline_match in timeline_matches:
            try:
                extracted_timeline = int(timeline_match)
                # Convert business days to calendar days if needed
                if re.search(r'robocz', proposal[proposal.find(timeline_match):proposal.find(timeline_match) + 30], re.IGNORECASE):
                    extracted_timeline = max(7, int(extracted_timeline * 1.4))
                
                if extracted_timeline >= 7:
                    timeline = extracted_timeline
                    break
            except ValueError:
                continue
    
    # Check for timeline range
    timeline_range_match = re.search(r'(\d+)(?:\s*[-–]\s*)(\d+)\s*(?:dni|dniach|dniowy|dni\s+robocz(?:ych|e)|dniach\s+robocz(?:ych|e))', proposal, re.IGNORECASE)
    if timeline_range_match:
        try:
            lower_timeline = int(timeline_range_match.group(1))
            if re.search(r'robocz', proposal[proposal.find(timeline_range_match.group(0)):proposal.find(timeline_range_match.group(0)) + 30], re.IGNORECASE):
                lower_timeline = max(7, int(lower_timeline * 1.4))
                
            if lower_timeline >= 7:
                timeline = lower_timeline
        except ValueError:
            pass
    
    # Check for weeks and convert to days
    weeks_matches = re.findall(r'(\d+)(?:\s*(?:tygodni|tygodnie|tygodniowy))', proposal, re.IGNORECASE)
    if weeks_matches:
        for weeks_match in weeks_matches:
            try:
                weeks = int(weeks_match)
                days = weeks * 7
                if days >= 7:
                    timeline = days
                    break
            except ValueError:
                continue
    
    return int(timeline)

def parse_csv_file(csv_file_path):
    """Parse CSV file containing job descriptions."""
    try:
        jobs = []
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for i, row in enumerate(csv_reader):
                # Extract job ID from URL
                job_id = ""
                if 'url' in row and row['url']:
                    # Extract ID from URL pattern like https://useme.com/pl/jobs/projekt-ulotki,115348/
                    id_match = re.search(r'(?:,|/)(\d+)/?$', row['url'])
                    if id_match:
                        job_id = id_match.group(1)
                    else:
                        job_id = f"job_{i+1}"
                else:
                    job_id = f"job_{i+1}"
                
                job_data = {
                    'id': job_id,
                    'description': row.get('full_description', '') or row.get('short_description', ''),
                    'client_info': row.get('username', ''),
                    'budget': row.get('budget', ''),
                    'timeline': row.get('expiry_date', ''),
                    'additional_requirements': row.get('category', ''),
                    'title': row.get('title', f"Projekt {i+1}"),
                    'avatar_url': row.get('avatar_url_source', '')
                }
                jobs.append(job_data)
            
        return jobs
    except Exception as e:
        console.print(f"[bold red]Błąd podczas parsowania pliku CSV: {str(e)}[/bold red]")
        return []

def save_to_json(proposals, output_file):
    """Save generated proposals to a JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(proposals, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        console.print(f"[bold red]Błąd podczas zapisywania do pliku JSON: {str(e)}[/bold red]")
        return False

def sanitize_filename(filename):
    """Sanitize filename to be valid for file system."""
    # Replace invalid characters with underscore
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def generate_slug(title, description, client_name):
    """Generate a unique slug for the project based on title and description."""
    prompt = f"""
    Wygeneruj krótki, unikalny slug (identyfikator URL) dla projektu na podstawie poniższych informacji.
    Slug powinien być w języku polskim, zawierać tylko małe litery, cyfry i myślniki, oraz opisywać typ projektu i nazwę klienta lub branżę.
    Przykład: "wykonanie-strony-internetowej-ecobike" dla projektu strony dla firmy EcoBike.
    
    Tytuł projektu: {title}
    Opis projektu: {description}
    Nazwa klienta: {client_name}
    
    Zwróć tylko sam slug, bez żadnych dodatkowych komentarzy.
    """
    
    try:
        response = get_gemini_response(prompt)
        # The response is already a string
        slug = response.lower()
        # Usuń polskie znaki diakrytyczne
        slug = unicodedata.normalize('NFKD', slug).encode('ASCII', 'ignore').decode('utf-8')
        # Usuń wszystkie znaki specjalne i zamień spacje na myślniki
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        # Upewnij się, że slug nie zawiera podwójnych myślników
        slug = re.sub(r'-+', '-', slug)
        # Usuń myślniki z początku i końca
        slug = slug.strip('-')
        
        return slug
    except Exception as e:
        console.print(f"[bold red]Błąd generowania sluga: {str(e)}[/bold red]")
        # Fallback - generuj prosty slug z tytułu
        simple_slug = title.lower()
        simple_slug = unicodedata.normalize('NFKD', simple_slug).encode('ASCII', 'ignore').decode('utf-8')
        simple_slug = re.sub(r'[^\w\s-]', '', simple_slug)
        simple_slug = re.sub(r'[\s_]+', '-', simple_slug)
        simple_slug = re.sub(r'-+', '-', simple_slug)
        simple_slug = simple_slug.strip('-')
        return simple_slug or "projekt"

def post_generated_proposals(proposals_file, auto_post=False):
    """Post generated proposals to Useme."""
    try:
        with open(proposals_file, 'r', encoding='utf-8') as f:
            proposals = json.load(f)
        
        console.print(f"\n[bold yellow]Found {len(proposals)} proposals in {proposals_file}[/bold yellow]")
        
        if not auto_post:
            post_all = console.input("[bold green]Post all proposals automatically? (y/n): [/bold green]").lower() == 'y'
        else:
            post_all = True
        
        poster = UsemeProposalPoster()
        proposal_updates = []
        
        for i, proposal in enumerate(proposals, 1):
            job_id = proposal['job_id'].replace('job_', '')
            job_url = f"https://useme.com/pl/jobs/{job_id}/"
            project_slug = proposal.get('project_slug', '')
            
            console.print(f"[bold cyan]Proposal {i}/{len(proposals)} for job {job_id}:[/bold cyan]")
            console.print(Markdown(proposal['proposal']))
            
            if not post_all:
                post_this = console.input(f"[bold green]Post this proposal to {job_url}? (y/n): [/bold green]").lower() == 'y'
            else:
                post_this = True
                
            if post_this:
                console.print(f"[bold yellow]Posting proposal to {job_url}...[/bold yellow]")
                success = poster.post_proposal(
                    job_url=job_url,
                    proposal_text=proposal['proposal'],
                    payment=proposal.get('price', 40),  # Use price from proposal if available
                    work_days=proposal.get('timeline', 7)   # Use timeline from proposal if available
                )
                
                if success:
                    console.print(f"[bold green]Successfully posted proposal to {job_url}[/bold green]")
                    # Save employer email if available
                    if poster.employer_email:
                        proposal['employer_email'] = poster.employer_email
                        proposal_updates.append(True)
                        console.print(f"[bold green]Extracted employer email: {poster.employer_email}[/bold green]")
                        
                        # Update presentation JSON if it exists
                        if project_slug:
                            presentation_file = os.path.join("presentations", f"{project_slug}.json")
                            if os.path.exists(presentation_file):
                                try:
                                    with open(presentation_file, 'r', encoding='utf-8') as f:
                                        presentation_data = json.load(f)
                                    
                                    # Add employer_email to presentation data
                                    presentation_data['employer_email'] = poster.employer_email
                                    
                                    with open(presentation_file, 'w', encoding='utf-8') as f:
                                        json.dump(presentation_data, f, ensure_ascii=False, indent=2)
                                    
                                    console.print(f"[bold green]Updated presentation data with employer email in {presentation_file}[/bold green]")
                                except Exception as e:
                                    console.print(f"[bold red]Error updating presentation data: {str(e)}[/bold red]")
                else:
                    console.print(f"[bold red]Failed to post proposal to {job_url}[/bold red]")
                
                # Sleep briefly to avoid rate limiting
                time.sleep(1)
        
        # If any proposals were updated with employer emails, save the changes
        if proposal_updates:
            with open(proposals_file, 'w', encoding='utf-8') as f:
                json.dump(proposals, f, ensure_ascii=False, indent=2)
                console.print(f"[bold green]Updated proposals with employer emails in {proposals_file}[/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Error posting proposals: {str(e)}[/bold red]")

def generate_email(job_description, project_slug, client_info="", job_title=""):
    """Generate a follow-up email for a job proposal."""
    # Try to get prompt from database first
    custom_prompt = get_prompt_from_db('email')
    
    if custom_prompt:
        # Replace placeholders in the custom prompt
        prompt = custom_prompt
        prompt = prompt.replace("{job_description}", job_description)
        prompt = prompt.replace("{client_info}", client_info or "")
        prompt = prompt.replace("{project_slug}", project_slug or "")
        prompt = prompt.replace("{job_title}", job_title or "")
    else:
        # Use default prompt
        prompt = f"""
        Wygeneruj niezwykle skuteczny email follow-up wykorzystujący najnowocześniejsze strategie konwersji oparte na badaniach behawioralnych. Email będzie wysłany po złożeniu propozycji na Useme.
        
        Opis zlecenia: {job_description}
        {f"Informacje o kliencie: {client_info}" if client_info else ""}    
        
        Email musi wykorzystywać następujące techniki psychologii perswazji:
        
        1. PERSONALIZACJA I ROZPOZNANIE - rozpocznij od silnego, spersonalizowanego powitania nawiązującego do konkretnego projektu z Useme
        2. PRZEMYŚLANA DIAGNOZA - udowodnij, że dokładnie rozumiesz UKRYTE problemy i potrzeby klienta (głębsze niż to, co wyraził bezpośrednio)
        3. OPOWIADANIE HISTORII - przedstaw krótką historię podobnego sukcesu (z liczbami i konkretnymi rezultatami)
        4. PODKREŚLENIE WARTOŚCI - wyjaśnij, dlaczego współpraca z Soft Synergy to nie koszt, ale inwestycja o wymiernym zwrocie
        5. PILNOŚĆ DZIAŁANIA - subtelnie podkreśl koszty zwlekania z decyzją 
        6. ELEMENT ZASKOCZENIA - zaoferuj coś nieoczekiwanego, co przekracza standardową propozycję
        7. SILNE CTA - zaproś do obejrzenia przygotowanej prezentacji: prezentacje.soft-synergy.com/{project_slug}
        
        PSYCHOLOGICZNE WYZWALACZE:
        - Wykorzystaj efekt świeżości i primacy stawiając najważniejsze treści na początku i końcu
        - Wstaw co najmniej jedno pytanie angażujące czytelnika
        - Użyj technik presupozycji (np. "Kiedy zobaczy Pan/Pani efekty naszej pracy..." zamiast "Jeśli zdecyduje się Pan/Pani...")
        - Zastosuj przynajmniej jedną technikę wzbudzania ciekawości/luki informacyjnej
        - Zawrzyj przynajmniej jedną uwiarygadniającą statystykę lub liczbę
        - Użyj języka inkluzywnego (my/nasz) zamiast dystansującego (ja/mój)
        - Dodaj element wzmacniający poczucie ekskluzywności propozycji
        
        FORMATOWANIE:
        - Maksymalnie 180 słów
        - Email musi być w języku polskim, profesjonalny i naturalny
        - Krótkie paragrafy (max 2-3 linijki)
        - Przynajmniej 1 pytanie retoryczne (zwiększa zaangażowanie o 85%)
        - Link do prezentacji: prezentacje.soft-synergy.com/{project_slug} musi być wyraźnie wyróżniony
        - NIE używaj korporacyjnych klisz czy przesadnie formalnego języka
        
        Dane kontaktowe (umieść je na końcu w osobnych liniach):
        Z poważaniem,
        Antoni Seba
        Soft Synergy
        Tel: 576 205 389
        Email: info@soft-synergy.com
        
        Zwróć tylko treść emaila bez dodatkowych komentarzy czy objaśnień.
        """
    
    try:
        response = get_gemini_response(prompt)
        # The response is already a string
        return response
    except Exception as e:
        return f"Błąd generowania emaila: {str(e)}"

def generate_proposals_from_database(db=None, min_relevance=5, limit=10, auto_save=True, auto_post=False):
    """Generate proposals for eligible jobs in the database."""
    if db is None:
        # Import database module if not provided
        import database
        db = database.Database()
    
    # Get jobs for proposal generation
    jobs = db.get_jobs_for_proposal_generation(min_relevance, limit)
    
    if not jobs:
        console.print("[yellow]⚠[/yellow] Brak ofert o odpowiedniej ocenie dostępnych do generowania propozycji")
        return {
            "success": True,
            "count": 0,
            "message": "Brak ofert o odpowiedniej ocenie"
        }
    
    # Count how many jobs we're processing
    job_count = len(jobs)
    console.print(f"[bold blue]Generowanie propozycji dla {job_count} ofert...[/bold blue]")
    
    # Process each job
    proposals = []
    processed_count = 0
    posted_count = 0
    emails_sent = 0
    
    for i, job in enumerate(jobs):
        job_id = job['job_id']
        job_title = job.get('title', f"Projekt {i+1}")
        job_description = job.get('full_description', '') or job.get('short_description', '')
        client_info = job.get('username', '')
        budget = job.get('budget', '')
        timeline = job.get('expiry_date', '')
        additional_requirements = job.get('category', '')
        
        # Determine if this job has attachments
        attachments = []
        if job.get('attachments'):
            try:
                if isinstance(job['attachments'], str):
                    import json
                    attachments = json.loads(job['attachments'])
                else:
                    attachments = job['attachments']
                console.print(f"[blue]Znaleziono {len(attachments)} załączników dla oferty {job_id}[/blue]")
            except Exception as e:
                console.print(f"[red]Błąd parsowania załączników dla oferty {job_id}: {str(e)}[/red]")
        
        console.print(f"\n[bold cyan]Przetwarzanie oferty {job_id} ({i+1}/{job_count}): {job_title}[/bold cyan]")
        
        # Generate project slug
        project_slug = generate_slug(job_title, job_description, client_info)
        console.print(f"[blue]Wygenerowany slug projektu: {project_slug}[/blue]")
        
        # Try to extract employer email directly from Useme
        employer_email = None
        try:
            console.print(f"[blue]Próba ekstraktowania adresu email pracodawcy dla {job_id}...[/blue]")
            # Get cookies from UsemeProposalPoster to ensure they're up-to-date
            try:
                from useme_post_proposal import COOKIES as USEME_COOKIES
                console.print(f"[blue]Używanie aktualnych cookie z useme_post_proposal.py[/blue]")
                employer_email = extract_employer_email(job_id, cookies=USEME_COOKIES)
            except ImportError:
                # Fallback to default cookies in extract_useme_email
                console.print(f"[yellow]Używanie domyślnych cookie z extract_useme_email.py[/yellow]")
                employer_email = extract_employer_email(job_id)
                
            if employer_email:
                console.print(f"[green]✓[/green] Wyodrębniono adres email pracodawcy: {employer_email}")
            else:
                console.print(f"[yellow]⚠[/yellow] Nie udało się wyodrębnić adresu email pracodawcy")
        except Exception as e:
            console.print(f"[red]✗[/red] Błąd podczas próby wyodrębnienia adresu email: {str(e)}")
        
        try:
            # Generate proposal
            proposal_text = generate_proposal(
                job_description=job_description,
                client_info=client_info,
                budget=budget,
                timeline=timeline,
                additional_requirements=additional_requirements,
                project_slug=project_slug
            )
            
            # Generate follow-up email content
            email_content = generate_email(
                job_description=job_description, 
                project_slug=project_slug,
                client_info=client_info,
                job_title=job_title
            )
            console.print(f"[green]✓[/green] Wygenerowano treść email dla oferty {job_id}")
            
            # Calculate relevance score
            relevance_score = job.get('relevance_score')
            if not relevance_score:
                relevance_score = evaluate_relevance(
                    job_description=job_description,
                    client_info=client_info,
                    budget=budget,
                    timeline=timeline,
                    additional_requirements=additional_requirements
                )
            
            # Skip jobs with relevance < 5 to save API tokens
            if relevance_score < 5:
                console.print(f"[yellow]⚠[/yellow] Pomijam ofertę {job_id} - zbyt niska ocena relevance: {relevance_score}")
                continue
                
            # Prepare proposal data
            proposal_data = {
                "job_id": job_id,
                "title": job_title,
                "proposal_text": proposal_text,
                "url": job.get('url', f"https://useme.com/pl/jobs/{job_id}/"),
                "project_slug": project_slug,
                "relevance_score": relevance_score,
                "price": extract_price_from_proposal(proposal_text, budget),
                "timeline_days": extract_timeline_from_proposal(proposal_text),
                "email_content": email_content,
                "attachments": attachments
            }
            
            # Add employer email if available
            if employer_email:
                proposal_data["employer_email"] = employer_email
            
            proposals.append(proposal_data)
            
            # Update job in the database
            if auto_save:
                db.update_job_proposal(
                    job_id=job_id,
                    proposal_text=proposal_text,
                    project_slug=project_slug,
                    relevance_score=relevance_score,
                    employer_email=employer_email,
                    price=proposal_data["price"],
                    timeline_days=proposal_data["timeline_days"],
                    email_content=email_content,
                    attachments=attachments
                )
                console.print(f"[green]✓[/green] Zaktualizowano ofertę {job_id} w bazie danych")
                processed_count += 1
            
            # Optional: generate presentation data
            try:
                presentation_data = generate_presentation_data(
                    job_description=job_description,
                    proposal=proposal_text,
                    job_id=job_id,
                    client_info=client_info,
                    budget=budget,
                    timeline=timeline,
                    additional_requirements=additional_requirements,
                    employer_email=employer_email
                )
                
                # Save presentation data to file
                if presentation_data:
                    # Create presentations directory if it doesn't exist
                    os.makedirs('presentations', exist_ok=True)
                    
                    # Save presentation data
                    presentation_file = os.path.join('presentations', f"{project_slug}.json")
                    with open(presentation_file, 'w', encoding='utf-8') as f:
                        json.dump(presentation_data, f, ensure_ascii=False, indent=2)
                    console.print(f"[green]✓[/green] Zapisano dane prezentacji do pliku {presentation_file}")
                
                console.print(f"[green]✓[/green] Wygenerowano prezentację dla oferty {job_id}")
            except Exception as e:
                console.print(f"[red]✗[/red] Błąd generowania prezentacji dla oferty {job_id}: {str(e)}")
          # POST PROPOSAL TO USEME
            from useme_post_proposal import UsemeProposalPoster
            
            poster = UsemeProposalPoster()
            job_url = job.get('url')
            
            # Post the proposal
            result = poster.post_proposal(
                job_url=job_url,
                proposal_text=proposal_text,
                price=proposal_data["price"],
                timeline_days=proposal_data["timeline_days"]
            )
            
            if result.get('success'):
                console.print(f"[green]✓[/green] Pomyślnie wysłano propozycję dla oferty {job_id}")
                posted_count += 1
            else:
                console.print(f"[red]✗[/red] Błąd wysyłania propozycji: {result.get('error', 'Nieznany błąd')}")
            if relevance_score > 5 and employer_email:
                # Get the job details from the database
                job = db.get_job_by_id(job_id)
                # Configure EmailSender with settings from config.ini
                from mailer import EmailSender
                
                email_sender = EmailSender()  # This will load config automatically
                
                # Send the email
                subject = "Nasza odpowiedź na Państwa zgłoszenie na Useme"
                recipient_email = employer_email  # Use the employer_email we already have
                email_content = proposal_data.get("email_content")  # Get email content from proposal data
                
                if email_sender.send_email(recipient_email, subject, email_content):
                    # Update the database to mark email as sent
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE jobs 
                        SET follow_up_email_sent = 1, follow_up_email_sent_at = ? 
                        WHERE job_id = ?
                    """, (datetime.now().isoformat(), job_id))
                    conn.commit()
                    console.print(f"[green]✓[/green] Wysłano email do pracodawcy: {recipient_email}")
                    emails_sent += 1
                else:
                    console.print(f"[red]✗[/red] Błąd wysyłania emaila do {recipient_email}")
            # Also send a message through Useme if relevance > 7
            if relevance_score > 7:
                console.print(f"[bold yellow]Relevance score {relevance_score} > 7, sending message through Useme...[/bold yellow]")
                try:
                    # Send message using the proposal text
                    message_result = send_useme_message(job_id=job_id, message_content="", use_proposal=True)
                    
                    if message_result.get('success'):
                        console.print(f"[bold green]Successfully sent message through Useme for job {job_id}[/bold green]")
                        # Update the job in the database
                        db.mark_message_sent(job_id)
                    else:
                        console.print(f"[bold red]Failed to send message through Useme: {message_result.get('message')}[/bold red]")
                except Exception as e:
                    console.print(f"[bold red]Error sending message through Useme: {str(e)}[/bold red]")
            
            # Small delay to avoid rate limiting
            time.sleep(1.5)
                
        except Exception as e:
            console.print(f"[red]✗[/red] Błąd generowania propozycji dla oferty {job_id}: {str(e)}")
            continue
    
    # Save all proposals to JSON file
    if auto_save and proposals:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = f"proposals_{timestamp}.json"
        save_to_json(proposals, output_file)
        console.print(f"[green]✓[/green] Zapisano {len(proposals)} propozycji do pliku {output_file}")
    
    return {
        "success": True,
        "count": processed_count,
        "proposals_posted": posted_count,
        "emails_sent": emails_sent,
        "message": f"Wygenerowano {processed_count} propozycji, wysłano {posted_count} na Useme, wysłano {emails_sent} emaili"
    }

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
                logger.error("Could not extract employer ID from job page")
                return {
                    "success": False,
                    "message": "Could not extract employer ID from job page"
                }
        
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

def main():
    """Main function for generating proposals."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Proposal Generator for Useme jobs")
    parser.add_argument('--input', type=str, help='Input CSV or JSON file with job data')
    parser.add_argument('--output', type=str, help='Output JSON file for generated proposals')
    parser.add_argument('--min-relevance', type=int, default=5, help='Minimum relevance score (1-10) for generating proposals')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of proposals to generate')
    parser.add_argument('--auto-post', action='store_true', help='Automatically post generated proposals to Useme')
    parser.add_argument('--use-database', action='store_true', help='Use database instead of input file')
    
    args = parser.parse_args()
    
    try:
        db = Database()
        
        if args.use_database:
            # Generate proposals from the database
            logger.info("Generowanie propozycji na podstawie zleceń z bazy danych...")
            generated_proposals = generate_proposals_from_database(
                db=db,
                min_relevance=args.min_relevance,
                limit=args.limit,
                auto_post=args.auto_post
            )
            
            if generated_proposals:
                logger.info(f"Wygenerowano {len(generated_proposals)} propozycji.")
            else:
                logger.info("Nie wygenerowano żadnych propozycji.")
        else:
            # Legacy mode - use input file
            if args.input:
                if args.input.endswith('.csv'):
                    jobs = parse_csv_file(args.input)
                elif args.input.endswith('.json'):
                    with open(args.input, 'r', encoding='utf-8') as f:
                        jobs = json.load(f)
                else:
                    logger.error("Nieobsługiwany format pliku wejściowego. Używaj .csv lub .json")
                    return
                
                # Generate proposals for each job
                generated_proposals = []
                for job in jobs:
                    # Check if job already has a proposal in the database
                    job_id = db.extract_job_id_from_url(job.get('url', ''))
                    if job_id and db.check_proposal_submitted(job_id):
                        logger.info(f"Zlecenie {job_id} już ma wygenerowaną propozycję. Pomijam.")
                        continue
                
            else:
                logger.error("Nie podano pliku wejściowego ani opcji --use-database.")
                return
    
    except Exception as e:
        logger.error(f"Wystąpił błąd: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
        main()
