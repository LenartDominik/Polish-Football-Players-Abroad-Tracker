# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Security Rules

**NEVER read or access:**
- `.env` file or any `.env.*` files
- Files containing API keys, secrets, passwords, or credentials
- `secrets.toml` or any Streamlit secrets files
- Database connection strings or authentication tokens

If credentials are needed for debugging, ask the user to provide only the necessary information.

---

## Project Overview

**Polish Football Players Abroad Tracker** is a sports analytics application that tracks 90+ Polish footballers playing abroad. It consists of:
- **Backend**: FastAPI RESTful API with automated data synchronization
- **Frontend**: Streamlit multi-page dashboard for data visualization
- **Database**: PostgreSQL via Supabase with SQLAlchemy ORM 2.0+
- **Data Source**: RapidAPI Football API (free-api-live-football-data)

---

## Running the Application

### Backend API (port 8000)
```powershell
.\start_backend.ps1
# Or: python -m uvicorn app.backend.main:app --reload --port 8000
```

### Frontend Dashboard (port 8501)
```powershell
.\start_frontend.ps1
# Or: streamlit run streamlit_app_cloud.py
```

### Access Points
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Frontend Dashboard: http://localhost:8501

---

## Data Synchronization

### Automatic Sync (Scheduler)
The backend scheduler automatically syncs all players via RapidAPI:
- **Player Stats**: Thursday & Sunday at 23:00 (Europe/Warsaw)
- **Match Logs**: Daily at 09:00 (Europe/Warsaw)
- **Cache Cleanup**: Daily at 03:00 (Europe/Warsaw)
- **Quota Check**: Daily at 12:00 (Europe/Warsaw)

Enable via `.env`: `ENABLE_SCHEDULER=true`

### Rate Limiting & Caching
- **RapidAPI Free Tier**: 100 requests/month
- **Multi-layer caching**: lineups (24h), squads (6h), matches (1h), players (12h)
- **Quota monitoring**: Alerts at 80% daily, 90% monthly usage

---

## Architecture

### Directory Structure
```
polish-players-tracker/
├── app/
│   ├── backend/              # FastAPI backend
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic (RapidAPI client, data mapper)
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── utils/           # Helper functions
│   │   └── main.py          # FastAPI app + scheduler
│   └── frontend/            # API client for Streamlit
├── pages/                   # Streamlit Cloud pages
│   └── 2_Compare_Players.py # Player comparison page
├── alembic/                 # Database migrations
│   └── versions/            # Migration files
├── streamlit_app_cloud.py   # Main Streamlit app (cloud & local)
└── start_*.ps1              # Startup scripts
```

### API Routers
- `/api/players/` - Player CRUD and listing
- `/api/comparison/` - Player comparison
- `/api/matchlogs/` - Match-by-match logs
- `/api/live/` - Live match tracking
- `/api/leaderboard/` - Top players by stats

### Database Models
- **players**: Basic player info (name, team, league, position, rapidapi_player_id, rapidapi_team_id)
- **competition_stats**: Field player statistics by competition/season
- **goalkeeper_stats**: Goalkeeper-specific statistics
- **player_matches**: Detailed match logs (game-by-game)
- **season_stats**: Aggregated seasonal statistics
- **cache_store**: Generic cache for API responses
- **api_usage_metrics**: API usage tracking for quota monitoring
- **lineup_cache**: Cached lineup data from RapidAPI

### Competition Types
- `LEAGUE`: Domestic league matches
- `EUROPEAN_CUP`: UCL, UEL, UECL, Club World Cup
- `NATIONAL_TEAM`: International matches (uses calendar year, not season format)
- `DOMESTIC_CUP`: Domestic cup competitions

---

## Key Development Patterns

### Database Sessions (Critical for Supabase)
Due to Supabase Port 6543 connection pooling, always follow this pattern:
```python
db = SessionLocal()
try:
    # Database operations here
    db.commit()
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()  # ALWAYS close sessions explicitly
```

### Caching Pattern
When caching ORM objects, always convert to dicts first:
```python
# Correct - convert to dict before caching
players_data = [PlayerResponse.model_validate(p).model_dump() for p in players]
cache_manager.set_sync("players_list", cache_key, players_data)

# Wrong - ORM objects are not JSON serializable
cache_manager.set_sync("players_list", cache_key, players)  # TypeError!
```

### Player Comparison Rules
- Goalkeepers can only be compared with other goalkeepers
- Field players can only be compared with other field players
- The `/api/comparison/compare` endpoint enforces this

---

## Environment Configuration

Required in `.env`:
- `DATABASE_URL`: Supabase PostgreSQL connection string
- `RAPIDAPI_KEY`: RapidAPI key for football data

Optional:
- `ENABLE_SCHEDULER`: true/false for automatic sync
- `RESEND_API_KEY`: Resend API key for email notifications
- `EMAIL_FROM`: Sender email
- `EMAIL_TO`: Recipient email
- `GA_ID`: Google Analytics ID (for Streamlit Cloud)

---

## Common Tasks

### Database Migrations
```bash
alembic upgrade head    # Apply all migrations
alembic downgrade -1    # Rollback one migration
alembic current         # Check current migration
```

### Testing API Endpoints
Use Swagger UI at http://localhost:8000/docs for interactive testing.

### MCP Server
The project includes an MCP server for API access:
- Local: `http://localhost:8000`
- Production: Use the deployed backend URL

---

## Deployment

### Production Stack
- **Backend**: Render.com (free tier)
- **Frontend**: Streamlit Cloud (free tier)
- **Database**: Supabase PostgreSQL (500MB free tier)

### Streamlit Cloud Configuration
Set in Streamlit secrets:
```toml
BACKEND_API_URL = "https://your-backend.onrender.com"
```

---

## Legal & Attribution

- **Data Source**: RapidAPI Football API (free-api-live-football-data)
- **Usage**: Educational/portfolio purposes only
- **NOT for commercial use** without proper licensing

---

## File Notes

- `start_backend.ps1` and `start_frontend.ps1` contain hardcoded paths - may need adjustment
- Both cloud and local use `streamlit_app_cloud.py` (not `app/frontend/streamlit_app.py`)
- API client automatically detects environment (cloud vs local) and connects accordingly
- All pages in `pages/` directory are for Streamlit Cloud multi-page app
