# 📚 API Documentation - Polish Football Players Abroad

**Base URL:** `http://localhost:8000` (local) or `https://your-backend.onrender.com` (production)
**Interactive Docs:**
- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

> ✅ **All endpoints listed below are tested and working**

---

## ⚖️ Legal Notice

**This API is for educational and non-commercial use only.**

- **Data Source:** RapidAPI free-api-live-football-data
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
5. [Leaderboard](#leaderboard)
6. [Live Matches](#live-matches)

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
  "title": "Polish Football Players Abroad - Backend API",
  "version": "1.0.0",
  "description": "Backend API for tracking Polish football players statistics from RapidAPI",
  "features": [
    "📊 Player statistics from RapidAPI",
    "🔄 Automated data synchronization",
    "⚖️ Visual player comparison (field players & goalkeepers)",
    "🏆 League leaderboards (goals, assists, rating)",
    "📺 Live match tracking"
  ],
  "scheduler": {
    "enabled": true,
    "stats_sync_schedule": "Thursday & Sunday at 23:00 (Europe/Warsaw)",
    "matchlogs_sync_schedule": "Daily at 09:00",
    "cache_cleanup": "Daily at 03:00"
  },
  "database": {
    "type": "PostgreSQL",
    "provider": "Supabase",
    "tier": "Free (500MB storage)"
  }
}
```

---

## 👥 Players

### Get All Players

**GET** `/api/players/`

Get list of all Polish players in the database.

**Query Parameters:**
- `league` (string, optional): Filter by league
- `team` (string, optional): Filter by team
- `position` (string, optional): Filter by position
- `limit` (int, optional): Max results (default: 100)

**Example:**
```bash
curl http://localhost:8000/api/players/
curl "http://localhost:8000/api/players/?league=Serie%20A"
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
    "rapidapi_player_id": 12345,
    "rapidapi_team_id": 529,
    "is_goalkeeper": false,
    "last_updated": "2025-12-02"
  },
  {
    "id": 2,
    "name": "Wojciech Szczęsny",
    "position": "Goalkeeper",
    "current_team": "Juventus",
    "league": "Serie A",
    "nationality": "Poland",
    "rapidapi_player_id": 67890,
    "rapidapi_team_id": 496,
    "is_goalkeeper": true,
    "last_updated": "2025-12-02"
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
  "rapidapi_player_id": 12345,
  "rapidapi_team_id": 529,
  "is_goalkeeper": false,
  "last_updated": "2025-12-02"
}
```

**Status Codes:**
- `200 OK` - Player found
- `404 Not Found` - Player not found

---

### Get All Competition Stats

**GET** `/api/players/stats/competition`

Get all competition statistics for all players (competition_stats table).

**Query Parameters:**
- `season` (string, optional): Filter by season (e.g., "2025-2026")
- `competition_type` (string, optional): LEAGUE, EUROPEAN_CUPS, DOMESTIC_CUPS, NATIONAL_TEAM

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
    "yellow_cards": 2,
    "red_cards": 0,
    "penalty_goals": 3,
    "data_source": "rapidapi"
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
    "goals_conceded": 18,
    "clean_sheets": 5,
    "data_source": "rapidapi"
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
    "yellow_cards": 0,
    "red_cards": 0,
    "data_source": "rapidapi"
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
curl "http://localhost:8000/api/comparison/players/1/stats?season=2025-2026"
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
    "minutes_played": 1260
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
    "G+A_per_90": 0.80
  },
  "comparison_date": "2025-12-02T12:00:00",
  "player_type": "field_player"
}
```

**Status Codes:**
- `200 OK` - Comparison successful
- `400 Bad Request` - Trying to compare goalkeeper with field player
- `404 Not Found` - One or both players not found

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
    {"key": "G+A_per_90", "label": "G+A per 90", "type": "decimal"}
  ],
  "defensive": [
    {"key": "yellow_cards", "label": "Yellow Cards", "type": "count"},
    {"key": "red_cards", "label": "Red Cards", "type": "count"}
  ],
  "general": [
    {"key": "matches", "label": "Matches Played", "type": "count"},
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
    "total_yellow_cards": 2,
    "total_red_cards": 0,
    "avg_minutes_per_match": 84.0,
    "avg_goals_per_match": 0.80,
    "avg_assists_per_match": 0.33
  }
}
```

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
  "discipline": {
    "yellow_cards": 0,
    "red_cards": 0
  }
}
```

---

## 🏆 Leaderboard (NEW!)

### Get Top Scorers

**GET** `/api/leaderboard/goals/{league_name}`

Get top scorers for a specific league.

**Path Parameters:**
- `league_name` (string, required): League name (e.g., "Serie A", "Premier League", "La Liga")

**Available Leagues:**
- Premier League
- La Liga
- Bundesliga
- Serie A
- Ligue 1
- Eredivisie
- Primeira Liga
- Belgian Pro League
- Scottish Premiership
- Super Lig
- Champions League
- Europa League
- Conference League

**Example:**
```bash
curl http://localhost:8000/api/leaderboard/goals/Serie%20A
```

**Response:**
```json
{
  "league_name": "Serie A",
  "league_id": 55,
  "category": "goals",
  "players": [
    {
      "rank": 1,
      "player_id": 12345,
      "name": "Mateo Retegui",
      "team": "Atalanta",
      "position": "FW",
      "value": 15.0,
      "nationality": "Argentina"
    },
    {
      "rank": 2,
      "player_id": 67890,
      "name": "Lautaro Martínez",
      "team": "Inter",
      "position": "FW",
      "value": 12.0,
      "nationality": "Argentina"
    }
  ]
}
```

