# 🇵🇱 Polish Football Data Hub International

**Status:** ✅ Production Ready | **Database:** PostgreSQL (Supabase) | **Deployment:** Cloud-Ready

> 📊 Real-time monitoring and analysis of 90+ Polish footballers playing abroad

## 🎯 Project Overview

This project demonstrates the use of **web scraping** to regularly fetch and process current player statistics from **fbref.com**. The **FastAPI-based backend** cyclically updates the database, while the **Streamlit frontend** enables quick data viewing in a user-friendly format. The platform is built on mechanisms that automate data retrieval, validation, and presentation.

**Key Technologies & Techniques:**
- 🕸️ **Web Scraping:** Playwright headless browser for dynamic content extraction
- 🔄 **Automation:** APScheduler for periodic data synchronization (2-3x/week)
- 🛡️ **Data Validation:** Pydantic models for type safety and schema validation
- 🗄️ **Database ORM:** SQLAlchemy 2.0+ with Alembic migrations
- 🔐 **Rate Limiting:** 12-second delays between requests (FBref ToS compliant)
- 📊 **Data Processing:** pandas for statistics aggregation and transformation
- 🎨 **Interactive Visualization:** Streamlit with Plotly charts
- 🔗 **RESTful API:** FastAPI with auto-generated OpenAPI documentation
- 📧 **Notifications:** SMTP email reports after each synchronization

## 🌐 Live Application

