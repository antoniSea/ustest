# Generator Prezentacji z plików JSON

Serwer Flask do generowania prezentacji z plików JSON, z wykorzystaniem szablonów HTML.

## Struktura projektu

- `app.py` - główny plik serwera Flask
- `templates/presentations/` - katalog zawierający pliki JSON z danymi prezentacji oraz szablony HTML
  - `*.json` - pliki z danymi prezentacji
  - `prezentation1.html`, `prezentation2.html`, ... - szablony HTML do renderowania prezentacji

## Instalacja

1. Zainstaluj wymagane zależności:

```bash
pip install -r requirements.txt
```

## Uruchomienie serwera

Aby uruchomić serwer:

```bash
python app.py
```

Serwer będzie dostępny pod adresem: `http://localhost:5000`

## Korzystanie z serwera

### Adres URL

Format adresów URL: `/{nazwa pliku}`

Przykłady:
- `http://localhost:5000/data` - wygeneruje prezentację z pliku `data.json`
- `http://localhost:5000/1` - wygeneruje prezentację z pliku `1.json`

Można również użyć pełnej nazwy pliku z rozszerzeniem:
- `http://localhost:5000/data.json`

### Tryb debugowania

Aby zobaczyć dane JSON wykorzystywane do generowania prezentacji, dodaj parametr `debug=1`:
- `http://localhost:5000/data?debug=1`

### Szablony prezentacji

Serwer automatycznie wybiera szablon na podstawie nazwy pliku JSON:
- Jeśli istnieje plik `prezentation{nazwa_pliku}.html` - zostanie on użyty
- W przeciwnym razie zostanie użyty domyślny szablon `prezentation1.html`

## Tworzenie własnych prezentacji

1. Utwórz plik JSON w katalogu `templates/presentations/`
2. Struktura pliku JSON powinna odpowiadać strukturze używanej w szablonie prezentacji
3. Opcjonalnie: utwórz własny szablon HTML z nazwą `prezentation{nazwa_pliku}.html`

## Błędy i obsługa wyjątków

- Jeśli plik JSON nie istnieje - zostanie wyświetlona strona 404
- Jeśli wystąpi błąd przetwarzania pliku JSON - zostanie wyświetlona strona błędu z informacją o problemie 