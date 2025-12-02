# FINALNA INSTRUKCJA - Poprawka Season Total

## ✅ Stan: Plik przywrócony do oryginalnego backupu (1273 linie)

## 🎯 CEL: 
Season Total ma sumować statystyki z 4 kolumn: League + European + Domestic + National

## 📝 INSTRUKCJA KROK PO KROKU:

### KROK 1: Otwórz plik w edytorze
`polish-players-tracker/app/frontend/streamlit_app.py`

---

### KROK 2: Dodaj funkcje helper (po linii 119)

**Znajdź linię 119-120:**
```python
    return yearly_stats

st.markdown("""
```

**Wklej MIĘDZY te linie (po `return yearly_stats`, przed `st.markdown`):**

```python

# Helper function to get European Cup stats from matches for current season
def get_european_stats_from_matches(player_id, matches_df, season='2025-2026'):
    """Get European Cup statistics from player_matches, grouped by competition"""
    if matches_df.empty:
        return pd.DataFrame()
    
    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists']
    if not all(col in matches_df.columns for col in required_columns):
        return pd.DataFrame()
    
    european_competitions = ['Champions Lg', 'Europa Lg', 'Conf Lg']
    
    euro_matches = matches_df[
        (matches_df['player_id'] == player_id) &
        (matches_df['competition'].isin(european_competitions)) &
        (matches_df['minutes_played'] > 0)
    ].copy()
    
    if euro_matches.empty:
        return pd.DataFrame()
    
    euro_matches['match_date'] = pd.to_datetime(euro_matches['match_date'], errors='coerce')
    euro_matches = euro_matches.dropna(subset=['match_date'])
    
    if season in ['2025-2026', '2025/2026']:
        season_start = pd.to_datetime('2025-07-01')
        season_end = pd.to_datetime('2026-06-30')
        euro_matches = euro_matches[
            (euro_matches['match_date'] >= season_start) &
            (euro_matches['match_date'] <= season_end)
        ]
    
    if euro_matches.empty:
        return pd.DataFrame()
    
    grouped = euro_matches.groupby('competition').agg({
        'match_date': 'count',
        'goals': 'sum',
        'assists': 'sum',
        'minutes_played': 'sum',
        'xg': 'sum' if 'xg' in euro_matches.columns else lambda x: 0,
        'xa': 'sum' if 'xa' in euro_matches.columns else lambda x: 0,
    }).reset_index()
    
    grouped.columns = ['competition_name', 'games', 'goals', 'assists', 'minutes', 'xg', 'xa']
    grouped['competition_type'] = 'EUROPEAN_CUP'
    
    return grouped
```

---

### KROK 3: Dodaj sekcję obliczającą statystyki (przed linią "col1, col2, col3, col4, col5 = st.columns")

**Znajdź linię ~238 (około):**
```python
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
```

**Wklej PRZED tą linią:**

