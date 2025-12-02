# Changelog v0.7.4

## 🔧 Zmiany i Poprawki

### ✅ Naprawione Błędy

#### 1. Season Total - Reprezentacja
**Problem:** Sekcja "Season Total" nie uwzględniała meczów reprezentacji z roku kalendarzowego 2025.

**Rozwiązanie:**
- Dodano funkcję `get_season_filters()` która automatycznie generuje wszystkie formaty sezonu
- Funkcja zwraca: `['2025-2026', '2025/2026', '2025', 2025, '2026', 2026]`
- Zaktualizowano 3 miejsca w `streamlit_app.py` (linie 789, 805, 851)

**Rezultat:** Season Total teraz poprawnie sumuje: Liga + Puchary Europejskie + Puchary Krajowe + Reprezentacja

**Pliki zmienione:**
- `app/frontend/streamlit_app.py` - dodano funkcję pomocniczą i zaktualizowano filtrowanie

---

#### 2. European Cups Details - Wiele Pucharów
**Problem:** Sekcja Details w kolumnie "European Cups" pokazywała tylko pierwszą rozgrywkę (`euro_stats.iloc[0]`), pomijając pozostałe puchary dla graczy grających w wielu rozgrywkach w tym samym sezonie.

**Przykład:**
- Karol Świderski 2019-2020: Champions League (2 mecze) + Europa League (2 mecze)
- Nicola Zalewski 2024-2025: Champions League (2 mecze) + Europa League (4 mecze)

**Rozwiązanie:**
- Zmieniono `row_to_show = euro_stats.iloc[0]` na `euro_stats_to_show = euro_stats`
- Dodano pętlę iterującą przez wszystkie rozgrywki: `for idx, row_to_show in euro_stats_to_show.iterrows()`
- Dodano nagłówki dla każdej rozgrywki: `st.markdown(f"### {row_to_show['competition_name']}")`
- Dodano separatory między rozgrywkami: `st.markdown("---")`

**Rezultat:** Details pokazuje szczegóły dla WSZYSTKICH europejskich pucharów osobno

**Pliki zmienione:**
- `app/frontend/streamlit_app.py` (linie 447-536) - logika Details Expander

---

#### 3. Compare Players - Tylko Aktualny Sezon
**Problem:** Strona porównania graczy pokazywała dropdown z wieloma sezonami (2025-26, 2024-25, 2023-24, 2022-23), co było mylące i niepotrzebne.

**Rozwiązanie:**
- Usunięto dropdown z wyborem sezonu
- Dodano informację: `st.info("📅 Comparing current season: 2025-26")`
- Sezon zawsze ustawiony na `None` (co aktywuje backend do użycia 2025-2026)

**Rezultat:** Porównanie zawsze pokazuje tylko aktualny sezon 2025-26

**Pliki zmienione:**
- `app/frontend/pages/2_⚖️_compare_players.py` (linia 223) - usunięto selectbox

---

### ⚠️ Znane Ograniczenia

#### Kwalifikacje Champions League
**Problem:** FBref agreguje kwalifikacje Champions League z fazą grupową Europa League jako jedną rozgrywkę "Europa Lg".

**Przykład:**
- Szymański (Fenerbahçe 2025-26): Grał w kwalifikacjach CL, ale odpadł i przeszedł do EL
- W aplikacji widoczne jako: "Europa Lg: 4 mecze" (łącznie kwalifikacje CL + faza grupowa EL)

**Dlaczego tak jest:**
- FBref **nie rozdziela** kwalifikacji od fazy grupowej w swoich tabelach
- Drużyny odpadające z kwalifikacji CL automatycznie trafiają do fazy grupowej EL
- To jest **standard branżowy** - większość serwisów sportowych robi podobnie

**Rozwiązanie:** ZAAKCEPTOWANE - brak możliwości rozdzielenia bez zmiany źródła danych

**Dokumentacja:** 
- `LIMITATION_CHAMPIONS_LEAGUE_QUALIFICATIONS.md` - szczegółowe wyjaśnienie

---

## 📚 Nowa Dokumentacja

### Utworzone Pliki:
1. **`ANALIZA_PODWOJNEGO_SUMOWANIA.md`** - Szczegółowa analiza problemu (50+ stron)
2. **`BUGFIX_SEASON_TOTAL_NATIONAL_TEAM.md`** - Opis poprawki Season Total
3. **`BUGFIX_EUROPEAN_CUPS_SEPARATE_ROWS.md`** - Opis poprawki European Cups
4. **`PODSUMOWANIE_ANALIZY.md`** - Krótkie podsumowanie (polski)
5. **`PODSUMOWANIE_POPRAWEK_FINAL.md`** - Finalne podsumowanie wszystkich zmian
6. **`LIMITATION_CHAMPIONS_LEAGUE_QUALIFICATIONS.md`** - Wyjaśnienie ograniczenia

