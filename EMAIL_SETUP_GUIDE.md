# 📧 Email Notifications - Przewodnik Konfiguracji

## Quick Start

Email notifications są **opcjonalne**. Scheduler działa bez nich!

## 📋 Step by Step: Gmail

### 1. Enable 2-Step Verification

1. Idź do: https://myaccount.google.com/security
2. Znajdź "2-Step Verification"
3. Click "Get started" i postępuj według instrukcji

### 2. Generate App Password

1. Idź do: https://myaccount.google.com/apppasswords
2. W "Select app" Select **"Mail"**
3. W "Select device" Select **"Other (Custom name)"**
4. Wpisz: "Polish Football Data Hub International"
5. Click **"Generate"**
6. **Skopiuj** 16-znakowe hasło (format: `xxxx xxxx xxxx xxxx`)

### 3. Configure .env

Edytuj plik `.env` (lub utwórz jeśli nie istnieje):

```env
# Email notification settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=twoj-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_FROM=twoj-email@gmail.com
EMAIL_TO=gdzie-wyslac@example.com
```

**Ważne:**
- `SMTP_PASSWORD` - użyj **App Password**, nie zwykłego hasła!
- `EMAIL_TO` - może być inny adres niż `SMTP_USER`

### 4. Test!

```bash
cd polish-players-tracker

# Test email dla stats sync
python -c "from app.backend.main import send_sync_notification_email; send_sync_notification_email(1, 0, 1, 0.5, []); print('Stats sync email sent!')"

# Test email dla matchlogs sync
python -c "from app.backend.main import send_matchlogs_notification_email; send_matchlogs_notification_email(1, 0, 1, 25, 0.5, []); print('Matchlogs sync email sent!')"
```

---

## 📋 Inne providery email

### Outlook / Hotmail

```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=twoj-email@outlook.com
SMTP_PASSWORD=twoje-haslo
EMAIL_FROM=twoj-email@outlook.com
EMAIL_TO=recipient@example.com
```

**Uwaga:** Outlook może wymagać "App Password" jeśli masz 2FA.

### Yahoo Mail

```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=twoj-email@yahoo.com
SMTP_PASSWORD=app-password
EMAIL_FROM=twoj-email@yahoo.com
EMAIL_TO=recipient@example.com
```

**Uwaga:** Yahoo **wymaga** App Password. Wygeneruj tutaj:
https://login.yahoo.com/account/security

### SendGrid (for production)

SendGrid to profesjonalny serwis email (darmowy plan: 100 emails/dzień).

1. Sign up: https://sendgrid.com/
2. Create API Key: Settings > API Keys > Create API Key
3. Konfiguracja:

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=twoj-sendgrid-api-key
EMAIL_FROM=twoj-zweryfikowany-email@example.com
EMAIL_TO=recipient@example.com
```

**Ważne:** `SMTP_USER` musi być dokładnie `apikey` (nie zmieniaj!)

### Mailgun (for production)

```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@twoja-domena.mailgun.org
SMTP_PASSWORD=twoj-mailgun-password
EMAIL_FROM=noreply@twoja-domena.mailgun.org
EMAIL_TO=recipient@example.com
```

---

## 🧪 Testowanie konfiguracji

### Test 1: Simple Import

```bash
python -c "from app.backend.main import send_sync_notification_email; print('✅ OK')"
```

### Test 2: Wysłanie testowego emaila

Utwórz plik `tmp_rovodev_test_email.py`:

```python
import os
import sys
sys.path.insert(0, '.')

