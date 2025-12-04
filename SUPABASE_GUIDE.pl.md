# 🚀 Przewodnik: Praca z Supabase

## ✅ Co zostało zmienione?

### Domyślna baza danych to teraz **Supabase PostgreSQL**!

- ✅ `DATABASE_URL` wskazuje na Supabase
- ✅ Backend automatycznie używa Supabase
- ✅ Frontend automatycznie używa Supabase
- ✅ Wszystkie komendy synchronizacji używają Supabase

---

## 📊 Jak synchronizować graczy?

### **Te same komendy co zawsze!**

#### **1. Synchronizacja wszystkich graczy:**
```powershell
python sync_player.py
```

#### **2. Synchronizacja konkretnych graczy:**
```powershell
python sync_player_full.py "Robert Lewandowski" --all-seasons
python sync_player_full.py "Lewandowski" --all-seasons "Zieliński"
```

#### **3. Synchronizacja z wszystkimi sezonami:**
```powershell
python sync_player_full.py --all-seasons --all-seasons
```

#### **4. Synchronizacja widoczna (bez headless):**
```powershell
python sync_player_full.py --visible --all-seasons
```

### **Nowe opcje:**

```powershell
# Synchronizacja konkretnego sezonu
python sync_playwright.py --season=2024-2025

# Synchronizacja z ID (bez wyszukiwania)
python sync_player_full.py --use-id --all-seasons
```

---

## 🌐 Gdzie zobaczyć dane?

### **Frontend Streamlit (localhost:8501)**

#### **Uruchomienie:**
```powershell
streamlit run app/frontend/streamlit_app.py
```

lub

```powershell
.\start_frontend.ps1
```

#### **Co zobaczysz:**
- ✅ Wszystkie dane z **Supabase**
- ✅ 3 graczy (Lewandowski, Cash, Fabiański)
- ✅ Statystyki z podziałem na rozgrywki
- ✅ Porównania graczy

### **Backend API (localhost:8000)**

#### **Uruchomienie:**
```powershell
uvicorn app.backend.main:app --reload
```

lub

```powershell
.\start_backend.ps1
```

#### **Endpointy API:**
- 📍 `http://localhost:8000/` - Welcome
- 📍 `http://localhost:8000/docs` - Swagger UI
- 📍 `http://localhost:8000/api/players` - Lista graczy
- 📍 `http://localhost:8000/api/players/{id}` - Szczegóły gracza
- 📍 `http://localhost:8000/health` - Status API

### **Supabase Dashboard**

Możesz również zobaczyć dane bezpośrednio w Supabase:

1. Wejdź na: https://supabase.com/dashboard
2. Wybierz projekt
3. Kliknij **Table Editor** (ikona tabeli)
4. Wybierz tabelę:
   - `players` - Lista graczy
   - `competition_stats` - Statystyki z podziałem na rozgrywki
   - `goalkeeper_stats` - Statystyki bramkarzy

---

## 📝 Ważne informacje

### **PostgreSQL to jedyna wspierana baza danych**
- ✅ Stabilna, skalowalna, produkcyjna
- ✅ Automatyczne backupy w Supabase
- ✅ Dashboard do zarządzania danymi
- ✅ DARMOWE 500MB dla projektów hobby!

### **Zalecenia:**

1. **Zsynchronizuj więcej graczy do Supabase:**
   ```powershell
   python sync_player.py
   ```

2. **Lub zsynchronizuj konkretnych graczy:**
   ```powershell
   python sync_player_full.py "Zieliński" --all-seasons "Szczęsny"
   ```

3. **Sprawdź dane w frontend:**
   ```powershell
   streamlit run app/frontend/streamlit_app.py
   ```
   Otwórz: http://localhost:8501

---

## 🆘 Rozwiązywanie problemów

### **Problem: "No players found"**
**Rozwiązanie:** Zsynchronizuj graczy:
```powershell
python sync_playwright.py
```

### **Problem: "Connection error"**
**Rozwiązanie:** Sprawdź czy Supabase jest aktywny:
- Wejdź na https://supabase.com/dashboard
- Sprawdź status projektu

### **Problem: "Password authentication failed"**
**Rozwiązanie:** Zresetuj hasło w Supabase i zaktualizuj `.env`

### **Problem: "Duplicate SASL authentication"**
**Rozwiązanie:** Poczekaj chwilę i spróbuj ponownie (cold start)

---

## 📊 Struktura bazy danych

### **Tabela: players**
- `id` - ID gracza
- `name` - Imię i nazwisko
- `team` - Klub
- `league` - Liga
- `position` - Pozycja
- `nationality` - Narodowość

### **Tabela: competition_stats**
- `player_id` - ID gracza (FK)
- `season` - Sezon (np. "2024-2025")
- `competition_type` - Typ rozgrywek: **VARCHAR**
  - `"LEAGUE"` - Liga krajowa
  - `"DOMESTIC_CUP"` - Puchar krajowy
  - `"EUROPEAN_CUP"` - Puchar europejski
  - `"NATIONAL_TEAM"` - Reprezentacja
- `competition_name` - Nazwa rozgrywek
- `games`, `goals`, `assists`, `xg`, `npxg`, `xa` - Statystyki

### **Tabela: goalkeeper_stats**
- `player_id` - ID gracza (FK)
- `season` - Sezon
- `competition_type` - Typ rozgrywek: **VARCHAR**
- `saves`, `clean_sheets`, `goals_against` - Statystyki bramkarskie

---

## 🎯 Najczęściej używane komendy

```powershell
# Synchronizacja wszystkich graczy
python sync_playwright.py

# Uruchomienie frontend
streamlit run app/frontend/streamlit_app.py

# Uruchomienie backend
uvicorn app.backend.main:app --reload

# Sprawdzenie stanu bazy
python -c "from app.backend.database import SessionLocal; from app.backend.models.player import Player; db = SessionLocal(); print(f'Graczy: {db.query(Player).count()}'); db.close()"
```

---

## 💡 Tips & Tricks

### **Szybka synchronizacja 5 graczy (test):**
```powershell
python sync_player_full.py "Lewandowski" --all-seasons "Zieliński" "Szczęsny" "Fabiański" "Cash"
```

### **Synchronizacja tylko aktualnego sezonu:**
```powershell
python sync_player_full.py --season=2024-2025 --all-seasons
```

### **Sprawdzenie co jest w bazie:**
```powershell
python -c "from sqlalchemy import create_engine, text; import os; from dotenv import load_dotenv; load_dotenv(); engine = create_engine(os.getenv('DATABASE_URL')); conn = engine.connect(); players = conn.execute(text('SELECT COUNT(*) FROM players')).scalar(); stats = conn.execute(text('SELECT COUNT(*) FROM competition_stats')).scalar(); print(f'Gracze: {players}, Statystyki: {stats}'); conn.close()"
```

---

**🎉 Gotowe! Twoja aplikacja działa teraz z Supabase PostgreSQL!**
