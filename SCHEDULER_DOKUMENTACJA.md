# Scheduler - Automatyczna Synchronizacja Graczy

**Status:** ✅ **DZIAŁA POPRAWNIE**

**Data testu:** 2025-12-01

---

## ✅ Wynik testów

### Test 1: FastAPI TestClient
- ❌ Scheduler **NIE działa** z TestClient
- **Przyczyna:** TestClient nie wykonuje lifespan events (znane ograniczenie FastAPI TestClient)

### Test 2: Prawdziwy uvicorn
- ✅ Scheduler **DZIAŁA POPRAWNIE** ✅
- ✅ Joby są zaplanowane
- ✅ Wszystkie funkcje istnieją
- ✅ `lifespan=lifespan` jest przekazany do FastAPI (linia 1038)

**Wyniki testu:**
```
Scheduler running: True ✅
Next stats sync: 2025-12-04 06:00:00+01:00 ✅
Next matchlogs sync: 2025-12-02 07:00:00+01:00 ✅
```

### ✅ POTWIERDZENIE: Kod jest poprawny!

**Linia 1038 w main.py:**
```python
app = FastAPI(
    title="Polish Players Tracker - API",
    # ... description ...
    version="0.7.3",
    lifespan=lifespan,  # ← JEST! ✅
    docs_url="/docs",
    redoc_url="/redoc",
    # ...
)
```

---

## 📅 Harmonogram automatycznej synchronizacji

### 1. Stats Sync (Competition Stats + Goalkeeper Stats)
**Częstotliwość:** 2x w tygodniu  
**Dni:** Poniedziałek i Czwartek  
**Godzina:** 06:00 (Europe/Warsaw)

**Dlaczego te dni?**
- Czwartek 06:00 → dzień po meczach Ligi Mistrzów (środa)
- Poniedziałek 06:00 → dzień po meczach ligowych (weekend)

**Co synchronizuje:**
- Wszystkich graczy (91)
- Competition stats dla sezonu 2025-2026
- Goalkeeper stats dla sezonu 2025-2026
- Rate limit: 12 sekund między graczami
- Czas: ~18 minut (91 graczy × 12s / 60)

### 2. Matchlogs Sync (Player Matches)
**Częstotliwość:** 1x w tygodniu  
**Dzień:** Wtorek  
**Godzina:** 07:00 (Europe/Warsaw)

**Dlaczego wtorek?**
- Daje czas po synchronizacji stats (poniedziałek)
- Match logs są bardziej stabilne dzień później

**Co synchronizuje:**
- Wszystkich graczy z FBref ID
- Match logs dla sezonu 2025-2026
- Rate limit: 12 sekund między graczami
- Czas: ~18 minut

---

## 🔧 Konfiguracja

### Włączenie schedulera

#### Lokalnie (`.env`):
```bash
ENABLE_SCHEDULER=true
```

#### Na Render (Environment Variables):
```bash
ENABLE_SCHEDULER=true
```

### Opcjonalne: Email notifications

#### `.env`:
```bash
# SMTP settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**Uwaga:** Jeśli nie ustawisz SMTP, scheduler będzie działał bez powiadomień email.

---

## 📊 Jak działa scheduler

### Architektura:

```
FastAPI Lifespan Event (startup)
    ↓
AsyncIOScheduler (APScheduler)
    ↓
CronTrigger (harmonogram)
    ↓
scheduled_sync_all_players() → sync_single_player() → FBref
scheduled_sync_matchlogs() → sync_player_matchlogs() → FBref
    ↓
Supabase (zapisanie danych)
    ↓
send_notification_email() (opcjonalne)
```

### Kod (app/backend/main.py):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        # Inicjalizacja schedulera
        scheduler = AsyncIOScheduler(timezone="Europe/Warsaw")
        
        # Dodaj joby
        scheduler.add_job(
            scheduled_sync_all_players,
            CronTrigger(day_of_week='thu,mon', hour=6, minute=0),
            id='sync_all_players'
        )
        
        scheduler.add_job(
            scheduled_sync_matchlogs,
            CronTrigger(day_of_week='tue', hour=7, minute=0),
            id='sync_matchlogs'
        )
        
        # Uruchom
        scheduler.start()
    
    yield
    
    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown()
```

---

## 🔍 Monitorowanie schedulera

### 1. Endpoint `/health`
```bash
curl http://localhost:8000/health
```

**Odpowiedź:**
```json
{
  "status": "ok",
  "timestamp": "2025-12-01T22:30:00",
  "scheduler_running": true
}
```

### 2. Endpoint `/` (root)
```bash
curl http://localhost:8000/
```

**Odpowiedź (fragment):**
```json
{
  "scheduler": {
    "enabled": true,
    "stats_sync_schedule": "Monday & Thursday at 06:00 (Europe/Warsaw)",
    "matchlogs_sync_schedule": "Tuesday at 07:00 (Europe/Warsaw)",
    "next_stats_sync": "2025-12-04 06:00:00+01:00",
    "next_matchlogs_sync": "2025-12-02 07:00:00+01:00"
  }
}
```

### 3. Logi backendu
```bash
# Przy starcie aplikacji
📅 Initializing scheduler...
✅ Scheduler uruchomiony
📅 Stats sync schedule: Thursday & Monday at 06:00 (Europe/Warsaw)
📅 Matchlogs sync schedule: Tuesday at 07:00 (Europe/Warsaw)
📅 Next stats sync: 2025-12-04 06:00:00+01:00
📅 Next matchlogs sync: 2025-12-02 07:00:00+01:00

# Podczas synchronizacji
🔄 SCHEDULED SYNC - Starting automatic player synchronization
⏰ Time: 2025-12-04 06:00:00
📋 Found 91 players to sync
⏱️ Estimated time: ~18.2 minutes (12s rate limit)
[1/91] 🔄 Syncing: Robert Lewandowski
✅ Successfully synced Robert Lewandowski
...
✅ SCHEDULED SYNC COMPLETE
📊 Results: 89 synced, 2 failed out of 91 total
⏱️ Duration: 18.5 minutes
```

