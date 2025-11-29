# 📋 TODO: FBref Scraper - Playing Time & Shots Support

**Data utworzenia:** 2025-01-XX  
**Priorytet:** Średni  
**Szacowany czas:** 2-3 godziny

---

## 🎯 Cel

Dodać pełną obsługę tabel **Playing Time** i **Shots** z FBref, aby automatycznie scrapować:
- ✅ **Minutes** (minuty gry) - obecnie brak dla lig
- ✅ **Shots** i **Shots on Target** - obecnie brak dla wszystkich

---

## 📊 Problem

### Obecna sytuacja:
- ❌ **Minuty** dla LEAGUE: 68.7% rekordów ma `minutes = 0`
- ❌ **Shots**: 100% rekordów ma `shots = 0`
- ✅ **Minuty** dla CUPS/National Team: Działają (są w tabeli Standard Stats)

### Dlaczego nie działa?

**FBref ma dane w oddzielnych tabelach:**

1. **Standard Stats** (`stats_standard_dom_lg`):
   - ✅ games, goals, assists, xG, xA, yellow_cards, red_cards
   - ❌ **NIE MA: minutes** (dla lig)

2. **Playing Time** (`stats_playing_time_dom_lg`):
   - ✅ **minutes, games_starts, minutes_per_game**
   - Tylko na stronie głównej gracza (nie w `/all_comps/`)

3. **Shooting** (`stats_shooting_dom_lg`):
   - ✅ **shots, shots_on_target, shot_accuracy**
   - Scraper parsuje xG ale ignoruje shots

**Scraper pobiera z `/all_comps/`** → nie ma tam Playing Time!

---

## ✅ Rozwiązanie (3 kroki)

### KROK 1: Dodać funkcję `_parse_playing_time_table()`

**Plik:** `app/backend/services/fbref_playwright_scraper.py`  
**Gdzie:** Po funkcji `_parse_shooting_table()` (~linia 826)

```python
def _parse_playing_time_table(self, table) -> List[Dict]:
    """
    Parse Playing Time stats table (minutes) from FBref
    This is needed because minutes are NOT in the Standard Stats table for leagues
    """
    playing_time_stats = []
    
    tbody = table.find('tbody')
    if not tbody:
        return playing_time_stats
    
    rows = tbody.find_all('tr')
    
    for row in rows:
        # Skip header rows
        if row.get('class') and 'thead' in row.get('class'):
            continue
        
        stat = {}
        
        # Season
        season_cell = row.find('th', {'data-stat': 'season'})
        if not season_cell:
            season_cell = row.find('th')
        if season_cell:
            season_text = season_cell.get_text(strip=True)
            season_link = season_cell.find('a')
            if season_link:
                season_text = season_link.get_text(strip=True)
            stat['season'] = season_text
        
        # Competition name
        comp_cell = row.find('td', {'data-stat': 'comp_level'})
        if not comp_cell:
            comp_cell = row.find('td', {'data-stat': 'comp_name'})
        if not comp_cell:
            all_tds = row.find_all('td')
            if len(all_tds) >= 2:
                comp_cell = all_tds[1]
        if comp_cell:
            comp_text = comp_cell.get_text(strip=True)
            comp_link = comp_cell.find('a')
            if comp_link:
                comp_text = comp_link.get_text(strip=True)
            stat['competition_name'] = comp_text
        
        # Minutes played - THE MAIN DATA WE NEED
        minutes_cell = row.find('td', {'data-stat': 'minutes'})
        if minutes_cell:
            minutes_val = self._parse_int(minutes_cell.get_text(strip=True))
            if minutes_val is not None and minutes_val > 0:
                stat['minutes'] = minutes_val
        
        # Games starts (bonus data)
        starts_cell = row.find('td', {'data-stat': 'games_starts'})
        if starts_cell:
            starts_val = self._parse_int(starts_cell.get_text(strip=True))
            if starts_val is not None:
                stat['games_starts'] = starts_val
        
        # Only add if we have season, competition, and minutes
        if stat.get('season') and stat.get('competition_name') and 'minutes' in stat:
            playing_time_stats.append(stat)
    
    logger.info(f"📊 Parsed {len(playing_time_stats)} Playing Time stat rows")
    return playing_time_stats
```

