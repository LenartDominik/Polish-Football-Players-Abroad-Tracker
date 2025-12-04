# 🤝 Contributing to Polish Football Data Hub International

Thank you for considering contributing! This project welcomes contributions from the community.

---

## 📋 How to Contribute

### 🐛 Report Bugs

Found a bug? Please create an issue with:
- **Description:** Clear description of the bug
- **Steps to reproduce:** How to trigger the bug
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Environment:** Local/Render/Streamlit Cloud
- **Logs:** Relevant error messages

### 💡 Suggest Features

Have an idea? Create an issue with:
- **Feature description:** What you'd like to see
- **Use case:** Why this would be useful
- **Implementation ideas:** (optional) How it could work

### 🔧 Submit Pull Requests

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly:** Run backend and frontend locally
5. **Commit:** Follow commit message format (see below)
6. **Push:** `git push origin feature/your-feature-name`
7. **Create Pull Request** with clear description

---

## 📝 Commit Message Format

Use clear, descriptive commit messages:

```
feat: Add goalkeeper comparison charts
fix: Correct xG calculation for substitutes
docs: Update deployment guide for Render
refactor: Simplify API client error handling
test: Add unit tests for player sync
```

**Prefixes:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Code style (formatting, no logic change)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

---

## 🧪 Development Setup

### Prerequisites
- Python 3.10+
- PostgreSQL (Supabase recommended)
- Git

### Setup Steps

1. **Clone repository:**
   ```bash
   git clone https://github.com/LenartDominik/Polish-Football-Data-Hub-International.git
   cd Polish-Football-Data-Hub-International/polish-players-tracker
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   source venv/bin/activate      # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Add your `DATABASE_URL` (Supabase)
   - Optionally add SMTP settings for email testing

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start backend:**
   ```bash
   python -m uvicorn app.backend.main:app --reload
   ```

7. **Start frontend (separate terminal):**
   ```bash
   streamlit run app/frontend/streamlit_app.py
   ```

---

## 🧪 Testing

**Manual testing:**
- Test all modified endpoints in Swagger UI (`http://localhost:8000/docs`)
- Test frontend features in Streamlit
- Verify data sync works correctly

**Future:** Unit tests will be added (contributions welcome!)

---

## 📚 Code Style

**Python:**
- Follow PEP 8
- Use type hints where possible
- Keep functions small and focused
- Comment complex logic

**SQL/Alembic:**
- Use descriptive migration names
- Test migrations both up and down
- Keep migrations atomic

---

## 🔒 Data & Legal

**Important:**
- All data comes from FBref.com
- Must maintain attribution (see [LEGAL_NOTICE.md](LEGAL_NOTICE.md))
- Non-commercial use only
- Respect FBref Terms of Service (12-second rate limiting)

**Do not:**
- Remove FBref attribution
- Use for commercial purposes without licensing
- Scrape faster than 12 seconds between requests

---

## 📖 Documentation

When adding features:
- Update relevant `.md` files
- Add docstrings to functions/classes
- Update API documentation if needed
- Keep Polish translations in `.pl.md` files

---

## ✅ Pull Request Checklist

Before submitting PR:

- [ ] Code runs without errors
- [ ] Tested locally (backend + frontend)
- [ ] Commit messages follow format
- [ ] Documentation updated
- [ ] No sensitive data in commits (passwords, API keys)
- [ ] Attribution maintained

---

## 🙏 Code of Conduct

**Be respectful:**
- Constructive feedback
- Welcoming to newcomers
- Patient with questions
- Professional communication

---

## 📧 Questions?

- **GitHub Issues:** For bugs and features
- **GitHub Discussions:** For questions and ideas
- **Email:** (Add if you want direct contact)

---

**Thank you for contributing! 🎉**
