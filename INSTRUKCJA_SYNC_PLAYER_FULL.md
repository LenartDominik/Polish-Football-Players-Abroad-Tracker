# Instrukcja: sync_player_full.py

## Co robi ten skrypt?

Nowy skrypt `sync_player_full.py` synchronizuje **kompletne dane gracza**:

1. **Competition Stats** (statystyki sezonowe) - rozgrywki według typu:
   - League (liga krajowa)
   - Domestic Cups (puchary krajowe)
   - European Cups (rozgrywki europejskie)
   - **National Team** (reprezentacja) - z podziałem na lata kalendarzowe i typy rozgrywek

2. **Match Logs** (szczegółowe statystyki meczowe) - mecz po meczu dla wybranych sezonów

## Użycie

### Podstawowe komendy

```powershell
# Synchronizacja wybranych sezonów (np. ostatnie 2-3 sezony)
python sync_player_full.py "Kamil Grabara" --seasons 2024-2025 2025-2026

# Synchronizacja WSZYSTKICH sezonów z całej kariery
python sync_player_full.py "Kamil Grabara" --all-seasons

# Tylko aktualny sezon 2025-2026 (domyślnie)
python sync_player_full.py "Kamil Grabara"
```

### Parametry

- `player_name` - nazwa gracza (wymagane)
- `--seasons` - lista sezonów do synchronizacji match logs (opcjonalnie)
- `--all-seasons` - synchronizuj match logs ze WSZYSTKICH sezonów kariery (opcjonalnie)

## Przykłady użycia

### 1. Grabara - pełna kariera

```powershell
python sync_player_full.py "Grabara" --all-seasons
```

**Rezultat:**
- Competition stats ze wszystkich sezonów (2016-2026)
- Match logs ze wszystkich sezonów (setki meczów)
- Dane National Team z różnych lat (2022, 2022-2023, 2025, 2026)

**Czas:** ~3-5 minut (10+ sezonów × 12s rate limit)

### 2. Lewandowski - ostatnie 3 sezony

```powershell
python sync_player_full.py "Lewandowski" --seasons 2023-2024 2024-2025 2025-2026
```

**Rezultat:**
- Competition stats ze wszystkich sezonów kariery
- Match logs tylko z ostatnich 3 sezonów

**Czas:** ~1 minuta

### 3. Szybka aktualizacja - tylko aktualny sezon

```powershell
python sync_player_full.py "Zieliński"
```

**Rezultat:**
- Competition stats ze wszystkich sezonów
- Match logs tylko z sezonu 2025-2026

**Czas:** ~30 sekund

## Co się dzieje po wykonaniu?

### 1. Competition Stats zapisane w bazie

Tabela `goalkeeper_stats` (dla bramkarzy) lub `competition_stats` (dla graczy z pola):
- Każdy sezon × każdy typ rozgrywek = osobny wiersz
- National Team może mieć wiele wpisów (np. 2025 Friendlies, 2026 WCQ)

### 2. Match Logs zapisane w bazie

Tabela `player_matches`:
- Każdy mecz = osobny wiersz
- Zawiera szczegóły: data, przeciwnik, wynik, minuty, gole, asysty, xG, xa, etc.

## Frontend - jak to wygląda?

Po synchronizacji, na Streamlit frontend:

### Kolumna "National Team 2025"
Teraz pokazuje zagregowane dane z:
- `2025` | Friendlies (M) 
- `2026` | WCQ

**Dla Grabary:**
- Caps: 2
- CS: 1
- GA: 1

### Zakładka "Match Logs"
Po kliknięciu w gracza, pokazuje tabelę ze wszystkimi meczami:
- Filtrowanie po sezonie
- Filtrowanie po rozgrywkach
- Szczegółowe statystyki każdego meczu

## Synchronizacja wielu graczy

Przykładowy skrypt PowerShell:

```powershell
# sync_all_key_players.ps1
$players = @(
    "Lewandowski",
    "Zieliński", 
    "Szczęsny",
    "Grabara",
    "Cash",
    "Zalewski"
)

foreach ($player in $players) {
    Write-Host "=== Syncing $player ===" -ForegroundColor Green
    python sync_player_full.py $player --seasons 2024-2025 2025-2026
    Start-Sleep -Seconds 15  # Rate limiting - czekaj 15s między graczami
}

Write-Host "`n=== All players synced! ===" -ForegroundColor Green
```

## Troubleshooting

### Problem: "Player not found"
**Rozwiązanie:** Upewnij się, że gracz istnieje w bazie. Sprawdź dokładną pisownię:
```powershell
python quick_add_player.py  # Dodaj gracza najpierw
```

### Problem: "No FBref ID"
**Rozwiązanie:** Gracz nie ma przypisanego FBref ID. Użyj:
```powershell
python add_fbref_ids.py
```

### Problem: "No match logs found for season"
**Rozwiązanie:** FBref może nie mieć match logs dla starszych sezonów lub młodzieżówek. To normalne.

### Problem: Bardzo długi czas wykonania
**Rozwiązanie:** 
- Użyj `--seasons` zamiast `--all-seasons`
- Synchronizuj tylko ostatnie 2-3 sezony
- Rate limit (12s) jest wymagany przez FBref

## Różnice vs stary sync_match_logs.py

| Funkcja | sync_match_logs.py | sync_player_full.py |
|---------|-------------------|---------------------|
| Competition stats | ❌ Nie | ✅ Tak |
| Match logs | ✅ Tak (1 sezon) | ✅ Tak (wiele sezonów) |
| National Team | ❌ Brak wsparcia | ✅ Pełne wsparcie |
| Goalkeeper stats | ⚠️ Częściowe | ✅ Pełne |
| Wszystkie sezony | ❌ Nie | ✅ Tak (--all-seasons) |
| Wybrane sezony | ❌ Nie | ✅ Tak (--seasons) |

## Zalecenia

1. **Dla nowych graczy**: Użyj `--all-seasons` raz, aby pobrać pełną historię
2. **Regularna aktualizacja**: Użyj `--seasons 2024-2025 2025-2026` co tydzień
3. **Przed ważnym meczem**: Szybka aktualizacja bez parametrów (tylko 2025-2026)
4. **Batch sync**: Użyj skryptu PowerShell do synchronizacji wielu graczy naraz

## Uwagi techniczne

- **Rate limiting**: 12 sekund między requestami do FBref (obowiązkowe)
- **Playwright**: Używa prawdziwej przeglądarki do obejścia anti-bot protection
- **Database**: Automatyczne usuwanie starych danych przed zapisem nowych
- **Error handling**: Kontynuuje przy błędach, loguje wszystko
