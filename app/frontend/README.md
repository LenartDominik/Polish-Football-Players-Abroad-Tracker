# Polish Football Players Abroad - Frontend

****Status:** ✅ Production Ready

## ⚖️ Legal Notice

**This application is for EDUCATIONAL and NON-COMMERCIAL use only.**

- **Data Source:** RapidAPI Football API (free-api-live-football-data)
- **Usage:** Portfolio, CV, education
- **NOT for commercial use** without proper licensing
- **See:** [LEGAL_NOTICE.md](../../docs/LEGAL_NOTICE.md) in root directory

---

**Multi-page** interaktywny dashboard w Streamlit do przeglądania i analizy danych polskich piłkarzy grających za granicą.

## 📁 Struktura Frontend

### Dla lokalnego uruchomienia:
```
app/frontend/
├── streamlit_app.py          # Główna aplikacja (local)
├── api_client.py              # API client
├── requirements.txt
└── pages/
    └── 2_⚖️_compare_players.py  # Strona porównywania
```

### Dla Streamlit Cloud:
```
root/
├── streamlit_app_cloud.py     # Główna aplikacja (cloud)
├── api_client.py              # API client (obsługa st.secrets)
├── requirements.txt
└── pages/
    └── 2_Compare_Players.py   # Strona porównywania
```

**Kluczowa różnica:** Streamlit Cloud wymaga plików w root repozytorium Git.

## 🔌 API Client - Różnice między Local vs Cloud

### 📁 Dwie wersje aplikacji Streamlit:

#### 1️⃣ **Local Development** (`app/frontend/streamlit_app.py`)
- Używany podczas lokalnego developmentu
- Uruchamiany przez: `.\start_frontend.ps1` lub `streamlit run app/frontend/streamlit_app.py`
- API URL z `.env`: `API_BASE_URL=http://localhost:8000`

#### 2️⃣ **Streamlit Cloud** (`streamlit_app_cloud.py` w root)
- Używany na Streamlit Cloud deployment
- Pliki muszą być w root repozytorium (wymaganie Streamlit Cloud)
- API URL z Streamlit Secrets: `BACKEND_API_URL = "https://your-backend.onrender.com"`

### Automatyczne wykrywanie środowiska (api_client.py):

```python
# api_client.py obsługuje 3 scenariusze:

# 1. Streamlit Cloud (priorytet #1)
st.secrets["BACKEND_API_URL"]  # z Streamlit Cloud Secrets

# 2. Lokalne środowisko (priorytet #2)
os.getenv("API_BASE_URL")  # z pliku .env

# 3. Domyślny fallback (priorytet #3)
"http://localhost:8000"  # jeśli nic nie jest skonfigurowane
```

### Konfiguracja:

**Lokalnie:**
```powershell
# Dodaj do .env (opcjonalne - domyślnie localhost:8000):
API_BASE_URL=http://localhost:8000
```

**Streamlit Cloud:**
```toml
# Settings → Secrets (WYMAGANE!):
BACKEND_API_URL = "https://your-backend.onrender.com"
```

📖 **Szczegóły deployment:** [STREAMLIT_CLOUD_DEPLOYMENT.pl.md](../../docs/STREAMLIT_CLOUD_DEPLOYMENT.pl.md)

## 🚀 Szybki start

### Uruchom frontend

Z głównego katalogu projektu:
```powershell
.\start_frontend.ps1
```

Lub ręcznie:
```powershell
# Aktywuj środowisko wirtualne
.\.venv\Scripts\Activate.ps1

# Przejdź do katalogu frontend
cd app\frontend

# Uruchom Streamlit
streamlit run streamlit_app.py
```

Dashboard otworzy się automatycznie w przeglądarce pod adresem: **http://localhost:8501**

## ✨ Funkcje

### 📊 Strona główna (Home)

**Przeglądanie graczy:**
- 📋 Lista wszystkich polskich piłkarzy za granicą
- 🔍 Wyszukiwanie po nazwisku
- 🎯 Filtrowanie po:
  - Liga (La Liga, Premier League, Bundesliga, etc.)
  - Drużyna
  - Pozycja (FW, MF, DF, GK)
  - Typ rozgrywek (Liga, Puchary Europejskie, Reprezentacja)
  - Sezon

