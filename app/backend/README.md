# Polish Football Data Hub International - Backend API

****Status:** ✅ Production Ready

## ⚖️ Legal Notice

**This API is for EDUCATIONAL and NON-COMMERCIAL use only.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Portfolio, CV, education
- **NOT for commercial use** without proper licensing
- **See:** [LEGAL_NOTICE.md](../../LEGAL_NOTICE.md) in root directory

# Polish Football Data Hub International - Backend API

FastAPI backend do zarządzania danymi polskich piłkarzy grających za granicą. Automatyczna synchronizacja danych z FBref.com przez Playwright scraper.

## 🆕 Nowe w v0.7.3

- ✅ **Naprawione porównywanie bramkarzy** - Poprawione nazwy kolumn SQL dla goalkeeper_stats
- ✅ **Scheduler z email notifications** - HTML raporty po synchronizacji (stats + matchlogs)
- ✅ **Match logs endpoint** - Pełne wsparcie dla szczegółowych statystyk meczowych
- ✅ **Improved comparison API** - Walidacja typu gracza (GK vs field player)
- ✅ **Enhanced Swagger/ReDoc docs** - Zaktualizowana dokumentacja API

## 🚀 Szybki start

### 1. Uruchom backend

Z głównego katalogu projektu:
```powershell
.\start_backend.ps1
```

Lub ręcznie:
```powershell
# Aktywuj środowisko wirtualne (z głównego katalogu)
..\..\.venv\Scripts\Activate.ps1

# Uruchom serwer FastAPI
python -m uvicorn app.backend.main:app --reload --port 8000
```

Serwer będzie dostępny pod adresem: **http://127.0.0.1:8000**

### 2. Dokumentacja API

Interaktywna dokumentacja API (automatycznie generowana przez FastAPI):
- **Swagger UI:** http://localhost:8000/docs - testuj endpointy w przeglądarce
- **ReDoc:** http://localhost:8000/redoc - czytelna dokumentacja

**💡 Swagger UI pozwala:**
- ✅ Testować wszystkie endpointy bez Postmana
- ✅ Zobacz request/response schemas
- ✅ Przykładowe requesty i responses
- ✅ Automatyczna walidacja parametrów

## 📡 Endpointy API

### 🔍 Players (Gracze)

#### `GET /api/players`
Zwraca listę wszystkich piłkarzy z bazy danych.

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/players"
```

**Odpowiedź:**
```json
[
  {
    "id": 1,
    "name": "Robert Lewandowski",
    "team": "Barcelona",
    "league": "La Liga",
    "position": "FW",
    "nationality": "Poland",
    "is_goalkeeper": false,
    "last_updated": "2025-01-15"
  }
]
```

#### `GET /api/players/{player_id}`
Zwraca szczegółowe dane konkretnego piłkarza.

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/players/1"
```

### 📊 Comparison (Porównanie graczy)

#### `GET /api/comparison/players/{player_id}/stats`
Pobiera wszystkie statystyki dla jednego gracza.

**Parametry:**
- `season` (opcjonalny) - np. "2025-2026"

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/comparison/players/1/stats?season=2025-2026"
```

#### `GET /api/comparison/compare`
Porównuje statystyki dwóch graczy.

**Parametry:**
- `player1_id` (wymagany) - ID pierwszego gracza
- `player2_id` (wymagany) - ID drugiego gracza
- `season` (opcjonalny) - sezon do porównania
- `stats` (opcjonalny) - lista statystyk do porównania

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/comparison/compare?player1_id=1&player2_id=2&season=2025-2026"
```

#### `GET /api/comparison/available-stats`
Zwraca listę dostępnych statystyk do porównania.

**Parametry:**
- `player_type` (opcjonalny) - "goalkeeper" lub "field_player"

**Kategorie dla zawodników z pola:**
- `offensive` - gole, asysty, xG, xA, strzały
- `defensive` - żółte/czerwone kartki
- `general` - mecze, minuty, podstawowe składy

**Kategorie dla bramkarzy:**
- `goalkeeper_specific` - saves, save_percentage, clean_sheets, goals_against, etc.
- `penalties` - penalties_attempted, penalties_saved, penalties_allowed
- `performance` - wins, draws, losses
- `general` - matches, games_starts, minutes_played

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/comparison/available-stats?player_type=goalkeeper"
```

### 📋 Matchlogs (Szczegóły meczów)

#### `GET /api/matchlogs/{player_id}`
Pobiera match logs dla konkretnego gracza z możliwością filtrowania.

**Parametry query:**
- `season` (opcjonalny) - filtruj po sezonie (np. "2025-2026")
- `competition` (opcjonalny) - filtruj po rozgrywkach (np. "La Liga")
- `limit` (opcjonalny) - maksymalna liczba wyników

#### `GET /api/matchlogs/{player_id}/stats`
Pobiera zagregowane statystyki z meczów dla gracza.

#### `GET /api/matchlogs/match/{match_id}`
Pobiera szczegóły pojedynczego meczu.

**Przykład:**
```powershell
# Pobierz match logs gracza
Invoke-RestMethod "http://127.0.0.1:8000/api/matchlogs/1"

