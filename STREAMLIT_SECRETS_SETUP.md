# 🔐 Streamlit Cloud Secrets - Przewodnik Konfiguracji

## Problem
Jeśli widzisz błędy w Streamlit Cloud:
```
❌ Cannot connect to API at http://localhost:8000
❌ No data available. Please sync data first.
```

To znaczy, że **secrets nie są skonfigurowane** w Streamlit Cloud.

---

## Rozwiązanie - Krok Po Kroku

### 1️⃣ Znajdź URL swojego backendu na Render.com

1. Zaloguj się do [Render Dashboard](https://dashboard.render.com/)
2. Kliknij na swój backend service (np. `polish-players-backend`)
3. Skopiuj URL z górnej części strony (np. `https://polish-players-backend.onrender.com`)

**⚠️ WAŻNE:** URL **NIE** powinien kończyć się slash'em (`/`)

✅ Poprawnie: `https://polish-players-backend.onrender.com`  
❌ Źle: `https://polish-players-backend.onrender.com/`

---

### 2️⃣ Dodaj Secret w Streamlit Cloud

1. Przejdź do [Streamlit Cloud](https://share.streamlit.io/)
2. Znajdź swoją aplikację na liście
3. Kliknij **Settings** (⚙️) → **Secrets**
4. Wklej poniższy kod (zamień URL na swój):

```toml
# Backend API URL - WYMAGANE
BACKEND_API_URL = "https://polish-players-backend.onrender.com"
```

5. Kliknij **Save**
6. Streamlit automatycznie zrestartuje aplikację

---

### 3️⃣ Sprawdź czy działa

1. Odśwież swoją aplikację Streamlit Cloud
2. Powinieneś zobaczyć dane graczy
3. Jeśli widzisz "Loading..." lub błąd połączenia:
   - Sprawdź czy backend na Render działa (otwórz URL w przeglądarce)
   - Sprawdź czy URL w secrets jest poprawny (bez slash'a na końcu)
   - Sprawdź czy zapisałeś secrets (kliknąłeś "Save")

---

## 🔍 Weryfikacja

### Sprawdź backend
Otwórz w przeglądarce:
```
https://twoj-backend.onrender.com/health
```

Powinno zwrócić:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Sprawdź API
Otwórz w przeglądarce:
```
https://twoj-backend.onrender.com/api/players/
```

Powinno zwrócić JSON z listą graczy (lub pustą listę `[]`)

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to API at http://localhost:8000"
**Przyczyna:** Secrets nie są skonfigurowane lub są źle skonfigurowane

**Rozwiązanie:**
1. Sprawdź czy dodałeś secret `BACKEND_API_URL` w Streamlit Cloud
2. Sprawdź czy URL jest poprawny (bez slash'a)
3. Zapisz secrets i poczekaj ~30s na restart aplikacji

---

### Problem: "Backend is starting. This may take 1-2 minutes..."
**Przyczyna:** Backend na Render.com uruchamia się po okresie nieaktywności (Free Tier)

**Rozwiązanie:**
- **To jest normalne!** Free tier Render usypia serwis po 15 minutach nieaktywności
- Pierwsze połączenie może trwać 1-2 minuty
- Odśwież stronę po chwili - dane powinny się załadować

---

### Problem: "No data available. Please sync data first"
**Przyczyna:** Backend działa, ale baza danych jest pusta

**Rozwiązanie:**
1. Sprawdź czy `DATABASE_URL` jest skonfigurowany w Render Dashboard
2. Uruchom synchronizację danych (backend → `/docs` → endpoint `/api/players/sync`)
3. Lub użyj lokalnie: `python sync_player_full.py`

---

## 📝 Pełny przykład secrets.toml

```toml
# ===== WYMAGANE =====
BACKEND_API_URL = "https://polish-players-backend.onrender.com"

# ===== OPCJONALNE =====
# Tylko jeśli chcesz dodać autoryzację API
# API_KEY = "your-secret-key-here"

# Tylko jeśli chcesz łączyć się bezpośrednio z bazą (NIE ZALECANE)
# DATABASE_URL = "postgresql://user:pass@host:port/db"
```

---

## 🎯 Najczęstsze błędy

| Błąd | Przyczyna | Rozwiązanie |
|------|-----------|-------------|
| `http://localhost:8000` w URL | Brak secrets | Dodaj `BACKEND_API_URL` w Streamlit Secrets |
| `404 Not Found` | Źle skonfigurowany URL | Sprawdź URL backendu (usuń `/` na końcu) |
| `Connection timeout` | Backend śpi (Free Tier) | Odśwież po 1-2 minutach |
| `Empty response` | Baza danych pusta | Zsynchronizuj dane przez backend API |

---

## ✅ Checklist

- [ ] Mam działający backend na Render.com
- [ ] Skopiowałem URL backendu (bez `/` na końcu)
- [ ] Dodałem `BACKEND_API_URL` w Streamlit Secrets
- [ ] Zapisałem secrets (kliknąłem "Save")
- [ ] Poczekałem ~30s na restart aplikacji
- [ ] Backend zwraca `{"status": "healthy"}` na `/health`
- [ ] Backend zwraca dane na `/api/players/`

---

## 🚀 Gotowe!

Twoja aplikacja Streamlit Cloud powinna teraz łączyć się z backendem na Render.com i wyświetlać dane graczy! 🎉

**Pytania?** Sprawdź [STREAMLIT_CLOUD_DEPLOYMENT.md](STREAMLIT_CLOUD_DEPLOYMENT.md) lub [TROUBLESHOOTING_DATABASE.md](TROUBLESHOOTING_DATABASE.md)
