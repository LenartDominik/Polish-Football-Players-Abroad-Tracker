# Polish Players Tracker - Frontend

**Wersja:** v0.7.4 | **Status:** ✅ Production Ready

## ⚖️ Legal Notice

**This application is for EDUCATIONAL and NON-COMMERCIAL use only.**

- **Data Source:** FBref.com (© Sports Reference LLC)
- **Usage:** Portfolio, CV, education
- **NOT for commercial use** without proper licensing
- **See:** [LEGAL_NOTICE.md](../../LEGAL_NOTICE.md) in root directory

---

Interaktywny dashboard w Streamlit do przeglądania i analizy danych polskich piłkarzy grających za granicą.

## 📊 Najnowsze Zmiany (v0.7.4)

### ✅ Poprawki:
1. **Season Total** - Teraz uwzględnia mecze reprezentacji z roku kalendarzowego (2025)
2. **European Cups Details** - Pokazuje wszystkie europejskie puchary osobno (dla graczy z wieloma pucharami)
3. **Compare Players** - Ograniczone tylko do aktualnego sezonu 2025-26

### ⚠️ Znane Ograniczenia:
- **Kwalifikacje Champions League:** FBref agreguje kwalifikacje CL z Europa League jako "Europa Lg" (standard branżowy)
- Zobacz: `../../LIMITATION_CHAMPIONS_LEAGUE_QUALIFICATIONS.md`

## 🚀 Szybki start

### Uruchom frontend

Z głównego katalogu projektu:
```powershell
.\start_frontend.ps1
```

Lub ręcznie:
```powershell
# Aktywuj środowisko wirtualne
.\venv\Scripts\Activate.ps1

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
- Sprawdź czy baza danych `players.db` zawiera dane
- Zsynchronizuj graczy: `python sync_all_playwright.py`

### Błąd importu modułów
```powershell
# Zainstaluj wszystkie zależności
pip install -r requirements.txt
```

### Season Total nie zawiera meczów reprezentacji

**Problem rozwiązany w v0.7.4:**
- Dodano funkcję `get_season_filters()` która automatycznie uwzględnia rok kalendarzowy (2025) dla reprezentacji
- Season Total teraz sumuje: Liga + Puchary + Reprezentacja

### European Cups - brakuje niektórych rozgrywek

**Uwaga:**
- FBref agreguje kwalifikacje Champions League z Europa League jako "Europa Lg"
- To jest **standard branżowy**, nie błąd aplikacji
- Zobacz: `LIMITATION_CHAMPIONS_LEAGUE_QUALIFICATIONS.md`

### Dashboard się nie odświeża
- Naciśnij `R` w przeglądarce aby wymusić odświeżenie
- Lub użyj przycisku "Rerun" w prawym górnym rogu

## 📚 Technologie

- **Streamlit 1.51+** - framework do budowy dashboardów
- **Pandas 2.3+** - analiza i manipulacja danymi
- **Plotly 5.18+** - interaktywne wykresy
- **Requests 2.32+** - komunikacja z API

## 🆕 Co Nowego w v0.7.3

### Enhanced Stats dla zawodników z pola:
- ✅ **xGI** (Expected Goal Involvement = xG + xA)
- ✅ **Metryki per 90** (G+A/90, xG/90, xA/90, npxG/90, xGI/90)
- ✅ **Uproszczony Season Total** (tylko kluczowe statystyki)
- ✅ Warunkowe wyświetlanie xG stats (tylko gdy > 0)

### Reprezentacja Narodowa (2025):
- ✅ **Statystyki według roku kalendarzowego** - używa tabeli player_matches
- ✅ **Wykluczono Nations League 2024-2025** - wszystkie mecze były w 2024
- ✅ **Poprawne liczenie meczów** - tylko mecze z 2025 roku
- ✅ Usunięto Shots/SoT z Season Statistics History

### Porównywanie zawodników:
- ✅ **Pełne wsparcie dla bramkarzy** - GK vs GK z dedykowanymi statystykami
- ✅ **Walidacja typu gracza** - blokada GK vs field player
- ✅ **Dynamiczne kategorie statystyk** - dostosowane do typu gracza
- ✅ **Wizualne wskazanie typu** - 🧤 "Comparing goalkeepers" vs ⚽ "Comparing field players"

**Zobacz więcej:** [FINAL_COMPLETE_SUMMARY_v0.7.3.md](../../FINAL_COMPLETE_SUMMARY_v0.7.3.md)

## 🔗 Powiązane komponenty

- **Backend API:** `app/backend/` (FastAPI)
- **Baza danych:** `players.db` (katalog główny)
- **Dokumentacja projektu:** `README.md` (katalog główny)

## 📖 Dokumentacja szczegółowa

- [VISUAL_COMPARISON_GUIDE.md](../../VISUAL_COMPARISON_GUIDE.md) - Przewodnik wizualny porównań
- [QUICK_START_COMPARISON.md](../../QUICK_START_COMPARISON.md) - Szybki start z porównaniami
- [FRONTEND_TESTING_CHECKLIST.md](../../FRONTEND_TESTING_CHECKLIST.md) - Checklist testowania
- [STREAMLIT_CLOUD_DEPLOYMENT.md](../../STREAMLIT_CLOUD_DEPLOYMENT.md) - Deployment na Streamlit Cloud

## 🎯 Kluczowe Zmiany Techniczne

### National Team (2025) - Rok Kalendarzowy
```python
# Funkcja: get_national_team_stats_by_year()
# Źródło: tabela player_matches
# Filtrowanie: match_date.startswith('2025')
# WAŻNE: Wykluczono Nations League 2024-2025 (mecze w 2024)
```

### Enhanced Stats - Obliczanie Metryk
```python
# xGI = xG + xA
def calculate_xgi(xg, xa):
    return (xg or 0.0) + (xa or 0.0)

# Metryki per 90
def calculate_per_90(value, minutes):
    return (value / minutes) * 90 if minutes > 0 else 0.0
```

### Porównywanie - Walidacja Typu
```python
# Automatyczna detekcja typu gracza
player1_is_gk = player1_data['is_goalkeeper']
player2_is_gk = player2_data['is_goalkeeper']

# Blokada nieprawidłowych porównań
if player1_is_gk != player2_is_gk:
    st.error("⚠️ You cannot compare goalkeepers with field players!")
```

