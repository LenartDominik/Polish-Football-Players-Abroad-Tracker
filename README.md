# 🇵🇱 Polish Football Data Hub International

**Wersja:** v0.7.3 | **Status:** ✅ Production Ready | **Ostatnia aktualizacja:** 25.11.2025

> 📚 **[Zobacz co nowego w v0.7.3](FINAL_COMPLETE_SUMMARY_v0.7.3.md)**

## 🆕 Najnowsze Zmiany w v0.7.3

### Nowe Funkcjonalności:
- ✅ **Porównywanie bramkarzy** - Pełne wsparcie dla porównań GK vs GK
- ✅ **Statystyki kadry według roku kalendarzowego** - National Team (2025) używa player_matches
- ✅ **Wykluczenie Nations League 2024-2025** - Poprawne liczenie meczów kadry w 2025
- ✅ **Enhanced Stats dla zawodników z pola** - xGI, G+A/90, metryki per 90
- ✅ **Scheduler z e-mail notifications** - Automatyczna synchronizacja 3x/tydzień

### Poprawki:
- 🐛 Naprawiono błąd w API comparison dla bramkarzy (nieprawidłowe nazwy kolumn)
- 🐛 Naprawiono liczenie meczów reprezentacji (wykluczono NL 2024-25 z roku 2025)
- 🐛 Usunięto kolumny Shots/SoT z Season Statistics History  
> ⚖️ **[Informacje prawne - Ważne!](LEGAL_NOTICE.md)** | 🚀 **[Deployment Guide](STREAMLIT_CLOUD_DEPLOYMENT.md)**

## ⚖️ Legal Notice

**This is an educational, non-commercial project.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Educational and portfolio purposes only
- **NOT for commercial use** without proper licensing
- **See [LEGAL_NOTICE.md](LEGAL_NOTICE.md) for full details**

# 🇵🇱 Polish Players Tracker

Nowoczesny system do monitorowania polskich piłkarzy grających za granicą. Automatyczna synchronizacja statystyk z FBref.com z użyciem Playwright, zaawansowana analiza danych i interaktywny dashboard.

## 📊 Data Source & Attribution

