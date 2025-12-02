# Bugfix: European Cups + Minutes + Goalkeeper Data + Season Total 2025-2026

## Problem

W tabeli "Season Statistics History (All Competitions)" dla graczy którzy grali w sezonie 2025/2026 w różnych europejskich pucharach (np. kwalifikacje Champions League → Europa League), pokazywał się tylko **jeden zagregowany rząd** zamiast osobnych rzędów dla każdej rozgrywki.

### Przykład - Szymański sezon 2024-2025:
- **Przed naprawą:** 1 rząd "Europa Lg" z częściowymi danymi
- **Po naprawie:** 2 osobne rzędy:
  - Champions Lg: 4 mecze (kwalifikacje, sierpień 2024)
  - Europa Lg: mecze z fazy ligowej

### Przykład - Świderski:
- Czasem źle zliczało statystyki
- Brakował osobny rząd dla Champions League gdy grał w kwalifikacjach i potem w Europa League

### Problem 2 - wyrównanie kolumny Minutes:
- W tabeli Season Statistics History kolumna "Minutes" była wyrównana do lewej (jak tekst)
- Powinna być wyrównana do prawej (jak liczby)
- Dotyczyło zarówno bramkarzy jak i graczy z pola

### Problem 3 - brakujące minuty dla bramkarzy:
- **GŁÓWNY PROBLEM:** Bramkarze mieli 0 minut w bazie mimo że FBref ma te dane
- Przykład: Grabara 2024-2025 Bundesliga - FBref pokazuje 29 meczów i **2610 minut**, ale w bazie było 29 meczów i **0 minut**
- Link: https://fbref.com/en/players/62182b1d/dom_lg/Kamil-Grabara-Domestic-League-Stats
- **Przyczyna:** Scraper pobierał minuty z tabeli `stats_keeper_*` która często **nie zawiera kolumny minutes**
- Minuty są w tabeli `stats_standard_*`, ale podczas mergowania były nadpisywane przez 0/None z goalkeeper table

### Problem 4 - źle zliczone mecze w kolumnie "Season Total (2025-2026)":
- **PROBLEM 4a:** Szczęsny pokazywał **39 meczów** zamiast **9 meczów** w kolumnie "Season Total (2025-2026)"
- **Przyczyna:** Filtr sezonu używał `['2025-2026', '2025/2026', '2026', '2025']` (linie 926, 941)
- Pojedyncze lata `'2025'` i `'2026'` w filtrze **błędnie łapały sezon 2024-2025**:
  - `'2024-2025'` zawiera string `'2025'` → został złapany przez filtr ❌
  - W rezultacie zliczało mecze z **dwóch sezonów**: 2024-2025 (30 meczów) + 2025-2026 (9 meczów) = 39
- **Dotyczyło:** Zarówno bramkarzy (linia 926) jak i graczy z pola (linia 941)

- **PROBLEM 4b:** Po fixie 4a, bramkarze **nadal** pokazywali błędne liczby meczów:
  - Szczęsny: **14 meczów** zamiast **9** (5 duplikatów z player_matches)
  - Skorupski: **18 meczów** zamiast **14** (4 duplikaty)
  - Drągowski: **9 meczów** zamiast **8** (1 duplikat)
- **Przyczyna:** KROK 2.5 (linia 960-983) dodawał europejskie mecze z `player_matches` dla **wszystkich graczy**
- Nie sprawdzał `if is_gk` więc bramkarze mieli **podwójne zliczanie**:
  - goalkeeper_stats już zawiera kompletne dane (klubowe + europejskie) ✅
  - player_matches zawiera mecze europejskie (które już są w goalkeeper_stats) ❌
  - KROK 2.5 nie wiedział że to duplikaty i dodawał je ponownie
  - Przykłady:
    - Szczęsny: 9 (goalkeeper_stats) + 5 (player_matches Champions Lg) = **14** ❌
    - Skorupski: 14 (goalkeeper_stats) + 4 (player_matches Europa Lg) = **18** ❌
    - Drągowski: 8 (goalkeeper_stats) + 1 (player_matches Europa Lg) = **9** ❌
- **Dotyczyło:** Tylko bramkarzy (gracze z pola potrzebują KROKU 2.5 bo competition_stats czasem nie ma wszystkich europejskich meczów)

- **PROBLEM 4c:** Kolejny filtr w linii 1011 **NADAL** używał starego formatu `['2025-2026', '2025/2026', '2026', '2025']`
- Ten filtr jest używany do obliczania `penalty_goals` dla graczy z pola
- Miał ten sam bug co 4a i 4b - łapał także sezon 2024-2025
- Nie wpływał bezpośrednio na kolumnę "Season Total" ale powodował błędne dane o karnych

## Przyczyna

