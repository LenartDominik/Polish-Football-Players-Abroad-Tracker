# 🇵🇱 Polish Football Players Abroad

**Status:** ✅ Production Ready | **Database:** PostgreSQL (Supabase) | **Deployment:** Cloud-Ready

> 📊 Real-time monitoring and analysis of 90+ Polish footballers playing abroad

## 🎯 Project Overview

This project demonstrates the use of **RapidAPI integration** to regularly fetch and process current player statistics from **free-api-live-football-data**. The **FastAPI-based backend** cyclically updates the database, while the **Streamlit frontend** enables quick data viewing in a user-friendly format. The platform is built on mechanisms that automate data retrieval, validation, and presentation.

**Key Technologies & Techniques:**
- 🌐 **API Integration**: RapidAPI free-api-live-football-data for professional football data
- 🔄 **Automation**: APScheduler for periodic data synchronization
- 🛡️ **Data Validation**: Pydantic models for type safety and schema validation
- 🗄️ **Database ORM**: SQLAlchemy 2.0+ with Alembic migrations
- ⚡ **Rate Limiting**: API quota monitoring and caching (100 requests/month free tier)
- 📊 **Data Processing**: pandas for statistics aggregation and transformation
- 🎨 **Interactive Visualization**: Streamlit with Plotly charts
- 🔗 **RESTful API**: FastAPI with auto-generated OpenAPI documentation
- 📧 **Notifications**: SMTP email reports after each synchronization

## 🌐 Live Application

