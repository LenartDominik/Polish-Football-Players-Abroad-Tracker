# Kolejność Synchronizacji Gracza (Który Jest Już w Bazie)

**Komenda:** `python sync_player.py "Nazwisko"`

**Typ:** Częściowa synchronizacja (tylko sezon 2025-2026)

---

## 📋 Szczegółowa kolejność kroków

### **KROK 1: Wyszukanie gracza na FBref** 🔍

```python
# Linia 529-542
fbref_id = player.get('fbref_id') or player.get('api_id')

if not use_search and fbref_id:
    # Opcja A: Użyj FBref ID (jeśli jest zapisany)
    player_data = await scraper.get_player_by_id(fbref_id, player_name)
else:
    # Opcja B: Wyszukaj po nazwisku
    player_data = await scraper.search_player(player_name)
```

**Co się dzieje:**
- ✅ Próba pobrania gracza przez FBref ID (szybsze)
- ✅ Jeśli brak ID lub nie znaleziono - wyszukiwanie po nazwisku
- ⏱️ Rate limit: 12 sekund między requestami

**Wynik:** Dane gracza z FBref (competition_stats dla wszystkich sezonów)

---

### **KROK 2: Aktualizacja informacji o graczu** 💾

```python
# Linia 548-562
db_player = db.query(Player).filter(Player.id == player['id']).first()

if player_data.get('player_id'):
    db_player.api_id = player_data['player_id']  # Zapisz FBref ID
    db_player.last_updated = date.today()         # Ustaw datę ostatniej aktualizacji
    db.commit()
```

**Co jest aktualizowane w tabeli `players`:**
- ✅ `api_id` (FBref ID) - jeśli wcześniej nie było
- ✅ `last_updated` - dzisiejsza data (2025-12-01)

**Nie jest aktualizowane:**
- ❌ `name` - zostaje bez zmian
- ❌ `team` - zostaje bez zmian
- ❌ `league` - zostaje bez zmian
- ❌ `position` - zostaje bez zmian

**Dlaczego?** Te dane są aktualizowane tylko przy dodawaniu nowego gracza.

---

### **KROK 3: Usunięcie starych danych sezonu 2025-2026** 🗑️

```python
# Linia 282-313 (save_competition_stats)
season_variants = ['2025-2026', '2025/2026', '2025', '2026']

# Usuń competition_stats dla sezonu 2025-2026
db.query(CompetitionStats).filter(
    CompetitionStats.player_id == player.id,
    CompetitionStats.season.in_(season_variants)
).delete()

# Usuń goalkeeper_stats dla sezonu 2025-2026
db.query(GoalkeeperStats).filter(
    GoalkeeperStats.player_id == player.id,
    GoalkeeperStats.season.in_(season_variants)
).delete()

db.flush()  # Flush session
```

**Co jest usuwane:**
- ✅ **Tylko rekordy sezonu 2025-2026** z `competition_stats`
- ✅ **Tylko rekordy sezonu 2025-2026** z `goalkeeper_stats`

**Co NIE jest usuwane:**
- ❌ Starsze sezony (2024-2025, 2023-2024, etc.) - **ZOSTAJĄ BEZ ZMIAN**
- ❌ `player_matches` - **zostają na razie** (usuną się później)

**Dlaczego delete przed insert?**
- Unika duplikatów
- Odświeża dane (FBref może zmienić liczbę meczów/goli)

---

### **KROK 4: Zapis nowych danych competition_stats** 💾

```python
# Linia 326-400 (save_competition_stats)
for stat_data in current_stats:
    if player.is_goalkeeper:
        # Bramkarz: zapisz do goalkeeper_stats
        gk_stat = GoalkeeperStats(
            player_id=player.id,
            season='2025-2026',
            competition_type='LEAGUE',  # lub EUROPEAN_CUP, DOMESTIC_CUP, NATIONAL_TEAM
            competition_name='La Liga',
            games=10,
            minutes=900,
            clean_sheets=3,
            saves=45,
            # etc.
        )
        db.add(gk_stat)
    else:
        # Zawodnik z pola: zapisz do competition_stats
        comp_stat = CompetitionStats(
            player_id=player.id,
            season='2025-2026',
            competition_type='LEAGUE',
            competition_name='La Liga',
            games=10,
            minutes=900,
            goals=5,
            assists=3,
            xg=4.5,
            xa=2.8,
            # etc.
        )
        db.add(comp_stat)
```

