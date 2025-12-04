# 🇵🇱 Polish Football Data Hub International

**Status:** ✅ Production Ready | **Database:** PostgreSQL (Supabase) | **Deployment:** Cloud-Ready

> 📊 Real-time monitoring and analysis of 90+ Polish footballers playing abroad

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
> ⚖️ **[Legal Notice - Important!](LEGAL_NOTICE.md)** | 🚀 **[Deployment Guide](STREAMLIT_CLOUD_DEPLOYMENT.md)**

## ⚖️ Legal Notice

**This is an educational, non-commercial project.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Educational and portfolio purposes only
- **NOT for commercial use** without proper licensing
- **See [LEGAL_NOTICE.md](LEGAL_NOTICE.md) for full details**

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
- **Endpoints**: players, comparisons, statistics, matchlogs, live matches (in development)
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
.\venv\Scripts\Activate.ps1

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

**Cloud deployment:** See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for free 24/7 hosting!

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
- `GET /api/players` - Lista all players
- `GET /api/players/{id}` - Szczegóły player

### Comparison
- `GET /api/comparison/compare` - Porównaj dwóch players
- `GET /api/comparison/players/{id}/stats` - Player statistics
- `GET /api/comparison/available-stats` - Dostępne statystyki

### Matches
- `GET /api/matches/live` - Mecze live (w budowie)
- `GET /api/matches/upcoming/{league}` - Nadchodzące mecze

### Matchlogs (Szczegóły meczów)
- `GET /api/players/{id}/matches` - Lista meczów player
- `GET /api/players/{id}/matches/stats` - Statystyki zagregowane z meczów
- `GET /api/matches/{match_id}` - Szczegóły konkretnego meczu

## 📁 Struktura projektu

```
polish-players-tracker/
├── .env                          # Configuration (gitignored)
├── .env.example                  # Przykładowa Configuration
├── .gitignore
├── requirements.txt              # Zależności Python
├── api_client.py                 # API client dla Streamlit (obsługa st.secrets)
├── streamlit_app_cloud.py        # Główna afileacja Streamlit Cloud
├── pages/                        # Strony Streamlit (multi-page app)
│   └── 2_Compare_Players.py      # Strona porównywania players
├── README.md                     # Ten file
│
├── venv/                         # Środowisko wirtualne Python
│
├── app/
│   ├── backend/                  # Backend FastAPI
│   │   ├── main.py               # Główna afileacja + scheduler
│   │   ├── config.py             # Configuration
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
├── start_backend.ps1             # Start backend
├── start_frontend.ps1            # Start frontend
│
├── sync_player_full.py           # Sync player (all seasons: stats+matchlogs)
├── sync_match_logs.py            # Sync tylko matchlogs (current season)
├── sync_missing_players.py       # Sync players bez danych
├── add_piatek_manual.py          # Ręczne dodanie player
│
└── tools/                        # Narzędzia pomocnicze
    └── check_reqs.py             # Weryfikacja pakietów
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

#### Ręczne dodanie player
Edit file `add_piatek_manual.py` as template:
```python
# Przykład dodania player
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
```

#### Synchronizacja po dodaniu
```powershell
python sync_player_full.py "Krzysztof Piątek" --all-seasons
```
**Parametry:**
- `"Imię Nazwisko"` - pełne nazwisko player
- `"Kor"` - nazwa koru
- `"Liga"` - nazwa ligi
- `"Pozycja"` - FW (napastnik), MF (pomocnik), DF (obrońca), GK (bramkarz)
- `--sync` - automatically Synchronize statystyki i matchlogs

**Ta komenda:**
1. Adds player to database
2. Synchronizuje statystyki sezonowe (all seasons)
3. Synchronizuje matchlogs (current season 2025-2026)

#### Ręczne dodanie przez kod (dla deweloperów)
```powershell
# Edit file add_piatek_manual.py i Start
python add_piatek_manual.py
```
file `add_piatek_manual.py` to przykład jak dodać player bezpośrednio przez kod Python.

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

### Dodawanie players

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔧 Dodaj ręcznie (edit template) | `python add_piatek_manual.py` |
| 🔄 Synchronizuj po dodaniu | `python sync_player_full.py "Nazwisko" --all-seasons` |

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

**Szczegółowa instrukcja:** [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

---

### 🏢 Option 2: Commercial Deployment (PostgreSQL + Streamlit Cloud)

**Dla afileacji komercyjnych:**
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

