# 🛠️ Stack Technologiczny - Polish Football Data Hub International

## 📋 Overview

Full-stack web application for tracking Polish footballers playing abroad with real-time statistics.

**Architecture:** Modern Python-based web application
- **Backend:** FastAPI REST API
- **Frontend:** Streamlit multi-page dashboard
- **Database:** PostgreSQL (Supabase)
- **Deployment:** Cloud-ready (Render.com + Streamlit Cloud)
- **Data Source:** FBref.com (automated scraping)

---

## 🔧 Backend (API)

### Framework
- **FastAPI 0.120+** - Nowoczesny, szybki framework do budowy REST API
  - Automatyczna walidacja danych (Pydantic)
  - Auto-generowana dokumentacja (Swagger UI + ReDoc)
  - Obsługa async/await
  - Type hints i modern Python

### Serwer ASGI
- **Uvicorn 0.38+** - Lightning-fast ASGI server
  - Wspiera WebSockets
  - Hot reload w development

### ORM i Baza Danych
- **SQLAlchemy 2.0+** - Najpopularniejszy Python ORM
  - Deklaratywne modele
  - Query builder
  - Relationship management
- **PostgreSQL** - Zaawansowana relacyjna baza danych
- **Supabase** - Hosting PostgreSQL (darmowe 500MB)
  - Automatyczne backupy
  - Connection pooling
  - Dashboard do zarządzania danymi
  - ACID compliant

### Migracje
- **Alembic 1.17+** - Database migration tool
  - Version control dla schematu bazy
  - Auto-generowane migracje
  - Rollback support

### Web Scraping
- **Playwright 1.48+** - Modern browser automation
  - Headless Chromium
  - Async support
  - Niezawodne dla dynamicznych stron (JavaScript)
  - Rate limiting (12s między requestami)
- **BeautifulSoup4 4.12+** - HTML parsing (legacy scrapers)

### Scheduling
- **APScheduler 3.10+** - Advanced Python Scheduler
  - Cron-like scheduling
  - Background job execution
  - Email notifications po synchronizacji
  - Automatyczna synchronizacja statystyk: 2x w tygodniu (Pon/Czw 6:00)
  - Automatyczna synchronizacja matchlogs: 1x w tygodniu (Wtorek 7:00)

### Walidacja i Schemas
- **Pydantic 2.12+** - Data validation using Python type hints
  - Request/Response validation
  - Settings management
  - JSON Schema generation

### Biblioteki pomocnicze
- **Python-dotenv 1.2+** - Zarządzanie zmiennymi środowiskowymi
- **Requests 2.32+** - HTTP client (legacy scrapers)
- **Pandas 2.3+** - Data manipulation (comparison endpoints)

---

## 🎨 Frontend (Dashboard)

### Framework
- **Streamlit 1.51+** - Framework do budowy data apps w Pythonie
  - Reactive UI components
  - Automatyczne re-rendering
  - Zero frontend code needed
  - Built-in caching

### Biblioteki do wizualizacji
- **Plotly 5.18+** - Interaktywne wykresy
  - Responsive charts
  - Hover tooltips
  - Export to PNG/SVG
- **Pandas 2.3+** - Data processing i tabele
  - DataFrame operations
  - Data filtering i grouping

### Komunikacja z API
- **Requests 2.32+** - HTTP client do komunikacji z backendem FastAPI

---

## 🗄️ Struktura danych

### Tabele bazy danych

#### `players`
Podstawowe informacje o graczach
```sql
- id (PRIMARY KEY)
- name
- team
- league
- position
- nationality
- is_goalkeeper (BOOLEAN)
- api_id (FBref player ID)
- last_updated (DATE)
```

#### `competition_stats`
Statystyki zawodników (nie-bramkarzy) per rozgrywki
```sql
- id (PRIMARY KEY)
- player_id (FOREIGN KEY)
- season (e.g., "2025-2026")
- competition_type (LEAGUE/EUROPEAN_CUP/NATIONAL_TEAM/DOMESTIC_CUP)
- competition_name
- games, goals, assists
- xg, xa (Expected Goals/Assists)
- minutes, yellow_cards, red_cards
```

#### `goalkeeper_stats`
Statystyki bramkarzy per rozgrywki
```sql
- id (PRIMARY KEY)
- player_id (FOREIGN KEY)
- season
- competition_type
- competition_name
- games, saves, clean_sheets
- goals_against, save_percentage
- penalties_saved, penalties_attempted
```

#### `player_matches`
Szczegółowe statystyki z pojedynczych meczów (matchlogs)
```sql
- id (PRIMARY KEY)
- player_id (FOREIGN KEY)
- match_date (DATE)
- competition (e.g., "La Liga", "Champions League")
- opponent, result, venue (Home/Away)
- goals, assists, minutes_played
- shots, shots_on_target
- xg, xa (Expected Goals/Assists)
- passes_completed, passes_attempted
- tackles, interceptions, blocks
- touches, dribbles_completed, carries
- yellow_cards, red_cards
```

---

## 🔄 Przepływ danych