---

### KROK 2: Zmodyfikować `_parse_player_page()` 

**Problem:** Obecnie scraper pobiera tylko z `/all_comps/` (linia 252)  
**Rozwiązanie:** Pobierać TAKŻE ze strony głównej gracza

**Plik:** `app/backend/services/fbref_playwright_scraper.py`  
**Funkcja:** `_parse_player_page()` (~linia 226)

**Zmiana:**

```python
async def _parse_player_page(self, soup: BeautifulSoup, url: str) -> Dict:
    """Parse player page and extract data"""
    
    player_data = {
        'url': url,
        'name': None,
        'competition_stats': []
    }
    
    # Extract player ID from URL
    player_id = None
    if '/players/' in url:
        parts = url.split('/players/')
        if len(parts) > 1:
            player_id = parts[1].split('/')[0]
            player_data['player_id'] = player_id
    
    # Get player name
    name_elem = soup.find('h1')
    if name_elem:
        player_data['name'] = name_elem.get_text(strip=True)
    
    if player_id:
        logger.info(f"📊 Fetching complete stats from /all_comps/ page...")
        all_comps_soup = await self._fetch_all_comps_page(player_id)
        
        # NOWE: Pobierz też stronę główną dla Playing Time
        logger.info(f"📊 Fetching Playing Time from main page...")
        main_page_soup = soup  # Już mamy główną stronę
        
        if all_comps_soup:
            player_data['competition_stats'] = self._parse_competition_stats(
                all_comps_soup, 
                main_page_soup=main_page_soup  # NOWY PARAMETR
            )
        else:
            logger.warning("⚠️ Could not fetch /all_comps/, using current page")
            player_data['competition_stats'] = self._parse_competition_stats(soup)
    else:
        player_data['competition_stats'] = self._parse_competition_stats(soup)
    
    return player_data
```

---

### KROK 3: Zmodyfikować `_parse_competition_stats()`

**Dodać wywołania Playing Time dla każdego typu rozgrywek**

**Plik:** `app/backend/services/fbref_playwright_scraper.py`  
**Funkcja:** `_parse_competition_stats()` (~linia 268)

**Zmiany w 4 miejscach:**

#### 3.1 Domestic League (~linia 322)

```python
# PRZED:
competition_stats.extend(league_stats)

# DODAJ PRZED TĄ LINIĄ:
# Get Playing Time for minutes (DOMESTIC LEAGUE)
if main_page_soup:  # Only if we have main page
    pt_table = main_page_soup.find('table', {'id': 'stats_playing_time_dom_lg'})
    if not pt_table:
        pt_table = find_table_in_comments('stats_playing_time_dom_lg')
    if pt_table:
        logger.info("✅ Found Playing Time table for domestic league")
        pt_stats = self._parse_playing_time_table(pt_table)
        league_stats = self._merge_expected_stats(league_stats, pt_stats)
    else:
        logger.warning("⚠️ Playing Time table NOT FOUND for domestic league")

competition_stats.extend(league_stats)
```

#### 3.2 Domestic Cups (~linia 350)

```python
# Get Playing Time for minutes (DOMESTIC CUPS)
if main_page_soup:
    pt_dom_cup = main_page_soup.find('table', {'id': 'stats_playing_time_dom_cup'})
    if not pt_dom_cup:
        pt_dom_cup = find_table_in_comments('stats_playing_time_dom_cup')
    if pt_dom_cup:
        logger.info("✅ Found Playing Time table for domestic cups")
        pt_stats = self._parse_playing_time_table(pt_dom_cup)
        dom_cup_stats = self._merge_expected_stats(dom_cup_stats, pt_stats)

competition_stats.extend(dom_cup_stats)
```

