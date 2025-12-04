# 🚀 Deployment Guide - Polish Football Data Hub International

**Complete guide for deploying the full stack application to production.**

## 🎯 About This Project

This project demonstrates **web scraping automation** for regularly fetching and processing current player statistics from **fbref.com**. The **FastAPI backend** cyclically updates the PostgreSQL database, while the **Streamlit frontend** provides a user-friendly interface for data exploration. The platform automates data retrieval, validation, and presentation.

**Key Technologies:**
- 🕸️ **Web Scraping:** Playwright headless browser
- 🔄 **Automation:** APScheduler for periodic sync
- 🗄️ **Database:** PostgreSQL (Supabase) with SQLAlchemy ORM
- 🔗 **API:** FastAPI with auto-generated docs
- 🎨 **Frontend:** Streamlit with Plotly visualizations

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Database Setup (Supabase)](#database-setup-supabase)
4. [Backend Deployment (Render.com)](#backend-deployment-rendercom)
5. [Frontend Deployment (Streamlit Cloud)](#frontend-deployment-streamlit-cloud)
6. [Configuration & Secrets](#configuration--secrets)
7. [Testing Deployment](#testing-deployment)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**Architecture:**
```
Frontend (Streamlit Cloud) → Backend (Render.com) → Database (Supabase PostgreSQL)
```

**Cost:** 100% FREE for hobby projects!

**Deployment Time:** ~30 minutes total

---

## 📋 Prerequisites

Before deploying, you need:

✅ **GitHub account** (free)  
✅ **Code pushed to GitHub repository**  
✅ **Supabase account** (free - sign up at https://supabase.com)  
✅ **Render.com account** (free - sign up at https://render.com)  
✅ **Streamlit Cloud account** (free - sign up at https://share.streamlit.io)

---

## 💾 Database Setup (Supabase)

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Sign in with GitHub
3. Click **New Project**
4. Configure:
   - **Name:** `polish-players-db` (or your choice)
   - **Database Password:** Create strong password ⚠️ **Save this!**
   - **Region:** `Europe (Frankfurt)` or closest to you
5. Click **Create new project**
6. Wait ~2 minutes for project to initialize

### Step 2: Get Database Connection String

1. In Supabase Dashboard → **Settings** → **Database**
2. Find **Connection string** section
3. Click **URI** tab
4. Copy the **Connection pooler** string (recommended):
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your actual password from Step 1

**Important:** Use **Connection pooler** (port 6543) not direct connection (port 5432) for better performance.

### Step 3: Run Database Migrations

Migrations will be run automatically when backend starts for the first time.

**Verify tables created:**
1. Supabase Dashboard → **Table Editor**
2. You should see:
   - `players`
   - `competition_stats`
   - `goalkeeper_stats`
   - `player_matches`
   - `alembic_version`

---

## 🔧 Backend Deployment (Render.com)

### Step 1: Create Web Service

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `polish-players-backend` (or your choice)
   - **Region:** Choose closest to your users
   - **Branch:** `master` (or `main`)
   - **Root Directory:** `polish-players-tracker` (if your code is in subfolder)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Add Environment Variables

In Render Dashboard → **Environment** → Add:

```env
# Required - Database
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# Optional - Scheduler (for automatic data sync)
ENABLE_SCHEDULER=true
SYNC_DAILY_HOUR=6

# Optional - Email Notifications (see Email Setup in Troubleshooting)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**Important:** Replace placeholders with your actual values!

### Step 3: Deploy

1. Click **Create Web Service**
2. Wait ~3-5 minutes for first deploy
3. Render will:
   - Install dependencies
   - Run database migrations
   - Start backend

### Step 4: Verify Backend

Once deployed, check:

**Health check:**
```
https://your-backend.onrender.com/health
```
Should return: `{"status": "healthy", "database": "connected"}`

**API docs:**
```
https://your-backend.onrender.com/docs
```
Should show Swagger UI

**⚠️ Note:** Free tier Render spins down after 15 minutes of inactivity. First request may take 1-2 minutes.

---

## 🎨 Frontend Deployment (Streamlit Cloud)

### Step 1: Prepare Files

Ensure your repository has these files in root:
- ✅ `streamlit_app_cloud.py` - Main application
- ✅ `api_client.py` - API client
- ✅ `requirements.txt` - Dependencies
- ✅ `pages/` folder - With `2_Compare_Players.py`

### Step 2: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **New app**
4. Configure:
   - **Repository:** Select your repo
   - **Branch:** `master` (or `main`)
   - **Main file path:** `streamlit_app_cloud.py`
5. Click **Deploy!**

### Step 3: Add Secrets (CRITICAL!)

**Without this step, frontend won't connect to backend!**

1. In Streamlit Cloud → Your app → **Settings** ⚙️ → **Secrets**
2. Add:
   ```toml
   BACKEND_API_URL = "https://your-backend.onrender.com"
   ```
3. Replace `your-backend.onrender.com` with your actual Render URL
4. **Important:** NO trailing slash!
5. Click **Save**
6. App will restart automatically (~30 seconds)

### Step 4: Verify Frontend

1. Open your Streamlit app URL: `https://your-app.streamlit.app`
2. You should see:
   - ✅ Player data loading
   - ✅ Filters working
   - ✅ **Compare Players** page in sidebar

**If you see "Cannot connect to API":**
- Check if `BACKEND_API_URL` is correct in Secrets
- Check if backend is running (visit health check URL)
- Wait 1-2 minutes if backend was sleeping

---

## 🔐 Configuration & Secrets

### Backend Environment Variables (Render)

**Required:**
```env
DATABASE_URL=postgresql://...  # Supabase connection string
```

**Optional (Scheduler):**
```env
ENABLE_SCHEDULER=true          # Enable automatic sync
SYNC_DAILY_HOUR=6             # Hour for daily sync (0-23)
```

**Optional (Email Notifications):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Gmail App Password, NOT regular password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

**For Gmail App Password setup, see [Troubleshooting](#troubleshooting) section.**

### Frontend Secrets (Streamlit Cloud)

**Required:**
```toml
BACKEND_API_URL = "https://your-backend.onrender.com"
```

**Important:**
- NO trailing slash (`/`)
- Must be HTTPS
- Use actual Render URL (find in Render Dashboard)

---

## ✅ Testing Deployment

### 1. Test Backend API

**Health Check:**
```bash
curl https://your-backend.onrender.com/health
```
Expected: `{"status": "healthy", "database": "connected"}`

**Get Players:**
```bash
curl https://your-backend.onrender.com/api/players/
```
Expected: JSON array of players (or empty `[]` if no data synced yet)

**API Documentation:**
Visit: `https://your-backend.onrender.com/docs`

### 2. Test Frontend

1. Open: `https://your-app.streamlit.app`
2. Check:
   - ✅ Players load without errors
   - ✅ Filters work (league, team, position)
   - ✅ Compare Players page exists in sidebar
   - ✅ Can compare two players

### 3. Test Full Integration

1. Sync data via backend:
   - Go to `https://your-backend.onrender.com/docs`
   - Find endpoint: `POST /api/players/sync`
   - Click "Try it out" → "Execute"
   - Wait 2-3 minutes
2. Refresh frontend - data should appear!

---

## 🐛 Troubleshooting

### Problem: "Could not connect to database"

**Causes:**
- ❌ Wrong password in `DATABASE_URL`
- ❌ Supabase project paused (free tier pauses after 7 days inactivity)
- ❌ Wrong connection string format

**Solutions:**
1. Check `DATABASE_URL` in Render environment variables
2. Go to Supabase Dashboard → Resume project if paused
3. Verify you're using **Connection pooler** (port 6543)

### Problem: "Cannot connect to API at http://localhost:8000"

**Cause:** Frontend is missing `BACKEND_API_URL` secret.

**Solution:**
1. Streamlit Cloud → App → Settings → Secrets
2. Add: `BACKEND_API_URL = "https://your-backend.onrender.com"`
3. Save and wait 30s for restart

### Problem: Backend returns 502/503 errors

**Cause:** Render free tier is spinning up (cold start after 15min inactivity).

**Solution:** Wait 1-2 minutes and try again. First request wakes up the service.

### Problem: Email notifications not working

**Cause:** Using regular Gmail password instead of App Password.

**Solution:**
1. Enable 2-Step Verification in Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password (16 characters) in `SMTP_PASSWORD` env var
4. Restart Render service

### Problem: No data in frontend

**Cause:** Database is empty (no sync performed yet).

**Solution:**
1. Go to backend `/docs`
2. Use `POST /api/players/sync` endpoint
3. Wait 2-3 minutes for sync
4. Refresh frontend

---

## 🎉 Success Checklist

- [ ] ✅ Supabase project created with PostgreSQL
- [ ] ✅ Backend deployed on Render.com
- [ ] ✅ Backend health check returns "healthy"
- [ ] ✅ Frontend deployed on Streamlit Cloud
- [ ] ✅ `BACKEND_API_URL` added to Streamlit Secrets
- [ ] ✅ Frontend connects to backend (no connection errors)
- [ ] ✅ Data synced successfully
- [ ] ✅ Compare Players page works

---

## 📚 Additional Resources

- **Supabase Docs:** https://supabase.com/docs
- **Render Docs:** https://render.com/docs
- **Streamlit Cloud Docs:** https://docs.streamlit.io/streamlit-community-cloud

**Need more help?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

---

**Congratulations! Your application is now live! 🚀**
