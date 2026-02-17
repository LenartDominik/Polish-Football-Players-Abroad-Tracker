# Database Documentation

Polish Football Tracker uses **PostgreSQL** (via Supabase) for data storage.

## Database Configuration

### Connection String (Supabase)
```
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### Key Settings
- **Port**: 6543 (Supabase connection pooling)
- **Pooler**: Transaction mode (recommended for SQLAlchemy)
- **Free Tier**: 500MB storage, 2GB transfer/month

## Tables Overview

### Core Tables

#### `players`
Basic player information and metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key (auto-increment) |
| name | VARCHAR | NO | Player name |
| team | VARCHAR | YES | Current team |
| league | VARCHAR | YES | Current league |
| position | VARCHAR | YES | Position (GK, DF, MF, FW) |
| nationality | VARCHAR | YES | Nationality |
| is_goalkeeper | BOOLEAN | NO | Whether player is a goalkeeper |
| rapidapi_player_id | INTEGER | YES | RapidAPI player ID |
| rapidapi_team_id | INTEGER | YES | RapidAPI team ID |
| level | INTEGER | NO | Priority level (1=Top 8 leagues, 2=Lower leagues) |
| last_updated | DATE | YES | Last sync date |
| data_source | VARCHAR | NO | Data source ('rapidapi', 'fbref') |

**Indexes:**
- `ix_players_team_league` (team, league) - compound index
- `ix_players_position_league` (position, league) - compound index
- `ix_players_rapidapi_team_player` (rapidapi_team_id, rapidapi_player_id) - compound index

---

#### `competition_stats`
Field player statistics by competition and season.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| player_id | INTEGER | NO | Foreign key to players |
| season | VARCHAR | NO | Season (e.g., "2025-2026") |
| competition_type | VARCHAR | NO | Type: LEAGUE, EUROPEAN_CUPS, DOMESTIC_CUPS, NATIONAL_TEAM |
| competition_name | VARCHAR | YES | Competition name |
| games | INTEGER | YES | Games played |
| games_starts | INTEGER | YES | Games started |
| minutes | INTEGER | YES | Minutes played |
| goals | INTEGER | YES | Goals scored |
| assists | INTEGER | YES | Assists |
| ga_plus | INTEGER | YES | Goals + Assists |
| ga_per_90 | FLOAT | YES | (Goals + Assists) per 90 minutes |
| xg | FLOAT | YES | Expected Goals |
| npxg | FLOAT | YES | Non-Penalty Expected Goals |
| xa | FLOAT | YES | Expected Assists |
| xg_xa | FLOAT | YES | xG + xA |
| penalty_goals | INTEGER | YES | Penalty goals |
| shots | INTEGER | YES | Total shots |
| shots_on_target | INTEGER | YES | Shots on target |
| yellow_cards | INTEGER | YES | Yellow cards |
| red_cards | INTEGER | YES | Red cards |
| data_source | VARCHAR | NO | Data source ('rapidapi', 'fbref') |

**Indexes:**
- `ix_competition_stats_player_season_datasource` (player_id, season, data_source) - compound index

---

#### `goalkeeper_stats`
Goalkeeper-specific statistics by competition and season.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| player_id | INTEGER | NO | Foreign key to players |
| season | VARCHAR | NO | Season (e.g., "2025-2026") |
| competition_type | VARCHAR | NO | Type: LEAGUE, EUROPEAN_CUPS, DOMESTIC_CUPS, NATIONAL_TEAM |
| competition_name | VARCHAR | YES | Competition name |
| games | INTEGER | YES | Games played |
| games_starts | INTEGER | YES | Games started |
| minutes | INTEGER | YES | Minutes played |
| goals_against | INTEGER | YES | Goals conceded |
| goals_against_per90 | FLOAT | YES | Goals against per 90 minutes |
| shots_on_target_against | INTEGER | YES | Shots on target conceded |
| saves | INTEGER | YES | Total saves |
| save_percentage | FLOAT | YES | Save percentage |
| clean_sheets | INTEGER | YES | Clean sheets |
| clean_sheet_percentage | FLOAT | YES | Clean sheet percentage |
| wins | INTEGER | YES | Wins |
| draws | INTEGER | YES | Draws |
| losses | INTEGER | YES | Losses |
| penalties_attempted | INTEGER | YES | Penalties faced |
| penalties_allowed | INTEGER | YES | Penalties conceded |
| penalties_saved | INTEGER | YES | Penalties saved |
| penalties_missed | INTEGER | YES | Penalties missed |
| data_source | VARCHAR | NO | Data source ('rapidapi', 'fbref') |

**Indexes:**
- `ix_goalkeeper_stats_player_season_datasource` (player_id, season, data_source) - compound index

---

#### `player_matches`
Detailed match-by-match statistics (match logs).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| player_id | INTEGER | NO | Foreign key to players |
| match_date | DATE | YES | Match date |
| competition | VARCHAR | YES | Competition name |
| round | VARCHAR | YES | Round/week |
| venue | VARCHAR | YES | Home/Away/Neutral |
| opponent | VARCHAR | YES | Opponent team |
| result | VARCHAR | YES | Result (e.g., "W 3-1", "L 0-2") |
| minutes_played | INTEGER | YES | Minutes played |
| goals | INTEGER | YES | Goals scored |
| assists | INTEGER | YES | Assists |
| shots | INTEGER | YES | Total shots |
| shots_on_target | INTEGER | YES | Shots on target |
| xg | FLOAT | YES | Expected Goals |
| xa | FLOAT | YES | Expected Assists |
| npxg | FLOAT | YES | Non-Penalty xG |
| npxg_xa | FLOAT | YES | npxG + xA |
| passes_completed | INTEGER | YES | Passes completed |
| passes_attempted | INTEGER | YES | Passes attempted |
| pass_completion_pct | FLOAT | YES | Pass completion % |
| key_passes | INTEGER | YES | Key passes |
| tackles | INTEGER | YES | Tackles |
| interceptions | INTEGER | YES | Interceptions |
| blocks | INTEGER | YES | Blocks |
| touches | INTEGER | YES | Touches |
| dribbles_completed | INTEGER | YES | Successful dribbles |
| carries | INTEGER | YES | Carries |
| fouls_committed | INTEGER | YES | Fouls committed |
| fouls_drawn | INTEGER | YES | Fouls won |
| yellow_cards | INTEGER | YES | Yellow cards |
| red_cards | INTEGER | YES | Red cards |
| data_source | VARCHAR | NO | Data source ('rapidapi', 'fbref') |

**Indexes:**
- `ix_player_matches_player_date_comp` (player_id, match_date, competition) - compound index

---

### Supporting Tables

#### `cache_store`
API response caching for performance optimization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| cache_key | VARCHAR | NO | Unique cache key |
| cache_type | VARCHAR | NO | Cache type (lineup, squad, match, player) |
| data | JSONB | YES | Cached data |
| created_at | TIMESTAMP | NO | Creation timestamp |
| expires_at | TIMESTAMP | NO | Expiration timestamp |
| hits | INTEGER | NO | Cache hit count |

**TTL Settings:**
- `lineup`: 24 hours
- `squad`: 6 hours
- `match`: 1 hour
- `player`: 12 hours
- `league_teams`: 24 hours

---

#### `api_usage_metrics`
API usage tracking for quota monitoring.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| date | DATE | NO | Request date |
| month | VARCHAR | NO | Month (YYYY-MM format) |
| requests_count | INTEGER | NO | Number of requests |
| endpoint | VARCHAR | YES | API endpoint called |
| status_code | INTEGER | YES | HTTP status code |
| created_at | TIMESTAMP | NO | Creation timestamp |

**Quota Limits:**
- Monthly: 100 requests (RapidAPI free tier)
- Daily: ~10 requests (soft limit)

---

#### `lineup_cache`
Deprecated - use `cache_store` instead.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key |
| event_id | INTEGER | NO | Match event ID |
| home_team_id | INTEGER | YES | Home team RapidAPI ID |
| away_team_id | INTEGER | YES | Away team RapidAPI ID |
| home_lineup | JSONB | YES | Home team lineup data |
| away_lineup | JSONB | YES | Away team lineup data |
| fetched_at | TIMESTAMP | NO | Fetch timestamp |
| data_source | VARCHAR | NO | Data source ('rapidapi', 'fbref') |

---

## Competition Types

The database categorizes competitions into 4 types:

| Type | Description | Examples |
|------|-------------|----------|
| `LEAGUE` | Domestic league matches | Premier League, La Liga, Bundesliga, Serie A |
| `EUROPEAN_CUPS` | European club competitions | Champions League, Europa League, Conference League |
| `DOMESTIC_CUPS` | Domestic cup competitions | FA Cup, DFB-Pokal, Coppa Italia |
| `NATIONAL_TEAM` | International matches | World Cup, Euro qualifiers, Nations League |

**Important Note:** National team statistics use **calendar year** (e.g., "2025") instead of season format (e.g., "2025-2026").

---

## Data Source Migration

### `data_source` Column
All core tables have a `data_source` column tracking the origin of data:
- `'rapidapi'` - Data from RapidAPI Football API
- `'fbref'` - Historical data from FBref.com (legacy)

This allows for:
- Gradual migration from FBref to RapidAPI
- Tracking data provenance
- Potential multi-source strategies

---

## Performance Indexes

### Compound Indexes
```sql
-- Player lookups by team and league
CREATE INDEX ix_players_team_league ON players(team, league);

