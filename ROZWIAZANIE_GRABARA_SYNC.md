# Rozwiązanie: Synchronizacja National Team 2025 dla Grabary i Match Logs

## Problem

1. **National Team 2025 nie pokazuje się na frontend** - kolumna była pusta z komunikatem "No national team stats for 2025"
2. **Match logs pokazują tylko sezon 2025-26** - brak danych z poprzednich sezonów i brak meczów reprezentacyjnych

## Przyczyna

1. **Dane National Team ISTNIEJĄ** w FBref:
   - `2025` | Friendlies (M) | 1 mecz | 45 minut | 0 GA | 1 CS
   - `2026` | WCQ | 1 mecz | 90 minut | 1 GA | 0 CS | 2 saves

2. Problem był w **braku synchronizacji**:
   - Stary skrypt `sync_match_logs.py` synchronizował tylko jeden sezon (domyślnie 2025-2026)
   - Nie było opcji synchronizacji wszystkich sezonów z całej kariery
   - Brak mechanizmu do pobierania statystyk reprezentacyjnych z różnych lat kalendarzowych

## Rozwiązanie

### 1. Nowy skrypt: `sync_player_full.py`

Stworzony nowy skrypt do pełnej synchronizacji gracza:

```bash
# Synchronizacja wybranych sezonów
python sync_player_full.py "Grabara" --seasons 2024-2025 2025-2026

# Synchronizacja WSZYSTKICH sezonów z kariery
python sync_player_full.py "Grabara" --all-seasons

# Tylko aktualny sezon (domyślnie)
python sync_player_full.py "Grabara"
```

**Funkcjonalność:**
- ✅ Pobiera **competition stats** (season-by-season) - zawiera National Team z różnych lat
- ✅ Pobiera **match logs** (match-by-match) dla wybranych sezonów
- ✅ Obsługuje zarówno bramkarzy (goalkeeper stats) jak i graczy z pola
- ✅ Wspiera synchronizację wszystkich sezonów z kariery (`--all-seasons`)

### 2. Naprawione mapowanie pól dla GoalkeeperStats

Model `GoalkeeperStats` używa innych nazw pól niż scraper:
- `save_pct` → `save_percentage`
- `clean_sheets_pct` → `clean_sheet_percentage`
- `pens_att` → `penalties_attempted`
- `pens_allowed` → `penalties_allowed`
- `pens_saved` → `penalties_saved`
- `pens_missed` → `penalties_missed`
- `psxg` → `post_shot_xg`

## Jak używać

### Dla Grabary (wszystkie sezony):

```powershell
cd polish-players-tracker
python sync_player_full.py "Grabara" --all-seasons
```

To pobierze:
- Wszystkie statystyki sezonowe (League, Domestic Cups, European Cups, National Team)
- Match logs ze WSZYSTKICH sezonów kariery (2016-2017 do 2025-2026)

### Dla innego gracza (wybrane sezony):

```powershell
python sync_player_full.py "Lewandowski" --seasons 2023-2024 2024-2025 2025-2026
```

### Automatyczna synchronizacja wszystkich graczy:

Można stworzyć skrypt batch który synchronizuje wszystkich:

```powershell
# sync_all_players_full.ps1
$players = @("Lewandowski", "Grabara", "Zieliński", "Szczęsny")

foreach ($player in $players) {
    Write-Host "Syncing $player..."
    python sync_player_full.py $player --seasons 2024-2025 2025-2026
    Start-Sleep -Seconds 15  # Rate limiting
}
```

## Weryfikacja

Po uruchomieniu dla Grabary:
- ✅ **24 competition stats** zapisane (w tym National Team 2025 i 2026)
- ✅ **50 match logs** z sezonów 2024-2025 i 2025-2026

Frontend powinien teraz pokazywać:
- 🇵🇱 **National Team (2025)**: 2 mecze (Friendlies + WCQ), 135 minut, 1 GA, 1 CS

## Match Logs - Historia całej kariery

Aby mieć **pełną historię matchlogów** ze wszystkich sezonów:

```powershell
python sync_player_full.py "Grabara" --all-seasons
```

To pobierze szczegółowe match-by-match dane z:
- 2016-2017 (Liverpool U23)
- 2017-2018 (Liverpool U23)
- 2018-2019 (AGF + Liverpool U23)
- 2019-2020 (Huddersfield)
- 2020-2021 (AGF)
- 2021-2022 (FC Copenhagen)
- 2022-2023 (FC Copenhagen + Poland NT)
- 2023-2024 (FC Copenhagen)
- 2024-2025 (Wolfsburg + Poland NT)
- 2025-2026 (Wolfsburg + Poland NT)

## Uwagi

1. **Rate limiting**: Skrypt respektuje 12-sekundowy limit między requestami do FBref
2. **Czas wykonania**: Synchronizacja wszystkich sezonów (~10 sezonów) zajmuje ~2-3 minuty
3. **National Team**: Dane reprezentacyjne są teraz poprawnie zapisywane z osobnymi wpisami dla każdego roku kalendarzowego (2025, 2026) i typu rozgrywek (Friendlies, WCQ, Nations League)
