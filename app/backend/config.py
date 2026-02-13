from __future__ import annotations
import os
from dotenv import load_dotenv

# Load environment variables - szukaj .env w głównym katalogu projektu
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent  # polish-players-tracker/
env_path = project_root / ".env"
load_dotenv(env_path, override=False)

class Settings:
    def __init__(self) -> None:
        # Baza danych - Supabase PostgreSQL (wymagane w .env)
        self.database_url: str = os.getenv("DATABASE_URL")

        if not self.database_url:
            raise ValueError(
                "❌ DATABASE_URL not found in environment variables!\n"
                "Please set DATABASE_URL in .env file.\n"
                "Example:\n"
                "  DATABASE_URL=postgresql://postgres.xxx:password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres\n"
                "See SUPABASE_GUIDE.md for setup instructions."
            )
        
        # Ustawienia synchronizacji
        self.sync_daily_hour: int = int(os.getenv("SYNC_DAILY_HOUR", "6"))

        # Timezone dla schedulera (domyślnie Europe/Warsaw)
        self.scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Europe/Warsaw")

        # --- RapidAPI Configuration (nowe źródło danych) ---
        self.rapidapi_key: str = os.getenv("RAPIDAPI_KEY")

        # --- Konfiguracja Email (Resend API) ---
        # Używamy API zamiast SMTP ze względu na blokadę portów na Render
        self.resend_api_key: str = os.getenv("RESEND_API_KEY")
        
        # Opcjonalnie: Adresy do powiadomień
        self.email_from: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev") # Domyślny nadawca
        self.email_to: str = os.getenv("EMAIL_TO", "twoj_email@gmail.com")      # Domyślny odbiorca

settings = Settings()


