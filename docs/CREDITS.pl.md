# 📜 Podziękowania i Źródła Danych

## Atrybucja Danych

### FBref.com (Sports Reference LLC)

Ten projekt nie byłby możliwy bez **[FBref.com](https://fbref.com/)**, wiodącego źródła statystyk i analiz piłkarskich.

**Co wykorzystujemy z FBref:**
- Baza statystyk graczy (gole, asysty, xG, xA, minuty, strzały, podania, itp.)
- Logi meczowe (szczegółowe statystyki mecz po meczu)
- Klasyfikacje rozgrywek (ligi, puchary, mecze międzynarodowe)
- Metryki specyficzne dla bramkarzy (obrony, czyste konta, bramki stracone)

**Licencja i Warunki:**
- Dane wykorzystywane zgodnie z Warunkami Użytkowania FBref
- Niekomercyjne użycie edukacyjne
- Atrybucja zawarta w UI, dokumentacji i odpowiedziach API
- Zastosowane ograniczenie częstotliwości (12 sekund między requestami)

**Oficjalne Linki:**
- Strona: https://fbref.com/
- O nas: https://fbref.com/en/about/
- Twitter: [@fbref](https://twitter.com/fbref)

**Wspieraj FBref:** Jeśli te dane są dla Ciebie wartościowe, rozważ odwiedzenie FBref.com bezpośrednio i wsparcie ich pracy. Dostarczają nieocenioną usługę dla społeczności piłkarskiej.

---

## Stack Technologiczny

### Biblioteki Open Source

Ten projekt zbudowany jest w oparciu o niesamowite technologie open source:

**Backend:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Playwright](https://playwright.dev/) - Browser automation for web scraping
- [APScheduler](https://apscheduler.readthedocs.io/) - Advanced Python Scheduler
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation using Python type annotations

**Frontend:**
- [Streamlit](https://streamlit.io/) - Fast way to build and share data apps
- [Pandas](https://pandas.pydata.org/) - Data analysis and manipulation
- [Plotly](https://plotly.com/) - Interactive graphing library

**Development:**
- [Python](https://www.python.org/) - Programming language
- [PostgreSQL](https://www.postgresql.org/) - Powerful open-source database
- [Supabase](https://supabase.com/) - Open-source Firebase alternative (PostgreSQL hosting)

Pełna lista zależności w `requirements.txt`.

---

## Inspiracja i Zasoby

**Statystyki Piłkarskie:**
- [FBref.com](https://fbref.com/) - Główne źródło danych
- [Transfermarkt](https://www.transfermarkt.com/) - Wartości zawodników i dane transferowe (obecnie nieużywane)
- [Understat](https://understat.com/) - Statystyki xG (obecnie nieużywane)

**Zasoby Techniczne:**
- [Real Python](https://realpython.com/) - Tutoriale Python
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Stack Overflow](https://stackoverflow.com/) - Wsparcie społeczności

---

## Disclaimer

**Polish Football Data Hub International** is an independent, non-commercial project created for educational purposes and to showcase Polish football talent playing abroad.

This application is **NOT** affiliated with, endorsed by, or connected to:
- FBref.com or Sports Reference LLC
- Any football clubs or leagues
- UEFA, FIFA, or other football governing bodies
- Any commercial entities

All trademarks, logos, and brand names are the property of their respective owners.

---

## Contributing

This project is open source and welcomes contributions! If you'd like to contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please ensure that any contributions respect FBref's Terms of Service and maintain proper attribution.

---

## Contact

**Questions about data usage?** Open an issue on GitHub or contact the maintainer.

**Questions about data licensing?** Contact Sports Reference LLC directly at https://fbref.com/

---

**Made with ❤️ for Polish football fans**

Last updated: 2025-11-23
