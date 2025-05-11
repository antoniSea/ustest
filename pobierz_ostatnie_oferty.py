#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skrypt do pobierania ofert pracy z ostatnich 5 stron Useme.com
"""

import os
import subprocess
import sys

def main():
    print("Pobieranie ofert z ostatnich 5 stron Useme.com...")
    
    # Sprawdź czy istnieje plik useme_scraper.py
    if not os.path.isfile("useme_scraper.py"):
        print("Błąd: Nie znaleziono pliku useme_scraper.py!")
        return
    
    # Pobierz tylko ostatnie 5 stron, format JSON i zapisz do pliku ostatnie_oferty.json
    cmd = [
        sys.executable,  # Używa tego samego interpretera Pythona
        "useme_scraper.py",
        "--last-pages", "5",
        "--output-format", "json",
        "--output-file", "ostatnie_oferty"
    ]
    
    print("Uruchamiam komendę:", " ".join(cmd))
    
    try:
        # Uruchom skrypt scrapera
        subprocess.run(cmd, check=True)
        
        print("\nGotowe! Oferty zostały zapisane do pliku 'ostatnie_oferty.json'")
        print("Możesz otworzyć ten plik w przeglądarce lub edytorze tekstu, aby zobaczyć wyniki.")
        
    except subprocess.CalledProcessError as e:
        print(f"Wystąpił błąd podczas uruchamiania scrapera: {e}")
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    main() 