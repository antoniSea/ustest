import sqlite3
import os
import logging

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_database_schema(db_path="useme.db"):
    """
    Aktualizuje schemat bazy danych, dodając brakujące kolumny.
    """
    try:
        # Połączenie z bazą danych
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Dodanie nowych kolumn do tabeli jobs
        logger.info("Aktualizacja schematu bazy danych...")
        
        # Sprawdzenie czy kolumny już istnieją
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Dodanie brakujących kolumn
        new_columns = {
            "employer_email": "TEXT",
            "price": "INTEGER",
            "timeline_days": "INTEGER",
            "presentation_url": "TEXT",
            "email_content": "TEXT",
            "attachments": "TEXT"
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                logger.info(f"Dodawanie kolumny: {column_name}")
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")
                
        conn.commit()
        logger.info("Aktualizacja schematu bazy danych zakończona pomyślnie.")
        
        # Sprawdzenie aktualnego schematu
        cursor.execute("PRAGMA table_info(jobs)")
        updated_columns = cursor.fetchall()
        logger.info("Aktualny schemat tabeli jobs:")
        for column in updated_columns:
            logger.info(f"  {column[1]} ({column[2]})")
        
        conn.close()
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji schematu bazy danych: {str(e)}")
        if conn:
            conn.close()

if __name__ == "__main__":
    update_database_schema()
    logger.info("Skrypt zakończył działanie.") 