**Co jest zapisywane:**
- ✅ Wszystkie rozgrywki dla sezonu 2025-2026 z FBref
- ✅ Liga krajowa (LEAGUE)
- ✅ Puchary krajowe (DOMESTIC_CUP)
- ✅ Rozgrywki europejskie (EUROPEAN_CUP) - **JEŚLI FBref je zwraca**
- ✅ Reprezentacja (NATIONAL_TEAM)

**Uwaga:** FBref czasami nie zwraca wszystkich rozgrywek europejskich (np. Champions League może brakować w tabelach statystyk, ale jest w match logs).

---

### **KROK 5: Usunięcie starych match logs sezonu 2025-2026** 🗑️

```python
# Linia 432-436 (sync_match_logs_for_season)
season_start = date(2025, 7, 1)   # 1 lipca 2025
season_end = date(2026, 6, 30)     # 30 czerwca 2026

db.query(PlayerMatch).filter(
    PlayerMatch.player_id == player.id,
    PlayerMatch.match_date >= season_start,
    PlayerMatch.match_date <= season_end
).delete(synchronize_session='fetch')
```

**Co jest usuwane:**
- ✅ **Tylko mecze z przedziału 2025-07-01 do 2026-06-30**

**Co NIE jest usuwane:**
- ❌ Mecze z poprzednich sezonów - **ZOSTAJĄ BEZ ZMIAN**

---

### **KROK 6: Zapis nowych match logs** 💾

```python
# Linia 438-484 (sync_match_logs_for_season)
match_logs = await scraper.get_player_match_logs(fbref_id, player_name, '2025-2026')

for match_data in match_logs:
    match = PlayerMatch(
        player_id=player.id,
        match_date=datetime.strptime(match_data['match_date'], '%Y-%m-%d').date(),
        competition='La Liga',
        opponent='Real Madrid',
        result='W 2-1',
        minutes_played=90,
        goals=1,
        assists=0,
        xg=0.5,
        xa=0.2,
        shots=3,
        shots_on_target=2,
        # etc. - ~30 kolumn statystyk meczowych
    )
    db.add(match)
```

**Co jest zapisywane:**
- ✅ Wszystkie mecze sezonu 2025-2026 z FBref
- ✅ Liga krajowa
- ✅ Puchary krajowe
- ✅ Rozgrywki europejskie (Champions Lg, Europa Lg, Conference Lg)
- ✅ Reprezentacja (WCQ, Friendlies, etc.)

**Dane szczegółowe dla każdego meczu:**
- Data, rozgrywki, przeciwnik, wynik
- Minuty, gole, asysty
- xG, xA, strzały, podania
- Przechwyty, bloki, faule
- ~30 różnych statystyk

---

### **KROK 7: Naprawa brakujących minut** 🔧

```python
# Linia 593-594
if matches_saved > 0:
    fix_missing_minutes_from_matchlogs(db, db_player)
```

**Co robi funkcja `fix_missing_minutes_from_matchlogs`:**

```python
# Linia 98-244
# 1. Znajdź rekordy w competition_stats i goalkeeper_stats z 0 minut ale games > 0
comp_stats_to_fix = db.query(CompetitionStats).filter(
    CompetitionStats.player_id == player.id,
    CompetitionStats.minutes == 0,
    CompetitionStats.games > 0
).all()

# 2. Dla każdego rekordu:
for stat in comp_stats_to_fix:
    # 2a. Znajdź odpowiednie mecze w player_matches
    matches = db.query(PlayerMatch).filter(
        PlayerMatch.player_id == player.id,
        PlayerMatch.match_date >= season_start,
        PlayerMatch.match_date <= season_end,
        PlayerMatch.competition.ilike(f"%{stat.competition_name}%")
    ).all()
    
    # 2b. Zsumuj minuty z meczów
    total_minutes = sum(m.minutes_played or 0 for m in matches)
    
    # 2c. Zaktualizuj competition_stats
    if total_minutes > 0:
        stat.minutes = total_minutes
```

**Co jest naprawiane:**
- ✅ Rekordy w `competition_stats` gdzie `minutes = 0` ale `games > 0`
- ✅ Rekordy w `goalkeeper_stats` gdzie `minutes = 0` ale `games > 0`

**Skąd dane:** Z `player_matches` (zsumowane minuty z meczów)

**Uwaga:** To działa tylko dla sezonu 2025-2026 (bo tylko dla niego mamy match logs).

---

### **KROK 8: Commit do bazy danych** ✅

```python
# Linia 598
db.commit()
```