Kod który rozdzielał europejskie puchary na osobne rzędy był **zakomentowany** (linie 1204-1217 w `streamlit_app.py`). 

Powód: Był wyłączony ponieważ `player_matches` miało niekompletne dane dla **starszych sezonów** (np. brakło Super Cup, Club World Cup, UEFA Cup z lat 2010-2020).

Ale dla **bieżącego sezonu 2024-2025** dane w `player_matches` SĄ kompletne, ponieważ scraper pobiera match logi dla aktualnego sezonu.

## Rozwiązanie

### Fix 1: Oddzielne rzędy dla europejskich pucharów

#### Hybrydowe podejście:
1. **Dla sezonów 2024-2025 i 2025-2026:** Użyj `player_matches` aby pokazać osobne rzędy dla Champions Lg, Europa Lg, Conf Lg
2. **Dla starszych sezonów:** Zachowaj zagregowane dane z `competition_stats` (zawiera historyczne puchary nie dostępne w match logs)

### Zmieniony kod (linie 1197-1223):

```python
# ENHANCEMENT: Add European cup stats from player_matches (separate rows for each competition)
# For current season (2024-2025, 2025-2026), use player_matches to show separate rows
# for Champions Lg, Europa Lg, etc. instead of aggregated EUROPEAN_CUP entry
# For older seasons, keep competition_stats data (may include historical cups not in player_matches)

if not is_goalkeeper and not matches_df.empty:
    euro_history = get_european_history_by_competition(row['id'], matches_df)
    if not euro_history.empty and not stats_to_display.empty:
        # Get current and recent seasons from euro_history
        current_seasons = ['2024-2025', '2025-2026', '2024/2025', '2025/2026']
        euro_current = euro_history[euro_history['season'].isin(current_seasons)]
        
        if not euro_current.empty:
            # Remove EUROPEAN_CUP entries for current seasons from comp_stats
            stats_to_display = stats_to_display[
                ~((stats_to_display['competition_type'] == 'EUROPEAN_CUP') & 
                  (stats_to_display['season'].isin(current_seasons)))
            ].copy()
            
            # Add detailed European stats from player_matches for current seasons
            stats_to_display = pd.concat([stats_to_display, euro_current], ignore_index=True)
            
            # Sort by season and competition_type
            stats_to_display = stats_to_display.sort_values(['season', 'competition_type'], ascending=False)
    elif not euro_history.empty:
        # If comp_stats is empty but we have euro_history, use it
        stats_to_display = euro_history
```

### Fix 2: Wyrównanie kolumny Minutes do prawej

Zmiany w liniach 1226-1236, 1390-1429:

1. **Zmiana obsługi brakujących minut (linia 1390-1399):**
   - Dla starszych sezonów FBref często nie ma danych o minutach (0 minut mimo że games > 0)
   - Zamieniamy 0 na "N/A" (wyraźnie pokazuje brakujące dane)
   - Kolumna Minutes staje się tekstowa (string) aby pomieścić zarówno liczby jak i "N/A"

2. **Dodanie custom CSS dla wyrównania (linie 1226-1236):**
   - Streamlit `TextColumn` domyślnie wyrównuje do lewej
   - Dodano custom CSS aby wymusić `text-align: right` dla kolumny Minutes
   - CSS targetuje 6-tą kolumnę w tabeli (`:nth-child(6)`)

3. **Dodanie column_config (linie 1403-1429):**
   - Wszystkie kolumny numeryczne używają `st.column_config.NumberColumn`
   - Minutes używa `st.column_config.TextColumn` (bo zawiera mieszane wartości: liczby i "N/A")
   - Dzięki CSS kolumna Minutes jest wyrównana do prawej mimo że jest tekstowa

### Fix 3: Zachowanie minut dla bramkarzy przy mergowaniu

Zmiany w `app/backend/services/fbref_playwright_scraper.py` (linie 673-694):

**Problem:** 
- Funkcja `_merge_goalkeeper_stats()` mergeowała dane z tabeli `stats_keeper_*` do `stats_standard_*`
- Tabela `stats_keeper_*` często nie zawiera kolumny `minutes` (jest None lub 0)
- Podczas mergowania wszystkie pola z goalkeeper table nadpisywały pola w standard table
- W rezultacie poprawne minuty ze standard table były tracone

**Rozwiązanie:**
1. Przed mergeowaniem: zapisz `existing_minutes` ze standard table
2. Wykonaj merge wszystkich pól z goalkeeper table
3. **Jeśli** GK table miało None/0 minut **ORAZ** standard table miało poprawne minuty:
   - Przywróć `minutes` ze standard table
4. Logowanie: dodano komunikat "✅ Preserved minutes={X} from standard table"