All player statistics in this application are sourced from **[FBref.com](https://fbref.com/)** (Sports Reference LLC), the leading resource for football statistics worldwide.

**What data comes from FBref:**
- ⚽ Player statistics (goals, assists, xG, xA, minutes played)
- 📋 Match logs (detailed game-by-game performance)
- 🏆 Competition data (leagues, cups, international matches)
- 🧤 Goalkeeper statistics (saves, clean sheets, goals against)

**Our commitment to responsible data use:**
- ✅ **Rate Limiting**: 12-second delay between requests (respects server load)
- ✅ **Clear Attribution**: FBref credited throughout the application
- ✅ **Non-Commercial**: Educational/portfolio project
- ✅ **Respectful Scraping**: Following best practices and Terms of Service

**Disclaimer:** Polish Players Tracker is an independent project and is not affiliated with, endorsed by, or connected to FBref.com or Sports Reference LLC. For official statistics and in-depth analysis, please visit [FBref.com](https://fbref.com/).

---

## ✨ Główne funkcjonalności

### 🕸️ FBref Playwright Scraper
- **Automatyczny scraping** danych z FBref.com używając Playwright (headless browser)
- **Zaawansowane statystyki zawodników z pola**: mecze, gole, asysty, xG, xA, xGI, G+A/90, minuty, kartki
- **Statystyki bramkarzy**: obrony, czyste konta, % obron, karne, PSxG (Post-Shot xG)
- **Rate limiting**: 12s między requestami (bezpieczne dla ToS)
- **Rozbicie na rozgrywki**: Liga, Puchary Europejskie (LM/LE/LK), Reprezentacja (ROK KALENDARZOWY!), Puchary krajowe
- **Match logs**: Szczegółowe statystyki meczowe dla każdego zawodnika
- **Tracking 100+ polskich piłkarzy** z europejskich lig

### 📊 Backend API (FastAPI)
- **RESTful API** z automatyczną dokumentacją Swagger/ReDoc
- **Endpointy**: gracze, porównania, statystyki, matchlogs, mecze live (w budowie)
- **Baza danych**: SQLite (dev) / PostgreSQL (production - Supabase darmowe!)
- **Scheduler**: automatyczna synchronizacja
  - Statystyki: 2x w tygodniu (Poniedziałek/Czwartek 6:00)
  - Matchlogs: 1x w tygodniu (Wtorek 7:00)
- **Email notifications**: HTML raporty po każdej synchronizacji
- **Rate limiting**: 12 sekund między requestami (bezpieczne dla FBref ToS)
- **Cloud deployment**: gotowy do deployment na Render.com (darmowy hosting!)

### 🎨 Frontend Dashboard (Streamlit)
- **Interaktywne filtrowanie**: liga, drużyna, pozycja, typ rozgrywek, sezon
- **Wyszukiwanie graczy** po nazwisku
- **Widoki**: karty graczy, tabele, wykresy top strzelców
- **Enhanced Stats w Details**: xGI, metryki per 90 (xG/90, xA/90, npxG/90, xGI/90, G+A/90)
- **Porównanie graczy**: side-by-side z wizualizacjami
  - ⚽ Field players vs field players
  - 🧤 Goalkeepers vs goalkeepers
  - ⚠️ Blokada nieprawidłowych porównań (GK vs field player)
- **National Team (2025)**: Statystyki kadry według roku kalendarzowego (z tabeli player_matches)
- **Season Statistics History**: Pełna historia wszystkich sezonów (bez kolumn Shots/SoT)
- **Export do CSV**: eksport przefiltrowanych danych
- **Dedykowane statystyki bramkarzy**

### 🔄 Synchronizacja danych
- **CLI Scripts**: `sync_playwright.py`, `sync_all_playwright.py`, `sync_match_logs.py`
- **Automatyczny scheduler**: synchronizacja w tle
  - Statystyki graczy: poniedziałek i czwartek 6:00
  - Szczegółowe matchlogi: wtorek 7:00
- **Retry mechanism**: ponowne próby dla nieudanych synchronizacji

## ⚡ Quick Start - Najczęstsze komendy

### Zsynchronizuj pojedynczego gracza
```powershell
python sync_playwright.py "Robert Lewandowski"
```

### Dodaj nowego gracza i zsynchronizuj
```powershell
# Interaktywnie (pyta o dane)
python quick_add_player.py

# Lub wszystko w jednej komendzie (automatyczna synchronizacja)
python quick_add_player.py "Krzysztof Piątek" "Istanbul Basaksehir" "Super Lig" "FW" --sync
```

### Uruchom aplikację
```powershell
.\start_backend.ps1    # Backend API (port 8000)
.\start_frontend.ps1   # Dashboard (port 8501)
```

### Zsynchronizuj wszystkich graczy
```powershell
python sync_all_playwright.py
```

### Zsynchronizuj szczegóły meczów (matchlogs)
```powershell
python sync_match_logs.py "Robert Lewandowski"
```

---

## 🚀 Pełna Instalacja

### Wymagania wstępne
- Python 3.10+
- Playwright (Chromium)
- SQLite (development) / PostgreSQL (production)

### 1. Instalacja zależności

```powershell
# Aktywuj środowisko wirtualne
.\venv\Scripts\Activate.ps1

# Zainstaluj pakiety
pip install -r requirements.txt

# Zainstaluj Playwright Chromium
python -m playwright install chromium
```

### 2. Konfiguracja

Utwórz plik `.env` w głównym katalogu (lub skopiuj z `.env.example`):

```env
# Baza danych (Development - SQLite)
DATABASE_URL=sqlite:///./players.db

# Baza danych (Production - Supabase PostgreSQL - DARMOWE!)
# DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
# 📖 Pełna instrukcja: SUPABASE_MIGRATION_GUIDE.md

# Scheduler (włącz dla automatycznej synchronizacji 2x w tygodniu)
ENABLE_SCHEDULER=false

# Timezone dla schedulera (domyślnie Europe/Warsaw)
SCHEDULER_TIMEZONE=Europe/Warsaw

# Email notifications (opcjonalne - scheduler działa bez nich!)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Użyj Gmail App Password!
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**📧 Email Setup:**
- **Wymagane**: Gmail App Password (nie zwykłe hasło!)
- **Instrukcje**: Zobacz [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)
- **Opcjonalne**: Scheduler działa bez emaili (tylko logi w konsoli)

### 3. Uruchom aplikację

```powershell
# Uruchom backend (port 8000)
.\start_backend.ps1

# Uruchom frontend (port 8501)
.\start_frontend.ps1
```

**Dostęp do aplikacji:**
- 🔧 **Backend API (Swagger UI):** http://localhost:8000/docs
- 📖 **Backend API (ReDoc):** http://localhost:8000/redoc
- 🏥 **Backend Health Check:** http://localhost:8000/health
- 🎨 **Frontend Dashboard:** http://localhost:8501

**💡 Tip:** Swagger UI pozwala testować API bezpośrednio w przeglądarce!

## 🔄 Synchronizacja danych

### 🤖 Automatyczna synchronizacja (Scheduler)

**Włącz scheduler w `.env`:**
```env
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=Europe/Warsaw
```

**Harmonogram:**
- 📅 **Poniedziałek 6:00** - po meczach weekendowych (liga)
- 📅 **Czwartek 6:00** - po Lidze Mistrzów (środa)

**Co synchronizuje:**
- ✅ Statystyki sezonu 2025-2026 dla wszystkich graczy
- ✅ Liga krajowa + Puchary Europejskie + Reprezentacja
- ✅ Rate limiting: 12 sekund między każdym graczem
- ✅ Email z raportem po zakończeniu (opcjonalnie)

**Wymagania:**
- ⚠️ Backend musi być uruchomiony 24/7
- ⚠️ Komputer musi być włączony (lub użyj cloud deployment!)

**Cloud deployment:** Zobacz [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) dla darmowego hostingu 24/7!

---

### ⚡ Manualna synchronizacja

#### Synchronizacja pojedynczego gracza

```powershell
# Zsynchronizuj gracza z FBref
python sync_playwright.py "Robert Lewandowski"

# Z pełną historią wszystkich sezonów
python sync_playwright.py "Robert Lewandowski" --all-seasons

# Zobacz przeglądarkę (debug mode)
python sync_playwright.py "Robert Lewandowski" --visible
```

#### Synchronizacja wszystkich graczy

```powershell
# Zsynchronizuj wszystkich graczy z bazy
python sync_all_playwright.py

# Z pełną historią
python sync_all_playwright.py --all-seasons

# Tylko wybrani gracze
python sync_all_playwright.py "Lewandowski" "Zieliński" "Szczęsny"
```

#### Synchronizacja szczegółów meczów (matchlogs)

```powershell
# Zsynchronizuj matchlogs dla gracza (sezon 2025-2026)
python sync_match_logs.py "Robert Lewandowski"

# Dla innego sezonu
python sync_match_logs.py "Robert Lewandowski" --season 2024-2025
```

**Co synchronizuje matchlogs:**
- Szczegóły pojedynczych meczów (data, przeciwnik, wynik)
- Statystyki per mecz (gole, asysty, minuty, strzały)
- Zaawansowane statystyki (xG, xA, podania, dryblingi, pressings)

### Automatyczna synchronizacja (Scheduler)

Ustaw w pliku `.env`:
```env
ENABLE_SCHEDULER=true
```

Scheduler automatycznie zsynchronizuje wszystkich graczy:
- **Poniedziałek 6:00** - dzień po meczach weekendowych
- **Czwartek 6:00** - dzień po meczach Ligi Mistrzów

## 📡 API Endpoints

### Players
- `GET /api/players` - Lista wszystkich graczy
- `GET /api/players/{id}` - Szczegóły gracza

### Comparison
- `GET /api/comparison/compare` - Porównaj dwóch graczy
- `GET /api/comparison/players/{id}/stats` - Statystyki gracza
- `GET /api/comparison/available-stats` - Dostępne statystyki

### Matches
- `GET /api/matches/live` - Mecze live (w budowie)
- `GET /api/matches/upcoming/{league}` - Nadchodzące mecze

### Matchlogs (Szczegóły meczów)
- `GET /api/players/{id}/matches` - Lista meczów gracza
- `GET /api/players/{id}/matches/stats` - Statystyki zagregowane z meczów
- `GET /api/matches/{match_id}` - Szczegóły konkretnego meczu

## 📁 Struktura projektu

```
polish-players-tracker/
├── .env                          # Konfiguracja (gitignored)
├── .env.example                  # Przykładowa konfiguracja
├── .gitignore
├── requirements.txt              # Zależności Python
├── players.db                    # Baza danych SQLite (dev tylko!)
├── migrate_sqlite_to_postgres.py # Skrypt migracji do Supabase
├── README.md                     # Ten plik
│
├── venv/                         # Środowisko wirtualne Python
│
├── app/
│   ├── backend/                  # Backend FastAPI
│   │   ├── main.py               # Główna aplikacja + scheduler
│   │   ├── config.py             # Konfiguracja
│   │   ├── database.py           # Połączenie z bazą
│   │   ├── models/               # Modele SQLAlchemy
│   │   │   ├── player.py
│   │   │   ├── competition_stats.py
│   │   │   ├── goalkeeper_stats.py
│   │   │   └── ...
│   │   ├── routers/              # Endpointy API
│   │   │   ├── players.py
│   │   │   ├── comparison.py
│   │   │   └── matches.py
│   │   ├── schemas/              # Pydantic schemas
│   │   └── services/             # Serwisy biznesowe
│   │       └── fbref_playwright_scraper.py  # Główny scraper
│   │
│   └── frontend/                 # Frontend Streamlit
│       ├── streamlit_app.py      # Główna strona
│       ├── requirements.txt
│       └── pages/
│           └── 2_⚖️_compare_players.py
│
├── alembic/                      # Migracje bazy danych
│   └── versions/
│
├── start_backend.ps1             # Uruchom backend
├── start_frontend.ps1            # Uruchom frontend
│
├── sync_playwright.py            # Sync pojedynczego gracza
├── sync_all_playwright.py        # Sync wszystkich graczy
├── sync_match_logs.py            # Sync szczegółów meczów (matchlogs)
├── sync_missing_players.py       # Sync graczy bez danych
├── add_piatek_manual.py          # Ręczne dodanie gracza
├── quick_add_player.py           # Szybkie dodanie gracza
│
└── tools/                        # Narzędzia pomocnicze
    └── check_reqs.py             # Weryfikacja pakietów
```

## 🗄️ Baza danych

### 📦 Development (lokalnie)
- **SQLite** (`players.db`) - szybkie, proste, bez konfiguracji

### ☁️ Production (Render/Streamlit Cloud)
- **PostgreSQL (Supabase)** - DARMOWE NA ZAWSZE! ✅
- 500 MB storage (wystarczy dla setek graczy)
- Automatyczne backupy
- Dashboard do przeglądania danych
- 📖 **[Instrukcja migracji (15 minut)](SUPABASE_MIGRATION_GUIDE.md)**

**Dlaczego nie SQLite w chmurze?**
- ❌ Render Free: dane znikają przy każdym restarcie (filesystem efemeryczny)
- ❌ Streamlit Cloud: read-only filesystem (scheduler nie może zapisywać)
- ✅ **Rozwiązanie**: Supabase PostgreSQL (też darmowe!)

### 🔄 Migracja (3 proste komendy):
```powershell
python migrate_sqlite_to_postgres.py export   # Eksport z SQLite
python migrate_sqlite_to_postgres.py import   # Import do Supabase
python migrate_sqlite_to_postgres.py verify   # Sprawdzenie
```

---

## 🗄️ Struktura bazy danych

### Główne tabele:

**`players`** - podstawowe informacje o graczach
- id, name, team, league, position, nationality, is_goalkeeper, api_id, last_updated

**`competition_stats`** - statystyki zawodników (nie-bramkarzy)
- player_id, season, competition_type, competition_name
- games, goals, assists, xg, xa, minutes, yellow_cards, red_cards

**`goalkeeper_stats`** - statystyki bramkarzy
- player_id, season, competition_type, competition_name
- games, saves, clean_sheets, goals_against, save_percentage, penalties_saved

**`player_matches`** - szczegółowe statystyki z pojedynczych meczów
- player_id, match_date, competition, opponent, result
- goals, assists, minutes, shots, xg, xa, passes, tackles, etc.

## 🛠️ Narzędzia CLI

### Dodawanie graczy

#### Interaktywne dodanie (rekomendowane)
```powershell
python quick_add_player.py
```
Skrypt zapyta o:
- Imię i nazwisko
- Klub
- Liga
- Pozycja (FW/MF/DF/GK)
- Czy bramkarz (y/n)

#### Automatyczne dodanie z synchronizacją
```powershell
python quick_add_player.py "Krzysztof Piątek" "Istanbul Basaksehir" "Super Lig" "FW" --sync
```
**Parametry:**
- `"Imię Nazwisko"` - pełne nazwisko gracza
- `"Klub"` - nazwa klubu
- `"Liga"` - nazwa ligi
- `"Pozycja"` - FW (napastnik), MF (pomocnik), DF (obrońca), GK (bramkarz)
- `--sync` - automatycznie zsynchronizuj statystyki i matchlogs

**Ta komenda:**
1. Dodaje gracza do bazy
2. Synchronizuje statystyki sezonowe (wszystkie sezony)
3. Synchronizuje matchlogs (sezon 2025-2026)

#### Ręczne dodanie przez kod (dla deweloperów)
```powershell
# Edytuj plik add_piatek_manual.py i uruchom
python add_piatek_manual.py
```
Plik `add_piatek_manual.py` to przykład jak dodać gracza bezpośrednio przez kod Python.

### Zarządzanie bazą
```powershell
# Migracje Alembic
alembic upgrade head
alembic downgrade -1

# Weryfikacja pakietów
python tools/check_reqs.py
```

## 🚀 Quick Reference - Najważniejsze komendy

### Synchronizacja

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔄 Zsynchronizuj gracza | `python sync_playwright.py "Lewandowski"` |
| 📊 Sync wszystkich | `python sync_all_playwright.py` |
| 🎯 Sync matchlogs | `python sync_match_logs.py "Lewandowski"` |
| 📅 Sync graczy bez danych | `python sync_missing_players.py` |
| 🤖 **Automatyczna sync (scheduler)** | **Ustaw `ENABLE_SCHEDULER=true` w `.env`** |
| 🧪 Test emaila | `python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, [])"` |

### Synchronizacja (pełne przykłady)

| Co chcesz zrobić | Komenda | Czas |
|------------------|---------|------|
| 📊 Zaktualizuj gracza (szybko) | `python sync_playwright.py "Nazwisko"` | ~15s |
| 📚 Pełna historia gracza | `python sync_playwright.py "Nazwisko" --all-seasons` | ~30-60s |
| 👥 Wszyscy gracze (szybko) | `python sync_all_playwright.py` | ~20 min |
| 👥 Wszyscy gracze (pełna historia) | `python sync_all_playwright.py --all-seasons` | ~2-3h |
| 🏆 Szczegóły meczów | `python sync_match_logs.py "Nazwisko"` | ~15s |
| 🏆 Szczegóły meczów (inny sezon) | `python sync_match_logs.py "Nazwisko" --season 2024-2025` | ~15s |

### Dodawanie graczy

| Co chcesz zrobić | Komenda |
|------------------|---------|
| ➕ Dodaj gracza (interaktywnie) | `python quick_add_player.py` |
| 🚀 Dodaj + sync wszystko | `python quick_add_player.py "Imię" "Klub" "Liga" "Poz" --sync` |
| 🔧 Dodaj ręcznie (kod) | `python add_piatek_manual.py` |

### Uruchamianie

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔧 Backend API | `.\start_backend.ps1` lub `python -m uvicorn app.backend.main:app --reload` |
| 🎨 Frontend Dashboard | `.\start_frontend.ps1` lub `streamlit run app/frontend/streamlit_app.py` |

### API Endpoints

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Strona główna API |
| `/health` | GET | Health check (dla monitoringu) |
| `/api/players` | GET | Lista wszystkich graczy z filtrami |
| `/api/players/{id}` | GET | Szczegóły gracza + statystyki |
| `/api/players/{id}/competition-stats` | GET | Statystyki po rozgrywkach |
| `/api/players/{id}/matches` | GET | Match logs gracza |
| `/api/players/{id}/matches/stats` | GET | Statystyki zagregowane z meczów |
| `/api/comparison/compare` | GET | Porównaj dwóch graczy |
| `/api/matchlogs` | GET | Wszystkie match logs z filtrami |

**📚 Dokumentacja API:**
- **Swagger UI (interaktywna):** http://localhost:8000/docs
- **ReDoc (czytelna):** http://localhost:8000/redoc

**💡 Swagger UI Features:**
- ✅ Testuj endpointy bezpośrednio w przeglądarce
- ✅ Zobacz wszystkie parametry i response schemas
- ✅ Przykładowe requesty i responses
- ✅ Automatyczna walidacja

---

## 📚 Dokumentacja szczegółowa

### 📖 Dokumentacja projektu
- 📘 [Backend API - Dokumentacja](app/backend/README.md)
- 📗 [Frontend - Dokumentacja](app/frontend/README.md)
- 📄 [Stack technologiczny](STACK.md)
- 📚 [Documentation Index (ENG)](DOCUMENTATION_INDEX.md) - Pełny indeks dokumentacji
- 📚 [Dokumentacja Index (PL)](DOKUMENTACJA_INDEX.md) - Pełny indeks dokumentacji
- 🔐 [Email Setup Guide](EMAIL_SETUP_GUIDE.md) - Konfiguracja Gmail/Outlook/SendGrid
- 📋 [Classification Rules](CLASSIFICATION_RULES.md) - Reguły klasyfikacji rozgrywek
- 🏗️ [Architecture Diagram](ARCHITECTURE_DIAGRAM.md) - Diagram architektury systemu
- 🚀 [Render Deployment Guide](RENDER_DEPLOYMENT.md) - **Darmowy hosting 24/7!**
- ☁️ [Streamlit Cloud Deployment](STREAMLIT_CLOUD_DEPLOYMENT.md) - **Darmowy hosting frontendu!**
- 🏢 [Commercial Deployment Guide](COMMERCIAL_DEPLOYMENT.md) - **PostgreSQL + Streamlit Cloud**
- 📖 [API Documentation](API_DOCUMENTATION.md) - Szczegółowa dokumentacja API
- 📖 [API Endpoints Guide](API_ENDPOINTS_GUIDE.md) - Przewodnik po endpointach
- ⚖️ [Legal Notice](LEGAL_NOTICE.md) - **WAŻNE - Przeczytaj przed użyciem!**
- 🎓 [Credits](CREDITS.md) - Podziękowania i atrybuty

### 🌐 Linki zewnętrzne
- 🌐 [FBref (źródło danych)](https://fbref.com/)
- 📖 [FastAPI Docs](https://fastapi.tiangolo.com/)
- 🎨 [Streamlit Docs](https://docs.streamlit.io/)
- 🎭 [Playwright Docs](https://playwright.dev/python/)

## ☁️ Cloud Deployment (Darmowy hosting 24/7!)

### 🚀 Opcja 1: Render.com - Backend + Supabase (DARMOWE!)

**Dla hobby/testów - Darmowy Plan:**
- ✅ **$0/miesiąc** - całkowicie darmowe!
- ✅ **24/7 uptime** - scheduler działa bez Twojego komputera
- ✅ **Automatyczne deploye** - push do GitHub = auto update
- ✅ **Persistent disk** - baza danych nie ginie
- ✅ **Email notifications** - działają w chmurze

**Setup (15 minut):**
1. Push projektu do GitHub
2. Zarejestruj się na https://render.com
3. Połącz repozytorium
4. Render wykrywa `render.yaml` automatycznie! ✨
5. Dodaj zmienne środowiskowe (email)
6. Deploy!

**Szczegółowa instrukcja:** [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

---

### 🏢 Opcja 2: Komercyjny Deployment (PostgreSQL + Streamlit Cloud)

**Dla aplikacji komercyjnych:**
- ✅ **PostgreSQL** w chmurze (Supabase/Railway/Render)
- ✅ **Streamlit Cloud** - frontend dashboard
- ✅ **Skalowalna architektura**
- ✅ **Automatyczne backupy**
- ✅ **Connection pooling**

**Stack:**
```
Frontend: Streamlit Cloud (darmowe!)
Backend:  Render.com (FastAPI + Scheduler)
Database: Supabase PostgreSQL (darmowe 500 MB)
Email:    SendGrid (darmowe 100/dzień)
```

**Koszty:** $0-52/miesiąc (zależnie od skali)

**Szczegółowa instrukcja:** [COMMERCIAL_DEPLOYMENT.md](COMMERCIAL_DEPLOYMENT.md)

---

### 🖥️ Lokalny deployment (wymaga włączonego komputera)

**Windows Task Scheduler:**
- Automatyczne uruchomienie po restarcie
- Backend działa w tle

**Raspberry Pi:**
- Niskie zużycie energii (~3W)
- Zawsze włączony
- ~200-300 zł jednorazowo

**Instrukcje:** Zobacz [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

---

## 🐛 Rozwiązywanie problemów

### Backend nie startuje
```powershell
# Sprawdź czy port 8000 jest wolny
netstat -ano | findstr :8000

# Uruchom na innym porcie
python -m uvicorn app.backend.main:app --port 8001
```

### Frontend pokazuje błąd połączenia
```powershell
# Upewnij się że backend działa
Invoke-RestMethod http://localhost:8000/health

# Uruchom backend jeśli nie działa
.\start_backend.ps1
```

### Brak Playwright/Chromium
```powershell
python -m playwright install chromium
python -m playwright install-deps chromium  # Linux: zainstaluj system dependencies
```

### Błędy synchronizacji
```powershell
# Sprawdź logi
# Backend wyświetla szczegółowe logi w konsoli

# Przetestuj pojedynczego gracza
python sync_playwright.py "Robert Lewandowski" --visible

# Debug mode z widoczną przeglądarką
python sync_playwright.py "Lewandowski" --visible
```

### Scheduler nie działa
```powershell
# Sprawdź czy jest włączony w .env
ENABLE_SCHEDULER=true

# Sprawdź logi backendu
# Powinno być: "✅ Scheduler uruchomiony"
# Jeśli nie ma - sprawdź .env

# Sprawdź następną synchronizację
# Logi: "📅 Next run: 2025-01-27 06:00:00+01:00"
```

### Email nie wysyła się
```powershell
# Test emaila
python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, []); print('Email sent!')"

# Sprawdź konfigurację
# Zobacz: EMAIL_SETUP_GUIDE.md
# Użyj Gmail App Password (nie zwykłe hasło!)
```

## 📊 Statystyki projektu

- **100+** polskich piłkarzy śledzonych
- **20+** europejskich lig
- **4 typy rozgrywek**: Liga, Puchary Europejskie, Reprezentacja, Puchary krajowe
- **30+** statystyk per gracz (gracze) + **15+** statystyk (bramkarze)
- **Rate limiting**: 12s między requestami (bezpieczne dla FBref ToS)
- **Automatyczna synchronizacja**: 2x w tygodniu (Poniedziałek/Czwartek 6:00)
- **Cloud deployment ready**: Render.com, Railway, DigitalOcean, AWS
- **Email notifications**: HTML raporty z wynikami synchronizacji

## 🤝 Wkład w projekt

Projekt jest otwarty na sugestie i poprawki. W przypadku znalezienia błędów lub pomysłów na ulepszenia:
1. Sprawdź istniejące issues
2. Utwórz nowy issue z opisem
3. Pull requesty są mile widziane!

## 📝 Changelog

### v0.6.0 (2025-01) - Matchlogs Scheduler 📋
- 📋 **Matchlogs Scheduler** - automatyczna synchronizacja szczegółowych logów meczowych
  - Nowy job schedulera: wtorek 7:00 (Europe/Warsaw)
  - Funkcja `scheduled_sync_matchlogs()` - sync dla wszystkich graczy
  - Funkcja `sync_player_matchlogs()` - sync pojedynczego gracza
  - Rate limiting 12s między requestami
- 📧 **Email Notifications dla Matchlogs** - dedykowane HTML raporty
  - Podsumowanie liczby zsynchronizowanych meczów
  - Lista graczy z błędami synchronizacji
  - Kolorowe formatowanie (niebieski header)
- 📊 **Rozszerzone dane meczowe**
  - Szczegółowe statystyki dla każdego meczu
  - Goals, assists, xG, xA, shots, passes, tackles
  - Touches, dribbles, fouls, cards
- 📚 **Dokumentacja**
  - `MATCHLOGS_SCHEDULER.md` - pełna dokumentacja funkcjonalności
  - Zaktualizowany README
  - Rozszerzone API docs

### v0.5.0 (2025-01) - Cloud Deployment & Email Notifications 🚀
- ☁️ **Render.com Deployment** - darmowy hosting 24/7
  - Konfiguracja `render.yaml` i `Dockerfile`
  - Persistent disk dla bazy danych
  - Automatyczne deploye z GitHub
  - Dokumentacja: `RENDER_DEPLOYMENT.md`
- 📧 **Email Notifications** - HTML raporty po synchronizacji
  - Gmail/Outlook/SendGrid support
  - App Password authentication
  - Szczegółowe raporty z wynikami i błędami
  - Dokumentacja: `EMAIL_SETUP_GUIDE.md`
- 🌍 **Timezone Support** - scheduler w polskim czasie
  - `SCHEDULER_TIMEZONE=Europe/Warsaw`
  - Automatyczne wykrywanie czy działa na Render czy lokalnie
- 📚 **Rozszerzona dokumentacja**
  - `DEPLOYMENT_SUMMARY.md` - FAQ i troubleshooting
  - Zaktualizowany README z wszystkimi funkcjami
  - Swagger UI i ReDoc z pełną dokumentacją API

### v0.4.0 (2025-01) - Playwright Upgrade & Scheduler 🚀
- ✨ **Playwright Scraper** - modernizacja scrapera z użyciem headless browser
  - Zastąpiono cloudscraper Playwright
  - Lepsza stabilność i niezawodność
  - Rate limiting 12s (zgodny z ToS FBref)
- ✨ **Scheduler** - automatyczna synchronizacja 2x w tygodniu
  - Poniedziałek i czwartek o 6:00 (Europe/Warsaw)
  - Async scheduler z APScheduler
- 🔧 **API v2** - nowe endpointy z prefiksem `/api`
  - `/api/players`, `/api/comparison`, `/api/matches`, `/api/matchlogs`
  - Health check endpoint: `/health`
- 📊 **Ulepszone statystyki** - pełne rozbicie na typy rozgrywek
  - Liga, Puchary Europejskie, Reprezentacja, Puchary krajowe
  - Dedykowane statystyki bramkarzy

### v0.3.0 (2025-11) - FBref Integration
- ✨ FBref Web Scraper (cloudscraper)
- 📊 92/97 graczy zsynchronizowanych

### v0.2.0 (2025-11)
- ✨ APScheduler, live matches

### v0.1.0
- 🎉 Pierwsza wersja

## 📝 Licencja

MIT License - Projekt edukacyjny

---

**Made with ❤️ for Polish football fans**