# Filtruj po sezonie
Invoke-RestMethod "http://127.0.0.1:8000/api/matchlogs/1?season=2025-2026"

# Agregowane statystyki
Invoke-RestMethod "http://127.0.0.1:8000/api/matchlogs/1/stats"
```

**Odpowiedź:**
```json
{
  "player_id": 1,
  "player_name": "Robert Lewandowski",
  "total_matches": 16,
  "matches": [
    {
      "date": "2025-11-08",
      "competition": "La Liga",
      "opponent": "Real Madrid",
      "result": "W 3-1",
      "goals": 2,
      "assists": 1,
      "minutes_played": 90,
      "xg": 1.8,
      "xa": 0.4
    }
  ]
}
```

#### `GET /api/matchlogs/{player_id}/stats`
Pobiera zagregowane statystyki z meczów (podsumowanie).

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/players/1/matches/stats?season=2025-2026"
```

#### `GET /api/matches/{match_id}`
Pobiera szczegółowe statystyki konkretnego meczu.

**Przykład:**
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/matches/123"
```

## 🗄️ Struktura bazy danych

Backend używa SQLite (`players.db`).

### Główne tabele:

#### `players`
Podstawowe informacje o graczach.

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | INTEGER | Klucz główny |
| name | VARCHAR | Imię i nazwisko |
| team | VARCHAR | Aktualny klub |
| league | VARCHAR | Liga |
| position | VARCHAR | Pozycja |
| nationality | VARCHAR | Narodowość |
| is_goalkeeper | BOOLEAN | Czy bramkarz |
| api_id | INTEGER | ID z FBref |
| last_updated | DATE | Data ostatniej aktualizacji |

#### `competition_stats`
Statystyki zawodników w różnych rozgrywkach (dla zawodników nie-bramkarzy).

| Kolumna | Opis |
|---------|------|
| player_id | Klucz obcy do gracza |
| season | Sezon (np. "2025-2026") |
| competition_type | Typ rozgrywek: LEAGUE / EUROPEAN_CUP / NATIONAL_TEAM / DOMESTIC_CUP |
| competition_name | Nazwa rozgrywek |
| games | Liczba meczów |
| goals | Gole |
| assists | Asysty |
| xg | Expected Goals |
| xa | Expected Assists |
| npxg | Non-Penalty Expected Goals |
| penalty_goals | Bramki z karnych |
| minutes | Minuty |
| yellow_cards | Żółte kartki |
| red_cards | Czerwone kartki |

**Uwagi:**
- Mecze reprezentacji używają **roku kalendarzowego** (np. "2025"), nie sezonu ("2025-2026")
- Kwalifikacje Champions League są **agregowane** z Europa League jako "Europa Lg" (standard FBref)

#### `goalkeeper_stats`
Statystyki bramkarzy w różnych rozgrywkach.

| Kolumna | Opis |
|---------|------|
| player_id | Klucz obcy do gracza |
| season | Sezon |
| competition_type | Typ rozgrywek (LEAGUE / EUROPEAN_CUP / DOMESTIC_CUP / NATIONAL_TEAM) |
| competition_name | Nazwa rozgrywek |
| games | Liczba meczów |
| saves | Obrony |
| clean_sheets | Czyste konta |
| goals_against | Bramki stracone |
| save_percentage | % obron |
| penalties_saved | Obronione karne |

**Uwagi:**
- Te same zasady co `competition_stats` dla sezonów (reprezentacja = rok kalendarzowy)

#### `player_matches`
Szczegółowe statystyki z pojedynczych meczów (matchlogs).

| Kolumna | Opis |
|---------|------|
| player_id | Klucz obcy do gracza |
| match_date | Data meczu |
| competition | Nazwa rozgrywek (np. "La Liga") |
| opponent | Przeciwnik |
| result | Wynik (np. "W 3-1", "L 0-2") |
| venue | Home/Away |
| goals, assists | Gole i asysty |
| minutes_played | Minuty |
| shots, shots_on_target | Strzały |
| xg, xa | Expected Goals/Assists |
| passes_completed, passes_attempted | Podania |
| tackles, interceptions, blocks | Defensywa |
| touches, dribbles_completed | Posiadanie piłki |
| yellow_cards, red_cards | Kartki |

## 📁 Struktura projektu backend

```
app/backend/
├── __init__.py
├── config.py              # Konfiguracja (DATABASE_URL, etc.)
├── database.py            # Połączenie z bazą SQLAlchemy
├── main.py                # Główna aplikacja FastAPI + scheduler
│
├── models/                # Modele SQLAlchemy (ORM)
│   ├── __init__.py
│   ├── player.py          # Model Player
│   ├── competition_stats.py  # Statystyki według rozgrywek
│   ├── goalkeeper_stats.py   # Statystyki bramkarskie
│   ├── player_match.py    # Model PlayerMatch (matchlogs)
│   └── season_stats.py    # (deprecated - nieużywany)
│
├── routers/               # Endpointy API (routing)
│   ├── __init__.py
│   ├── players.py         # GET /api/players
│   ├── comparison.py      # GET /api/comparison/*
│   ├── matchlogs.py       # GET /api/matchlogs/*
│ 
│
├── schemas/               # Pydantic schemas (walidacja)
│   ├── __init__.py
│   └── player.py
│
└── services/              # Serwisy biznesowe
    ├── __init__.py
    ├── fbref_playwright_scraper.py  # Główny scraper FBref
   
