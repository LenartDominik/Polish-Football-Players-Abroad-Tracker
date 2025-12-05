# ☁️ Streamlit Cloud Deployment - Przewodnik Krok Po Kroku

## 🎯 Przegląd

Ten przewodnik pokazuje jak wdrożyć **Polish Football Data Hub International** na Streamlit Cloud (frontend) + Render.com (backend).

**Rezultat:**
- 🌐 Publiczny URL: `https://yourapp.streamlit.app`
- 💰 Koszt: **$0/miesiąc**
- ⏱️ Czas: **15 minut**
- 🔄 Auto-deploy: Przy każdym push do GitHub

---

## 📋 Wymagania Wstępne

### 1. Konto GitHub
- Kod musi być na GitHubie (public lub private repo)

### 2. Konta (darmowe):
- ✅ [Streamlit Cloud](https://streamlit.io/cloud) - frontend
- ✅ [Render.com](https://render.com) - backend + baza

### 3. Pliki w Projekcie (już masz!):
- ✅ `streamlit_app_cloud.py` - główna aplikacja frontend
- ✅ `requirements-streamlit.txt` - zależności
- ✅ `.streamlit/config.toml` - konfiguracja
- ✅ `render.yaml` - konfiguracja backend

---

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                     UŻYTKOWNIK                              │
│                  (Przeglądarka WWW)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              STREAMLIT CLOUD (Frontend)                     │
│          https://yourapp.streamlit.app                      │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  streamlit_app_cloud.py                               │ │
│  │  - Dashboard UI                                       │ │
│  │  - Wykresy (Plotly)                                   │ │
│  │  - Porównania graczy                                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  requirements-streamlit.txt:                                │
│  - streamlit, pandas, plotly, requests                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ REST API (HTTPS)
                       │ /api/players
                       │ /api/stats
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              RENDER.COM (Backend)                           │
│          https://yourapp.onrender.com                       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  FastAPI Backend (app/backend/main.py)                │ │
│  │  - REST API Endpoints                                 │ │
│  │  - Logika biznesowa                                   │ │
│  │  - Scheduler (scraping co 6h)                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  PostgreSQL Database (Supabase)                        │ │
│  │  - Persistent Disk (nie ginie przy redeploy)          │ │
│  │  - Tabele: players, competition_stats, player_matches │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Playwright Scraper (sync_player.py)              │ │
│  │  - Scraping FBref.com co 6h                           │ │
│  │  - Aktualizacja statystyk                             │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS (Scraping)
                       ▼
              ┌─────────────────┐
              │   FBref.com     │
              │  (Źródło danych)│
              └─────────────────┘
```

---

## 🚀 CZĘŚĆ 1: Deploy Backend na Render

### Krok 1.1: Przygotuj Kod

**Upewnij się że masz:**
```bash
polish-players-tracker/
├── render.yaml                 # ✅ Konfiguracja Render
├── Dockerfile                  # ✅ Container backend
├── requirements.txt            # ✅ Zależności backend
├── app/backend/main.py         # ✅ FastAPI app
└── .env.example               # ✅ Przykład zmiennych
```

**Push na GitHub:**
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

---

### Krok 1.2: Utwórz Web Service na Render

1. **Zaloguj się:** https://render.com
2. **New** → **Web Service**
3. **Connect Repository:** 
   - Wybierz GitHub
   - Autoryzuj Render
   - Wybierz repo `polish-players-tracker`

4. **Render automatycznie wykryje `render.yaml`!**
   - Jeśli nie, wybierz: **Use render.yaml**

5. **Kliknij "Create Web Service"**

---

### Krok 1.3: Konfiguracja (automatyczna z render.yaml)

Render użyje konfiguracji z `render.yaml`:
```yaml
name: polish-players-tracker
type: web
env: docker
dockerfilePath: ./Dockerfile
region: frankfurt
plan: free
healthCheckPath: /health
disk:
  name: data
  mountPath: /data
  sizeGB: 1
envVars:
  - key: DATABASE_URL
    value: postgresql://postgres.xxxxx:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**Nic nie musisz zmieniać!** ✅

---

### Krok 1.4: Poczekaj na Build (5-10 min)

Render:
1. Klonuje repo
2. Builduje Docker image
3. Uruchamia kontener
4. Scheduler startuje automatycznie

**Status:** Zielony ✅ → Backend działa!

---

### Krok 1.5: Zapisz Backend URL

Po deployu, Render pokaże URL:
```
https://polish-players-tracker-xxxx.onrender.com
```

**Zapisz go!** Będzie potrzebny dla frontendu.

---

## 🎨 CZĘŚĆ 2: Deploy Frontend na Streamlit Cloud

### Krok 2.1: Sprawdź Pliki

**Upewnij się że masz:**
```bash
polish-players-tracker/
├── streamlit_app_cloud.py              # ✅ Główna aplikacja
├── requirements-streamlit.txt          # ✅ Zależności
├── .streamlit/
│   └── config.toml                     # ✅ Konfiguracja
└── .streamlit/secrets.toml.example     # ✅ Przykład secrets
```

**Push na GitHub** (jeśli były zmiany):
```bash
git add .
git commit -m "Add Streamlit Cloud files"
git push origin main
```

---

### Krok 2.2: Utwórz App na Streamlit Cloud

1. **Zaloguj się:** https://streamlit.io/cloud
   - Użyj konta GitHub

2. **New app**

3. **Konfiguracja:**
   ```
   Repository:    twoje-username/polish-players-tracker
   Branch:        main
   Main file:     streamlit_app_cloud.py
   ```

4. **Advanced settings** → **Python version:** 3.11

---

### Krok 2.3: Dodaj Secrets (WAŻNE!)

**⚠️ To jest NAJWAŻNIEJSZY krok - bez tego aplikacja NIE BĘDZIE DZIAŁAĆ!**

**W Streamlit Cloud:**
1. **App settings** (⚙️)
2. **Secrets**
3. Dodaj:

```toml
# Backend API URL - WYMAGANE!
BACKEND_API_URL = "https://polish-players-backend.onrender.com"
```

**📖 Szczegółowy przewodnik:** [STREAMLIT_SECRETS_SETUP.md](STREAMLIT_SECRETS_SETUP.md)

**Zamień URL na swój Render backend URL:**
- Znajdź go w Render Dashboard (górna część strony)
- **NIE** dodawaj `/` na końcu URL
- Zapisz secrets i poczekaj ~30s na restart aplikacji

---

### Krok 2.4: Deploy! (2-3 min)

1. **Kliknij "Deploy"**
2. Streamlit:
   - Klonuje repo
   - Instaluje zależności z `requirements-streamlit.txt`
   - Uruchamia `streamlit_app_cloud.py`

**Status:** 🟢 Running → Frontend działa!

---

### Krok 2.5: Gotowe! 🎉

Twoja aplikacja jest dostępna pod:
```
https://yourapp.streamlit.app
```

**Możesz:**
- ✅ Udostępniać link
- ✅ Dodać do CV/Portfolio
- ✅ Pokazać na LinkedIn

---

## 🔧 Konfiguracja i Zmienne

### Backend (Render) - Environment Variables

```bash
# W render.yaml (już skonfigurowane)
DATABASE_URL=postgresql://postgres.xxxxx:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
PORT=8000
PYTHON_VERSION=3.11.0
```

**Dodatkowe (opcjonalne):**
```bash
# Dashboard Render → Environment → Add
LOG_LEVEL=INFO
SCRAPER_INTERVAL=21600  # 6 godzin
```

---

### Frontend (Streamlit Cloud) - Secrets

```toml
# App Settings → Secrets
BACKEND_API_URL = "https://your-backend.onrender.com"

# Opcjonalne:
DEBUG = false
CACHE_TTL = 3600
```

---

## 🧪 Testowanie

### Test 1: Backend Health Check
```bash
curl https://your-backend.onrender.com/health
```

**Oczekiwane:**
```json
{"status": "healthy", "database": "connected"}
```

---

### Test 2: Backend API
```bash
curl https://your-backend.onrender.com/api/players?limit=5
```

**Oczekiwane:** Lista 5 graczy (JSON)

---

### Test 3: Frontend
1. Otwórz `https://yourapp.streamlit.app`
2. Wyszukaj gracza (np. "Lewandowski")
3. Sprawdź statystyki

**Oczekiwane:** Dashboard z danymi ✅

---

## 🔄 Automatyczne Deploymenty

### GitHub → Streamlit Cloud (Auto)
```bash
git add .
git commit -m "Update frontend"
git push origin main
```
→ Streamlit Cloud automatycznie redeploy (1-2 min)

### GitHub → Render (Auto)
```bash
git add .
git commit -m "Update backend"
git push origin main
```
→ Render automatycznie rebuild (5-10 min)

**Nic nie musisz robić ręcznie!** ✅

---

## 📊 Monitoring

### Streamlit Cloud Dashboard
- **Analytics:** Liczba użytkowników, requesty
- **Logs:** Błędy aplikacji
- **Metrics:** Czas ładowania, uptime

### Render Dashboard
- **Logs:** Backend logi (FastAPI, scraper)
- **Metrics:** CPU, RAM, Disk usage
- **Events:** Deploys, crashes

---

## 🐛 Troubleshooting

### Problem 1: Frontend nie widzi danych

**Objaw:** "Error connecting to backend"

**Rozwiązanie:**
1. Sprawdź `BACKEND_API_URL` w secrets
2. Sprawdź czy backend działa: `curl https://your-backend.onrender.com/health`
3. Sprawdź CORS w `app/backend/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # W produkcji zmień na konkretny URL
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

### Problem 2: Backend timeout

**Objaw:** Backend odpowiada długo (>30s)

**Przyczyna:** Render free tier "zasypia" po 15 min bezczynności

**Rozwiązanie:**
1. Pierwszy request po okresie bezczynności może trwać 30-60s (cold start)
2. Dodaj ping co 10 min (opcjonalnie):
   ```python
   # W scheduler
   @scheduler.scheduled_job('interval', minutes=10)
   def keep_alive():
       requests.get("https://your-backend.onrender.com/health")
   ```

---

### Problem 3: Baza danych pusta

**Objaw:** "No players found"

**Rozwiązanie:**
1. SSH do Render (Render Dashboard → Shell)
2. Uruchom sync:
   ```bash
   python sync_player.py
   ```
3. Lub poczekaj na automatyczny scraping (co 6h)

---

## 🔒 Bezpieczeństwo

### Secrets w Streamlit Cloud
✅ **Dobre praktyki:**
- Nigdy nie commituj `.streamlit/secrets.toml` do GitHub
- Używaj secrets w Streamlit Cloud dashboard
- Rotuj klucze API regularnie (jeśli dodasz autentykację)

### API Keys (opcjonalnie)
Jeśli chcesz zabezpieczyć API:
```python
# Backend: app/backend/main.py
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

@app.get("/api/players")
async def get_players(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    # ...
```

```toml
# Frontend: secrets.toml
API_KEY = "your-secret-key"
```

---

## 💰 Limity Free Tier

### Streamlit Cloud (Free)
- ✅ 1 private app
- ✅ Unlimited public apps
- ✅ Unlimited users/traffic
- ✅ 1 GB RAM
- ⚠️ Śpi po 7 dniach bezczynności

### Render (Free)
- ✅ 750 godzin/miesiąc (wystarczy na 24/7)
- ✅ 512 MB RAM
- ✅ 1 GB persistent disk
- ⚠️ Śpi po 15 min bezczynności (cold start 30-60s)

**Dla edukacji/portfolio:** Wystarczy! ✅

---

## 📚 Przydatne Linki

### Dokumentacja:
- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Render Docs](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

### Monitoring:
- Streamlit Cloud: https://share.streamlit.io/
- Render: https://dashboard.render.com/

### Projekt:
- `RENDER_DEPLOYMENT.md` - szczegóły backend
- `COMMERCIAL_DEPLOYMENT.md` - opcje produkcyjne

---

## ✅ Checklist Deploymentu

### Przed Deploymentem:
- [ ] Kod na GitHubie (main branch)
- [ ] `render.yaml` skonfigurowany
- [ ] `streamlit_app_cloud.py` działa lokalnie
- [ ] `requirements-streamlit.txt` kompletny
- [ ] `.env.example` z opisem zmiennych

### Backend (Render):
- [ ] Utworzono Web Service
- [ ] Build zakończony sukcesem ✅
- [ ] Health check przechodzi (`/health`)
- [ ] Persistent disk zamontowany
- [ ] Zapisano Backend URL

### Frontend (Streamlit Cloud):
- [ ] Utworzono App
- [ ] Dodano `BACKEND_API_URL` w secrets
- [ ] Deploy zakończony sukcesem ✅
- [ ] Aplikacja ładuje dane
- [ ] Zapisano Frontend URL

### Post-Deployment:
- [ ] Przetestowano wyszukiwanie gracza
- [ ] Przetestowano Details
- [ ] Przetestowano Season Statistics History
- [ ] Sprawdzono logi (brak błędów)
- [ ] Udostępniono link (CV, portfolio)

---

## 🎉 Gotowe!

Twoja aplikacja jest teraz dostępna publicznie:
- **Frontend:** `https://yourapp.streamlit.app`
- **Backend:** `https://yourapp.onrender.com`

**Koszty:** $0/miesiąc  
**Uptime:** 24/7 (z cold start na Render)  
**Auto-deploy:** ✅ Przy push do GitHub

---

**Masz pytania?** Zobacz:
- `RENDER_DEPLOYMENT.md` - więcej o backend
- `COMMERCIAL_DEPLOYMENT.md` - opcje płatne/produkcyjne
- `FAQ_MATCHLOGS.md` - FAQ o danych

**Data:** 25.11.2025  
**Wersja:** v0.7.3  
**Status:** ✅ Production Ready
