from simple_queue import SimpleQueue

# Funkcja do wykonania później
def wyslij_powiadomienie(uzytkownik_id, wiadomosc):
    print(f"Wysyłam powiadomienie do {uzytkownik_id}: {wiadomosc}")
    # Faktyczna implementacja wysyłania powiadomienia

# Inicjalizacja kolejki
kolejka = SimpleQueue()

# Zaplanowanie zadania za godzinę (60 minut)
kolejka.schedule_task(
    wyslij_powiadomienie,
    {
        "uzytkownik_id": 123,
        "wiadomosc": "Twoje zamówienie zostało wysłane!"
    },
    delay_minutes=0
)

# Utrzymanie skryptu działającego
try:
    print("Kolejka działa. Naciśnij Ctrl+C aby zatrzymać.")
    
except KeyboardInterrupt:
    kolejka.stop()