-- Player lookups by position and league
CREATE INDEX ix_players_position_league ON players(position, league);

-- RapidAPI ID lookups
CREATE INDEX ix_players_rapidapi_team_player ON players(rapidapi_team_id, rapidapi_player_id);

-- Match logs by player, date, competition
CREATE INDEX ix_player_matches_player_date_comp ON player_matches(player_id, match_date, competition);

-- Competition stats by player, season, data source
CREATE INDEX ix_competition_stats_player_season_datasource ON competition_stats(player_id, season, data_source);

-- Goalkeeper stats by player, season, data source
CREATE INDEX ix_goalkeeper_stats_player_season_datasource ON goalkeeper_stats(player_id, season, data_source);
```

---

## Database Migrations

### Running Migrations
```powershell
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history
```

### Migration Files
- `0010_add_data_source_column.py` - Added `data_source` column to all tables
- `0020_add_cache_store_table.py` - Created `cache_store` table
- `0030_add_api_usage_metrics_table.py` - Created `api_usage_metrics` table
- `0040_drop_api_id_column.py` - Removed deprecated `api_id` column
- `0050_add_performance_indexes.py` - Added performance indexes

---

## Backup Strategy

### Automated Backups (Supabase)
- **Frequency**: Daily
- **Retention**: 7 days (free tier)
- **Location**: Supabase cloud storage

### Manual Backup
```powershell
python backup_database.py
```

Creates timestamped SQL dump in `backups/` directory.

---

## Connection Pooling (Supabase)

### Why Port 6543?
Supabase uses connection pooling via PgBouncer on port 6543:
- **Transaction mode**: Recommended for SQLAlchemy
- **Session mode**: NOT recommended (causes issues with ORM)
- **Max connections**: 60 (free tier)

### Best Practices
```python
# ✅ GOOD - Context manager pattern
from app.backend.utils.db import get_db_session

with get_db_session() as db:
    player = db.query(Player).first()
    # Session automatically committed and closed

# ✅ GOOD - FastAPI Depends
from fastapi import Depends
from app.backend.database import get_db

@router.get("/players")
def get_players(db: Session = Depends(get_db)):
    return db.query(Player).all()
```

---

## Troubleshooting

### Duplicate Key Errors
```powershell
python fix_postgres_sequences.py
```

### Slow Queries
- Check indexes are applied: `alembic upgrade head`
- Use compound indexes for multi-column filters
- Consider adding more indexes based on query patterns

### Connection Issues
- Verify `DATABASE_URL` uses port 6543
- Check Supabase project status
- Ensure connection pooling is enabled

---

## Schema Diagram

```
players (1) ----< (N) competition_stats
  |
  +----< (N) goalkeeper_stats
  |
  +----< (N) player_matches

cache_store (standalone)
api_usage_metrics (standalone)
lineup_cache (deprecated)
```