```
┌─────────────────────┐
│    FBref.com        │ ← Źródło danych
│  - /all_comps/      │   (statystyki sezonowe)
│  - /matchlogs/      │   (szczegóły meczów)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Playwright        │ ← Web scraping (headless browser)
│   Scraper           │   - Rate limiting (12s)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   PostgreSQL       │ ← Persistencja danych
│   (Supabase)       │
│  - players          │
│  - competition_stats│
│  - goalkeeper_stats │
│  - player_matches   │  ← matchlogs (szczegóły meczów)
│  - player_matches   │ ← Matchlogs
└──────────┬──────────┘
           │
      ┌────┴────┐
      ▼         ▼
  ┌────────┐  ┌──────────┐
  │FastAPI │  │Streamlit │
  │Backend │  │Frontend  │
  └────────┘  └──────────┘
      │          │
      └────┬─────┘
           ▼
      ┌─────────┐
      │ Browser │ ← Użytkownik
      └─────────┘
```

---

## 🚀 Deployment

### Development (Local)
- **Backend:** `uvicorn app.backend.main:app --reload --port 8000`
- **Frontend:** `streamlit run app/frontend/streamlit_app.py --server.port 8501`
- **Scripts:** `start_backend.ps1`, `start_frontend.ps1`

### Production (Self-hosted)
Rekomendowane podejście:
1. **Backend:**
   - Reverse proxy (nginx/Caddy)
   - Process manager (systemd/supervisor)
   - HTTPS (Let's Encrypt)
2. **Frontend:**
   - Streamlit Community Cloud (free tier)
   - Lub self-hosted z Docker

### Environment Variables
```env
DATABASE_URL=postgresql://postgres.xxxxx:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
ENABLE_SCHEDULER=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email@gmail.com
SMTP_PASSWORD=app-password
EMAIL_FROM=email@gmail.com
EMAIL_TO=recipient@email.com
```

---

## 📦 Zarządzanie zależnościami

### Główne pliki requirements
- **`requirements.txt`** - Główne zależności projektu
- **`app/frontend/requirements.txt`** - Zależności frontend

### Instalacja
```powershell
pip install -r requirements.txt
pip install -r app/frontend/requirements.txt
python -m playwright install chromium
```

### Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## 🔒 Bezpieczeństwo

### Obecne praktyki:
- ✅ `.env` w `.gitignore` (nie commitowane do repo)
- ✅ Rate limiting na scraper (12s między requestami)
- ✅ CORS disabled (local only)
- ✅ No authentication (local use)

### Rekomendacje dla production:
- 🔐 JWT authentication dla API
- 🔐 HTTPS tylko
- 🔐 Rate limiting na API endpoints
- 🔐 Input sanitization
- 🔐 Environment variables na serwerze (nie `.env`)

---

## 📊 Wydajność

### Optymalizacje:
- ✅ Async/await w Playwright scraper
- ✅ Database indexes na foreign keys
- ✅ Streamlit caching dla danych
- ✅ Rate limiting (oszczędność zasobów FBref)

### Limity:
- **PostgreSQL (Supabase):** Skalowalne, darmowe 500MB, automatyczne backupy
- **Scraper:** ~12 sekund per gracz (FBref ToS)
- **Streamlit:** ~1 GB RAM (free tier)

---

## 🧪 Testing

### Obecne podejście:
- Manual testing przez Swagger UI (`/docs`)
- Manual testing przez Streamlit dashboard
- CLI scripts do weryfikacji danych

### Potencjalne rozszerzenia:
- Unit tests (pytest)
- Integration tests (pytest + httpx)
- E2E tests (playwright)

---

## 📚 Dokumentacja

### Auto-generowana:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

### Ręczna:
- **README.md** - Główna dokumentacja
- **LEGAL_NOTICE.md** ⚠️ - Informacje prawne (WAŻNE!)
- **STACK.md** - Ten plik
- **STREAMLIT_CLOUD_DEPLOYMENT.md** - Przewodnik deployment
- **ARCHITECTURE_DIAGRAM.md** - Diagramy architektury
- **API_DOCUMENTATION.md** - Dokumentacja API
- **CLASSIFICATION_RULES.md** - Zasady klasyfikacji rozgrywek
- **DOCUMENTATION_INDEX.md** - Indeks wszystkich dokumentów

---

## 🎯 Current Features

### ✅ Implemented:
- **PostgreSQL Database** - Production-ready with Supabase
- **Automated Scraping** - Playwright-based FBref scraper
- **REST API** - Full CRUD operations with FastAPI
- **Scheduler** - Automatic data synchronization (2-3x/week)
- **Multi-page Frontend** - Streamlit dashboard with player comparison
- **Cloud Deployment** - Ready for Render.com + Streamlit Cloud
- **Email Notifications** - HTML reports after sync

### Frontend:
- [ ] React/Next.js (bardziej customizable)
- [ ] Progressive Web App (PWA)
- [ ] Mobile app (React Native)

### Features:
- [ ] AI analytics (OpenAI/Anthropic)
- [ ] Predykcje wyników
- [ ] Fantasy football integration
- [ ] Social features (komentarze, rankingi)

---

## 📝 Wersjonowanie

- **Python:** 3.10+
- **FastAPI:** 0.120+
- **Streamlit:** 1.51+
- **Playwright:** 1.48+
- **SQLAlchemy:** 2.0+

**Ostatnia aktualizacja:** Styczeń 2025  
**Wersja projektu:** 0.7.3

## ⚖️ Legal Notice

**This project is for EDUCATIONAL and NON-COMMERCIAL use only.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Portfolio, CV, education - NOT for commercial use without license
- **Full Details:** See [LEGAL_NOTICE.md](LEGAL_NOTICE.md)
