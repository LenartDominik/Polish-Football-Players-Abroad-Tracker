# 📚 API Documentation - Polish Football Data Hub International

**Base URL:** `http://localhost:8000` (local) or `https://your-backend.onrender.com` (production)  
**Interactive Docs:** 
- **Swagger UI:** `/docs` 
- **ReDoc:** `/redoc`

> ✅ **All endpoints listed below are tested and working**

---

## ⚖️ Legal Notice

**This API is for educational and non-commercial use only.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Educational and portfolio purposes only
- **NOT for commercial use** without proper licensing

See [LEGAL_NOTICE.md](LEGAL_NOTICE.md) for full details.

---

## 🔐 Authentication

**Current:** No authentication required (public API)

---

## 📑 Table of Contents

1. [Health & Info](#health--info)
2. [Players](#players)
3. [Comparison](#comparison)
4. [Matchlogs](#matchlogs)

---

## 🏥 Health & Info

### Health Check

**GET** `/health`

Check if API is running and scheduler status.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-12-02T12:47:56.350756",
  "scheduler_running": true
}
```

---

### API Root Info

**GET** `/`

Get comprehensive API information including scheduler status, database info, and available features.

**Response:**
```json
{
  "title": "Polish Football Data Hub International - Backend API",
  "version": "0.7.4",
  "description": "Backend API for tracking Polish football players statistics from FBref",
  "features": [
    "📊 Player statistics from FBref.com",
    "🔄 Automated data synchronization with Playwright",
    "⚖️ Visual player comparison (field players & goalkeepers)",
    "🤖 Automated scheduler (stats 2x/week, matchlogs 1x/week)"
  ],
  "scheduler": {
    "enabled": true,
    "stats_sync_schedule": "Monday & Thursday at 06:00 (Europe/Warsaw)",
    "matchlogs_sync_schedule": "Tuesday at 07:00 (Europe/Warsaw)",
    "next_stats_sync": "2025-12-04 06:00:00+01:00",
    "next_matchlogs_sync": "2025-12-09 07:00:00+01:00"
  },
  "database": {
    "type": "PostgreSQL",
    "provider": "Supabase",
    "tier": "Free (500MB storage, 2GB transfer/month)"
  }
}
```

---

## 👥 Players

### Get All Players

**GET** `/api/players/`

Get list of all Polish players in the database.

**Query Parameters:**
- None (returns all players)

**Example:**
```bash
curl http://localhost:8000/api/players/
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Robert Lewandowski",
    "position": "Striker",
    "current_team": "Barcelona",
    "league": "La Liga",
    "nationality": "Poland",
    "fbref_id": "8d78e732",
    "api_id": null
  },
  {
    "id": 2,
    "name": "Wojciech Szczęsny",
    "position": "Goalkeeper",
    "current_team": "Juventus",
    "league": "Serie A",
    "nationality": "Poland",
    "fbref_id": "a6d9c54e",
    "api_id": null
  }
]
```

---

### Get Player by ID

**GET** `/api/players/{player_id}`

Get detailed information about a specific player.

**Path Parameters:**
- `player_id` (int, required): Player ID

**Example:**
```bash
curl http://localhost:8000/api/players/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Robert Lewandowski",
  "position": "Striker",
  "current_team": "Barcelona",
  "league": "La Liga",
  "nationality": "Poland",
  "fbref_id": "8d78e732",
  "api_id": null
}
```

**Status Codes:**
- `200 OK` - Player found
- `404 Not Found` - Player not found

---

### Get All Competition Stats

**GET** `/api/players/stats/competition`

Get all competition statistics for all players (competition_stats table).

**Example:**
```bash
curl http://localhost:8000/api/players/stats/competition
```

**Response:**
```json
[
  {
    "id": 1,
    "player_id": 1,
    "season": "2025-2026",
    "competition_type": "LEAGUE",
    "competition_name": "La Liga",
    "games": 15,
    "games_starts": 14,
    "minutes": 1260,
    "goals": 12,
    "assists": 5,
    "xg": 10.5,
    "npxg": 9.2,
    "xa": 3.8,
    "penalty_goals": 3,
    "shots": 45,
    "shots_on_target": 28,
    "yellow_cards": 2,
    "red_cards": 0
  }
]
```

---

### Get All Goalkeeper Stats

**GET** `/api/players/stats/goalkeeper`

Get all goalkeeper statistics (goalkeeper_stats table).

**Example:**
```bash
curl http://localhost:8000/api/players/stats/goalkeeper
```

**Response:**
```json
[
  {
    "id": 1,
    "player_id": 2,
    "season": "2025-2026",
    "competition_type": "LEAGUE",
    "competition_name": "Serie A",
    "games": 15,
    "games_starts": 15,
    "minutes": 1350,
    "goals_against": 18,
    "goals_against_per90": 1.2,
    "shots_on_target_against": 65,
    "saves": 47,
    "save_percentage": 72.3,
    "clean_sheets": 5,
    "clean_sheet_percentage": 33.3,
    "wins": 8,
    "draws": 4,
    "losses": 3,
    "penalties_attempted": 2,
    "penalties_allowed": 1,
    "penalties_saved": 1,
    "penalties_missed": 0
  }
]
```

---

### Get All Matches

**GET** `/api/players/stats/matches`

Get all match records from player_matches table.

**Example:**
```bash
curl http://localhost:8000/api/players/stats/matches
```

**Response:**
```json
[
  {
    "id": 1,
    "player_id": 1,
    "match_date": "2025-08-28",
    "competition": "La Liga",
    "round": "Matchweek 3",
    "venue": "Home",
    "opponent": "Real Madrid",
    "result": "W 2-1",
    "minutes_played": 90,
    "goals": 1,
    "assists": 1,
    "shots": 4,
    "shots_on_target": 3,
    "xg": 0.8,
    "xa": 0.3,
    "passes_completed": 25,
    "passes_attempted": 32,
    "pass_completion_pct": 78.1,
    "key_passes": 2,
    "tackles": 1,
    "interceptions": 0,
    "blocks": 0,
    "touches": 45,
    "dribbles_completed": 2,
    "carries": 15,
    "fouls_committed": 1,
    "fouls_drawn": 2,
    "yellow_cards": 0,
    "red_cards": 0
  }
]
```

---

## ⚖️ Comparison

### Get Player Stats (for comparison)

**GET** `/api/comparison/players/{player_id}/stats`

Get all statistics for a single player, grouped by season.

**Path Parameters:**
- `player_id` (int, required): Player ID

**Query Parameters:**
- `season` (string, optional): Filter by specific season (e.g., "2025-2026")

**Example:**
```bash
curl http://localhost:8000/api/comparison/players/1/stats
curl http://localhost:8000/api/comparison/players/1/stats?season=2025-2026
```

**Response:**
```json
[
  {
    "name": "Robert Lewandowski",
    "position": "Striker",
    "team": "Barcelona",
    "league": "La Liga",
    "season": "2025-2026",
    "matches": 15,
    "goals": 12,
    "assists": 5,
    "yellow_cards": 2,
    "red_cards": 0,
    "minutes_played": 1260,
    "xG": 10.5,
    "xA": 3.8,
    "games_starts": 14
  }
]
```

---

### Compare Two Players

**GET** `/api/comparison/compare`

Compare statistics of two players. **Goalkeepers can only be compared with other goalkeepers. Field players can only be compared with other field players.**

**Query Parameters:**
- `player1_id` (int, required): ID of first player
- `player2_id` (int, required): ID of second player
- `season` (string, optional): Season to compare (default: latest season 2025-2026)
- `stats` (list[string], optional): List of specific stats to compare (default: all)

**Example:**
```bash
# Compare two strikers
curl "http://localhost:8000/api/comparison/compare?player1_id=1&player2_id=5"

