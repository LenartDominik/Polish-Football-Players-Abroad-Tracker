# 🇵🇱 Polish Football Data Hub International

**Status:** ✅ Production Ready | **Baza danych:** PostgreSQL (Supabase) | **Deployment:** Cloud-Ready

> 📊 Monitorowanie i analiza statystyk 90+ polskich piłkarzy grających za granicą w czasie rzeczywistym

## 🎯 Opis Projektu

Projekt demonstruje wykorzystanie **web scrapingu** do regularnego pobierania i przetwarzania aktualnych statystyk piłkarzy z witryny **fbref.com**. Część backendowa oparta na **FastAPI** cyklicznie aktualizuje bazę danych, a frontend **Streamlit** pozwala na szybki podgląd danych w przyjaznej formie. Moja platforma jest oparta na mechanizmach automatyzujących pobieranie, walidację i prezentację danych.

**Kluczowe Technologie i Techniki:**
- 🕸️ **Web Scraping:** Playwright headless browser do ekstrakcji dynamicznej treści
- 🔄 **Automatyzacja:** APScheduler do okresowej synchronizacji danych (2-3x/tydzień)
- 🛡️ **Walidacja Danych:** Modele Pydantic dla bezpieczeństwa typów i walidacji schematów
- 🗄️ **Database ORM:** SQLAlchemy 2.0+ z migracjami Alembic
- 🔐 **Rate Limiting:** 12-sekundowe opóźnienia między requestami (zgodnie z FBref ToS)
- 📊 **Przetwarzanie Danych:** pandas do agregacji i transformacji statystyk
- 🎨 **Interaktywna Wizualizacja:** Streamlit z wykresami Plotly
- 🔗 **RESTful API:** FastAPI z automatycznie generowaną dokumentacją OpenAPI
- 📧 **Powiadomienia:** Raporty email SMTP po każdej synchronizacji

## 🌐 Aplikacja Live

