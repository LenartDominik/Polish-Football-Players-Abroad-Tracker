# 🔧 Troubleshooting Guide - Polish Football Data Hub International

**Common issues and solutions for deployment, configuration, and usage.**

---

## 📋 Table of Contents

1. [Database Issues](#database-issues)
2. [Backend API Issues](#backend-api-issues)
3. [Frontend Issues](#frontend-issues)
4. [Email Notifications](#email-notifications)
5. [Data Sync Issues](#data-sync-issues)
6. [Performance Issues](#performance-issues)

---

## 💾 Database Issues

### ❌ Problem: "Could not connect to database"

**Symptoms:**
- Backend won't start
- Error: "could not connect to server"
- Health check fails

**Causes & Solutions:**

#### 1. Incorrect DATABASE_URL

**Check:**
- Verify `DATABASE_URL` format in `.env` or Render environment variables
- Should look like: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`

**Fix:**
1. Go to Supabase Dashboard → Settings → Database
2. Copy **Connection pooler** string (port 6543)
3. Replace `[YOUR-PASSWORD]` with your actual password
4. Update in Render Dashboard → Environment variables
5. Restart service

#### 2. Supabase Project Paused

**Cause:** Free tier pauses projects after 7 days of inactivity.

**Fix:**
1. Go to Supabase Dashboard
2. If project shows "Paused", click **Resume project**
3. Wait 1-2 minutes
4. Restart backend

#### 3. Wrong Password

**Fix:**
1. Supabase Dashboard → Settings → Database
2. Click **Reset Database Password**
3. Save new password
4. Update `DATABASE_URL` with new password
5. Restart backend

### ❌ Problem: "Relation 'players' does not exist"

**Cause:** Database migrations not run.

**Fix:**
1. Ensure `alembic.ini` is in repository
2. Backend runs migrations automatically on startup
3. Check logs in Render Dashboard for migration errors
4. Verify in Supabase: Table Editor should show `players`, `competition_stats`, etc.

**Manual migration (if needed):**
```bash
# Locally
alembic upgrade head

# On Render, migrations run automatically via main.py
```

---

## 🔧 Backend API Issues

### ❌ Problem: Backend returns 502/503

**Cause:** Render free tier cold start (spins down after 15min inactivity).

**Symptoms:**
- First request takes 1-2 minutes
- Subsequent requests are fast
- Frontend shows "Cannot connect"

**Solution:**
- This is **normal behavior** for free tier
- Wait 1-2 minutes for backend to wake up
- Use Cron-job.org to ping health check every 14 minutes (keeps backend warm)

**Cron-job setup:**
1. Go to https://cron-job.org
2. Create free account
3. Add job: `https://your-backend.onrender.com/health`
4. Schedule: Every 14 minutes
5. This keeps backend alive

### ❌ Problem: "404 Not Found" on API endpoints

**Cause:** Wrong API URL or endpoint path.

**Fix:**
- Verify URL format: `https://your-backend.onrender.com/api/players/`
- Note the `/api/` prefix
- Check Swagger docs: `https://your-backend.onrender.com/docs`

### ❌ Problem: CORS errors in browser console

**Cause:** Backend CORS settings.

**Fix:**
- Backend already has CORS configured for all origins
- If issue persists, check browser dev tools console for specific error
- Verify `BACKEND_API_URL` in Streamlit secrets has correct protocol (https://)

---

## 🎨 Frontend Issues

### ❌ Problem: "Cannot connect to API at http://localhost:8000"

**Cause:** Missing or incorrect `BACKEND_API_URL` in Streamlit Cloud secrets.

**Fix:**
1. Go to https://share.streamlit.io
2. Click your app → **Settings** ⚙️ → **Secrets**
3. Add or update:
   ```toml
   BACKEND_API_URL = "https://your-backend.onrender.com"
   ```
4. **Important:** 
   - NO trailing slash
   - Use HTTPS (not HTTP)
   - Use actual Render URL
5. Click **Save**
6. Wait ~30 seconds for automatic restart

### ❌ Problem: "Compare Players" page missing in sidebar

**Cause:** `pages/` folder not in repository root.

**Fix:**
1. Verify structure:
   ```
   repository-root/
   ├── streamlit_app_cloud.py
   ├── api_client.py
   ├── requirements.txt
   └── pages/
       └── 2_Compare_Players.py
   ```
2. If files are in subfolder (e.g., `polish-players-tracker/`), ensure Streamlit Cloud **Main file path** includes folder:
   - Set to: `polish-players-tracker/streamlit_app_cloud.py`
3. Commit and push to GitHub
4. Streamlit Cloud will auto-deploy

### ❌ Problem: "No data available"

**Cause:** Backend database is empty (no sync performed).

**Fix:**
1. Go to backend API docs: `https://your-backend.onrender.com/docs`
2. Find endpoint: `POST /api/players/sync`
3. Click "Try it out" → "Execute"
4. Wait 2-3 minutes for sync to complete
5. Refresh frontend
6. Data should now appear

### ❌ Problem: Frontend shows old data after backend update

**Cause:** Streamlit caching.

**Fix:**
1. In frontend app, press **C** to clear cache
2. Or click menu (≡) → **Clear cache**
3. Refresh page

---

## 📧 Email Notifications

### ❌ Problem: "Authentication failed (535)"

**Cause:** Using regular Gmail password instead of App Password.

**Fix - Gmail App Password Setup:**

1. **Enable 2-Step Verification:**
   - Go to https://myaccount.google.com/security
   - Find "2-Step Verification"
   - Click "Get started" and follow steps

2. **Generate App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other" → Enter "Polish Players Tracker"
   - Click "Generate"
   - Copy 16-character password (without spaces)

3. **Update Environment Variables:**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-char App Password
   EMAIL_FROM=your-email@gmail.com
   EMAIL_TO=recipient@example.com
   ```

4. **Restart backend**

**Note:** Never use your regular Gmail password for SMTP!

### ❌ Problem: Emails not sending but no error

**Causes & Fixes:**

1. **Wrong SMTP settings:**
   - Gmail: `smtp.gmail.com:587`
   - Outlook: `smtp-mail.outlook.com:587`
   - Yahoo: `smtp.mail.yahoo.com:587`

2. **Firewall blocking:**
   - Render.com allows port 587 (TLS)
   - Check Render logs for connection errors

3. **Email in spam:**
   - Check recipient spam folder
   - Add sender to contacts

### 📧 Email Providers Configuration

**Gmail:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # NOT regular password!
```

**Outlook/Hotmail:**
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

**SendGrid (Recommended for production):**
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey  # Literally "apikey"
SMTP_PASSWORD=your-sendgrid-api-key
```
Free: 100 emails/day - https://sendgrid.com

---

## 🔄 Data Sync Issues

### ❌ Problem: Sync fails with "Rate limit exceeded"

**Cause:** Too many requests to FBref.com too quickly.

**Fix:**
- Backend has built-in 12-second rate limiting (FBref ToS compliant)
- This is normal and expected
- Sync takes time: ~90 players × 12 seconds = ~18 minutes
- **Don't run multiple syncs simultaneously**

### ❌ Problem: "Player not found on FBref"

**Cause:** Player name doesn't match FBref exactly.

**Fix:**
1. Check FBref.com for exact player name format
2. Update player name in database
3. Re-sync

**Example:**
- ❌ `Robert Lewandowski`
- ✅ `Robert Lewandowski` (with proper Unicode)

### ❌ Problem: Scheduler not running automatically

**Verify configuration:**
```env
ENABLE_SCHEDULER=true
SYNC_DAILY_HOUR=6  # Hour in 24h format (0-23)
```

**Check logs:**
- Render Dashboard → Logs
- Look for: "Scheduler initialized"
- Should see: "Scheduled stats sync for Monday/Thursday at 06:00"

**Note:** Scheduler runs in UTC timezone by default. Adjust `SYNC_DAILY_HOUR` accordingly.

---

## ⚡ Performance Issues

### ❌ Problem: Frontend slow to load

**Causes & Fixes:**

1. **Backend cold start (Render free tier):**
   - First request takes 1-2 minutes
   - Keep backend warm with cron-job.org (see above)

2. **Large dataset:**
   - Use filters to reduce data shown
   - Streamlit caches data automatically

3. **Network latency:**
   - Choose Render region close to users
   - Use Supabase connection pooler

### ❌ Problem: Database queries slow

**Fixes:**

1. **Use connection pooler:**
   - Port 6543 (pooler) instead of 5432 (direct)
   - Already configured in recommended setup

2. **Check indexes:**
   - Alembic migrations create necessary indexes
   - Verify in Supabase: Table Editor → players → Indexes

3. **Optimize queries:**
   - Backend already uses SQLAlchemy optimizations
   - Avoid `SELECT *` when possible (backend does this)

---

## 🔍 Debugging Tips

### Check Backend Logs

**Render.com:**
- Dashboard → Your service → Logs
- Real-time logs show requests, errors, sync progress

### Check Frontend Logs

**Streamlit Cloud:**
- Open app → Menu (≡) → Manage app → Logs
- Shows Python errors, API connection issues

### Test API Manually

**Use Swagger UI:**
1. Go to `https://your-backend.onrender.com/docs`
2. Try each endpoint
3. See request/response in browser dev tools

**Use curl:**
```bash
# Health check
curl https://your-backend.onrender.com/health

# Get players
curl https://your-backend.onrender.com/api/players/

# Get specific player
curl https://your-backend.onrender.com/api/players/1
```

---

## 📚 Still Having Issues?

1. **Check deployment guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
2. **Review API docs:** `https://your-backend.onrender.com/docs`
3. **Check GitHub Issues:** https://github.com/LenartDominik/Polish-Football-Data-Hub-International/issues
4. **Create new issue** with:
   - Error message
   - Steps to reproduce
   - Backend logs (if relevant)
   - Environment (local/Render/Streamlit Cloud)

---

**Most issues are configuration-related. Double-check environment variables and secrets!** ✅