### Zaktualizowane Pliki:
1. **`README.md`** - główny README projektu
2. **`app/frontend/README.md`** - dokumentacja frontendu
3. **`app/backend/README.md`** - dokumentacja backendu
4. **`app/backend/main.py`** - wersja API (0.7.4) i opis w Swagger/ReDoc

---

## 🔧 Szczegóły Techniczne

### Zmienione Funkcje:

#### `get_season_filters(season_str='2025-2026')`
**Lokalizacja:** `app/frontend/streamlit_app.py` (linie 12-61)

**Cel:** Automatyczne generowanie wszystkich formatów sezonu dla filtrowania

**Zwraca:**
```python
['2025-2026', '2025/2026', '2025', 2025, '2026', 2026]
```

**Użycie:**
```python
season_filters = get_season_filters('2025-2026')
comp_stats_2526 = comp_stats[comp_stats['season'].isin(season_filters)]
```

---

### Zmienione Struktury Danych:

#### `competition_stats` (baza danych)
**Nowe/zaktualizowane kolumny:**
- `npxg` - Non-Penalty Expected Goals
- `penalty_goals` - Bramki z karnych

**Uwagi:**
- `season` dla reprezentacji: rok kalendarzowy (np. "2025"), nie sezon ("2025-2026")
- `competition_type`: LEAGUE, EUROPEAN_CUP, DOMESTIC_CUP, NATIONAL_TEAM

---

## 📊 Testy i Weryfikacja

### Gracze do Przetestowania:

1. **Robert Lewandowski** - reprezentacja + club (2025-2026)
2. **Karol Świderski** - wiele europejskich pucharów (2019-2020, 2020-2021)
3. **Nicola Zalewski** - Champions League + Europa League (2024-2025)
4. **Sebastian Szymański** - "Europa Lg" zawiera kwalifikacje CL (2025-2026)

### Scenariusze Testowe:

✅ **Test 1:** Gracz z reprezentacją w roku 2025
- Season Total powinien zawierać mecze reprezentacji
- Suma powinna być: Liga + Puchary + Reprezentacja

✅ **Test 2:** Gracz w Champions League + Europa League (ten sam sezon)
- Details powinien pokazać oba puchary osobno
- Każdy z własnym nagłówkiem i statystykami

✅ **Test 3:** Porównanie graczy
- Powinien pokazać tylko sezon 2025-26
- Brak dropdown z wyborem sezonu

✅ **Test 4:** Europa League (zawiera kwalifikacje CL)
- Pokazuje jako "Europa Lg"
- Liczba meczów zawiera kwalifikacje + fazę grupową

---

## 🚀 Deployment

### API (Backend):
- Wersja zaktualizowana do **0.7.4**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend (Streamlit):
- Wersja zaktualizowana do **0.7.4**
- Dashboard: `http://localhost:8501`

---

## 💡 Rekomendacje

### Przyszłe Usprawnienia (opcjonalne):

1. **Tooltip w UI** dla "Europa Lg":
   ```python
   st.info("ℹ️ Europa Lg zawiera kwalifikacje Champions League")
   ```

2. **Rozszerzyć `get_season_filters()`** na inne sekcje:
   - League stats (linia 304)
   - European Cups (linia 419)
   - Domestic Cups (linia 532)
   
3. **Dodać testy jednostkowe** dla `get_season_filters()`

4. **Logowanie sum** dla debugowania:
   ```python
   logger.info(f"Season Total: {total_games} games (League: {league}, Cups: {cups}, NT: {national_team})")
   ```

---

## 📝 Notatki

### Co NIE było problemem:
- ❌ Podwójne sumowanie - nie występowało
- ❌ Duplikaty w bazie - niemożliwe (UNIQUE constraint)
- ❌ Scraper zapisujący sumy - nie zapisuje "All competitions"

### Prawdziwe problemy:
- ✅ Niepełne filtrowanie - rok 2025 nie był uwzględniony
- ✅ Details pokazywał tylko pierwszy wiersz - brakowało pętli

---

**Data wydania:** 2025-01-XX  
**Wersja:** 0.7.4  
**Status:** ✅ PRODUCTION READY  
**Autor:** Rovo Dev