**Try it now:** [https://polish-football-data-international-tracker.streamlit.app/](https://polish-football-data-international-tracker.streamlit.app/)

### 📱 How to Use:

1. **Browse Players** - View all tracked Polish footballers with their current statistics
2. **Filter Data** - Use sidebar filters to narrow down by:
   - League (Bundesliga, La Liga, Serie A, etc.)
   - Team
   - Position (GK, DF, MF, FW)
   - Competition Type (League, European Cups, National Team)
   - Season
3. **Compare Players** - Click "Compare Players" in sidebar to compare two players side-by-side
4. **Export Data** - Download filtered data as CSV for your own analysis

**📊 Data Updates:** Automatically synchronized 3x per week (Monday, Thursday, Tuesday) from FBref.com

---  
> ⚖️ **[Legal Notice - Important!](docs/LEGAL_NOTICE.md)** | 🚀 **[Deployment Guide](docs/STREAMLIT_CLOUD_DEPLOYMENT.pl.md)**

## ⚖️ Legal Notice

**This is an educational, non-commercial project.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Educational and portfolio purposes only
- **NOT for commercial use** without proper licensing
- **See [docs/LEGAL_NOTICE.md](docs/LEGAL_NOTICE.md) for full details**

# 🇵🇱 Polish Football Data Hub International

Modern system for monitoring Polish footballers playing abroad. Automatic statistics synchronization from FBref.com using Playwright, advanced data analysis, and interactive dashboard.

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

**Disclaimer:** Polish Football Data Hub International is an independent project and is not affiliated with, endorsed by, or connected to FBref.com or Sports Reference LLC. For official statistics and in-depth analysis, please visit [FBref.com](https://fbref.com/).

---

## ✨ Key Features

### 🕸️ FBref Playwright Scraper
- **Automatic scraping** of data from FBref.com using Playwright (headless browser)
- **Advanced field player statistics**: matches, goals, assists, xG, xA, xGI, G+A/90, minutes, cards
- **Goalkeeper statistics**: saves, clean sheets, save %, penalties, PSxG (Post-Shot xG)
- **Rate limiting**: 12s between requests (ToS compliant)
- **Competition breakdown**: League, European Cups (UCL/UEL/UECL), National Team (CALENDAR YEAR!), Domestic Cups
- **Match logs**: Detailed match statistics for each player
- **Tracking 90+ Polish footballers** from European leagues

### 📊 Backend API (FastAPI)
- **RESTful API** with automatic Swagger/ReDoc documentation
- **Endpoints**: players, comparisons, statistics, matchlogs
- **Database**: PostgreSQL (Supabase - free 500MB!)
- **Scheduler**: automatic synchronization
  - Stats: 2x per week (Monday/Thursday 6:00 AM)
  - Matchlogs: 1x per week (Tuesday 7:00 AM)
- **Email notifications**: HTML reports after each sync
- **Rate limiting**: 12 seconds between requests (FBref ToS compliant)
- **Cloud deployment**: ready for Render.com deployment (free hosting!)

### 🎨 Frontend Dashboard (Streamlit)
**Multi-page application** with interactive dashboard and player comparison

#### 🏠 Main Page (`streamlit_app_cloud.py`)
- **Interactive filtering**: league, team, position, competition type, season
- **Player search** by name
- **Views**: player cards, tables, top scorers charts
- **Enhanced Stats in Details**: xGI, per 90 metrics (xG/90, xA/90, npxG/90, xGI/90, G+A/90)
- **National Team (2025)**: Stats by calendar year (from player_matches table)
- **Season Statistics History**: Full history of all seasons (without Shots/SoT columns)
- **CSV Export**: export filtered data
- **Dedicated goalkeeper statistics**

#### ⚖️ Compare Players (`pages/2_Compare_Players.py`)
- **Side-by-side comparison** of two players with visualizations
- ⚽ Field players vs field players
- 🧤 Goalkeepers vs goalkeepers  
- ⚠️ Prevents invalid comparisons (GK vs field player)
- 📊 Radar and bar charts
- 📈 Per 90 minutes statistics comparison

#### 🔌 API Client (`api_client.py`)
- **Smart backend connection**:
  - ☁️ Streamlit Cloud: uses `st.secrets["BACKEND_API_URL"]`
  - 💻 Local: uses `os.getenv("API_BASE_URL")` or `localhost:8000`
  - ✅ Automatic environment detection
- **Error handling**: clear error messages
- **Caching**: optimized API queries

### 🔄 Data Synchronization
- **CLI Scripts**: `sync_player_full.py`, `sync_match_logs.py`
- **Automatic scheduler**: background synchronization (backend on Render)
  - Player stats: Monday and Thursday 6:00 AM
  - Detailed matchlogs: Tuesday 7:00 AM
  - Email notifications after each sync
- **Cron-job.org**: wakes up backend before sync (5:55, 6:55)
- **Retry mechanism**: automatic retries for failed syncs

## ⚡ Quick Start - Most Common Commands

### Run the application
```powershell
.\start_backend.ps1    # Backend API (port 8000)
.\start_frontend.ps1   # Dashboard (port 8501)
```

### Sync single player (all seasons)
```powershell
python sync_player_full.py "Robert Lewandowski" --all-seasons
```

### Sync match details (matchlogs - current season)
```powershell
python sync_match_logs.py "Robert Lewandowski"
```

### Automatic synchronization (recommended!)
Backend on Render automatically syncs all players:
- **Monday and Thursday at 6:00 AM** - full statistics
- **Tuesday at 7:00 AM** - match logs
- **Email notifications** after each sync

**Nie musisz ręcznie synchronizować!** 🤖
```

---

## 🚀 Full Installation

### Prerequisites
- Python 3.10+
- Playwright (Chromium)
- PostgreSQL (Supabase - free for hobby projects)

### 1. Install Dependencies

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install pakiety
pip install -r requirements.txt

# Install Playwright Chromium
python -m playwright install chromium
```

### 2. Configuration

Utwórz file `.env` w głównym katalogu (or copy from `.env.example`):

```env

# Baza danych (Production - Supabase PostgreSQL - DARMOWE!)
# DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
# 📖 Pełna instrukcja: SUPABASE_MIGRATION_GUIDE.md

# Scheduler (włącz dla automatycznej synchronizacji 2x w tygodniu)
ENABLE_SCHEDULER=false

# Timezone dla schedulera (domyślnie Europe/Warsaw)
SCHEDULER_TIMEZONE=Europe/Warsaw

# Email notifications (Optional - scheduler działa bez nich!)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Użyj Gmail App Password!
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**📧 Email Setup:**
- **Required**: Gmail App Password (nie zwykłe hasło!)
- **Instructions**: See [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)
- **Optional**: Scheduler działa bez emaili (tylko logi w konsoli)

### 3. Run the Application

```powershell
# Start backend (port 8000)
.\start_backend.ps1

# Start frontend (port 8501)
.\start_frontend.ps1
```

**Access the application:**
- 🔧 **Backend API (Swagger UI):** http://localhost:8000/docs
- 📖 **Backend API (ReDoc):** http://localhost:8000/redoc
- 🏥 **Backend Health Check:** http://localhost:8000/health
- 🎨 **Frontend Dashboard:** http://localhost:8501

**💡 Tip:** Swagger UI allows testing API directly in your browser!

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
- ✅ Competition stats i match logs sezonu 2025-2026 dla all players
- ✅ Liga krajowa + Puchary Europejskie + Reprezentacja
- ✅ Rate limiting: 12 sekund między każdym graczem
- ✅ Email z raportem po zakończeniu (opcjonalnie)

**Wymagania:**
- ⚠️ Backend musi być Startiony 24/7
- ⚠️ Komputer musi być włączony (or użyj cloud deployment!)

**Cloud deployment:** See [DEPLOYMENT.md](DEPLOYMENT.md) for free 24/7 hosting!

---

### ⚡ Manualna synchronizacja

#### Synchronize single player

```powershell
# Pełna synchronizacja - all seasons (competition stats + match logs)
python sync_player_full.py "Robert Lewandowski" --all-seasons

# Tylko match logs dla obecnego sezonu (2025-2026)
python sync_match_logs.py "Robert Lewandowski"

# Match logs dla konkretnego sezonu
python sync_match_logs.py "Robert Lewandowski" --season 2024-2025
```

**Co synchronizuje:**
- **sync_player_full.py**: Competition stats + match logs ze all sezonów kariery
- **sync_match_logs.py**: Tylko szczegółowe match logs (data, przeciwnik, wynik, gole, asysty, xG, xA, podania, etc.)

#### Automatyczna synchronizacja all players (zalecane!)

Backend on Render automatically syncs all players:
- **Poniedziałek i Czwartek o 6:00** - pełne statystyki (all seasons)
- **Wtorek o 7:00** - match logs (current season)
- **Email powiadomienia** z raportem po każdej synchronizacji
- **Cron-job.org** budzi backend 5 minut przed synchronizacją

**Nie musisz ręcznie synchronizować!** Scheduler robi to automatically. 🤖

Ręczna synchronizacja potrzebna tylko dla:
- New players (dodaj i sync ręcznie)
- Natychmiastowej aktualizacji (nie chcesz czekać do Pon/Czw/Wt)

### Automatyczna synchronizacja (Scheduler)

Ustaw w file `.env`:
```env
ENABLE_SCHEDULER=true
```

Scheduler automatically Synchronizee all players:
- **Poniedziałek 6:00** - dzień po meczach weekendowych
- **Czwartek 6:00** - dzień po meczach Ligi Mistrzów

## 📡 API Endpoints

### Players
- `GET /api/players` - Lista wszystkich graczy
- `GET /api/players/{id}` - Szczegóły gracza
- `GET /api/players/stats/competition` - Wszystkie statystyki ligowe/europejskie
- `GET /api/players/stats/goalkeeper` - Wszystkie statystyki bramkarskie
- `GET /api/players/stats/matches` - Wszystkie mecze (match logs)

### Comparison
- `GET /api/comparison/compare` - Porównaj dwóch graczy
- `GET /api/comparison/players/{id}/stats` - Statystyki gracza
- `GET /api/comparison/available-stats` - Dostępne statystyki

### Matchlogs (Szczegóły meczów)
- `GET /api/matchlogs/{player_id}` - Match logs gracza (z filtrami)
- `GET /api/matchlogs/{player_id}/stats` - Agregowane statystyki z meczów
- `GET /api/matchlogs/match/{match_id}` - Szczegóły pojedynczego meczu

## 📁 Struktura projektu

```
polish-players-tracker/
├── .env                          # Konfiguracja (gitignored)
├── .env.example                  # Przykładowa konfiguracja
├── .gitignore
├── requirements.txt              # Zależności Python (Backend)
├── alembic.ini                   # Konfiguracja migracji bazy danych
│
├── api_client.py                 # API client (Streamlit Cloud)
├── streamlit_app_cloud.py        # Główna aplikacja Streamlit Cloud
├── pages/                        # Strony Streamlit Cloud (multi-page)
│   └── 2_Compare_Players.py      # Porównywanie graczy (cloud)
│
├── sync_player_full.py           # Skrypt: pełna synchronizacja gracza
├── sync_competition_stats.py     # Skrypt: synchronizacja statystyk z meczów
├── sync_match_logs.py            # Skrypt: synchronizacja match logs
│
├── alembic/                      # Migracje bazy danych
│   └── versions/                 # Wersje migracji
│
├── app/
│   ├── backend/                  # Backend FastAPI
│   │   ├── __init__.py
│   │   ├── main.py               # Główna aplikacja + scheduler
│   │   ├── config.py             # Konfiguracja
│   │   ├── database.py           # Połączenie z bazą
│   │   ├── README.md             # Dokumentacja backend
│   │   ├── models/               # Modele SQLAlchemy (ORM)
│   │   │   ├── __init__.py
│   │   │   ├── player.py         # Model Player
│   │   │   ├── competition_stats.py  # Statystyki według rozgrywek
│   │   │   ├── goalkeeper_stats.py   # Statystyki bramkarskie
│   │   │   ├── player_match.py   # Matchlogs (szczegóły meczów)
│   │   │   └── season_stats.py   # Statystyki sezonowe (agregowane)
│   │   ├── routers/              # API Endpoints
│   │   │   ├── __init__.py
│   │   │   ├── players.py        # /api/players
│   │   │   ├── comparison.py     # /api/comparison
│   │   │   └── matchlogs.py      # /api/matchlogs
│   │   ├── schemas/              # Pydantic schemas (API contracts)
│   │   │   ├── __init__.py
│   │   │   └── player.py         # Player response schemas
│   │   └── services/             # Business logic
│   │       ├── __init__.py
│   │       └── fbref_playwright_scraper.py  # Web scraping FBref
│   │
│   └── frontend/                 # Frontend Streamlit (Local Development)
│       ├── streamlit_app.py      # Główna aplikacja (LOCAL)
│       ├── api_client.py         # API client
│       ├── requirements.txt      # Zależności frontend
│       ├── README.md             # Dokumentacja frontend
│       └── pages/                # Strony (multi-page app)
│           └── 2_⚖️_compare_players.py  # Porównywanie graczy (local)
│
├── .streamlit/                   # Konfiguracja Streamlit
│   ├── config.toml               # Theme i ustawienia UI
│   └── secrets.toml.example      # Przykład secrets (BACKEND_API_URL)
│
├── start_backend.ps1             # Skrypt startowy backend
├── start_frontend.ps1            # Skrypt startowy frontend
│
└── 
```

## 🗄️ Baza danych

### 💾 PostgreSQL (Supabase)
- **Jedyna wspierana baza danych** - stabilna, skalowalna, darmowa!
- ✅ **500 MB storage** (wystarczy dla setek players)
- ✅ **Automatyczne backupy**
- ✅ **Dashboard do przeglądania danych**
- ✅ **Connection pooling**
- ✅ **DARMOWE NA ZAWSZE** dla projektów hobby!

### 🚀 Configuration (5 minut):
```powershell
# 1. Zarejestruj się: https://supabase.com (DARMOWE!)
# 2. Utwórz projekt
# 3. Skopiuj DATABASE_URL z Settings → Database → Connection string
# 4. Dodaj do .env:
DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# 5. Start migracje (tworzy tabele):
alembic upgrade head
```

**📖 Szczegółowa instrukcja:** [SUPABASE_GUIDE.md](SUPABASE_GUIDE.md)

---

## 🗄️ Struktura bazy danych

### Główne tabele:

**`players`** - basic player information
- id, name, team, league, position, nationality, is_goalkeeper, api_id, last_updated

**`competition_stats`** - statystyki zawodników (nie-bramkarzy)
- player_id, season, competition_type, competition_name
- games, goals, assists, xg, xa, npxg, minutes, yellow_cards, red_cards, penalty_goals
- **competition_type:** LEAGUE, EUROPEAN_CUP, DOMESTIC_CUP, NATIONAL_TEAM
- **Uwaga:** Mecze reprezentacji używają roku kalendarzowego (np. "2025"), nie sezonu ("2025-2026")
- **Ograniczenie:** Kwalifikacje Champions League są agregowane z Europa League jako "Europa Lg" (standard FBref)

**`goalkeeper_stats`** - statystyki bramkarzy
- player_id, season, competition_type, competition_name
- games, saves, clean_sheets, goals_against, save_percentage, penalties_saved
- **Uwaga:** Te same zasady co competition_stats dla sezonów i typów rozgrywek

**`player_matches`** - szczegółowe statystyki z pojedynczych meczów
- player_id, match_date, competition, opponent, result
- goals, assists, minutes, shots, xg, xa, passes, tackles, etc.

## 🛠️ Narzędzia CLI

### Dodawanie players

Gracze są dodawani bezpośrednio do bazy danych PostgreSQL (Supabase), a następnie synchronizowani za pomocą skryptów sync.

**Przykład dodania gracza:**
```python
# create_player.py
from app.backend.database import SessionLocal
from app.backend.models.player import Player

db = SessionLocal()

new_player = Player(
    name="Krzysztof Piątek",
    team="Istanbul Basaksehir",
    league="Super Lig",
    position="FW",
    nationality="Poland",
    is_goalkeeper=False
)

db.add(new_player)
db.commit()
print(f"✅ Dodano: {new_player.name}")
db.close()
```

**Następnie zsynchronizuj statystyki:**
```powershell
python sync_player_full.py "Krzysztof Piątek" --all-seasons
```

**Ta komenda:**
1. Wyszukuje gracza na FBref.com
2. Synchronizuje statystyki sezonowe (wszystkie sezony)
3. Synchronizuje matchlogs (obecny sezon 2025-2026)

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
| 🔄 Synchronize player (all seasons) | `python sync_player_full.py "Lewandowski" --all-seasons` |
| 🎯 Sync matchlogs (current season) | `python sync_match_logs.py "Lewandowski"` |
| 📅 Sync players bez danych | `python sync_missing_players.py` |
| 🤖 **Automatic sync (scheduler)** | **Backend on Render - automatically Mon/Thu/Tue** |
| 🧪 Test emaila | `python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, [])"` |

### Synchronizacja (pełne przykłady)

| Co chcesz zrobić | Komenda | Czas |
|------------------|---------|------|
| 📚 Pełna synchronizacja player (all seasons) | `python sync_player_full.py "Nazwisko" --all-seasons` | ~60s |
| 🏆 Szczegóły meczów (current season) | `python sync_match_logs.py "Nazwisko"` | ~15s |
| 🏆 Szczegóły meczów (konkretny sezon) | `python sync_match_logs.py "Nazwisko" --season 2024-2025` | ~15s |
| 🤖 Wszyscy gracze (automatically) | **Scheduler na Render (Pon/Czw 6:00, Wt 7:00)** | ~20-30 min |

**💡 Zalecenie:** Używaj schedulera do regularnych aktualizacji. Ręcznie synchronizuj tylko New players or gdy potrzebujesz natychmiastowej aktualizacji.

### Dodawanie graczy

Aby dodać nowego gracza, ręcznie dodaj go do bazy danych, a następnie zsynchronizuj:

```powershell
# Synchronizuj nowego gracza (automatycznie znajdzie go na FBref)
python sync_player_full.py "Nazwisko Gracza" --all-seasons
```

### Uruchamianie

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔧 Backend API | `.\start_backend.ps1` or `python -m uvicorn app.backend.main:app --reload` |
| 🎨 Frontend Dashboard | `.\start_frontend.ps1` or `streamlit run app/frontend/streamlit_app.py` |

### API Endpoints

**Documentation interaktywna:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Główne endpointy:**

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Strona główna API + scheduler status |
| `/health` | GET | Health check (dla monitoringu) |
| `/api/players/` | GET | Lista all players |
| `/api/players/{id}` | GET | Szczegóły player |
| `/api/players/stats/competition` | GET | Wszystkie statystyki ligowe/europejskie |
| `/api/players/stats/goalkeeper` | GET | Wszystkie statystyki bramkarskie |
| `/api/players/stats/matches` | GET | Wszystkie mecze (match logs) |
| `/api/comparison/players/{id}/stats` | GET | Player statistics do porównania |
| `/api/comparison/compare` | GET | Porównaj dwóch players |
| `/api/comparison/available-stats` | GET | Dostępne statystyki do porównania |
| `/api/matchlogs/{player_id}` | GET | Player match logs (with filters) |
| `/api/matchlogs/{player_id}/stats` | GET | Agregowane statystyki z meczów |
| `/api/matchlogs/match/{match_id}` | GET | Szczegóły pojedynczego meczu |

**📚 Documentation API:**
- **Swagger UI (interaktywna):** http://localhost:8000/docs
- **ReDoc (czytelna):** http://localhost:8000/redoc

**💡 Swagger UI Features:**
- ✅ Testuj endpointy bezpośrednio w przeglądarce
- ✅ See wszystkie parametry i response schemas
- ✅ Przykładowe requesty i responses
- ✅ Automatyczna walidacja

---

## 📚 Documentation

### 🎓 Essential Guides

**Getting Started:**
- 📖 **[README.md](README.md)** - You are here! Complete overview and quick start
- 🚀 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deploy to production (FREE hosting!)
- 🔧 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solutions for common issues

**Reference:**
- 📚 **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- 🛠️ **[STACK.md](STACK.md)** - Technology stack overview  
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute

**Legal:**
- ⚖️ **[LEGAL_NOTICE.md](LEGAL_NOTICE.md)** - Data attribution (**Important!**)
- 📜 **[CREDITS.md](CREDITS.md)** - Technologies and data sources
- 📄 **[LICENSE](LICENSE)** - MIT License

**Polish Versions:**  
All documentation is available in Polish with `.pl.md` extension (e.g., `README.pl.md`)

### 🔗 Quick Links

**Live Application:**
- 🌐 **[Try it now!](https://polish-football-data-international-tracker.streamlit.app/)** - Live demo

**API Documentation (Local):**
- 📊 **[Swagger UI](http://localhost:8000/docs)** - Interactive API testing
- 📖 **[ReDoc](http://localhost:8000/redoc)** - Alternative API docs

**External Resources:**
- 🌐 [FBref.com](https://fbref.com/) - Data source
- 📖 [FastAPI Docs](https://fastapi.tiangolo.com/)
- 🎨 [Streamlit Docs](https://docs.streamlit.io/)

## ☁️ Cloud Deployment (Free 24/7 hosting!)

### 🚀 Option 1: Render.com - Backend + Supabase (FREE!)

**Dla hobby/testów - Darmowy Plan:**
- ✅ **$0/miesiąc** - całkowicie darmowe!
- ✅ **24/7 uptime** - scheduler działa bez Twojego komputera
- ✅ **Automatyczne deploye** - push do GitHub = auto update
- ✅ **Supabase PostgreSQL** - baza danych w chmurze (darmowe!)
- ✅ **Email notifications** - działają w chmurze

**Setup (15 minut):**
1. Push projektu do GitHub
2. Zarejestruj się na https://render.com
3. Połącz repozytorium
4. Render wykrywa `render.yaml` automatically! ✨
5. Dodaj zmienne środowiskowe (email)
6. Deploy!

**Szczegółowa instrukcja:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

### 🏢 Option 2: Production Deployment (PostgreSQL + Streamlit Cloud)

**Aktualny stack produkcyjny:**
- ✅ **PostgreSQL** w chmurze (Supabase - darmowe 500MB)
- ✅ **Streamlit Cloud** - frontend dashboard (darmowe!)
- ✅ **Render.com** - backend API + scheduler (darmowe!)
- ✅ **Automatyczne backupy** (Supabase)
- ✅ **Connection pooling** (Supabase)

**Deployment stack:**
```
Frontend: Streamlit Cloud (FREE tier)
Backend:  Render.com Web Service (FREE tier)
Database: Supabase PostgreSQL (FREE 500MB)
Sync:     Scheduler na Render (2x/week stats, 1x/week matchlogs)
Email:    Gmail SMTP (opcjonalne)
```

**Koszty:** $0/miesiąc (wszystko na darmowych tierach!)

**Szczegółowa instrukcja:** [STREAMLIT_CLOUD_DEPLOYMENT.pl.md](STREAMLIT_CLOUD_DEPLOYMENT.pl.md)

---

### 🖥️ Lokalny deployment (wymaga włączonego komputera)

**Windows Task Scheduler:**
- Automatyczne Startienie po restarcie
- Backend działa w tle

**Raspberry Pi:**
- Niskie zużycie energii (~3W)
- Zawsze włączony
- ~200-300 zł jednorazowo

**Instructions:** See [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

---

## 🐛 Rozwiązywanie problemów

### 📚 Dedykowane Przewodniki Troubleshooting

- **[TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)** - Problemy z połączeniem do bazy danych (Supabase, Render)
- **[SCHEDULER_STATUS_GUIDE.md](SCHEDULER_STATUS_GUIDE.md)** - Monitoring i Configuration automatycznej synchronizacji
- **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** - Configuration powiadomień email dla schedulera

### Backend won't start
```powershell
# Sprawdź czy port 8000 jest wolny
netstat -ano | findstr :8000

# Start na innym porcie
python -m uvicorn app.backend.main:app --port 8001
```

### Frontend pokazuje błąd połączenia
```powershell
# Upewnij się że backend działa
Invoke-RestMethod http://localhost:8000/health

# Start backend jeśli nie działa
.\start_backend.ps1
```

### Brak Playwright/Chromium
```powershell
python -m playwright install chromium
python -m playwright install-deps chromium  # Linux: Install system dependencies
```

### Błędy synchronizacji
```powershell
# Sprawdź logi
# Backend wyświetla szczegółowe logi w konsoli

# Test single player
python sync_player_full.py "Robert Lewandowski" --all-seasons

# Debug mode z widoczną przeglądarką
python sync_player_full.py "Lewandowski" --all-seasons
```

### PostgreSQL: "duplicate key value violates unique constraint"
```powershell
# Automatyczne naprawienie - Start skrypt naprawczy
python fix_postgres_sequences.py

# Problem rozwiązany automatically w skryptach:
# - sync_player_full.py
# - sync_match_logs.py

# Więcej info: BUGFIX_POSTGRES_SEQUENCES.md
```

### Database Connection Issues (Render/Supabase)

**Problem:** `password authentication failed` or `connection refused`

**Szybkie rozwiązanie:**
1. Sprawdź `DATABASE_URL` w Render Environment
2. Sprawdź format: `postgresql://postgres.PROJECT_REF:PASSWORD@...`
3. Sprawdź hasło w Supabase Dashboard

**Pełny przewodnik:** [TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)

### Scheduler nie działa
```powershell
# Sprawdź czy jest włączony w .env
ENABLE_SCHEDULER=true

# Sprawdź logi backendu
# Powinno być: "✅ Scheduler Startiony"
# Jeśli nie ma - sprawdź .env

# Sprawdź następną synchronizację
# Logi: "📅 Next run: 2025-01-27 06:00:00+01:00"
```

### Email nie wysyła się
```powershell
# Test emaila
python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, []); print('Email sent!')"

# Sprawdź konfigurację
# See: EMAIL_SETUP_GUIDE.md
# Użyj Gmail App Password (nie zwykłe hasło!)
```

## 📊 Statystyki projektu

- **90+** polskich piłkarzy śledzonych
- **20+** europejskich lig
- **4 typy rozgrywek**: Liga, Puchary Europejskie, Reprezentacja, Puchary krajowe
- **30+** statystyk per gracz (gracze) + **15+** statystyk (bramkarze)
- **Rate limiting**: 12s między requestami (bezpieczne dla FBref ToS)
- **Automatyczna synchronizacja**: 2x w tygodniu (Poniedziałek/Czwartek 6:00)
- **Cloud deployment ready**: Render.com, Railway, DigitalOcean, AWS
- **Email notifications**: HTML raporty z wynikami synchronizacji

## ⚠️ Known Limitations

- **Champions League Qualifications**: FBref aggregates CL qualifications with Europa League as "Europa Lg" (industry standard)
- **National Team Stats**: Uses calendar year (e.g., 2025) instead of season format (2025-2026)

## 🤝 Contributing

This project is open to suggestions and improvements. If you find bugs or have ideas:
1. Check existing issues
2. Create a new issue with description
3. Pull requests are welcome!

## 📝 Licencja

MIT License - Projekt edukacyjny

---

**Made with ❤️ for Polish football fans**