```python
            # Oblicz statystyki RAZ dla wszystkich kolumn
            season_filter = ['2025-2026', '2025/2026']
            
            league_games = league_goals = league_assists = league_cs = league_ga = 0
            euro_games = euro_goals = euro_assists = euro_cs = euro_ga = 0
            domestic_games = domestic_goals = domestic_assists = domestic_cs = domestic_ga = 0
            national_games = national_goals = national_assists = national_cs = national_ga = 0
            
            # LEAGUE
            if is_gk and not gk_stats.empty:
                gk_l = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'LEAGUE')]
                if not gk_l.empty:
                    league_games, league_cs, league_ga = int(gk_l['games'].sum()), int(gk_l['clean_sheets'].sum()), int(gk_l['goals_against'].sum())
            elif not comp_stats.empty:
                c_l = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'LEAGUE')]
                if not c_l.empty:
                    league_games, league_goals, league_assists = int(c_l['games'].sum()), int(c_l['goals'].sum()), int(c_l['assists'].sum())
            
            # EUROPEAN
            euro_from_matches = get_european_stats_from_matches(row['id'], matches_df, season='2025-2026')
            if not euro_from_matches.empty:
                euro_games = int(euro_from_matches['games'].sum())
                if not is_gk:
                    euro_goals, euro_assists = int(euro_from_matches['goals'].sum()), int(euro_from_matches['assists'].sum())
            elif is_gk and not gk_stats.empty:
                gk_e = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'EUROPEAN_CUP')]
                if not gk_e.empty:
                    euro_games, euro_cs, euro_ga = int(gk_e['games'].sum()), int(gk_e['clean_sheets'].sum()), int(gk_e['goals_against'].sum())
            elif not comp_stats.empty:
                c_e = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'EUROPEAN_CUP')]
                if not c_e.empty:
                    euro_games, euro_goals, euro_assists = int(c_e['games'].sum()), int(c_e['goals'].sum()), int(c_e['assists'].sum())
            
            # DOMESTIC
            if is_gk and not gk_stats.empty:
                gk_d = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'DOMESTIC_CUP')]
                if not gk_d.empty:
                    domestic_games, domestic_cs, domestic_ga = int(gk_d['games'].sum()), int(gk_d['clean_sheets'].sum()), int(gk_d['goals_against'].sum())
            elif not comp_stats.empty:
                c_d = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'DOMESTIC_CUP')]
                if not c_d.empty:
                    domestic_games, domestic_goals, domestic_assists = int(c_d['games'].sum()), int(c_d['goals'].sum()), int(c_d['assists'].sum())
            
            # NATIONAL
            if is_gk and not gk_stats.empty:
                gk_n = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'NATIONAL_TEAM')]
                if not gk_n.empty:
                    national_games, national_cs, national_ga = int(gk_n['games'].sum()), int(gk_n['clean_sheets'].sum()), int(gk_n['goals_against'].sum())
            elif not comp_stats.empty:
                c_n = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'NATIONAL_TEAM')]
                if not c_n.empty:
                    national_games, national_goals, national_assists = int(c_n['games'].sum()), int(c_n['goals'].sum()), int(c_n['assists'].sum())
            
            # TOTAL (suma)
            total_games = league_games + euro_games + domestic_games + national_games
            total_goals = league_goals + euro_goals + domestic_goals + national_goals
            total_assists = league_assists + euro_assists + domestic_assists + national_assists
            total_cs = league_cs + euro_cs + domestic_cs + national_cs
            total_ga = league_ga + euro_ga + domestic_ga + national_ga
            
```

---

### KROK 4: Zmień Season Total (col5) - znajdź i zastąp

**Znajdź sekcję zaczynającą się od (około linia 720):**
```python
            with col5:
                # GÓRA: Statystyki w sztywnym pudełku
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 📊 Season Total (2025-2026)")
```

**Zastąp CAŁĄ zawartość `with col5:` (aż do linii przed `# TABELA STATYSTYK`) tym prostym kodem:**

```python
            with col5:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 📊 Season Total (2025-2026)")
                    st.caption("All competitions combined")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Games", total_games)
                    if is_gk:
                        m2.metric("CS", total_cs)
                        m3.metric("GA", total_ga)
                    else:
                        m2.metric("Goals", total_goals)
                        m3.metric("Assists", total_assists)
                
                with st.expander("📊 Details"):
                    st.write(f"🏆 League: {league_games} games")
                    st.write(f"🌍 European: {euro_games} games")
                    st.write(f"🏠 Domestic: {domestic_games} games")
                    st.write(f"🇵🇱 National: {national_games} games")
                    st.write("---")
                    if is_gk:
                        st.write(f"🥅 Total CS: {total_cs}")
                        st.write(f"⚽ Total GA: {total_ga}")
                    else:
                        st.write(f"🎯 Total Goals: {total_goals}")
                        st.write(f"🅰️ Total Assists: {total_assists}")
```

---

## ✅ GOTOWE!

Zapisz plik, zrestartuj Streamlit i przetestuj.

Season Total = League + European + Domestic + National (obliczone raz, używane wszędzie)