#### 3.3 International Cups (~linia 376)

```python
# Get Playing Time for minutes (INTERNATIONAL CUPS)
if main_page_soup:
    pt_intl_cup = main_page_soup.find('table', {'id': 'stats_playing_time_intl_cup'})
    if not pt_intl_cup:
        pt_intl_cup = find_table_in_comments('stats_playing_time_intl_cup')
    if pt_intl_cup:
        logger.info("✅ Found Playing Time table for international cups")
        pt_stats = self._parse_playing_time_table(pt_intl_cup)
        intl_cup_stats = self._merge_expected_stats(intl_cup_stats, pt_stats)

competition_stats.extend(intl_cup_stats)
```

#### 3.4 National Team (~linia 431)

```python
if nat_tm_table:
    nat_tm_stats = self._parse_stats_table(nat_tm_table, 'NATIONAL_TEAM')
    
    # Get Playing Time for minutes (NATIONAL TEAM)
    if main_page_soup:
        pt_nat_tm = main_page_soup.find('table', {'id': 'stats_playing_time_nat_tm'})
        if not pt_nat_tm:
            pt_nat_tm = find_table_in_comments('stats_playing_time_nat_tm')
        if pt_nat_tm:
            logger.info("✅ Found Playing Time table for national team")
            pt_stats = self._parse_playing_time_table(pt_nat_tm)
            nat_tm_stats = self._merge_expected_stats(nat_tm_stats, pt_stats)
    
    competition_stats.extend(nat_tm_stats)
```

---

### KROK 4 (BONUS): Dodać obsługę Shots

**W funkcji `_parse_shooting_table()`** (~linia 762) już parsujemy `xG` i `npxG`.

**Dodaj także shots:**

```python
# ZNAJDŹ W _parse_shooting_table():
# xG (from shooting table)
xg_cell = row.find('td', {'data-stat': 'xg'})
if xg_cell:
    xg_val = self._parse_float(xg_cell.get_text(strip=True))
    if xg_val is not None and xg_val > 0:
        stat['xg'] = xg_val

# DODAJ PO TYM:
# Shots (from shooting table)
shots_cell = row.find('td', {'data-stat': 'shots'})
if shots_cell:
    shots_val = self._parse_int(shots_cell.get_text(strip=True))
    if shots_val is not None and shots_val > 0:
        stat['shots'] = shots_val

# Shots on target (from shooting table)
sot_cell = row.find('td', {'data-stat': 'shots_on_target'})
if sot_cell:
    sot_val = self._parse_int(sot_cell.get_text(strip=True))
    if sot_val is not None and sot_val > 0:
        stat['shots_on_target'] = sot_val
```

---

## 🧪 Testowanie

### Test 1: Lokalne testowanie funkcji

```python
# tmp_test_playing_time.py
import asyncio
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper

async def test():
    async with FBrefPlaywrightScraper(headless=True) as scraper:
        # Test na Matty Cash
        player_data = await scraper.get_player_by_id("2389cdc2", "Matty Cash")
        
        # Sprawdź minuty
        for stat in player_data['competition_stats']:
            if stat.get('season') == '2025-2026' and stat.get('competition_type') == 'LEAGUE':
                print(f"Minutes: {stat.get('minutes')}")  # Powinno być > 0
                assert stat.get('minutes', 0) > 0, "Minutes should be scraped!"

asyncio.run(test())
```

### Test 2: Re-scrapowanie 1 gracza

```bash
python sync_player_full.py
# Wybierz Matty Cash
# Sprawdź w bazie czy minutes > 0
```

### Test 3: Sprawdź bazę