# Compare with specific season
curl "http://localhost:8000/api/comparison/compare?player1_id=1&player2_id=5&season=2024-2025"

# Compare two goalkeepers
curl "http://localhost:8000/api/comparison/compare?player1_id=2&player2_id=3"
```

**Response (Field Players):**
```json
{
  "player1": {
    "id": 1,
    "name": "Robert Lewandowski",
    "position": "Striker",
    "team": "Barcelona",
    "league": "La Liga",
    "matches": 15,
    "goals": 12,
    "assists": 5,
    "yellow_cards": 2,
    "red_cards": 0,
    "minutes_played": 1260,
    "xG": 10.5,
    "xA": 3.8,
    "games_starts": 14,
    "G+A_per_90": 1.21
  },
  "player2": {
    "id": 5,
    "name": "Krzysztof Piątek",
    "position": "Striker",
    "team": "Istanbul Başakşehir",
    "league": "Süper Lig",
    "matches": 14,
    "goals": 8,
    "assists": 2,
    "yellow_cards": 3,
    "red_cards": 0,
    "minutes_played": 1120,
    "xG": 7.2,
    "xA": 1.5,
    "games_starts": 12,
    "G+A_per_90": 0.80
  },
  "comparison_date": "2025-12-02T12:00:00",
  "player_type": "field_player"
}
```

**Response (Goalkeepers):**
```json
{
  "player1": {
    "id": 2,
    "name": "Wojciech Szczęsny",
    "position": "Goalkeeper",
    "team": "Juventus",
    "league": "Serie A",
    "matches": 15,
    "games_starts": 15,
    "minutes_played": 1350,
    "goals_against": 18,
    "goals_against_per90": 1.2,
    "shots_on_target_against": 65,
    "saves": 47,
    "save_percentage": 72.3,
    "clean_sheets": 5,
    "clean_sheet_percentage": 33.3,
    "wins": 8,
    "draws": 4,
    "losses": 3,
    "penalties_attempted": 2,
    "penalties_allowed": 1,
    "penalties_saved": 1,
    "penalties_missed": 0
  },
  "player2": {
    "id": 3,
    "name": "Łukasz Skorupski",
    "position": "Goalkeeper",
    "team": "Bologna",
    "league": "Serie A",
    "matches": 14,
    "games_starts": 14,
    "minutes_played": 1260,
    "goals_against": 22,
    "goals_against_per90": 1.57,
    "shots_on_target_against": 70,
    "saves": 48,
    "save_percentage": 68.6,
    "clean_sheets": 3,
    "clean_sheet_percentage": 21.4,
    "wins": 6,
    "draws": 5,
    "losses": 3,
    "penalties_attempted": 3,
    "penalties_allowed": 2,
    "penalties_saved": 1,
    "penalties_missed": 0
  },
  "comparison_date": "2025-12-02T12:00:00",
  "player_type": "goalkeeper"
}
```

**Status Codes:**
- `200 OK` - Comparison successful
- `400 Bad Request` - Trying to compare goalkeeper with field player
- `404 Not Found` - One or both players not found, or no data for specified season

---

### Get Available Stats

**GET** `/api/comparison/available-stats`

Get list of available statistics for comparison, grouped by category.

**Query Parameters:**
- `player_type` (string, optional): "field_player" or "goalkeeper" (default: field_player)

**Example:**
```bash
curl "http://localhost:8000/api/comparison/available-stats?player_type=field_player"
curl "http://localhost:8000/api/comparison/available-stats?player_type=goalkeeper"
```

**Response (Field Player):**
```json
{
  "offensive": [
    {"key": "goals", "label": "Goals", "type": "count"},
    {"key": "assists", "label": "Assists", "type": "count"},
    {"key": "G+A_per_90", "label": "G+A per 90", "type": "decimal"},
    {"key": "xG", "label": "Expected Goals (xG)", "type": "decimal"},
    {"key": "xA", "label": "Expected Assists (xA)", "type": "decimal"}
  ],
  "defensive": [
    {"key": "yellow_cards", "label": "Yellow Cards", "type": "count"},
    {"key": "red_cards", "label": "Red Cards", "type": "count"}
  ],
  "general": [
    {"key": "matches", "label": "Matches Played", "type": "count"},
    {"key": "games_starts", "label": "Games Started", "type": "count"}
  ]
}
```

**Response (Goalkeeper):**
```json
{
  "goalkeeper_specific": [
    {"key": "saves", "label": "Saves", "type": "count"},
    {"key": "save_percentage", "label": "Save %", "type": "percentage"},
    {"key": "clean_sheets", "label": "Clean Sheets", "type": "count"},
    {"key": "clean_sheet_percentage", "label": "Clean Sheet %", "type": "percentage"},
    {"key": "goals_against", "label": "Goals Against", "type": "count"},
    {"key": "goals_against_per90", "label": "Goals Against per 90", "type": "decimal"},
    {"key": "shots_on_target_against", "label": "Shots on Target Against", "type": "count"}
  ],
  "penalties": [
    {"key": "penalties_attempted", "label": "Penalties Attempted", "type": "count"},
    {"key": "penalties_saved", "label": "Penalties Saved", "type": "count"},
    {"key": "penalties_allowed", "label": "Penalties Allowed", "type": "count"},
    {"key": "penalties_missed", "label": "Penalties Missed", "type": "count"}
  ],
  "performance": [
    {"key": "wins", "label": "Wins", "type": "count"},
    {"key": "draws", "label": "Draws", "type": "count"},
    {"key": "losses", "label": "Losses", "type": "count"}
  ],
  "general": [
    {"key": "matches", "label": "Matches Played", "type": "count"},
    {"key": "games_starts", "label": "Games Started", "type": "count"},
    {"key": "minutes_played", "label": "Minutes Played", "type": "count"}
  ]
}
```

---

## 📋 Matchlogs

### Get Player Matchlogs

**GET** `/api/matchlogs/{player_id}`

Get detailed match-by-match statistics for a specific player.

**Path Parameters:**
- `player_id` (int, required): Player ID

**Query Parameters:**
- `season` (string, optional): Filter by season (e.g., "2025-2026")
- `competition` (string, optional): Filter by competition name (e.g., "La Liga")
- `limit` (int, optional): Maximum number of matches (default: 100)

**Example:**
```bash
# Get all matches
curl http://localhost:8000/api/matchlogs/1