**Widoki:**
- 🃏 **Karty graczy** - rozwijane karty z podstawowymi danymi
- 📊 **Tabela** - kompletna tabela ze statystykami
- 📈 **Wykres top strzelców** - wizualizacja najlepszych strzelców

**Eksport danych:**
- 💾 Pobierz przefiltrowane dane jako CSV

**Statystyki ogólne:**
- 👥 Liczba graczy
- 🏆 Liczba lig
- ⚽ Liczba drużyn

### ⚖️ Porównanie graczy (Compare Players)

**Funkcje:**
- 🔄 Porównaj dwóch graczy side-by-side
- 📊 Wizualizacja statystyk (gole, asysty, minuty, kartki)
- 🎯 Filtrowanie po sezonie
- 📈 Wykresy radarowe i słupkowe
- 🏆 Zestawienie osiągnięć

**Dostępne statystyki:**
- **Ofensywne:** gole, asysty, xG, xA, strzały
- **Defensywne:** żółte kartki, czerwone kartki
- **Ogólne:** mecze, minuty, podstawowe składy

## 📁 Struktura katalogu frontend

```
app/frontend/
├── streamlit_app.py         # Główna strona (Home)
├── requirements.txt         # Zależności frontend
├── pages/
│   └── 2_⚖️_compare_players.py  # Strona porównania graczy
```

## 🔗 Połączenie z backendem

Frontend komunikuje się z backendem FastAPI przez API:

```python
# Domyślny adres backendu
BACKEND_API_URL = "http://127.0.0.1:8000"

# Używane endpointy:
# - GET /api/players - lista graczy
# - GET /api/comparison/compare - porównanie graczy
# - GET /api/comparison/players/{id}/stats - statystyki gracza
```

⚠️ **Ważne:** Backend musi być uruchomiony przed uruchomieniem frontendu!

## 🎨 Dostosowanie

### Zmiana portu Streamlit

```powershell
streamlit run streamlit_app.py --server.port 8502
```

### Zmiana adresu backendu

Edytuj `streamlit_app.py`:
```python
BACKEND_API_URL = "http://your-backend-url:8000"
```

## 🧪 Testowanie

### Sprawdź czy frontend działa:
1. Otwórz http://localhost:8501
2. Powinieneś zobaczyć listę graczy
3. Sprawdź filtry i wyszukiwanie
4. Przejdź do "Compare Players" w menu bocznym

### Jeśli widzisz błąd połączenia:
```
❌ Error: Connection refused
```
- Sprawdź czy backend jest uruchomiony na porcie 8000
- Uruchom: `.\start_backend.ps1`

## 📊 Wymagania

Frontend wymaga następujących bibliotek (zawarte w `requirements.txt`):

```
streamlit>=1.51.0
pandas>=2.3.0
plotly>=5.18.0
requests>=2.32.0
```

Instalacja:
```powershell
pip install -r requirements.txt
```

## 🐛 Rozwiązywanie problemów

### Port 8501 zajęty
```powershell
# Uruchom na innym porcie
streamlit run streamlit_app.py --server.port 8502
```

### Brak danych graczy
- Upewnij się, że backend jest uruchomiony
- Sprawdź połączenie z bazą danych (PostgreSQL/Supabase)
- Zsynchronizuj graczy: `python sync_player_full.py "Nazwisko Gracza" --all-seasons`
- Lub użyj schedulera na Render (automatyczna synchronizacja Pon/Czw/Wt)

### Błąd importu modułów
```powershell
# Zainstaluj wszystkie zależności
pip install -r requirements.txt
```

## 📚 Technologie

- **Streamlit 1.51+** - framework do budowy dashboardów
- **Pandas 2.3+** - analiza i manipulacja danymi
- **Plotly 5.18+** - interaktywne wykresy
- **Requests 2.32+** - komunikacja z API

## 🔗 Powiązane komponenty

- **Backend API:** `app/backend/` (FastAPI)
- **Baza danych:** PostgreSQL (Supabase) - produkcyjna baza danych
- **Dokumentacja projektu:** `README.md` (katalog główny)
- **Deployment guide:** `STREAMLIT_CLOUD_DEPLOYMENT.pl.md`


### National Team (2025) - Rok Kalendarzowy
```python
# Funkcja: get_national_team_stats_by_year()
# Źródło: tabela player_matches
# Filtrowanie: match_date.startswith('2025')
# WAŻNE: Wykluczono Nations League 2024-2025 (mecze w 2024)
```


