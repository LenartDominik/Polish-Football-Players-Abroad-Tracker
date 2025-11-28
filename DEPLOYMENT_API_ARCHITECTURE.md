# Deployment Configuration Guide - API Architecture

## 🏗️ Nowa Architektura

```
┌─────────────────┐      HTTP/REST      ┌──────────────────┐      SQL      ┌─────────────┐
│  Streamlit      │ ─────────────────► │  FastAPI         │ ────────────► │  PostgreSQL │
│  Frontend       │   (port 8501)       │  Backend         │  (psycopg2)   │  / Supabase │
│  (Cloud/Local)  │                     │  (port 8000)     │               │             │
└─────────────────┘                     └──────────────────┘               └─────────────┘
```

## 📦 Dependencies

### Frontend (`requirements-streamlit.txt`)
```
streamlit==1.51.0
pandas==2.3.3
plotly==5.18.0
requests==2.32.5  # ← REQUIRED for API communication
```

**NOT NEEDED anymore:**
- ❌ `psycopg2-binary` - backend handles DB
- ❌ `sqlalchemy` - backend handles DB
- ❌ `sqlite3` - backend handles DB

### Backend (`requirements.txt`)
```
fastapi==0.120.4
uvicorn[standard]==0.38.0
sqlalchemy==2.0.44
psycopg2-binary==2.9.9
requests==2.32.5
pandas==2.3.3
...
```

## 🚀 Local Development

### 1. Install Dependencies

**Backend:**
```bash
pip install -r requirements.txt
```

**Frontend:**
```bash
pip install -r requirements-streamlit.txt
```

### 2. Configure Environment Variables

**Backend** (`.env` or environment):
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
# or
DATABASE_URL=sqlite:///./players.db

# Optional
OPENAI_API_KEY=your_key_here
```

**Frontend** (`.streamlit/secrets.toml` or environment):
```toml
API_BASE_URL = "http://localhost:8000"
```

Or set environment variable:
```bash
export API_BASE_URL="http://localhost:8000"
```

### 3. Start Services

**Terminal 1 - Backend:**
```bash
cd polish-players-tracker
python -m uvicorn app.backend.main:app --reload
```
Backend runs on: http://localhost:8000

**Terminal 2 - Frontend:**
```bash
cd polish-players-tracker
streamlit run app/frontend/streamlit_app.py
```
Frontend runs on: http://localhost:8501

### 4. Verify

```bash
# Check backend health
curl http://localhost:8000/health

# Check API endpoints
curl http://localhost:8000/api/players/

# Open frontend
open http://localhost:8501
```

## ☁️ Cloud Deployment (Streamlit Cloud + Render)

### Backend on Render

**render.yaml:**
```yaml
services:
  - type: web
    name: polish-players-backend
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: postgres-db
          property: connectionString
```

Deploy URL example: `https://polish-players-backend.onrender.com`

### Frontend on Streamlit Cloud

**1. Connect GitHub Repository**

**2. Configure Streamlit Settings:**

File: `.streamlit/config.toml`
```toml
[server]
headless = true
port = 8501
enableCORS = false
```

**3. Configure Secrets:**

In Streamlit Cloud dashboard → App settings → Secrets:
```toml
API_BASE_URL = "https://polish-players-backend.onrender.com"

# Optional if frontend needs other services
OPENAI_API_KEY = "your_key_here"
```

**4. Specify Python File:**
```
Main file path: app/frontend/streamlit_app.py
```

**5. Requirements:**
```
Requirements file: requirements-streamlit.txt
```

## 🔧 Environment Variables Reference

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | No | `http://localhost:8000` | Backend API URL |

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `OPENAI_API_KEY` | No | - | For AI features |
| `SMTP_*` | No | - | For email notifications |

## 🧪 Testing Deployment

### Test Backend API
```bash
# Health check
curl https://your-backend.onrender.com/health

# Get players
curl https://your-backend.onrender.com/api/players/

# Get competition stats
curl https://your-backend.onrender.com/api/players/stats/competition
```

### Test Frontend
1. Open Streamlit app URL
2. Check browser console for errors
3. Verify players are loaded
4. Check if "Cannot connect to API" error appears

### Common Issues

**❌ "Cannot connect to API"**
- Check if `API_BASE_URL` is set correctly
- Verify backend is running
- Check CORS settings if frontend and backend are on different domains

**❌ "404 Not Found" from API**
- Verify endpoint paths use `/api/` prefix
- Check backend router configuration

**❌ Frontend shows empty data**
- Check browser console for API errors
- Verify backend has data in database
- Test API endpoints directly with curl

## 📝 Migration Checklist

When deploying the new API architecture:

- [ ] Backend deployed with all endpoints working
- [ ] Database connected to backend
- [ ] Frontend configured with `API_BASE_URL`
- [ ] All API endpoints tested (health, players, stats, matches)
- [ ] Frontend displays data correctly
- [ ] No SQLite/direct DB connections in frontend
- [ ] requirements-streamlit.txt updated (no DB dependencies)
- [ ] Environment variables configured in cloud platforms
- [ ] CORS configured if needed
- [ ] SSL/HTTPS working on both services

## 🔒 Security Notes

1. **Never expose database credentials in frontend**
   - ✅ Backend handles all database connections
   - ✅ Frontend only knows API URL

2. **Use environment variables**
   - ✅ Never hardcode URLs or credentials
   - ✅ Use secrets management in cloud platforms

3. **HTTPS in production**
   - ✅ Render provides HTTPS automatically
   - ✅ Streamlit Cloud provides HTTPS automatically

4. **API Rate Limiting** (future enhancement)
   - Consider adding rate limiting to backend API
   - Use API keys for authentication if needed

## 🎯 Benefits of This Architecture

1. **Separation of Concerns**
   - Frontend: UI/UX only
   - Backend: Business logic + data access
   
2. **Better Security**
   - No database credentials in frontend
   - Centralized authentication point

3. **Easier Scaling**
   - Scale frontend and backend independently
   - Add load balancing to backend

4. **Simpler Deployment**
   - Frontend has minimal dependencies
   - Backend can be cached and optimized

5. **Multiple Clients**
   - Same API can serve Streamlit, mobile apps, etc.
   - Consistent data access layer

---
**Version:** 1.0 - API Architecture Migration
**Last Updated:** 2024-11-28