# Filter by season
curl "http://localhost:8000/api/matchlogs/1?season=2025-2026"

# Filter by competition
curl "http://localhost:8000/api/matchlogs/1?competition=La%20Liga"

# Limit results
curl "http://localhost:8000/api/matchlogs/1?limit=10"
```

**Response:**
```json
{
  "player_id": 1,
  "player_name": "Robert Lewandowski",
  "total_matches": 15,
  "filters": {
    "season": "2025-2026",
    "competition": null
  },
  "matches": [
    {
      "id": 19244,
      "date": "2025-08-28",
      "competition": "La Liga",
      "round": "Matchweek 3",
      "venue": "Home",
      "opponent": "Real Madrid",
      "result": "W 2-1",
      "minutes_played": 90,
      "goals": 1,
      "assists": 1,
      "shots": 4,
      "shots_on_target": 3,
      "xg": 0.8,
      "xa": 0.3,
      "passes_completed": 25,
      "passes_attempted": 32,
      "pass_completion_pct": 78.1,
      "key_passes": 2,
      "tackles": 1,
      "interceptions": 0,
      "blocks": 0,
      "touches": 45,
      "dribbles_completed": 2,
      "carries": 15,
      "fouls_committed": 1,
      "fouls_drawn": 2,
      "yellow_cards": 0,
      "red_cards": 0
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Matchlogs retrieved
- `404 Not Found` - Player not found

---

### Get Matchlogs Stats Summary

**GET** `/api/matchlogs/{player_id}/stats`

Get aggregated statistics calculated from all match logs.

**Path Parameters:**
- `player_id` (int, required): Player ID

**Query Parameters:**
- `season` (string, optional): Filter by season
- `competition` (string, optional): Filter by competition

**Example:**
```bash
curl http://localhost:8000/api/matchlogs/1/stats
curl "http://localhost:8000/api/matchlogs/1/stats?season=2025-2026"
```

**Response:**
```json
{
  "player_id": 1,
  "player_name": "Robert Lewandowski",
  "filters": {
    "season": "2025-2026",
    "competition": null
  },
  "summary": {
    "total_matches": 15,
    "total_minutes": 1260,
    "total_goals": 12,
    "total_assists": 5,
    "total_shots": 45,
    "total_shots_on_target": 28,
    "total_xg": 10.5,
    "total_xa": 3.8,
    "total_yellow_cards": 2,
    "total_red_cards": 0,
    "avg_minutes_per_match": 84.0,
    "avg_goals_per_match": 0.80,
    "avg_assists_per_match": 0.33
  }
}
```

**Status Codes:**
- `200 OK` - Stats retrieved
- `404 Not Found` - Player not found

---

### Get Match Details

**GET** `/api/matchlogs/match/{match_id}`

Get detailed statistics for a specific match.

**Path Parameters:**
- `match_id` (int, required): Match ID

**Example:**
```bash
curl http://localhost:8000/api/matchlogs/match/19244
```

**Response:**
```json
{
  "match_id": 19244,
  "player": {
    "id": 1,
    "name": "Robert Lewandowski",
    "team": "Barcelona"
  },
  "match_info": {
    "date": "2025-08-28",
    "competition": "La Liga",
    "round": "Matchweek 3",
    "venue": "Home",
    "opponent": "Real Madrid",
    "result": "W 2-1"
  },
  "performance": {
    "minutes_played": 90,
    "goals": 1,
    "assists": 1
  },
  "shooting": {
    "shots": 4,
    "shots_on_target": 3,
    "xg": 0.8
  },
  "passing": {
    "passes_completed": 25,
    "passes_attempted": 32,
    "pass_completion_pct": 78.1,
    "key_passes": 2,
    "xa": 0.3
  },
  "defense": {
    "tackles": 1,
    "interceptions": 0,
    "blocks": 0
  },
  "possession": {
    "touches": 45,
    "dribbles_completed": 2,
    "carries": 15
  },
  "discipline": {
    "fouls_committed": 1,
    "fouls_drawn": 2,
    "yellow_cards": 0,
    "red_cards": 0
  }
}
```

**Status Codes:**
- `200 OK` - Match found
- `404 Not Found` - Match not found

---

## 📚 Additional Documentation

- **[TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)** - Database connection troubleshooting
- **[SCHEDULER_STATUS_GUIDE.md](SCHEDULER_STATUS_GUIDE.md)** - Scheduler monitoring and configuration
- **[README.md](README.md)** - Complete project documentation
- **[LEGAL_NOTICE.md](LEGAL_NOTICE.md)** - Legal terms and data attribution

---

## 🐛 Error Responses

All endpoints return standard HTTP status codes and JSON error messages:

**400 Bad Request:**
```json
{
  "detail": "Goalkeepers can only be compared with other goalkeepers. Please select two goalkeepers or two field players."
}
```

**404 Not Found:**
```json
{
  "detail": "Player not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error message"
}
```

---

## 📊 Data Models

### Player
```typescript
{
  id: number
  name: string
  position: string  // "Goalkeeper", "Defender", "Midfielder", "Striker", etc.
  current_team: string | null
  league: string | null
  nationality: string
  fbref_id: string | null
  api_id: number | null
}
```

### Competition Stats
```typescript
{
  id: number
  player_id: number
  season: string  // "2025-2026"
  competition_type: string  // "LEAGUE", "EUROPEAN_CUPS", "DOMESTIC_CUPS", "NATIONAL_TEAM"
  competition_name: string
  games: number
  games_starts: number
  minutes: number
  goals: number
  assists: number
  xg: number
  npxg: number
  xa: number
  penalty_goals: number
  shots: number
  shots_on_target: number
  yellow_cards: number
  red_cards: number
}
```

### Goalkeeper Stats
```typescript
{
  id: number
  player_id: number
  season: string
  competition_type: string
  competition_name: string
  games: number
  games_starts: number
  minutes: number
  goals_against: number
  goals_against_per90: number
  shots_on_target_against: number
  saves: number
  save_percentage: number
  clean_sheets: number
  clean_sheet_percentage: number
  wins: number
  draws: number
  losses: number
  penalties_attempted: number
  penalties_allowed: number
  penalties_saved: number
  penalties_missed: number
}
```

### Player Match
```typescript
{
  id: number
  player_id: number
  match_date: string  // ISO date
  competition: string
  round: string
  venue: string  // "Home" or "Away"
  opponent: string
  result: string  // "W 2-1", "L 0-3", "D 1-1"
  minutes_played: number
  goals: number
  assists: number
  shots: number
  shots_on_target: number
  xg: number
  xa: number
  passes_completed: number
  passes_attempted: number
  pass_completion_pct: number
  key_passes: number
  tackles: number
  interceptions: number
  blocks: number
  touches: number
  dribbles_completed: number
  carries: number
  fouls_committed: number
  fouls_drawn: number
  yellow_cards: number
  red_cards: number
}
```

---

**Last Updated:** 2025-12-02
