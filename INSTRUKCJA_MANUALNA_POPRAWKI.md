# Instrukcja ręcznej poprawki Season Total

## ✅ KROK 1 - WYKONANY
Funkcje helper zostały już dodane automatycznie.

## 🔧 KROK 2 - DO WYKONANIA RĘCZNIE

### Lokalizacja: Znajdź sekcję "Season Total" (około linii 820-900)

Szukaj fragmentu który zaczyna się od:
```python
            with col5:
                # GÓRA: Statystyki w sztywnym pudełku
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 📊 Season Total (2025-2026)")
```

### Zastąp całą zawartość `with col5:` (od linii z `with col5:` do linii przed `# TABELA STATYSTYK`) tym kodem:

```python
            with col5:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 📊 Season Total (2025-2026)")
                    st.caption("All competitions combined")

                    total_games, total_minutes = 0, 0
                    total_goals, total_assists = 0, 0
                    total_clean_sheets, total_ga = 0, 0
                    season_filter = ['2025-2026', '2025/2026']

                    # 1. LEAGUE
                    if is_gk and not gk_stats.empty:
                        gk_league = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'LEAGUE')]
                        if not gk_league.empty:
                            total_games += int(gk_league['games'].sum())
                            total_minutes += int(gk_league['minutes'].sum())
                            total_clean_sheets += int(gk_league['clean_sheets'].sum())
                            total_ga += int(gk_league['goals_against'].sum())
                    elif not comp_stats.empty:
                        comp_league = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'LEAGUE')]
                        if not comp_league.empty:
                            total_games += int(comp_league['games'].sum())
                            total_minutes += int(comp_league['minutes'].sum())
                            total_goals += int(comp_league['goals'].sum())
                            total_assists += int(comp_league['assists'].sum())

                    # 2. EUROPEAN CUPS
                    euro_from_matches = get_european_stats_from_matches(row['id'], matches_df, season='2025-2026')
                    if not euro_from_matches.empty:
                        total_games += int(euro_from_matches['games'].sum())
                        total_minutes += int(euro_from_matches['minutes'].sum())
                        if not is_gk:
                            total_goals += int(euro_from_matches['goals'].sum())
                            total_assists += int(euro_from_matches['assists'].sum())
                    elif is_gk and not gk_stats.empty:
                        gk_euro = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'EUROPEAN_CUP')]
                        if not gk_euro.empty:
                            total_games += int(gk_euro['games'].sum())
                            total_minutes += int(gk_euro['minutes'].sum())
                            total_clean_sheets += int(gk_euro['clean_sheets'].sum())
                            total_ga += int(gk_euro['goals_against'].sum())
                    elif not comp_stats.empty:
                        comp_euro = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'EUROPEAN_CUP')]
                        if not comp_euro.empty:
                            total_games += int(comp_euro['games'].sum())
                            total_minutes += int(comp_euro['minutes'].sum())
                            total_goals += int(comp_euro['goals'].sum())
                            total_assists += int(comp_euro['assists'].sum())

                    # 3. DOMESTIC CUPS
                    if is_gk and not gk_stats.empty:
                        gk_domestic = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'DOMESTIC_CUP')]
                        if not gk_domestic.empty:
                            total_games += int(gk_domestic['games'].sum())
                            total_minutes += int(gk_domestic['minutes'].sum())
                            total_clean_sheets += int(gk_domestic['clean_sheets'].sum())
                            total_ga += int(gk_domestic['goals_against'].sum())
                    elif not comp_stats.empty:
                        comp_domestic = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'DOMESTIC_CUP')]
                        if not comp_domestic.empty:
                            total_games += int(comp_domestic['games'].sum())
                            total_minutes += int(comp_domestic['minutes'].sum())
                            total_goals += int(comp_domestic['goals'].sum())
                            total_assists += int(comp_domestic['assists'].sum())

                    # 4. NATIONAL TEAM
                    if is_gk and not gk_stats.empty:
                        gk_national = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'NATIONAL_TEAM')]
                        if not gk_national.empty:
                            total_games += int(gk_national['games'].sum())
                            total_minutes += int(gk_national['minutes'].sum())
                            total_clean_sheets += int(gk_national['clean_sheets'].sum())
                            total_ga += int(gk_national['goals_against'].sum())
                    elif not comp_stats.empty:
                        comp_national = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'NATIONAL_TEAM')]
                        if not comp_national.empty:
                            total_games += int(comp_national['games'].sum())
                            total_minutes += int(comp_national['minutes'].sum())
                            total_goals += int(comp_national['goals'].sum())
                            total_assists += int(comp_national['assists'].sum())

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Games", total_games)
                    if is_gk:
                        m2.metric("CS", total_clean_sheets)
                        m3.metric("GA", total_ga)
                    else:
                        m2.metric("Goals", total_goals)
                        m3.metric("Assists", total_assists)
                
                with st.expander("📊 Details"):
                    if is_gk:
                        st.write(f"⚽ **Games:** {total_games}")
                        st.write(f"⏱️ **Minutes:** {total_minutes:,}")
                        st.write(f"🥅 **Clean Sheets:** {total_clean_sheets}")
                        st.write(f"⚽ **Goals Against:** {total_ga}")
                    else:
                        st.write(f"⚽ **Total Games:** {total_games}")
                        st.write(f"⏱️ **Total Minutes:** {total_minutes:,}")
                        st.write(f"🎯 **Total Goals:** {total_goals}")
                        st.write(f"🅰️ **Total Assists:** {total_assists}")
```

### KLUCZOWE:
- Season Total teraz sumuje **DOKŁADNIE** z tych samych źródeł co kolumny 1-4
- League + European + Domestic + National = Season Total
- Filtr sezonu: `['2025-2026', '2025/2026']` (bez pojedynczych lat)

## 📝 Po edycji:
1. Zapisz plik
2. Zrestartuj Streamlit
3. Sprawdź Szymańskiego, Świderskiego, Zalewskiego

## ✅ Weryfikacja:
Season Total powinien pokazywać **sumę** z 4 kolumn przed nim.