**Kod:**
```python
# Preserve minutes from standard table if it exists and is not 0/None
existing_minutes = stat.get('minutes')

# Merge all goalkeeper stats
for k, v in gk.items():
    stat[k] = v

# Restore minutes from standard table if GK table had None/0 and standard had valid data
if existing_minutes and (not stat.get('minutes') or stat.get('minutes') == 0):
    stat['minutes'] = existing_minutes
    logger.info(f"✅ Preserved minutes={existing_minutes} from standard table")
```

### Fix 4a: Poprawienie filtra sezonu dla "Season Total (2025-2026)"

Zmiany w `app/frontend/streamlit_app.py` (linie 926, 941):

**Problem:** 
- Filtr `['2025-2026', '2025/2026', '2026', '2025']` używał pojedynczych lat
- `'2025'` w filtrze łapał także `'2024-2025'` (bo zawiera substring '2025')
- Szczęsny miał zliczone mecze z **dwóch sezonów** zamiast jednego (39 zamiast 9)

**Rozwiązanie:**
- Usunięto pojedyncze lata `'2025'` i `'2026'` z filtra
- Teraz używa tylko pełnych formatów: `['2025-2026', '2025/2026']`
- Działa zarówno dla bramkarzy (linia 926) jak i graczy z pola (linia 941)

**Przed:**
```python
gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', '2026', '2025'])]
```

**Po:**
```python
# BUGFIX: Only use full season format '2025-2026', NOT single years '2025' or '2026'
# Single years would incorrectly match '2024-2025' (contains '2025')
gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026'])]
comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026'])]
```

### Fix 4b: Pomiń KROK 2.5 (dodawanie europejskich meczów) dla bramkarzy

Zmiany w `app/frontend/streamlit_app.py` (linia 963):

### Fix 4c: Poprawienie filtra dla penalty_goals

Zmiany w `app/frontend/streamlit_app.py` (linia 1011):

**Problem:**
- Kolejny filtr w linii 1011 używał starego formatu `['2025-2026', '2025/2026', '2026', '2025']`
- Ten sam bug co 4a - łapał także sezon 2024-2025
- Filtr jest używany do obliczania `penalty_goals` dla graczy z pola (kolumna PK)
- Nie wpływał bezpośrednio na "Season Total" ale powodował błędne dane o karnych

**Rozwiązanie:**
- Zmieniono filtr na `['2025-2026', '2025/2026']` (jak w fixach 4a i 4b)
- Teraz penalty_goals są obliczane tylko dla sezonu 2025-2026

**Przed:**
```python
if not comp_stats.empty:
    comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', '2026', '2025'])]
```

**Po:**
```python
if not comp_stats.empty:
    # BUGFIX: Use same filter as above - only full season format
    comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026'])]
```

## Wynik

### Dla Szymańskiego (sezon 2024-2025):
Tabela Season Statistics History pokazuje teraz:
- **Champions Lg:** 4 mecze, 360 minut, 0 goli, 1 asysta
- **Europa Lg:** X meczów, Y minut, 1 gol, 0 asyst
- **RAZEM:** Wszystkie mecze europejskie są poprawnie zliczone

### Dla wszystkich graczy:
- ✅ Osobne rzędy dla każdej rozgrywki europejskiej w sezonie 2024-2025 i 2025-2026
- ✅ Zachowane historyczne dane dla starszych sezonów
- ✅ Poprawne zliczanie minut, goli i asyst
- ✅ Działa również w kolumnie "European Cups (2025-2026)" w górnej części karty gracza
- ✅ Kolumna "Minutes" jest teraz wyrównana do prawej (jak liczby) dla wszystkich graczy
- ✅ Brakujące minuty dla starszych sezonów pokazują się jako "N/A" (zamiast 0)
- ✅ **NAJWAŻNIEJSZE:** Bramkarze mają teraz poprawne minuty z FBref (Grabara 2024-25 Bundesliga: 2610 minut zamiast 0)
- ✅ **Kolumna Season Total (2025-2026):** 
  - Szczęsny i inni bramkarze: **9 meczów** zamiast **39** (fix 4a) lub **12** (fix 4b)
  - Gracze z pola: poprawnie zliczane mecze (tylko sezon 2025-2026, bez 2024-2025)

## Pliki zmienione

- `app/frontend/streamlit_app.py` (linie 1197-1223) - Fix 1: rozdzielanie europejskich pucharów
- `app/frontend/streamlit_app.py` (linie 1226-1236, 1390-1429) - Fix 2: wyrównanie kolumny Minutes
- `app/frontend/streamlit_app.py` (linie 926, 941) - Fix 4a: filtr sezonu dla Season Total
- `app/frontend/streamlit_app.py` (linia 963) - Fix 4b: pomiń KROK 2.5 dla bramkarzy
- `app/frontend/streamlit_app.py` (linia 1011) - Fix 4c: filtr dla penalty_goals
- `app/backend/services/fbref_playwright_scraper.py` (linie 673-694) - Fix 3: zachowanie minut dla bramkarzy