# Konfiguracja (lub użyj .env)
os.environ['SMTP_HOST'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_USER'] = 'twoj-email@gmail.com'
os.environ['SMTP_PASSWORD'] = 'twoje-app-password'
os.environ['EMAIL_FROM'] = 'twoj-email@gmail.com'
os.environ['EMAIL_TO'] = 'gdzie-wyslac@example.com'

from app.backend.main import send_sync_notification_email

# Wyślij testowy email
print("📧 Sending test email...")
send_sync_notification_email(
    synced=98,
    failed=2,
    total=100,
    duration_minutes=20.5,
    failed_players=["Test Player 1", "Test Player 2"]
)
print("✅ Test email sent! Check your inbox.")
```

Uruchom:
```bash
cd polish-players-tracker
python tmp_rovodev_test_email.py
```

---

## ❌ Troubleshooting

### Problem: "Authentication failed"

**Rozwiązanie dla Gmail:**
1. Upewnij się, że masz włączoną 2-Step Verification
2. Użyj **App Password**, nie zwykłego hasła
3. Skopiuj App Password **without spaces** (ale ze spacjami też powinno działać)

**Rozwiązanie dla innych:**
1. Sprawdź czy hasło jest poprawne
2. Sprawdź czy wymaga App Password (jeśli masz 2FA)

### Problem: "Connection refused" / "Timeout"

**Solution:**
1. Sprawdź `SMTP_HOST` - czy jest poprawny?
2. Sprawdź `SMTP_PORT` - zwykle 587 (TLS) lub 465 (SSL)
3. Sprawdź firewall - czy blokuje port 587?
4. Spróbuj z inną siecią (może proxy/VPN blokuje?)

### Problem: Email nie configured - skipping notification

**To nie jest błąd!** To oznacza że email nie jest skonfigurowany.

**Jeśli chcesz emaile:**
1. Dodaj zmienne SMTP do `.env`
2. Upewnij się że wszystkie są ustawione:
   - `SMTP_HOST`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `EMAIL_TO`

### Problem: Email wysłany, ale nie doszedł

**Solution:**
1. Sprawdź **Spam folder**
2. Sprawdź logi - czy wysłanie się powiodło?
3. Sprawdź `EMAIL_TO` - czy adres jest poprawny?
4. Gmail: Sprawdź "Sent" folder w `SMTP_USER`

### Problem: "535 5.7.8 Username and Password not accepted"

**Gmail:**
- Użyj App Password zamiast normalnego hasła
- Upewnij się że 2-Step Verification jest włączona

**Outlook:**
- Włącz "Allow less secure apps" lub użyj App Password

---

## 🔒 Bezpieczeństwo

### ✅ Dobre praktyki

1. **NIE commituj** pliku `.env` do Git (jest w `.gitignore`)
2. **Użyj App Passwords** zamiast normalnych haseł
3. **Dla produkcji** - użyj SendGrid/Mailgun zamiast Gmail
4. **Ogranicz permissions** dla `.env`: `chmod 600 .env`
5. **Używaj różnych haseł** dla różnych serwisów

### ❌ Czego NIE robić

1. **NIE wklejaj** haseł do kodu
2. **NIE używaj** zwykłego hasła Gmail (użyj App Password)
3. **NIE udostępniaj** pliku `.env` nikomu
4. **NIE commituj** credentials do Git
5. **NIE używaj** Gmail w produkcji (limity, ryzyko)

---

## 📊 Limity wysyłania

### Gmail
- **500 emails/dzień** (dla kont darmowych)
- **2000 emails/dzień** (dla Google Workspace)
- Scheduler: 2 emails/tydzień = **OK!** ✅

### SendGrid (darmowy plan)
- **100 emails/dzień**
- Scheduler: 2 emails/tydzień = **OK!** ✅

### Mailgun (darmowy trial)
- **5000 emails/miesiąc** (pierwsze 3 miesiące)
- Scheduler: ~8 emails/miesiąc = **OK!** ✅

---

## 💡 Pro Tips

### Tip 1: Testuj z --visible mode

Gdy testujesz synchronizację, użyj:
```bash
python sync_player_full.py --visible --all-seasons Lewandowski
```
To otworzy przeglądarkę i zobaczysz co się dzieje.

### Tip 2: Użyj aliasu email

Gmail obsługuje aliasy:
- `twoj-email+scheduler@gmail.com` 
- Idzie do `twoj-email@gmail.com`
- Możesz filtrować w Gmail

### Tip 3: Dla wielu odbiorców

Chcesz wysyłać do wielu osób?
```env
EMAIL_TO=osoba1@example.com,osoba2@example.com,osoba3@example.com
```

**Uwaga:** Kod obecnie wspiera tylko jeden adres. Dla wielu musisz zmodyfikować `send_sync_notification_email()`.

### Tip 4: Gmail Filters

Utwórz filtr w Gmail dla emaili od schedulera:
1. From: `twoj-email@gmail.com`
2. Subject: "Scheduler Sync Complete"
3. Action: Apply label "Scheduler Reports"

---

## 🎨 Przykładowy email

Po konfiguracji, otrzymasz emaile w formacie HTML:

![Email Preview]
```
┌─────────────────────────────────────────┐
│   ✅ Polish Football Data Hub International             │
│   Scheduled Sync Report                 │
├─────────────────────────────────────────┤
│ Time: 2025-01-16 06:15:32              │
│ Duration: 21.3 minutes                  │
│                                         │
│ 📊 Results                              │
│ • Total players: 100                    │
│ • Successfully synced: 98 (98.0%)       │
│ • Failed: 2                             │
│                                         │
│ ❌ Failed Players                       │
│ • Player Name 1                         │
│ • Player Name 2                         │
├─────────────────────────────────────────┤
│ This is an automated message from       │
│ Polish Football Data Hub International Scheduler        │
└─────────────────────────────────────────┘
```

Z kolorami, emoji i profesjonalnym formatowaniem! 🎨

---

## ✅ Gotowe!

Po skonfigurowaniu email:
1. ✅ Scheduler będzie działał normalnie
2. ✅ Po każdej synchronizacji dostaniesz email:
   - **Zielony header** dla stats sync (Pon/Czw 6:00)
   - **Niebieski header** dla matchlogs sync (Wtorek 7:00)
3. ✅ Email zawiera szczegółowy raport
4. ✅ Błędy wysyłania nie zatrzymują schedulera

## 📋 Dwa Typy Email

### Email #1: Stats Sync (zielony)
- Wysyłany: Poniedziałek i Czwartek o 6:00
- Zawiera: Liczba zsynchronizowanych graczy, czas trwania
- Temat: "🤖 Scheduler Sync Complete: X/Y Players Synced"

### Email #2: Matchlogs Sync (niebieski)
- Wysyłany: Wtorek o 7:00
- Zawiera: Liczba graczy i meczów, czas trwania
- Temat: "📋 Matchlogs Sync Complete: X Matches from Y/Z Players"

**Enjoy email notifications! 📧🚀**
