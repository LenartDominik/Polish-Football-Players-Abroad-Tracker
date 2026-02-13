# RapidAPI Setup Guide

This document describes how to configure the RapidAPI integration for the Polish Football Players Abroad Tracker.

## Overview

The application now supports two data sources:
1. **FBref Scraper** (legacy) - Uses Playwright browser automation
2. **RapidAPI** (new) - Uses professional API for more reliable data

## RapidAPI Configuration

### 1. Get API Key

1. Sign up at [RapidAPI.com](https://rapidapi.com/)
2. Subscribe to the free tier of "free-api-live-football-data" by Creativesdev
3. Copy your API key from the dashboard

### 2. Add to Environment Variables

Add the following to your `.env` file:

```bash
# RapidAPI Configuration (new data source)
RAPIDAPI_KEY=your_rapidapi_key_here

# Existing configuration (keep these)
DATABASE_URL=your_database_url_here
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=Europe/Warsaw
RESEND_API_KEY=your_resend_key (optional)
EMAIL_FROM=your_email (optional)
EMAIL_TO=your_email (optional)
```

### 3. Run Database Migration

After updating the code, add the new database fields:

```bash
alembic upgrade head
```

Or manually in Supabase SQL Editor:

```sql
-- RapidAPI IDs
ALTER TABLE players ADD COLUMN rapidapi_player_id INTEGER;
CREATE INDEX ix_players_rapidapi_player_id ON players(rapidapi_player_id);

ALTER TABLE players ADD COLUMN rapidapi_team_id INTEGER;
CREATE INDEX ix_players_rapidapi_team_id ON players(rapidapi_team_id);

-- Level field for sync frequency (1 = Top 8 leagues, 2 = Lower leagues)
ALTER TABLE players ADD COLUMN level INTEGER NOT NULL DEFAULT 2;

-- Set level=1 for top leagues
UPDATE players SET level = 1 WHERE league IN (
    'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1',
    'Eredivisie', 'Primeira Liga', 'Süper Lig'
);
```

### 4. Populate RapidAPI IDs for Existing Players

For each player, you need to find their RapidAPI player and team IDs. You can do this by:

1. Using the RapidAPI search endpoints
2. Or manually looking up on RapidAPI dashboard

Also set the `level` field based on their league:
- **level = 1** for Top 8 leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Süper Lig)
- **level = 2** for all other leagues

Example SQL to update manually:

```sql
UPDATE players
SET rapidapi_player_id = 12345,
    rapidapi_team_id = 67890,
    level = 1
WHERE name = 'Robert Lewandowski';
```

## Sync Schedule

The new hybrid sync strategy is based on `level` field in database:

| Player Level | Leagues | Sync Frequency | Schedule |
|--------------|---------|----------------|----------|
| Level 1 | Top 8 leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Süper Lig) | 2x/week | Thursday & Sunday at 23:00 |
| Level 2 | Lower leagues (Championship, Serie B, 2. Bundesliga, etc.) | 1x/week | Sunday at 23:00 |

This approach:
- Ensures top league players are updated after mid-week and weekend matches
- Reduces API usage for lower league players
- Fits within the free tier (100 requests/month for testing)

## Usage

### Manual Sync with RapidAPI

```bash
# Sync using RapidAPI (auto-detected if configured)
python sync_player_full.py "Robert Lewandowski"

# Force use RapidAPI
python sync_player_full.py "Robert Lewandowski" --api rapidapi

# Force use FBref scraper
python sync_player_full.py "Robert Lewandowski" --api fbref
```

### Scheduler

The scheduler in `main.py` automatically uses RapidAPI if `RAPIDAPI_KEY` is configured.

Sync logic:
- **Thursday & Sunday at 23:00 (Europe/Warsaw timezone)**: All Level 1 players (Top 8 leagues)
- **Sunday at 23:00**: Level 2 players (lower leagues)

This hybrid approach reduces API usage while keeping top league data fresh.

## API Usage Tracking

The RapidAPI client tracks usage and logs warnings:

```
📡 API Request: /v3/players-list-all-by-team-id (Request #1)
✅ API Response received
⚠️ API usage: 80/100 requests this month
```

## Data Differences

### RapidAPI Provides:
- ✅ Goals, Assists, Cards
- ✅ Appearances, Minutes
- ✅ Shots, Passes
- ✅ Player/Team IDs for efficient sync

### RapidAPI Does NOT Provide (set to 0 or None):
- ❌ xG, npxG (Expected Goals)
- ❌ xA (Expected Assists)
- ❌ Detailed pass types, shot locations
- ❌ GCA/SCA (Goal/Shot Creating Actions)
- ❌ PSxG for goalkeepers

These advanced metrics are only available via FBref scraper.

## Troubleshooting

### "RAPIDAPI_KEY not configured"
- Add `RAPIDAPI_KEY=your_key` to `.env` file
- Restart the application

### "No RapidAPI IDs for player"
- Player needs `rapidapi_player_id` and `rapidapi_team_id` set in database
- Use search functionality to find IDs or set manually via SQL

### API Limit Reached
- Free tier: 100 requests/month
- Monitor usage in logs
- Consider upgrading to paid tier or reducing tracked players

## Migration Path

### Phase 1: Testing (2 weeks)
- Set `level` field for all players in database (1 or 2)
  - Level 1 = Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Süper Lig
  - Level 2 = All other leagues
- Use both FBref and RapidAPI in parallel
- Compare data quality
- Monitor API usage

### Phase 2: Decision
- If data quality is sufficient: Switch to RapidAPI only
- If advanced metrics needed: Keep FBref for xG/xA data
- Consider hybrid approach: RapidAPI for Level 2, FBref for Level 1

### Phase 3: Optimization
- Adjust sync frequency based on actual API usage
- Consider caching strategies
- Team-based sync for efficiency (already implemented)
