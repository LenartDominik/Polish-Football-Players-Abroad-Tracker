# ⚡ Szybka naprawa Streamlit Cloud - 2 minuty

## 🎯 Problem
```
❌ Cannot connect to API at http://localhost:8000
```

## ✅ Rozwiązanie (2 minuty)

### Krok 1: Znajdź URL backendu
1. Zaloguj się do https://dashboard.render.com/
2. Kliknij na swój backend (np. `polish-players-backend`)
3. Skopiuj URL z górnej części strony (np. `https://polish-players-backend.onrender.com`)

**⚠️ URL NIE MOŻE kończyć się slash'em (`/`)**

✅ Dobrze: `https://polish-players-backend.onrender.com`  
❌ Źle: `https://polish-players-backend.onrender.com/`

---

### Krok 2: Dodaj Secret w Streamlit Cloud
1. Przejdź do https://share.streamlit.io/
2. Kliknij swoją aplikację
3. Kliknij **Settings** ⚙️ (w prawym górnym rogu)
4. Kliknij **Secrets**
5. Wklej poniższy kod (zamień URL na swój):

```toml
BACKEND_API_URL = "https://polish-players-backend.onrender.com"
```

6. Kliknij **Save**

---

### Krok 3: Poczekaj ~30 sekund
Streamlit automatycznie zrestartuje aplikację.

---

### Krok 4: Sprawdź czy działa
1. Odśwież swoją aplikację Streamlit
2. Powinieneś zobaczyć dane graczy! 🎉

---

## 🐛 Nadal nie działa?

### Problem: Backend śpi (Free Tier Render)
**Objaw:** Długie ładowanie (1-2 minuty)

**Rozwiązanie:**  
To normalne! Free tier Render usypia backend po 15 minutach nieaktywności.  
Pierwsze połączenie zajmuje 1-2 minuty. Odśwież stronę.

---

### Problem: "Connection timeout"
**Objaw:** `Request timeout after 30s`

**Sprawdź:**
1. Czy backend działa?
   - Otwórz: `https://twoj-backend.onrender.com/health`
   - Powinno zwrócić: `{"status": "healthy", "database": "connected"}`

2. Czy URL jest poprawny w secrets?
   - **Bez** slash'a na końcu
   - **Bez** ścieżki (np. `/api`)

---

### Problem: "No data available"
**Objaw:** Backend działa, ale brak danych

**Rozwiązanie:**
Baza danych jest pusta. Zsynchronizuj dane:
1. Otwórz: `https://twoj-backend.onrender.com/docs`
2. Znajdź endpoint `/api/players/sync`
3. Kliknij "Try it out" → "Execute"
4. Poczekaj 2-3 minuty
5. Odśwież Streamlit

---

## 📖 Więcej pomocy

- **Szczegółowy przewodnik:** [STREAMLIT_SECRETS_SETUP.md](STREAMLIT_SECRETS_SETUP.md)
- **Deployment guide:** [STREAMLIT_CLOUD_DEPLOYMENT.md](STREAMLIT_CLOUD_DEPLOYMENT.md)
- **Troubleshooting:** [TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)

---

## ✅ Checklist

- [ ] Skopiowałem URL backendu z Render Dashboard
- [ ] URL **NIE** kończy się slash'em (`/`)
- [ ] Dodałem `BACKEND_API_URL` w Streamlit Secrets
- [ ] Zapisałem secrets (kliknąłem "Save")
- [ ] Poczekałem ~30s na restart
- [ ] Odświeżyłem aplikację Streamlit

**Gotowe!** 🎉
