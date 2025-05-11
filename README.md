# Useme Bot - System automatyzacji scrapowania i generowania propozycji

System do automatycznego scrapowania zleceń z Useme.com, generowania propozycji AI oraz śledzenia statusu zleceń.

## Funkcjonalności

- Automatyczne scrapowanie zleceń z Useme.com co 5 minut
- Przechowywanie zleceń w bazie danych SQLite
- Blokowanie duplikatów zleceń i propozycji
- Tworzenie prezentacji ofert
- Automatyczne generowanie propozycji za pomocą Google AI
- Interfejs webowy do zarządzania systemem
- System kolejek zadań
- Automatyczne wysyłanie e-maili z PDF-em po 30 minutach od pierwszego wyświetlenia prezentacji

## Wymagania systemowe

- Python 3.8+
- SQLite 3
- Dostęp do internetu

## Instalacja

1. Sklonuj repozytorium:
```
git clone https://github.com/twojuser/useme-bot.git
cd useme-bot
```

2. Zainstaluj wymagane pakiety:
```
pip install -r requirements.txt
```

3. Ustaw uprawnienia wykonywania dla skryptów:
```
chmod +x run_scheduler.sh run_presentation_follow_up.sh stop_presentation_follow_up.sh
```

## Struktura projektu

- `app.py` - Aplikacja Flask służąca do prezentacji danych
- `scraper.py` - Skrypt do scrapowania zleceń z Useme
- `ai_proposal_generator.py` - Generowanie propozycji za pomocą AI
- `database.py` - Moduł obsługi bazy danych SQLite
- `task_scheduler.py` - Scheduler zadań
- `run_scheduler.sh` - Skrypt do uruchamiania scheduler'a w tle
- `presentation_follow_up.py` - Skrypt do automatycznego wysyłania e-maili z PDF-em po 30 minutach
- `run_presentation_follow_up.sh` - Skrypt do uruchamiania systemu śledzenia prezentacji w tle
- `stop_presentation_follow_up.sh` - Skrypt do zatrzymywania systemu śledzenia prezentacji
- `mailer.py` - Moduł do wysyłania e-maili
- `presentations/` - Katalog z danymi prezentacji
- `templates/` - Szablony HTML dla aplikacji Flask
- `avatars/` - Pobrane avatary użytkowników
- `useme.db` - Baza danych SQLite (tworzona automatycznie)

## Uruchomienie

### Uruchomienie aplikacji webowej

```
python app.py
```

Aplikacja będzie dostępna pod adresem http://localhost:5001

### Uruchomienie scrapera

```
python scraper.py
```

Opcjonalne parametry:
- `--max-pages NUMBER` - Maksymalna liczba stron do przeskanowania
- `--start-page NUMBER` - Strona początkowa (domyślnie 1)
- `--output csv|json` - Format wyjściowy (domyślnie json)
- `--schedule` - Zaplanuj zadanie scrapowania co 5 minut
- `--process-queue` - Przetwórz zaplanowane zadania z kolejki

### Uruchomienie generatora propozycji

```
python ai_proposal_generator.py --use-database
```

Opcjonalne parametry:
- `--min-relevance NUMBER` - Minimalny poziom zgodności (1-10) dla generowania propozycji
- `--limit NUMBER` - Maksymalna liczba propozycji do wygenerowania
- `--auto-post` - Automatycznie publikuj wygenerowane propozycje na Useme

### Uruchomienie schedulera zadań

```
./run_scheduler.sh start
```

Dostępne komendy:
- `start` - Uruchom scheduler w tle
- `stop` - Zatrzymaj scheduler
- `restart` - Zrestartuj scheduler
- `status` - Sprawdź status schedulera

### Uruchomienie systemu śledzenia prezentacji i wysyłania e-maili

```
./run_presentation_follow_up.sh
```

Aby zatrzymać:
```
./stop_presentation_follow_up.sh
```

## Automatyzacja

System jest zaprojektowany do działania w trybie ciągłym. Scheduler automatycznie:
1. Scrapuje nowe zlecenia co 5 minut
2. Zapobiega duplikowaniu zleceń
3. Generuje propozycje tylko dla nowych zleceń
4. Tworzy prezentacje ofert

System śledzenia prezentacji automatycznie:
1. Śledzi wyświetlenia prezentacji przez klientów
2. Po 30 minutach od pierwszego wyświetlenia wysyła e-mail z załącznikiem PDF
3. Zapobiega ponownemu wysłaniu e-maila do tego samego klienta

## Baza danych

System korzysta z SQLite jako bazy danych, co nie wymaga instalacji zewnętrznego serwera DB.
Plik bazy danych `useme.db` jest tworzony automatycznie przy pierwszym uruchomieniu.

### Struktura bazy danych

- `jobs` - Tabela z zleceniami z Useme
- `scrape_queue` - Kolejka zadań scrapowania
- `submitted_proposals` - Rejestr wysłanych propozycji
- `presentation_views` - Rejestr wyświetleń prezentacji

## Licencja

Ten projekt jest udostępniony na licencji MIT. 