**Co zostaje zapisane:**
- ✅ Zaktualizowany rekord w `players` (last_updated, api_id)
- ✅ Nowe rekordy w `competition_stats` dla sezonu 2025-2026
- ✅ Nowe rekordy w `goalkeeper_stats` dla sezonu 2025-2026 (jeśli bramkarz)
- ✅ Nowe rekordy w `player_matches` dla sezonu 2025-2026
- ✅ Naprawione minuty w `competition_stats` i `goalkeeper_stats`

**Transakcja:** Atomowa - albo wszystko się zapisuje, albo nic (w razie błędu rollback).

---

## 📊 Podsumowanie w punktach

### Co jest aktualizowane:

| Tabela | Zakres | Operacja |
|--------|--------|----------|
| **players** | 1 rekord | UPDATE (last_updated, api_id) |
| **competition_stats** | Sezon 2025-2026 | DELETE → INSERT (odświeżenie) |
| **goalkeeper_stats** | Sezon 2025-2026 | DELETE → INSERT (odświeżenie) |
| **player_matches** | Sezon 2025-2026 | DELETE → INSERT (odświeżenie) |

### Co NIE jest zmieniane:

| Tabela | Zakres | Dlaczego |
|--------|--------|----------|
| **players** | name, team, league, position | Aktualizowane tylko przy dodawaniu gracza |
| **competition_stats** | Sezony 2024-2025 i starsze | Synchronizacja częściowa (tylko 2025-2026) |
| **goalkeeper_stats** | Sezony 2024-2025 i starsze | Synchronizacja częściowa (tylko 2025-2026) |
| **player_matches** | Sezony 2024-2025 i starsze | Match logs pobierane tylko dla bieżącego sezonu |

---

## ⏱️ Czas wykonania

| Krok | Czas |
|------|------|
| 1. Wyszukanie na FBref | ~3-5 sekund |
| 2. Aktualizacja players | ~0.1 sekund |
| 3. Usunięcie starych danych | ~0.2 sekund |
| 4. Zapis competition_stats | ~0.5 sekund |
| 5. Usunięcie starych match logs | ~0.2 sekund |
| 6. Pobranie match logs z FBref | ~5-8 sekund |
| 7. Zapis match logs | ~1-2 sekundy |
| 8. Naprawa minut | ~0.5 sekund |
| 9. Commit | ~0.1 sekund |
| **TOTAL** | **~15-20 sekund** |

**Rate limiting:** 12 sekund między graczami (ochrona przed zablokowaniem przez FBref)

---

## 🔄 Różnica: `sync_player.py` vs `sync_player_full.py`

### `sync_player.py` (domyślnie):
- ✅ Competition stats: wszystkie sezony z FBref
- ✅ Match logs: **TYLKO 2025-2026**
- ✅ Usuwa: tylko dane 2025-2026
- ✅ Starsze sezony: bez zmian

### `sync_player_full.py --all-seasons`:
- ✅ Competition stats: wszystkie sezony z FBref
- ✅ Match logs: **WSZYSTKIE sezony z FBref**
- ✅ Usuwa: **WSZYSTKIE dane gracza**
- ✅ Starsze sezony: odświeżone

---

## 🎯 Przykład: Robert Lewandowski

### Przed synchronizacją:
```
players: last_updated = 2025-11-20
competition_stats (2025-2026): 4 rekordy (Liga + Champions + Puchar + Repr.)
player_matches (2025-2026): 25 meczów
```

### Po synchronizacji:
```
players: last_updated = 2025-12-01  ← ZAKTUALIZOWANE
competition_stats (2025-2026): 4 rekordy (nowe liczby)  ← ODŚWIEŻONE
player_matches (2025-2026): 26 meczów (1 nowy)  ← ZAKTUALIZOWANE
```

### Co się nie zmieniło:
```
competition_stats (2024-2025): bez zmian
competition_stats (2023-2024): bez zmian
player_matches (2024-2025): bez zmian
```

---

## ✅ Bezpieczeństwo

### Transakcja atomowa:
```python
try:
    # Wszystkie operacje
    db.commit()  # ✅ Sukces - zapisz wszystko
except:
    db.rollback()  # ❌ Błąd - cofnij wszystko
```

### Ochrona przed duplikatami:
- ✅ DELETE przed INSERT
- ✅ Deduplikacja w kodzie (seen set)
- ✅ Unique constraint w bazie (player_id, match_date, competition, opponent)

### Ochrona przed utratą danych:
- ✅ Tylko sezon 2025-2026 jest usuwany
- ✅ Starsze sezony pozostają nietknięte
- ✅ Rollback w razie błędu

---

**Czy to wyjaśnia kolejność synchronizacji?** 🎯