**Wypróbuj teraz:** (https://polish-football-data-international-tracker.streamlit.app/)

### 📱 Jak korzystać:

1. **Przeglądaj graczy** - Zobacz wszystkich śledzonych polskich piłkarzy z aktualnymi statystykami
2. **Filtruj dane** - Użyj filtrów w sidebarze aby zawęzić według:
   - Ligi (Bundesliga, La Liga, Serie A, itp.)
   - Drużyny
   - Pozycji (GK, DF, MF, FW)
   - Typu rozgrywek (Liga, Puchary Europejskie, Reprezentacja)
   - Sezonu
3. **Porównaj graczy** - Kliknij "Compare Players" w sidebarze aby porównać dwóch graczy
4. **Eksportuj dane** - Pobierz przefiltrowane dane jako CSV do własnej analizy

**📊 Aktualizacje danych:** Automatyczna synchronizacja 3x w tygodniu (poniedziałek, czwartek, wtorek) z FBref.com

---

> ⚖️ **[Informacje prawne - Ważne!](docs/LEGAL_NOTICE.pl.md)** | 🚀 **[Deployment Guide](docs/STREAMLIT_CLOUD_DEPLOYMENT.pl.md)**

## ⚖️ Informacje prawne

**To jest projekt edukacyjny, niekomercyjny.**

- **Źródło danych:** FBref.com (© Sports Reference LLC)
- **Użycie:** Wyłącznie do celów edukacyjnych i portfolio
- **NIE do użytku komercyjnego** bez odpowiedniej licencji
- **Zobacz [docs/LEGAL_NOTICE.pl.md](docs/LEGAL_NOTICE.pl.md) dla pełnych szczegółów**

---

Nowoczesny system do monitorowania polskich piłkarzy grających za granicą. Automatyczna synchronizacja statystyk z FBref.com z użyciem Playwright, zaawansowana analiza danych i interaktywny dashboard.

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

## ✨ Główne funkcjonalności

### 🕸️ FBref Playwright Scraper
- **Automatyczny scraping** danych z FBref.com używając Playwright (headless browser)
- **Zaawansowane statystyki zawodników z pola**: mecze, gole, asysty, xG, xA, xGI, G+A/90, minuty, kartki
- **Statystyki bramkarzy**: obrony, czyste konta, % obron, karne, PSxG (Post-Shot xG)
- **Rate limiting**: 12s między requestami (bezpieczne dla ToS)
- **Rozbicie na rozgrywki**: Liga, Puchary Europejskie (LM/LE/LK), Reprezentacja (ROK KALENDARZOWY!), Puchary krajowe
- **Match logs**: Szczegółowe statystyki meczowe dla każdego zawodnika
- **Tracking 90+ polskich piłkarzy** z europejskich lig

### 📊 Backend API (FastAPI)
- **RESTful API** z automatyczną dokumentacją Swagger/ReDoc
- **Endpointy**: gracze, porównania, statystyki, matchlogs
- **Baza danych**: PostgreSQL (Supabase - darmowe 500MB!)
- **Scheduler**: automatyczna synchronizacja
  - Statystyki: 2x w tygodniu (Poniedziałek/Czwartek 6:00)
  - Matchlogs: 1x w tygodniu (Wtorek 7:00)
- **Email notifications**: HTML raporty po każdej synchronizacji
- **Rate limiting**: 12 sekund między requestami (bezpieczne dla FBref ToS)
- **Cloud deployment**: gotowy do deployment na Render.com (darmowy hosting!)

### 🎨 Frontend Dashboard (Streamlit)
**Multi-page aplikacja** z interaktywnym dashboard i porównywaniem graczy

#### 🏠 Strona główna (`streamlit_app_cloud.py`)
- **Interaktywne filtrowanie**: liga, drużyna, pozycja, typ rozgrywek, sezon
- **Wyszukiwanie graczy** po nazwisku
- **Widoki**: karty graczy, tabele, wykresy top strzelców
- **Enhanced Stats w Details**: xGI, metryki per 90 (xG/90, xA/90, npxG/90, xGI/90, G+A/90)
- **National Team (2025)**: Statystyki kadry według roku kalendarzowego (z tabeli player_matches)
- **Season Statistics History**: Pełna historia wszystkich sezonów (bez kolumn Shots/SoT)
- **Export do CSV**: eksport przefiltrowanych danych
- **Dedykowane statystyki bramkarzy**

#### ⚖️ Compare Players (`pages/2_Compare_Players.py`)
- **Porównanie side-by-side** dwóch graczy z wizualizacjami
- ⚽ Field players vs field players
- 🧤 Goalkeepers vs goalkeepers  
- ⚠️ Blokada nieprawidłowych porównań (GK vs field player)
- 📊 Wykresy radarowe i słupkowe
- 📈 Porównanie statystyk per 90 minut

#### 🔌 API Client (`api_client.py`)
- **Inteligentne połączenie z backendem**:
  - ☁️ Streamlit Cloud: używa `st.secrets["BACKEND_API_URL"]`
  - 💻 Lokalnie: używa `os.getenv("API_BASE_URL")` lub `localhost:8000`
  - ✅ Automatyczne wykrywanie środowiska
- **Error handling**: czytelne komunikaty błędów
- **Caching**: optymalizacja zapytań do API

### 🔄 Synchronizacja danych
- **CLI Scripts**: `sync_player_full.py`, `sync_match_logs.py`
- **Automatyczny scheduler**: synchronizacja w tle (backend na Render)
  - Statystyki graczy: poniedziałek i czwartek 6:00
  - Szczegółowe matchlogi: wtorek 7:00
  - Email powiadomienia po każdej synchronizacji
- **Cron-job.org**: budzi backend przed synchronizacją (5:55, 6:55)
- **Retry mechanism**: ponowne próby dla nieudanych synchronizacji

## ⚡ Quick Start - Najczęstsze komendy

### Uruchom aplikację
```powershell
.\start_backend.ps1    # Backend API (port 8000)
.\start_frontend.ps1   # Dashboard (port 8501)
```

### Zsynchronizuj pojedynczego gracza (wszystkie sezony)
```powershell
python sync_player_full.py "Robert Lewandowski" --all-seasons
```

### Zsynchronizuj szczegóły meczów (matchlogs - obecny sezon)
```powershell
python sync_match_logs.py "Robert Lewandowski"
```

### Automatyczna synchronizacja (najlepsze!)
Backend na Render automatycznie synchronizuje wszystkich graczy:
- **Poniedziałek i Czwartek o 6:00** - pełne statystyki
- **Wtorek o 7:00** - match logs
- **Email powiadomienia** po każdej synchronizacji

**Nie musisz ręcznie synchronizować!** 🤖
```

---

## 🚀 Pełna Instalacja

### Wymagania wstępne
- Python 3.10+
- Playwright (Chromium)
- PostgreSQL (Supabase - darmowe dla projektów hobby)

### 1. Instalacja zależności

```powershell
# Aktywuj środowisko wirtualne
.\.venv\Scripts\Activate.ps1

# Zainstaluj pakiety
pip install -r requirements.txt

# Zainstaluj Playwright Chromium
python -m playwright install chromium
```

### 2. Konfiguracja

Utwórz plik `.env` w głównym katalogu (lub skopiuj z `.env.example`):

```env

# Baza danych (Production - Supabase PostgreSQL - DARMOWE!)
# DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
# 📖 Pełna instrukcja: SUPABASE_MIGRATION_GUIDE.md

# Scheduler (włącz dla automatycznej synchronizacji 2x w tygodniu)
ENABLE_SCHEDULER=false

# Timezone dla schedulera (domyślnie Europe/Warsaw)
SCHEDULER_TIMEZONE=Europe/Warsaw

# Email notifications (opcjonalne - scheduler działa bez nich!)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Użyj Gmail App Password!
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**📧 Email Setup:**
- **Wymagane**: Gmail App Password (nie zwykłe hasło!)
- **Instrukcje**: Zobacz [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)
- **Opcjonalne**: Scheduler działa bez emaili (tylko logi w konsoli)

### 3. Uruchom aplikację

```powershell
# Uruchom backend (port 8000)
.\start_backend.ps1

# Uruchom frontend (port 8501)
.\start_frontend.ps1
```

**Dostęp do aplikacji:**
- 🔧 **Backend API (Swagger UI):** http://localhost:8000/docs
- 📖 **Backend API (ReDoc):** http://localhost:8000/redoc
- 🏥 **Backend Health Check:** http://localhost:8000/health
- 🎨 **Frontend Dashboard:** http://localhost:8501

**💡 Tip:** Swagger UI pozwala testować API bezpośrednio w przeglądarce!

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
- ✅ Competition stats i match logs sezonu 2025-2026 dla wszystkich graczy
- ✅ Liga krajowa + Puchary Europejskie + Reprezentacja
- ✅ Rate limiting: 12 sekund między każdym graczem
- ✅ Email z raportem po zakończeniu (opcjonalnie)

**Wymagania:**
- ⚠️ Backend musi być uruchomiony 24/7
- ⚠️ Komputer musi być włączony (lub użyj cloud deployment!)

**Cloud deployment:** Zobacz [DEPLOYMENT.md](DEPLOYMENT.md) dla darmowego hostingu 24/7!

---

### ⚡ Manualna synchronizacja

#### Synchronizacja pojedynczego gracza

```powershell
# Pełna synchronizacja - wszystkie sezony (competition stats + match logs)
python sync_player_full.py "Robert Lewandowski" --all-seasons

# Tylko match logs dla obecnego sezonu (2025-2026)
python sync_match_logs.py "Robert Lewandowski"

# Match logs dla konkretnego sezonu
python sync_match_logs.py "Robert Lewandowski" --season 2024-2025
```

**Co synchronizuje:**
- **sync_player_full.py**: Competition stats + match logs ze wszystkich sezonów kariery
- **sync_match_logs.py**: Tylko szczegółowe match logs (data, przeciwnik, wynik, gole, asysty, xG, xA, podania, etc.)

#### Automatyczna synchronizacja wszystkich graczy (zalecane!)

Backend na Render automatycznie synchronizuje wszystkich graczy:
- **Poniedziałek i Czwartek o 6:00** - pełne statystyki (wszystkie sezony)
- **Wtorek o 7:00** - match logs (obecny sezon)
- **Email powiadomienia** z raportem po każdej synchronizacji
- **Cron-job.org** budzi backend 5 minut przed synchronizacją

**Nie musisz ręcznie synchronizować!** Scheduler robi to automatycznie. 🤖

Ręczna synchronizacja potrzebna tylko dla:
- Nowych graczy (dodaj i sync ręcznie)
- Natychmiastowej aktualizacji (nie chcesz czekać do Pon/Czw/Wt)

### Automatyczna synchronizacja (Scheduler)

Ustaw w pliku `.env`:
```env
ENABLE_SCHEDULER=true
```

Scheduler automatycznie zsynchronizuje wszystkich graczy:
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
- ✅ **500 MB storage** (wystarczy dla setek graczy)
- ✅ **Automatyczne backupy**
- ✅ **Dashboard do przeglądania danych**
- ✅ **Connection pooling**
- ✅ **DARMOWE NA ZAWSZE** dla projektów hobby!

### 🚀 Konfiguracja (5 minut):
```powershell
# 1. Zarejestruj się: https://supabase.com (DARMOWE!)
# 2. Utwórz projekt
# 3. Skopiuj DATABASE_URL z Settings → Database → Connection string
# 4. Dodaj do .env:
DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# 5. Uruchom migracje (tworzy tabele):
alembic upgrade head
```

**📖 Szczegółowa instrukcja:** [SUPABASE_GUIDE.md](SUPABASE_GUIDE.md)

---

## 🗄️ Struktura bazy danych

### Główne tabele:

**`players`** - podstawowe informacje o graczach
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

### Dodawanie graczy

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
| 🔄 Zsynchronizuj gracza (wszystkie sezony) | `python sync_player_full.py "Lewandowski" --all-seasons` |
| 🎯 Sync matchlogs (obecny sezon) | `python sync_match_logs.py "Lewandowski"` |
| 📅 Sync graczy bez danych | `python sync_missing_players.py` |
| 🤖 **Automatyczna sync (scheduler)** | **Backend na Render - automatycznie Pon/Czw/Wt** |
| 🧪 Test emaila | `python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, [])"` |

### Synchronizacja (pełne przykłady)

| Co chcesz zrobić | Komenda | Czas |
|------------------|---------|------|
| 📚 Pełna synchronizacja gracza (wszystkie sezony) | `python sync_player_full.py "Nazwisko" --all-seasons` | ~60s |
| 🏆 Szczegóły meczów (obecny sezon) | `python sync_match_logs.py "Nazwisko"` | ~15s |
| 🏆 Szczegóły meczów (konkretny sezon) | `python sync_match_logs.py "Nazwisko" --season 2024-2025` | ~15s |
| 🤖 Wszyscy gracze (automatycznie) | **Scheduler na Render (Pon/Czw 6:00, Wt 7:00)** | ~20-30 min |

**💡 Zalecenie:** Używaj schedulera do regularnych aktualizacji. Ręcznie synchronizuj tylko nowych graczy lub gdy potrzebujesz natychmiastowej aktualizacji.

### Dodawanie graczy

Aby dodać nowego gracza, ręcznie dodaj go do bazy danych, a następnie zsynchronizuj:

```powershell
# Synchronizuj nowego gracza (automatycznie znajdzie go na FBref)
python sync_player_full.py "Nazwisko Gracza" --all-seasons
```

### Uruchamianie

| Co chcesz zrobić | Komenda |
|------------------|---------|
| 🔧 Backend API | `.\start_backend.ps1` lub `python -m uvicorn app.backend.main:app --reload` |
| 🎨 Frontend Dashboard | `.\start_frontend.ps1` lub `streamlit run app/frontend/streamlit_app.py` |

### API Endpoints

**Dokumentacja interaktywna:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Główne endpointy:**

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Strona główna API + scheduler status |
| `/health` | GET | Health check (dla monitoringu) |
| `/api/players/` | GET | Lista wszystkich graczy |
| `/api/players/{id}` | GET | Szczegóły gracza |
| `/api/players/stats/competition` | GET | Wszystkie statystyki ligowe/europejskie |
| `/api/players/stats/goalkeeper` | GET | Wszystkie statystyki bramkarskie |
| `/api/players/stats/matches` | GET | Wszystkie mecze (match logs) |
| `/api/comparison/players/{id}/stats` | GET | Statystyki gracza do porównania |
| `/api/comparison/compare` | GET | Porównaj dwóch graczy |
| `/api/comparison/available-stats` | GET | Dostępne statystyki do porównania |
| `/api/matchlogs/{player_id}` | GET | Match logs gracza (z filtrami) |
| `/api/matchlogs/{player_id}/stats` | GET | Agregowane statystyki z meczów |
| `/api/matchlogs/match/{match_id}` | GET | Szczegóły pojedynczego meczu |

**📚 Dokumentacja API:**
- **Swagger UI (interaktywna):** http://localhost:8000/docs
- **ReDoc (czytelna):** http://localhost:8000/redoc

**💡 Swagger UI Features:**
- ✅ Testuj endpointy bezpośrednio w przeglądarce
- ✅ Zobacz wszystkie parametry i response schemas
- ✅ Przykładowe requesty i responses
- ✅ Automatyczna walidacja

---

## 📚 Dokumentacja szczegółowa

### 📖 Dokumentacja projektu
- 📘 [Backend API - Dokumentacja](app/backend/README.md)
- 📗 [Frontend - Dokumentacja](app/frontend/README.md)
- 📄 [Stack technologiczny](STACK.md)
- 📖 [README (English)](README.md) - English version
- 📖 [README (Polish)](README.pl.md) - Polska wersja
- 💻 [Technology Stack](STACK.md) - Użyte technologie i architektura
- 💻 [Stack Technologiczny](STACK.pl.md) - Polska wersja stacku
- 🚀 [Deployment Guide](DEPLOYMENT.md) - **Pełny przewodnik deployment (EN)**
- ☁️ [Streamlit Cloud Deployment](STREAMLIT_CLOUD_DEPLOYMENT.pl.md) - **Szczegółowy tutorial (PL)**
- 📖 [API Documentation](API_DOCUMENTATION.md) - Kompletna dokumentacja API (EN)
- 📖 [Dokumentacja API](API_DOCUMENTATION.pl.md) - Dokumentacja API (PL)
- 🔧 [Troubleshooting](TROUBLESHOOTING.md) - Rozwiązywanie problemów
- ⚖️ [Legal Notice](LEGAL_NOTICE.md) - Informacje prawne (EN)
- ⚖️ [Informacje Prawne](LEGAL_NOTICE.pl.md) - Informacje prawne (PL)
- ⚖️ [Legal Notice](LEGAL_NOTICE.md) - **WAŻNE - Przeczytaj przed użyciem!**
- 🎓 [Credits](CREDITS.md) - Podziękowania i atrybuty

### 🌐 Linki zewnętrzne
- 🌐 [FBref (źródło danych)](https://fbref.com/)
- 📖 [FastAPI Docs](https://fastapi.tiangolo.com/)
- 🎨 [Streamlit Docs](https://docs.streamlit.io/)
- 🎭 [Playwright Docs](https://playwright.dev/python/)

## ☁️ Cloud Deployment (Darmowy hosting 24/7!)

### 🚀 Opcja 1: Render.com - Backend + Supabase (DARMOWE!)

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
4. Render wykrywa `render.yaml` automatycznie! ✨
5. Dodaj zmienne środowiskowe (email)
6. Deploy!

**Szczegółowa instrukcja:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

### 🏢 Opcja 2: Produkcyjny Deployment (PostgreSQL + Streamlit Cloud)

**Aktualny stack produkcyjny:**
- ✅ **PostgreSQL** w chmurze (Supabase - darmowe 500MB)
- ✅ **Streamlit Cloud** - frontend dashboard (darmowe!)
- ✅ **Render.com** - backend API + scheduler (darmowe!)
- ✅ **Automatyczne backupy** (Supabase)
- ✅ **Connection pooling** (Supabase)

**Stack deployment:**
```
Frontend: Streamlit Cloud (FREE tier)
Backend:  Render.com Web Service (FREE tier)
Database: Supabase PostgreSQL (FREE 500MB)
Sync:     Scheduler na Render (2x/tydzień stats, 1x/tydzień matchlogs)
Email:    Gmail SMTP (opcjonalne)
```

**Koszty:** $0/miesiąc (wszystko na darmowych tierach!)

**Szczegółowa instrukcja:** [STREAMLIT_CLOUD_DEPLOYMENT.pl.md](STREAMLIT_CLOUD_DEPLOYMENT.pl.md)

---

### 🖥️ Lokalny deployment (wymaga włączonego komputera)

**Windows Task Scheduler:**
- Automatyczne uruchomienie po restarcie
- Backend działa w tle

**Raspberry Pi:**
- Niskie zużycie energii (~3W)
- Zawsze włączony
- ~200-300 zł jednorazowo

**Instrukcje:** Zobacz [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

---

## 🐛 Rozwiązywanie problemów

### 📚 Dedykowane Przewodniki Troubleshooting

- **[TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)** - Problemy z połączeniem do bazy danych (Supabase, Render)
- **[SCHEDULER_STATUS_GUIDE.md](SCHEDULER_STATUS_GUIDE.md)** - Monitoring i konfiguracja automatycznej synchronizacji
- **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** - Konfiguracja powiadomień email dla schedulera

### Backend nie startuje
```powershell
# Sprawdź czy port 8000 jest wolny
netstat -ano | findstr :8000

# Uruchom na innym porcie
python -m uvicorn app.backend.main:app --port 8001
```

### Frontend pokazuje błąd połączenia
```powershell
# Upewnij się że backend działa
Invoke-RestMethod http://localhost:8000/health

# Uruchom backend jeśli nie działa
.\start_backend.ps1
```

### Brak Playwright/Chromium
```powershell
python -m playwright install chromium
python -m playwright install-deps chromium  # Linux: zainstaluj system dependencies
```

### Błędy synchronizacji
```powershell
# Sprawdź logi
# Backend wyświetla szczegółowe logi w konsoli

# Przetestuj pojedynczego gracza
python sync_player_full.py "Robert Lewandowski" --all-seasons

# Debug mode z widoczną przeglądarką
python sync_player_full.py "Lewandowski" --all-seasons
```

### PostgreSQL: "duplicate key value violates unique constraint"
```powershell
# Automatyczne naprawienie - uruchom skrypt naprawczy
python fix_postgres_sequences.py

# Problem rozwiązany automatycznie w skryptach:
# - sync_player_full.py
# - sync_match_logs.py

# Więcej info: BUGFIX_POSTGRES_SEQUENCES.md
```

### Database Connection Issues (Render/Supabase)

**Problem:** `password authentication failed` lub `connection refused`

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
# Powinno być: "✅ Scheduler uruchomiony"
# Jeśli nie ma - sprawdź .env

# Sprawdź następną synchronizację
# Logi: "📅 Next run: 2025-01-27 06:00:00+01:00"
```

### Email nie wysyła się
```powershell
# Test emaila
python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, []); print('Email sent!')"

# Sprawdź konfigurację
# Zobacz: EMAIL_SETUP_GUIDE.md
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