```

## 🔧 Konfiguracja

### Zmienne środowiskowe

Utwórz plik `.env` w głównym katalogu projektu:

```env
# Baza danych
DATABASE_URL=sqlite:///./players.db

# Scheduler (automatyczna synchronizacja)
ENABLE_SCHEDULER=false

# Email notifications (opcjonalne, dla schedulera)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**Scheduler:** Uruchom `ENABLE_SCHEDULER=true` aby włączyć automatyczną synchronizację:
- Stats: poniedziałek i czwartek o 6:00 AM
- Matchlogs: wtorek o 7:00 AM
- Email notifications po każdej synchronizacji
- Zobacz status schedulera: `GET /` (root endpoint zawiera scheduler info)

## 🔄 Synchronizacja danych

Backend **NIE** posiada endpointów do synchronizacji. Zamiast tego użyj skryptów CLI:

### Synchronizacja pojedynczego gracza:
```powershell
# Obecny sezon (2025-2026) - competition stats + match logs
python sync_player_full.py "Robert Lewandowski" --all-seasons

# Konkretny sezon
python sync_player_full.py "Robert Lewandowski" --all-seasons --season=2024-2025

# Wszystkie sezony
python sync_player_full.py "Robert Lewandowski" --all-seasons --all-seasons
```

### Synchronizacja wszystkich graczy:
```powershell
# Removed - use scheduler on Render (automatic sync Mon/Thu/Tue)
```

### Synchronizacja matchlogs (szczegóły meczów):
```powershell
python sync_match_logs.py "Robert Lewandowski"
```

### Automatyczna synchronizacja:
Ustaw `ENABLE_SCHEDULER=true` w pliku `.env` - scheduler zsynchronizuje wszystkich graczy automatycznie:

**Scheduler jobs:**
- **Stats sync**: Poniedziałek i Czwartek o 6:00 (Europe/Warsaw) - synchronizacja statystyk
- **Matchlogs sync**: Wtorek o 7:00 (Europe/Warsaw) - synchronizacja match logs

**Email notifications:**
- Automatyczne HTML raporty po każdej synchronizacji
- Konfiguracja w `.env`: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`
- Zobacz: [EMAIL_SETUP_GUIDE.md](../../EMAIL_SETUP_GUIDE.md)

## 🧪 Testowanie API

### Podstawowe testy

```powershell
# 1. Sprawdź status API
Invoke-RestMethod "http://127.0.0.1:8000/"

# 2. Pobierz listę graczy
$players = Invoke-RestMethod "http://127.0.0.1:8000/api/players"
Write-Host "Total players: $($players.Count)"

# 3. Szczegóły gracza
Invoke-RestMethod "http://127.0.0.1:8000/api/players/1"

# 4. Porównaj dwóch graczy
Invoke-RestMethod "http://127.0.0.1:8000/api/comparison/compare?player1_id=1&player2_id=2"
```

### Sprawdzanie danych w bazie

**Opcja 1: Przez Supabase Dashboard**
- Zaloguj się do https://supabase.com
- Wybierz projekt → Table Editor
- Zobacz tabele: players, competition_stats, goalkeeper_stats, player_matches

**Opcja 2: Przez API**
```powershell
# Liczba graczy
$players = Invoke-RestMethod "http://127.0.0.1:8000/api/players"
Write-Host "Total players: $($players.Count)"

# Statystyki competition
$stats = Invoke-RestMethod "http://127.0.0.1:8000/api/players/stats/competition"
Write-Host "Total competition stats records: $($stats.Count)"
```

## 🐛 Rozwiązywanie problemów

### Port 8000 zajęty
```powershell
# Uruchom na innym porcie
python -m uvicorn app.backend.main:app --reload --port 8001
```

### Błąd połączenia z bazą PostgreSQL
```powershell
# Sprawdź DATABASE_URL w .env
Get-Content .env | Select-String "DATABASE_URL"

# Testuj połączenie przez API
Invoke-RestMethod "http://127.0.0.1:8000/health"

# Uruchom migracje (jeśli potrzebne)
alembic upgrade head
```

### Brak Playwright/Chromium
```powershell
python -m playwright install chromium
```

## 📚 Technologie

- **FastAPI** - nowoczesny framework webowy
- **SQLAlchemy 2.0+** - ORM do pracy z bazą danych
- **Pydantic** - walidacja danych i schemas
- **Playwright** - automatyzacja przeglądarki do scrapingu
- **APScheduler** - scheduler do automatycznych zadań
- **PostgreSQL (Supabase)** - baza danych produkcyjna (darmowe 500MB)
- **Alembic** - migracje bazy danych