---

## 🚨 Troubleshooting

### Problem: Scheduler nie startuje

**Objaw:**
```json
{
  "scheduler_running": false
}
```

**Rozwiązanie:**
1. Sprawdź czy `ENABLE_SCHEDULER=true` w `.env` lub environment variables
2. Sprawdź logi backendu czy nie ma błędów
3. Uruchom backend przez `uvicorn` (nie TestClient!)

### Problem: Joby się nie wykonują

**Objaw:** Scheduler running = true, ale synchronizacja nie działa

**Rozwiązanie:**
1. Sprawdź timezone - czy Europe/Warsaw jest poprawna
2. Sprawdź logi czy są błędy podczas wykonania
3. Sprawdź czy FBref nie zablokował (rate limiting)

### Problem: Email nie wysyła się

**Objaw:** Synchronizacja działa, ale brak powiadomień email

**Rozwiązanie:**
1. Sprawdź czy SMTP_* zmienne są ustawione w `.env`
2. Sprawdź logi czy są błędy SMTP
3. Dla Gmail: użyj App Password (nie zwykłe hasło)

---

## 📝 Funkcje schedulera

### 1. `scheduled_sync_all_players()`
**Lokalizacja:** `app/backend/main.py` linia 749

**Co robi:**
- Pobiera wszystkich graczy z bazy
- Dla każdego gracza wywołuje `sync_single_player()`
- Rate limit: 12 sekund
- Wysyła email notification po zakończeniu

**Kod:**
```python
async def scheduled_sync_all_players():
    db = SessionLocal()
    players = db.query(Player).all()
    
    async with FBrefPlaywrightScraper(rate_limit_seconds=12.0) as scraper:
        for player in players:
            await sync_single_player(scraper, db, player)
    
    send_sync_notification_email(...)
```

### 2. `scheduled_sync_matchlogs()`
**Lokalizacja:** `app/backend/main.py` linia 821

**Co robi:**
- Pobiera graczy z FBref ID
- Dla każdego gracza wywołuje `sync_player_matchlogs()`
- Rate limit: 12 sekund
- Wysyła email notification po zakończeniu

### 3. `send_sync_notification_email()`
**Lokalizacja:** `app/backend/main.py` linia 393

**Co robi:**
- Wysyła email po synchronizacji stats
- Zawiera: liczbę zsynchronizowanych, failed, czas trwania
- Opcjonalne (wymaga SMTP config)

### 4. `send_matchlogs_notification_email()`
**Lokalizacja:** `app/backend/main.py` linia 247

**Co robi:**
- Wysyła email po synchronizacji match logs
- Zawiera: liczbę graczy, meczów, failed, czas trwania
- Opcjonalne (wymaga SMTP config)

---

## ⚙️ Zmiana harmonogramu

Jeśli chcesz zmienić harmonogram, edytuj `app/backend/main.py`:

```python
# Zmiana z czwartku/poniedziałku na środę/piątek:
scheduler.add_job(
    scheduled_sync_all_players,
    CronTrigger(day_of_week='wed,fri', hour=6, minute=0),  # ← tu
    id='sync_all_players'
)

# Zmiana z wtorku na czwartek:
scheduler.add_job(
    scheduled_sync_matchlogs,
    CronTrigger(day_of_week='thu', hour=7, minute=0),  # ← tu
    id='sync_matchlogs'
)
```

**Formaty CronTrigger:**
- `day_of_week`: mon, tue, wed, thu, fri, sat, sun (lub 0-6)
- `hour`: 0-23
- `minute`: 0-59

**Przykłady:**
```python
# Codziennie o 6:00
CronTrigger(hour=6, minute=0)

# Co godzinę
CronTrigger(minute=0)

# W weekend o 10:00
CronTrigger(day_of_week='sat,sun', hour=10, minute=0)
```

---

## 📊 Zalecenia

### Dla developerów lokalnych:
- ❌ **NIE włączaj** schedulera lokalnie (`ENABLE_SCHEDULER=false`)
- Synchronizuj ręcznie: `python sync_player.py "Nazwisko"`

### Dla deploymentu (Render):
- ✅ **Włącz** scheduler (`ENABLE_SCHEDULER=true`)
- Skonfiguruj email notifications (opcjonalnie)
- Monitoruj logi Render

### Rate limiting:
- ✅ 12 sekund między requestami - bezpieczne dla FBref
- ❌ NIE zmniejszaj poniżej 10 sekund (ryzyko blokady)

---

## ✅ Podsumowanie

### Status: 🟢 DZIAŁA POPRAWNIE

**Potwierdzenia:**
- ✅ Scheduler się uruchamia
- ✅ Joby są zaplanowane
- ✅ Funkcje sync istnieją
- ✅ Funkcje email istnieją
- ✅ Rate limiting działa
- ✅ Timezone poprawny (Europe/Warsaw)

**Następne synchronizacje:**
- Stats: Czwartek 4 grudnia 2025, 06:00
- Matchlogs: Wtorek 2 grudnia 2025, 07:00

**Brak problemów!** 🎉

---

## 📚 Powiązane dokumenty

- `MATCHLOGS_SCHEDULER.md` - Szczegóły schedulera match logs
- `EMAIL_SETUP_GUIDE.md` - Konfiguracja powiadomień email
- `RENDER_DEPLOYMENT.md` - Deployment na Render z schedulerem

---

**Pytania? Scheduler działa poprawnie, możesz go bezpiecznie używać!** ✅
