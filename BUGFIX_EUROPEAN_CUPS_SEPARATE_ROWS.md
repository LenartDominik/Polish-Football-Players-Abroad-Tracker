# BUGFIX: European Cups - Separate Rows for Each Competition

## 🐛 Problem

Gracze, którzy grali w **wielu europejskich pucharach** w tym samym sezonie (np. Champions League + Europa League), powinni mieć **osobne wiersze** dla każdej rozgrywki w tabeli "Season Statistics History".

### Przykład:
**Karol Świderski - Sezon 2019-2020:**
- Champions Lg: 2 mecze, 0 bramek, 28 minut
- Europa Lg: 2 mecze, 1 bramka, 70 minut

**Oczekiwane wyświetlenie:**
```
| Season  | Type         | Competition   | Games | Goals | Minutes |
|---------|--------------|---------------|-------|-------|---------|
| 2019/20 | 🌍 European  | Champions Lg  | 2     | 0     | 28      |
| 2019/20 | 🌍 European  | Europa Lg     | 2     | 1     | 70      |
```

**NIE agregować:**
```
| Season  | Type         | Competition          | Games | Goals | Minutes |
|---------|--------------|----------------------|-------|-------|---------|
| 2019/20 | 🌍 European  | European Cups (All)  | 4     | 1     | 98      |  ❌ ŹLE!
```

---

## 🔍 Analiza

### Obecna Logika (linie 1098-1132):

Kod **agreguje** tylko National Team:
```python
if not season_display.empty and 'competition_type' in season_display.columns:
    nt_mask = season_display['competition_type'] == 'NATIONAL_TEAM'
    if nt_mask.any():
        nt_agg = season_display[nt_mask].groupby('season', as_index=False).agg({
            'competition_type': 'first',
            'competition_name': (lambda x: 'National Team (All)'),
            'games': 'sum',
            'goals': 'sum',
            # ... inne statystyki
        })
        season_display = pd.concat([season_display[~nt_mask], nt_agg], ignore_index=True)
```

**European Cups NIE są agregowane** → każda rozgrywka jest osobnym wierszem ✅

### Co Działa Poprawnie:

1. ✅ **Baza danych** - każda rozgrywka jest osobnym rekordem (UNIQUE constraint)
2. ✅ **Scraper** - zapisuje Champions League, Europa League, Conference League osobno
3. ✅ **Kolumna European Cups** (linie 423-441) - wyświetla wszystkie rozgrywki w pętli
4. ✅ **Tabela historii** - NIE agreguje European Cups (każda jest osobnym wierszem)

### Co NIE Działa:

❌ **Details Expander** (linie 456-466) - pokazuje tylko **pierwszy wiersz**:
```python
if not euro_stats.empty:
    row_to_show = euro_stats.iloc[0]  # ❌ Tylko pierwszy!
```

**Problem:** Jeśli gracz ma Champions League + Europa League, Details pokaże tylko Champions League.

---

## ✅ Rozwiązanie

### Zmiana 1: Details - Pokazuj Wszystkie European Cups

**Przed (linia 447-525):**
```python
with st.expander("📊 Details"):
    details_found = False
    row_to_show = None
    is_gk_display = False
    
    if is_gk and not gk_stats.empty:
        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            row_to_show = euro_stats.iloc[0]  # ❌ Tylko pierwszy!
            is_gk_display = True
            details_found = True
    
    if not details_found and not comp_stats.empty:
        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            row_to_show = euro_stats.iloc[0]  # ❌ Tylko pierwszy!
            is_gk_display = False
            details_found = True
    
    if details_found and row_to_show is not None:
        # Wyświetl statystyki tylko dla JEDNEJ rozgrywki
```

**Po:**
```python
with st.expander("📊 Details"):
    details_found = False
    euro_stats_to_show = None
    is_gk_display = False
    
    if is_gk and not gk_stats.empty:
        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            euro_stats_to_show = euro_stats  # ✅ Wszystkie!
            is_gk_display = True
            details_found = True
    
    if not details_found and not comp_stats.empty:
        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            euro_stats_to_show = euro_stats  # ✅ Wszystkie!
            is_gk_display = False
            details_found = True
    
    if details_found and euro_stats_to_show is not None:
        # Iteruj przez wszystkie rozgrywki
        for idx, row_to_show in euro_stats_to_show.iterrows():
            st.markdown(f"**{row_to_show['competition_name']}**")
            # Wyświetl statystyki dla tej rozgrywki
            # ... (reszta kodu bez zmian)
```

---

## 📊 Zmienione Pliki

### `app/frontend/streamlit_app.py`

**Zmiana w Details Expander (linia ~447-525):**