```sql
SELECT id, name, season, competition_type, games, minutes, shots
FROM competition_stats
WHERE player_id = 2  -- Matty Cash
  AND competition_type = 'LEAGUE'
  AND season = '2025-2026'
```

Oczekiwane: `minutes > 0`, `shots > 0`

---

## 📦 Re-scrapowanie Wszystkich Graczy

**Po zakończeniu zmian:**

```bash
# Backup bazy przed re-scrapem!
python tools/backup_database.py

# Re-scrapuj wszystkich
python sync_all_playwright.py

# Sprawdź wyniki
python tools/check_minutes_coverage.py
```

**Oczekiwane rezultaty:**
- ✅ 100% graczy ma minuty dla lig (obecnie 31%)
- ✅ 100% graczy ma shots (obecnie 0%)

---

## 📝 Checklist Implementacji

- [ ] **KROK 1:** Dodać `_parse_playing_time_table()`
- [ ] **KROK 2:** Zmodyfikować `_parse_player_page()` (main_page_soup)
- [ ] **KROK 3:** Zmodyfikować `_parse_competition_stats()` (4 miejsca)
- [ ] **KROK 4:** Dodać shots w `_parse_shooting_table()`
- [ ] **TEST 1:** Testować funkcję lokalnie
- [ ] **TEST 2:** Re-scrapować 1 gracza (Matty Cash)
- [ ] **TEST 3:** Sprawdzić bazę (SQL)
- [ ] **Backup:** Zrobić backup bazy
- [ ] **Re-scrape:** Re-scrapować wszystkich graczy
- [ ] **Verify:** Sprawdzić coverage minut i shots
- [ ] **Update:** Zaktualizować frontend (odznacz shots/minutes)
- [ ] **Docs:** Zaktualizować dokumentację

---

## 🚨 Ostrzeżenia

1. **Backup przed re-scrapem!**
   - Re-scrapowanie nadpisze wszystkie dane
   - Ręczne poprawki (np. Cash: 1056 minut) zostaną nadpisane
   - Ale potem będą automatycznie zaktualizowane z FBref

2. **Rate Limit:**
   - Re-scrapowanie 9 graczy = ~2 minuty (12s rate limit)
   - Nie przerywaj procesu

3. **Testing:**
   - Testuj na 1 graczu PRZED re-scrapem wszystkich

---

## 💡 Alternatywne Rozwiązania

### Rozwiązanie A: Pozostaw ręczne poprawki (OBECNE)
- ✅ Szybkie
- ❌ Wymaga ręcznej pracy przy nowych graczach

### Rozwiązanie B: Zmodyfikuj scraper (TO TODO)
- ✅ Automatyczne dla wszystkich
- ❌ 2-3h pracy + testowanie

### Rozwiązanie C: Dual-source scraping
- Pobieraj Standard Stats z `/all_comps/`
- Pobieraj Playing Time ze strony głównej
- Merguj dane
- ✅ Najlepsze rozwiązanie
- ⏱️ 2-3h implementacji

**Rekomendacja:** Rozwiązanie C (opisane w tym TODO)

---

## 📚 Dokumentacja

Po implementacji zaktualizuj:
- `HOW_TO_SYNC_DATA.md` - nowe możliwości scrapera
- `INSTRUKCJA_SYNC_PLAYER_FULL.md` - minuty są teraz automatyczne
- `README.md` - feature: automatyczne minuty i shots

---

## ✅ Sukces!

Po zakończeniu tego TODO:
- ✅ Minuty będą automatycznie scrapowane dla wszystkich
- ✅ Shots będą automatycznie scrapowane
- ✅ G+A/90 będzie działać dla wszystkich graczy
- ✅ Nie będzie potrzeby ręcznych poprawek
- ✅ Frontend będzie pokazywał shots (nie N/A)

---

**Autor:** AI Assistant  
**Data:** 2025-01-XX  
**Status:** TODO  
**Priorytet:** Średni  
**Szacowany czas:** 2-3 godziny
