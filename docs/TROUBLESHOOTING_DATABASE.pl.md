# 🔧 Troubleshooting: Database Connection Issues

## Problem: `password authentication failed for user "postgres"`

### Przyczyny i Rozwiązania

#### 1. ❌ **Błędne hasło w DATABASE_URL**

**Objaw:**
```
psycopg2.OperationalError: password authentication failed for user "postgres"
```

**Rozwiązanie:**
1. Sprawdź hasło w **Supabase Dashboard** → Settings → Database → Reset Password (jeśli potrzeba)
2. Skopiuj **nowe hasło**
3. Zaktualizuj `DATABASE_URL` na Renderze:
   - Render Dashboard → Twój serwis → **Environment**
   - Znajdź `DATABASE_URL` i edytuj
   - Wklej poprawne hasło
   - **Save Changes** → **Manual Deploy**

**⚠️ UWAGA:** Hasło w Render Environment **NIE** jest automatycznie synchronizowane z lokalnym `.env`!

---

#### 2. ❌ **Nieprawidłowy format USERNAME dla Transaction Pooler**

**Objaw:**
```
connection to server at "aws-1-eu-west-1.pooler.supabase.com", port 6543 failed
FATAL: password authentication failed for user "postgres"
```

**Problem:** Transaction Pooler (port **6543**) wymaga formatu `postgres.PROJECT_REF`, nie samego `postgres`.

**Rozwiązanie:**

1. **Sprawdź w Supabase** poprawny format:
   - Supabase Dashboard → Settings → Database
   - **Connection String** → URI → **Transaction Pooling**
   - Skopiuj connection string

2. **Format MUSI być:**
   ```
   postgresql://postgres.XXXXX:YOUR_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
   ```
   
   **NIE:**
   ```
   postgresql://postgres:YOUR_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
   ```

3. **Gdzie znaleźć PROJECT_REF:**
   - Supabase Dashboard → Settings → General → **Reference ID**
   - Lub w URL Supabase: `https://app.supabase.com/project/XXXXX`

---

#### 3. ❌ **Render nie wykrywa zmiennej DATABASE_URL**

**Objaw:**
- Błąd połączenia pomimo prawidłowego `DATABASE_URL` w Dashboard

**Rozwiązanie:**

1. **Sprawdź czy zmienna istnieje:**
   - Render Dashboard → Environment
   - Czy `DATABASE_URL` jest na liście?

2. **Wymuś reload zmiennych:**
   - Manual Deploy → **Clear build cache & deploy**

3. **Sprawdź czy nie ma duplikatów:**
   - Usuń ewentualne inne zmienne typu `DATABASE_URL_POSTGRES` (jeśli nie są używane)
   - Render używa pierwszej pasującej zmiennej

---

#### 4. ❌ **Python 3.13 + psycopg2 Incompatibility**

**Objaw:**
```
ImportError: undefined symbol: _PyInterpreterState_Get
```

**Rozwiązanie:**

Plik `.python-version` wymusza Python 3.11:
```
3.11
```

✅ **Już naprawione w projekcie!**

---

## 📋 Checklist Diagnostyczna

Gdy backend na Renderze nie uruchamia się:

- [ ] Sprawdź **Render Logs** - przeczytaj dokładnie błąd
- [ ] Sprawdź czy `DATABASE_URL` **istnieje** w Render Environment
- [ ] Sprawdź czy **hasło jest poprawne** (porównaj z Supabase)
- [ ] Sprawdź **format username**:
  - Port 6543 → `postgres.PROJECT_REF`
  - Port 5432 → `postgres` (bez ref)
- [ ] Sprawdź czy connection string ma `postgresql://` (nie `postgres://`)
- [ ] Sprawdź czy `.python-version` istnieje (dla Python 3.11)
- [ ] Wymuś **Clear build cache & deploy** na Renderze

---

## 🔍 Debug Tips

### Sprawdź wersję Python na Renderze
W logach buildowania szukaj:
```
Python version: 3.X.X
```

### Sprawdź czy zmienne środowiskowe są załadowane
Backend loguje przy starcie:
```
🚀 Aplikacja startuje...
```

Jeśli widzisz:
```
❌ DATABASE_URL not found in environment variables!
```
To zmienna nie jest ustawiona w Render Environment.

---

## ✅ Prawidłowa Konfiguracja

### Supabase Connection String (Transaction Pooler)
```
postgresql://postgres.abcd1234:MySecurePassword123@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

### Render Environment Variables (minimum)
```
DATABASE_URL=postgresql://postgres.XXX:[PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=Europe/Warsaw
```

### Email (opcjonalne, ale zalecane dla schedulera)
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

---

## 📚 Powiązane Dokumenty

- **DATABASE.md** - Struktura i konfiguracja bazy danych
- **DEPLOYMENT.md** - Przewodnik deployment (backend + Supabase)
- **TROUBLESHOOTING.md** - Rozwiązywanie problemów

---

## 🆘 Nadal nie działa?

1. Sprawdź **Supabase Dashboard** → czy projekt jest aktywny?
2. Sprawdź **Render Status** → czy są awarie platformy?
3. Sprawdź **logi Render** → skopiuj pełny błąd i przeanalizuj
4. Zresetuj hasło w Supabase i zaktualizuj wszędzie
5. Wypróbuj **Session Pooler** (port 5432) zamiast Transaction (6543)