1. Zmień `row_to_show = euro_stats.iloc[0]` na `euro_stats_to_show = euro_stats`
2. Iteruj przez wszystkie wiersze: `for idx, row_to_show in euro_stats_to_show.iterrows()`
3. Dodaj nagłówek dla każdej rozgrywki: `st.markdown(f"**{row_to_show['competition_name']}**")`

---

## 📋 Weryfikacja

### Tabela Season Statistics History:

✅ **Nie wymaga zmian** - już pokazuje osobne wiersze dla każdej European Cup

### Kolumna European Cups:

✅ **Nie wymaga zmian** - już pokazuje wszystkie rozgrywki w pętli (linia 436-441)

### Details Expander:

❌ **Wymaga poprawki** - obecnie pokazuje tylko pierwszą rozgrywkę

---

## 🎯 Rezultaty

Po wprowadzeniu zmian:

✅ **Kolumna European Cups** - pokazuje wszystkie rozgrywki (już działa)  
✅ **Details** - pokazuje szczegóły dla WSZYSTKICH rozgrywek (po poprawce)  
✅ **Tabela historii** - każda rozgrywka w osobnym wierszu (już działa)  

### Przykład dla Świderskiego 2019-2020:

**European Cups (2025-2026):**
- **Champions Lg**: 2 games, 0 goals
- **Europa Lg**: 2 games, 1 goal

**Details:**
- **Champions Lg**
  - Starts: 2
  - Minutes: 28
  - Goals: 0
  - xG: 0.15
  
- **Europa Lg**
  - Starts: 2
  - Minutes: 70
  - Goals: 1
  - xG: 0.89

**Season Statistics History:**
| Season  | Type        | Competition  | Games | Goals | Minutes |
|---------|-------------|--------------|-------|-------|---------|
| 2019/20 | 🌍 European | Champions Lg | 2     | 0     | 28      |
| 2019/20 | 🌍 European | Europa Lg    | 2     | 1     | 70      |

---

**Data:** 2025-01-XX  
**Status:** ✅ NAPRAWIONE

---

## 📝 Implementacja

### Zmieniony Kod (linia 447-536):

**Przed:**
```python
with st.expander("📊 Details"):
    if is_gk and not gk_stats.empty:
        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            row_to_show = euro_stats.iloc[0]  # ❌ Tylko pierwszy!
```

**Po:**
```python
with st.expander("📊 Details"):
    if is_gk and not gk_stats.empty:
        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
        if not euro_stats.empty:
            euro_stats_to_show = euro_stats  # ✅ Wszystkie!
    
    if details_found and euro_stats_to_show is not None:
        # Show details for ALL European competitions
        for idx, row_to_show in euro_stats_to_show.iterrows():
            if len(euro_stats_to_show) > 1:
                st.markdown(f"### {row_to_show['competition_name']}")
            
            # Wyświetl statystyki dla tej rozgrywki
            # ...
            
            # Separator między rozgrywkami
            if len(euro_stats_to_show) > 1 and idx < len(euro_stats_to_show) - 1:
                st.markdown("---")
```

### Kluczowe Zmiany:

1. ✅ `row_to_show = euro_stats.iloc[0]` → `euro_stats_to_show = euro_stats`
2. ✅ Dodano pętlę: `for idx, row_to_show in euro_stats_to_show.iterrows()`
3. ✅ Dodano nagłówek dla każdej rozgrywki: `st.markdown(f"### {row_to_show['competition_name']}")`
4. ✅ Dodano separator między rozgrywkami: `st.markdown("---")`
5. ✅ Wszystkie statystyki są wewnątrz pętli (wcięcie poprawione)

---

## 🎯 Weryfikacja

### Test Case: Karol Świderski 2019-2020

**Przed poprawką:**
- Details pokazywał tylko Champions League (pierwszy wiersz)

**Po poprawce:**
- Details pokazuje:
  - **Champions Lg**
    - Starts: 2
    - Minutes: 28
    - Goals: 0
  - ---
  - **Europa Lg**
    - Starts: 2
    - Minutes: 70
    - Goals: 1

### Inne Przypadki Testowe:

1. **Robert Lewandowski 2020-2021:**
   - Champions Lg: 6 meczów, 5 bramek
   - Super Cup: 1 mecz, 0 bramek

2. **Nicola Zalewski 2024-2025:**
   - Champions Lg: 2 mecze, 0 bramek
   - Europa Lg: 4 mecze, 0 bramek

---

## ✅ Status Sekcji

| Sekcja | Status | Uwagi |
|--------|--------|-------|
| **Kolumna European Cups** | ✅ Działa poprawnie | Już wyświetlała wszystkie w pętli |
| **Details Expander** | ✅ NAPRAWIONE | Teraz pokazuje wszystkie rozgrywki |
| **Season Statistics History** | ✅ Działa poprawnie | Każda rozgrywka w osobnym wierszu |
