# Instalacja Useme Bot

Ten dokument zawiera szczegółowe instrukcje instalacji i konfiguracji systemu Useme Bot.

## Wymagania systemowe

- Python 3.8+ (zalecany Python 3.9 lub nowszy)
- SQLite 3.x
- Dostęp do internetu
- Ok. 100MB wolnego miejsca na dysku

## Instalacja krok po kroku

### 1. Przygotowanie środowiska

#### Dla Windows

1. Pobierz i zainstaluj Pythona 3.9+ ze strony [python.org](https://www.python.org/downloads/)
2. Podczas instalacji zaznacz opcję "Add Python to PATH"
3. Otwórz wiersz poleceń (cmd) lub PowerShell

#### Dla Linux

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Pobieranie repozytorium

#### Przez git

```bash
git clone https://github.com/twojuser/useme-bot.git
cd useme-bot
```

#### Ręcznie

1. Pobierz archiwum z projektem
2. Rozpakuj do wybranego katalogu
3. Otwórz terminal/wiersz poleceń w tym katalogu

### 3. Instalacja zależności

```bash
python3 -m pip install -r requirements.txt
```

### 4. Konfiguracja uprawnień (tylko Linux/Mac)

```bash
chmod +x run_scheduler.sh
```

### 5. Testowe uruchomienie

Aby sprawdzić czy system działa poprawnie:

```bash
# Uruchom scrapowanie testowe
python3 scraper.py --max-pages 1

# Sprawdź stan bazy danych
python3 check_db.py
```

### 6. Konfiguracja jako usługa systemowa (opcjonalnie)

#### Dla Linux (systemd)

1. Edytuj plik `useme-scheduler.service`, zmieniając:
   - `<your_username>` na nazwę swojego użytkownika
   - `/path/to/useme-bot` na pełną ścieżkę do katalogu z projektem

2. Skopiuj plik usługi do katalogu systemd:
   ```
   sudo cp useme-scheduler.service /etc/systemd/system/
   ```

3. Włącz i uruchom usługę:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable useme-scheduler
   sudo systemctl start useme-scheduler
   ```

4. Sprawdź status:
   ```
   sudo systemctl status useme-scheduler
   ```

#### Dla Windows

1. Zainstaluj NSSM (Non-Sucking Service Manager):
   - Pobierz ze strony [nssm.cc](https://nssm.cc/download)
   - Rozpakuj do wybranego katalogu

2. Stwórz usługę używając NSSM:
   ```
   nssm.exe install "Useme Bot Scheduler" "python" "C:\path\to\useme-bot\task_scheduler.py"
   nssm.exe set "Useme Bot Scheduler" AppDirectory "C:\path\to\useme-bot"
   nssm.exe start "Useme Bot Scheduler"
   ```

### 7. Uruchomienie aplikacji webowej

```bash
python3 app.py
```

Aplikacja będzie dostępna pod adresem http://localhost:5001

## Rozwiązywanie problemów

### Problem z połączeniem do Useme

Jeśli masz problemy z pobieraniem danych z Useme.com, spróbuj:

1. Sprawdzić swoje połączenie internetowe
2. Upewnić się, że Useme.com jest dostępne
3. Spróbować uruchomić scrapera z mniejszą liczbą stron (--max-pages 1)

### Problem z bazą danych

Jeśli pojawią się problemy z bazą danych:

1. Sprawdź uprawnienia do pliku useme.db
2. Spróbuj usunąć plik useme.db i uruchomić program ponownie (zostanie utworzony nowy plik)

### Problemy z API Gemini

Jeśli masz problemy z generowaniem propozycji:

1. Sprawdź czy masz poprawny klucz API w pliku ai_proposal_generator.py
2. Upewnij się, że masz połączenie internetowe
3. Sprawdź czy nie przekroczyłeś limitu zapytań do API

## Kontakt

W razie problemów z instalacją lub działaniem systemu, skontaktuj się z administratorem systemu. 