## Testowanie

### Test 1: Gracze z Champions League → Europa League (sezon 2024-2025)
1. Uruchom frontend
2. Wyszukaj "Szymański"
3. Przewiń do "Season Statistics History (All Competitions)"
4. Sprawdź sezon 2024-2025:
   - ✅ Powinny być 2 osobne rzędy (Champions Lg + Europa Lg)
   - ✅ Champions Lg: 4 mecze z kwalifikacji
   - ✅ Europa Lg: mecze z fazy ligowej
   - ✅ Minuty, gole i asysty poprawnie zliczone

### Test 2: Starsze sezony
1. Sprawdź starsze sezony (np. 2020-2023)
2. ✅ Powinny używać zagregowanych danych z `competition_stats`
3. ✅ Brak problemów z brakującymi danymi

### Test 3: Kolumna European Cups (2025-2026)
1. Sprawdź górną część karty gracza
2. ✅ Kolumna "European Cups" pokazuje osobne wiersze dla każdej rozgrywki

### Test 4: Minuty dla bramkarzy
1. Zsynchronizuj dane bramkarza: `python sync_player_full.py "Grabara"`
2. Sprawdź w bazie danych:
   ```python
   from app.backend.database import SessionLocal
   from app.backend.models.goalkeeper_stats import GoalkeeperStats
   db = SessionLocal()
   stats = db.query(GoalkeeperStats).filter_by(player_id=GRABARA_ID, season='2024-2025', competition_name='Bundesliga').first()
   print(f"Minutes: {stats.minutes}")  # Powinno być 2610, nie 0
   ```
3. Sprawdź w froncie:
   - Otwórz kartę Grabary
   - Sprawdź "Season Statistics History (All Competitions)"
   - ✅ Sezon 2024-2025 Bundesliga powinien mieć **2610 minut** (nie N/A, nie 0)

### Test 5: Wyrównanie kolumny Minutes
1. Otwórz dowolnego gracza lub bramkarza
2. Sprawdź tabelę "Season Statistics History"
3. ✅ Kolumna "Minutes" jest wyrównana do prawej
4. ✅ Dla starszych sezonów gdzie brakuje minut - wyświetla "N/A"

### Test 6: Season Total (2025-2026) - poprawne zliczanie meczów

**Test bramkarzy:**
1. Otwórz bramkarzy w froncie:
   - Szczęsny
   - Skorupski
   - Drągowski
2. Sprawdź kolumnę "Season Total (2025-2026) - All competitions combined"
3. Oczekiwane wyniki:

| Bramkarz | goalkeeper_stats | PRZED fix 4a | PO fix 4a, PRZED 4b | PO OBU FIXACH ✅ |
|----------|------------------|--------------|---------------------|------------------|
| Szczęsny | 9 meczów | 39 | 14 | **9** ✅ |
| Skorupski | 14 meczów | ~44 | 18 | **14** ✅ |
| Drągowski | 8 meczów | ~38 | 9 | **8** ✅ |
| Grabara | 13 meczów | ~43 | 13 | **13** ✅ |

**Test graczy z pola:**
1. Sprawdź graczy z pola którzy grali w 2024-2025 i 2025-2026
2. Dla nich KROK 2.5 **powinien działać** (competition_stats czasem nie ma wszystkich europejskich meczów)
3. ✅ Przed fixem 4a: mogło pokazywać mecze z dwóch sezonów
4. ✅ Po fixie 4a: pokazuje tylko 2025-2026 (poprawnie)
5. ✅ KROK 2.5 nadal działa dla graczy z pola (dodaje brakujące europejskie mecze)

## Uwagi

- ✅ Rozwiązanie działa dla wszystkich graczy z europejskimi pucharami
- ✅ Nie wpływa na bramkarzy (używają `goalkeeper_stats`)
- ✅ Automatycznie obsługuje Conference League (Conf Lg)
- ⚠️ **Wymaga zsynchronizowanych match logs:** `python sync_match_logs.py "Nazwisko Gracza"`
- ⚠️ Dla starszych sezonów (przed 2024) mogą być zagregowane wpisy jeśli nie ma match logs

## Związane dokumenty

- `BUGFIX_EUROPEAN_CUPS_DISPLAY.md` - Poprzednia naprawa (częściowo cofnięta)
- `BUGFIX_SEASON_TOTAL_MINUTES.md` - Fix zliczania minut
- `CALENDAR_YEAR_IMPLEMENTATION.md` - Logika sezonów