**Try it now:** [https://polish-footballers-abroad-tracker.streamlit.app/](https://polish-footballers-abroad-tracker.streamlit.app/)

### 📱 How to Use:

1. **Browse Players** - View all tracked Polish footballers with their current statistics
2. **Filter Data** - Use sidebar filters to narrow down by:
   - League (Bundesliga, La Liga, Serie A, etc.)
   - Team
   - Position (GK, DF, MF, FW)
   - Competition Type (League, European Cups, National Team)
   - Season
3. **Compare Players** - Click "Compare Players" in sidebar to compare two players side-by-side
4. **View Leaderboard** - See top scorers, assists, and ratings by league
5. **Export Data** - Download filtered data as CSV for your own analysis

**📊 Data Updates:** Automatically synchronized 2x per week from RapidAPI

---
> ⚖️ **[Legal Notice - Important!](docs/LEGAL_NOTICE.md)** | 🚀 **[Deployment Guide](docs/STREAMLIT_CLOUD_DEPLOYMENT.pl.md)**

## ⚖️ Legal Notice

**This is an educational, non-commercial project.**

- **Data Source:** RapidAPI free-api-live-football-data
- **Usage:** Educational and portfolio purposes only
- **NOT for commercial use** without proper licensing
- **See [docs/LEGAL_NOTICE.md](docs/LEGAL_NOTICE.md) for full details**

## ✨ Key Features

### 🌐 RapidAPI Integration
- **Professional football data** from free-api-live-football-data API
- **Comprehensive statistics**: goals, assists, cards, ratings, minutes played
- **Goalkeeper statistics**: saves, clean sheets, goals against
- **Competition breakdown**: League, European Cups (UCL/UEL/UECL), National Team, Domestic Cups
- **Match logs**: Detailed match statistics for each player
- **Leaderboards**: Top scorers, assists, ratings by league
- **Live matches**: Track Polish players playing today
- **Tracking 90+ Polish footballers** from European leagues

### 📊 Backend API (FastAPI)
- **RESTful API** with automatic Swagger/ReDoc documentation
- **Endpoints**: players, comparisons, statistics, matchlogs, leaderboard, live
- **Database**: PostgreSQL (Supabase - free 500MB!)
- **Scheduler**: automatic synchronization
  - Stats: 2x per week (Thursday & Sunday 11:00 PM)
  - Match logs: 1x per day (09:00 AM)
  - Cache cleanup: daily (03:00 AM)
  - Quota monitoring: daily (12:00 PM)
- **Email notifications**: HTML reports after each sync
- **Rate limiting**: API quota monitoring (100 requests/month)
- **Cloud deployment**: ready for Render.com deployment (free hosting!)

### 🎨 Frontend Dashboard (Streamlit)
**Multi-page application** with interactive dashboard and player comparison

#### 🏠 Main Page (`streamlit_app_cloud.py`)
- **Interactive filtering**: league, team, position, competition type, season
- **Player search** by name
- **Views**: player cards, tables, top scorers charts
- **Season Statistics History**: Full history of all seasons
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
- **CLI Scripts**: `sync_rapidapi.py`, `sync_single_player.py`
- **Automatic scheduler**: background synchronization (backend on Render)
  - Player stats: Thursday and Sunday 11:00 PM
  - Match logs: Daily 09:00 AM
  - Email notifications after each sync
- **Caching**: Multi-layer cache (lineups 24h, squads 6h, matches 1h)

## ⚡ Quick Start - Most Common Commands

### Run the application
```powershell
.\start_backend.ps1    # Backend API (port 8000)
.\start_frontend.ps1   # Dashboard (port 8501)
```

### Sync single player
```powershell
python sync_rapidapi.py "Robert Lewandowski"
```

### Sync with manual data
```powershell
python sync_rapidapi.py "Ziolkowski" --games 15 --minutes 1350
```

### Sync multiple competitions
```powershell
python sync_rapidapi.py "Ziolkowski" --competitions "Serie A,Coppa Italia" --games-list "15,2"
```

### Automatic synchronization (recommended!)
Backend on Render automatically syncs all players:
- **Thursday and Sunday at 11:00 PM** - full statistics
- **Daily at 09:00 AM** - match logs
- **Email notifications** after each sync

**Nie musisz ręcznie synchronizować!** 🤖

---

## 🚀 Full Installation

### Prerequisites
- Python 3.10+
- RapidAPI Account (free for hobby projects)
- PostgreSQL (Supabase - free for hobby projects)

### 1. Install Dependencies

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 2. Configuration

Utwórz file `.env` w głównym katalogu:

```env
# Baza danych (Production - Supabase PostgreSQL - DARMOWE!)
# DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres

# RapidAPI Key (REQUIRED!)
RAPIDAPI_KEY=your_rapidapi_key_here
# Get your key from: https://rapidapi.com/creativesdev/api/free-api-live-football-data

# Scheduler (włącz dla automatycznej synchronizacji)
ENABLE_SCHEDULER=false

# Timezone dla schedulera (domyślnie Europe/Warsaw)
SCHEDULER_TIMEZONE=Europe/Warsaw

# Email notifications (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

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

## 🔄 Synchronizacja danych

### 🤖 Automatyczna synchronizacja (Scheduler)

**Włącz scheduler w `.env`:**
```env
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=Europe/Warsaw
```

**Harmonogram:**
- 📅 **Czwartek 23:00** - statystyki zawodników
- 📅 **Niedziela 23:00** - statystyki zawodników
- 📅 **Codziennie 09:00** - szczegóły meczów
- 📅 **Codziennie 03:00** - czyszczenie cache
- 📅 **Codziennie 12:00** - monitoring quota API

### ⚡ Manualna synchronizacja

```powershell
# Podstawowa synchronizacja (statystyki z zespołu)
python sync_rapidapi.py "Lewandowski"

# Z ręcznymi danymi o meczach
python sync_rapidapi.py "Ziolkowski" --games 15 --minutes 1350

# Wiele rozgrywek naraz
python sync_rapidapi.py "Ziolkowski" --competitions "Serie A,Coppa Italia,Champions League" --games-list "15,2,5"

# Wszyscy polacy naraz
python sync_all_polish.py
```

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

### Matchlogs
- `GET /api/matchlogs/{player_id}` - Match logs gracza (z filtrami)
- `GET /api/matchlogs/{player_id}/stats` - Agregowane statystyki z meczów
- `GET /api/matchlogs/match/{match_id}` - Szczegóły pojedynczego meczu

### Leaderboard (NEW!)
- `GET /api/leaderboard/goals/{league}` - Top strzelcy ligi
- `GET /api/leaderboard/assists/{league}` - Top asystenci ligi
- `GET /api/leaderboard/rating/{league}` - Top oceniane gracze
- `GET /api/leaderboard/all/{league}` - Wszystkie leaderboardy naraz
- `GET /api/leaderboard/leagues` - Lista dostępnych lig

### Live Matches (NEW!)
- `GET /api/live/today` - Mecze dzisiejsze i live
- `GET /api/live/live` - Tylko live matches
- `GET /api/live/team/{team_name}` - Mecze drużyny
- `GET /api/live/player/{player_id}` - Czy gracz gra dziś?

## 📁 Struktura projektu

```
polish-players-tracker/
├── .env                          # Konfiguracja (gitignored)
├── .env.example                  # Przykładowa konfiguracja
├── .gitignore
├── requirements.txt              # Zależności Python
├── alembic.ini                   # Konfiguracja migracji bazy danych
│
├── api_client.py                 # API client (Streamlit Cloud)
├── streamlit_app_cloud.py        # Główna aplikacja Streamlit Cloud
├── pages/                        # Strony Streamlit Cloud
│   └── 2_Compare_Players.py      # Porównywanie graczy
│
├── sync_rapidapi.py              # Skrypt: synchronizacja z RapidAPI
├── sync_single_player.py         # Skrypt: synchronizacja pojedynczego gracza
├── sync_all_polish.py            # Skrypt: synchronizacja wszystkich Polaków
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
│   │   │   ├── competition_stats.py
│   │   │   ├── goalkeeper_stats.py
│   │   │   ├── player_match.py   # Matchlogs
│   │   │   ├── cache_store.py    # Cache API
│   │   │   └── api_usage_metrics.py
│   │   ├── routers/              # API Endpoints
│   │   │   ├── __init__.py
│   │   │   ├── players.py        # /api/players
│   │   │   ├── comparison.py     # /api/comparison
│   │   │   ├── matchlogs.py      # /api/matchlogs
│   │   │   ├── leaderboard.py    # /api/leaderboard
│   │   │   └── live.py           # /api/live
│   │   ├── schemas/              # Pydantic schemas
│   │   └── services/             # Business logic
│   │       ├── rapidapi_client.py    # RapidAPI client
│   │       ├── cache_manager.py      # Cache management
│   │       ├── rate_limiter.py       # Rate limiting
│   │       ├── match_logs_sync.py    # Match logs sync
│   │       └── live_match_tracker.py # Live matches
│   └── frontend/                 # Frontend Streamlit
│       ├── streamlit_app.py
│       ├── api_client.py
│       └── requirements.txt
│
├── .streamlit/                   # Konfiguracja Streamlit
│   ├── config.toml
│   └── secrets.toml.example
│
├── start_backend.ps1
├── start_frontend.ps1
```

## 🗄️ Baza danych

### 💾 PostgreSQL (Supabase)
- ✅ **500 MB storage**
- ✅ **Automatyczne backupy**
- ✅ **Dashboard do przeglądania danych**
- ✅ **Connection pooling**
- ✅ **DARMOWE NA ZAWSZE** dla projektów hobby!

### 🚀 Configuration:
```powershell
# 1. Zarejestruj się: https://supabase.com (DARMOWE!)
# 2. Utwórz projekt
# 3. Skopiuj DATABASE_URL
# 4. Dodaj do .env

# 5. Start migracje:
alembic upgrade head
```

### Struktura bazy danych

**`players`** - podstawowe informacje o graczach
- id, name, team, league, position, nationality
- rapidapi_player_id, rapidapi_team_id
- is_goalkeeper, last_updated

**`competition_stats`** - statystyki zawodników (nie-bramkarze)
- player_id, season, competition_type, competition_name
- games, minutes, goals, assists
- yellow_cards, red_cards, penalty_goals
- **competition_type:** LEAGUE, EUROPEAN_CUPS, DOMESTIC_CUPS, NATIONAL_TEAM

**`goalkeeper_stats`** - statystyki bramkarzy
- player_id, season, competition_type, competition_name
- games, minutes, saves, clean_sheets, goals_against

**`player_matches`** - szczegółowe statystyki z meczów
- player_id, match_date, competition, opponent, result
- goals, assists, minutes, cards

**`cache_store`** - cache dla API responses
- endpoint, params_hash, response_data, expires_at

**`api_usage_metrics`** - monitoring użycia API
- request_count, last_reset, alert_sent

## 🛠️ CLI Commands

### Synchronizacja

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔄 Sync player (basic) | `python sync_rapidapi.py "Lewandowski"` |
| 🎯 Sync z danymi ręcznymi | `python sync_rapidapi.py "Ziolkowski" --games 15` |
| 🏆 Sync wiele rozgrywek | `python sync_rapidapi.py "Ziolkowski" --competitions "Serie A,Coppa Italia" --games-list "15,2"` |
| 🤖 **Automatic sync** | **Scheduler na Render** |
| 📋 Sync wszystkich Polaków | `python sync_all_polish.py` |

### Uruchamianie

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔧 Backend API | `.\start_backend.ps1` |
| 🎨 Frontend Dashboard | `.\start_frontend.ps1` |

### API Endpoints

| Endpoint | Opis |
|----------|------|
| `/api/leaderboard/goals/Serie A` | Top strzelcy Serie A |
| `/api/leaderboard/all/Premier League` | Wszystkie leaderboardy |
| `/api/live/today` | Mecze dzisiejsze Polaków |
| `/api/players/` | Lista wszystkich graczy |

---

## 📚 Documentation

### 🎓 Essential Guides

**Getting Started:**
- 📖 **[README.md](README.md)** - You are here!
- 🚀 **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deploy to production
- 🔧 **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues

**Reference:**
- 📚 **[API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** - Complete API reference
- 🛠️ **[STACK.md](docs/STACK.md)** - Technology stack
- 🌐 **[RAPIDAPI_SETUP.md](docs/RAPIDAPI_SETUP.md)** - RapidAPI configuration

**Legal:**
- ⚖️ **[LEGAL_NOTICE.md](docs/LEGAL_NOTICE.md)** - Data attribution

## 🐛 Rozwiązywanie problemów

### Backend nie startuje
```powershell
# Sprawdź port
netstat -ano | findstr :8000

# Start na innym porcie
python -m uvicorn app.backend.main:app --port 8001
```

### API key nie działa
```powershell
# Sprawdź czy RAPIDAPI_KEY jest w .env
# Get key from: https://rapidapi.com/creativesdev/api/free-api-live-football-data
```

### Scheduler nie działa
```powershell
# Sprawdź .env
ENABLE_SCHEDULER=true
```

## 📊 Statystyki projektu

- **90+** polskich piłkarzy śledzonych
- **20+** europejskich lig
- **4 typy rozgrywek**: Liga, Puchary Europejskie, Reprezentacja, Puchary krajowe
- **Automatyczna synchronizacja**: 2x w tygodniu
- **Leaderboard**: Top strzelcy/asystenci/oceny
- **Live matches**: Śledzenie meczów na żywo

## 🤝 Contributing

Open to suggestions and improvements!

## 📝 Licencja

MIT License - Projekt edukacyjny

---

**Made with ❤️ for Polish football fans**