---

### Get Top Assists

**GET** `/api/leaderboard/assists/{league_name}`

Get top assist providers for a league.

**Example:**
```bash
curl http://localhost:8000/api/leaderboard/assists/Premier%20League
```

**Response:** Same structure as top scorers, with `category: "assists"`

---

### Get Top Rated Players

**GET** `/api/leaderboard/rating/{league_name}`

Get top rated players for a league.

**Example:**
```bash
curl http://localhost:8000/api/leaderboard/rating/Bundesliga
```

**Response:** Same structure as top scorers, with `category: "rating"`

---

### Get All Leaderboards

**GET** `/api/leaderboard/all/{league_name}`

Get all leaderboards (goals, assists, rating) for a league in one request.

**Example:**
```bash
curl http://localhost:8000/api/leaderboard/all/La%20Liga
```

**Response:**
```json
{
  "league_name": "La Liga",
  "league_id": 140,
  "top_scorers": [...],
  "top_assists": [...],
  "top_rated": [...]
}
```

---

### Get Available Leagues

**GET** `/api/leaderboard/leagues`

Get list of available leagues for leaderboard.

**Example:**
```bash
curl http://localhost:8000/api/leaderboard/leagues
```

**Response:**
```json
{
  "leagues": [
    {"name": "Premier League", "id": 39},
    {"name": "La Liga", "id": 140},
    {"name": "Bundesliga", "id": 78},
    {"name": "Serie A", "id": 55},
    {"name": "Ligue 1", "id": 61},
    {"name": "Champions League", "id": 2},
    {"name": "Europa League", "id": 3}
  ]
}
```

---

## 📺 Live Matches (NEW!)

### Get Today's Matches

**GET** `/api/live/today`

Get all matches for today involving Polish players.

**Example:**
```bash
curl http://localhost:8000/api/live/today
```

**Response:**
```json
{
  "date": "2025-12-02",
  "live_matches": [
    {
      "event_id": 123456,
      "home_team": "Roma",
      "away_team": "Inter",
      "home_score": 1,
      "away_score": 1,
      "status": "LIVE 45'",
      "competition": "Serie A",
      "polish_players": [
        {"name": "Piotr Zieliński", "team": "Inter"},
        {"name": "Nicola Zalewski", "team": "Roma"}
      ]
    }
  ],
  "scheduled_matches": [
    {
      "event_id": 123457,
      "home_team": "Juventus",
      "away_team": "Milan",
      "status": "NS",
      "kickoff_time": "20:45",
      "competition": "Serie A",
      "polish_players": [
        {"name": "Arkadiusz Milik", "team": "Juventus"}
      ]
    }
  ]
}
```

---

### Get Live Matches Only

**GET** `/api/live/live`

Get only currently live matches.

**Example:**
```bash
curl http://localhost:8000/api/live/live
```

**Response:**
```json
{
  "live_matches": [
    {
      "event_id": 123456,
      "home_team": "Roma",
      "away_team": "Inter",
      "home_score": 1,
      "away_score": 1,
      "status": "LIVE 67'",
      "competition": "Serie A",
      "polish_players": [...]
    }
  ]
}
```

---

### Get Team Matches

**GET** `/api/live/team/{team_name}`

Get live/scheduled matches for a specific team.

**Path Parameters:**
- `team_name` (string, required): Team name

**Example:**
```bash
curl http://localhost:8000/api/live/team/Roma
curl http://localhost:8000/api/live/team/Juventus
```

**Response:**
```json
{
  "team": "Roma",
  "matches": [
    {
      "event_id": 123456,
      "home_team": "Roma",
      "away_team": "Inter",
      "status": "LIVE 45'",
      "home_score": 1,
      "away_score": 1
    }
  ]
}
```

---

### Check Player Playing Today

**GET** `/api/live/player/{player_id}`

Check if a specific player is playing today.

**Path Parameters:**
- `player_id` (int, required): Player database ID

**Example:**
```bash
curl http://localhost:8000/api/live/player/1
```

**Response:**
```json
{
  "player_id": 1,
  "player_name": "Robert Lewandowski",
  "is_playing_today": true,
  "matches": [
    {
      "event_id": 123458,
      "team": "Barcelona",
      "opponent": "Real Madrid",
      "status": "NS",
      "kickoff_time": "21:00",
      "competition": "La Liga"
    }
  ]
}
```

---

## 📚 Additional Documentation

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Troubleshooting guide
- **[README.md](README.md)** - Complete project documentation
- **[LEGAL_NOTICE.md](LEGAL_NOTICE.md)** - Legal terms and data attribution
- **[RAPIDAPI_SETUP.md](RAPIDAPI_SETUP.md)** - RapidAPI configuration guide

---

## 🐛 Error Responses

All endpoints return standard HTTP status codes and JSON error messages:

**400 Bad Request:**
```json
{
  "detail": "Goalkeepers can only be compared with other goalkeepers."
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
  position: string  // "Goalkeeper", "Defender", "Midfielder", "Striker"
  current_team: string | null
  league: string | null
  nationality: string
  rapidapi_player_id: number | null
  rapidapi_team_id: number | null
  is_goalkeeper: boolean
  last_updated: string  // ISO date
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
  yellow_cards: number
  red_cards: number
  penalty_goals: number
  data_source: string  // "rapidapi"
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
  goals_conceded: number
  clean_sheets: number
  data_source: string
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
  yellow_cards: number
  red_cards: number
  data_source: string
}
```

---

**Last Updated:** 2025-12-02
