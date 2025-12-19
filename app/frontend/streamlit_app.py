"""Polish Players Tracker International - Streamlit Dashboard
A simple dashboard to browse and filter Polish football players data.
Usage:
    streamlit run app/frontend/streamlit_app.py
"""
import streamlit as st
import pandas as pd
# # import sqlite3  # REMOVED - using API now  # REMOVED - using API now
from pathlib import Path
from api_client import get_api_client


# --- FUNKCJA POMOCNICZA DO NAPRAWY BŁĘDU NAN (CRITICAL FIX) ---
def safe_int(value):
    """
    Pancerna konwersja do int. 
    Obsługuje: NaN, None, pusty string, float, a nawet błędy.
    """
    if value is None:
        return 0
    if pd.isna(value) or value == '':
        return 0
    try:
        # Najpierw na float (obsługa "5.0"), potem na int
        return int(float(value))
    except (ValueError, TypeError, OverflowError):
        return 0
# --------------------------------------------------------------


def get_season_filters(season_str='2025-2026'):
    """
    Zwraca listę możliwych formatów sezonu dla filtrowania.
    Uwzględnia:
    - Sezon klubowy (2025-2026, 2025/2026)
    - Rok kalendarzowy dla reprezentacji (2025, 2026)
    
    Args:
        season_str: Nazwa sezonu (np. "2025-2026", "2024-2025")
    
    Returns:
        Lista unikalnych formatów (np. ['2025-2026', '2025/2026', '2025', 2025, '2026', 2026])
    """
    # Obsługa różnych separatorów
    if '-' in season_str:
        parts = season_str.split('-')
    elif '/' in season_str:
        parts = season_str.split('/')
    else:
        # Single year format
        return [season_str, int(season_str)]
    
    if len(parts) != 2:
        # Nieprawidłowy format, zwróć oryginalną wartość
        return [season_str]
    
    year_start = parts[0]
    year_end = parts[1]
    
    filters = [
        # Formaty sezonowe (string)
        f"{year_start}-{year_end}",    # "2025-2026"
        f"{year_start}/{year_end}",    # "2025/2026"
        
        # Lata kalendarzowe dla reprezentacji (string i int)
        year_start,                     # "2025"
        int(year_start),                # 2025
        year_end,                       # "2026"
        int(year_end),                  # 2026
    ]
    
    # Usuń duplikaty zachowując kolejność
    seen = set()
    unique_filters = []
    for f in filters:
        if f not in seen:
            seen.add(f)
            unique_filters.append(f)
    
    return unique_filters

# Helper function to calculate per 90 metrics
def calculate_per_90(value, minutes):
    """Calculate per 90 minute metric"""
    if minutes > 0:
        return (value / minutes) * 90
    return 0.0

# Helper function to calculate xGI
def calculate_xgi(xg, xa):
    """Calculate xGI (xG + xAG)"""
    xg_val = xg if pd.notna(xg) else 0.0
    xa_val = xa if pd.notna(xa) else 0.0
    return xg_val + xa_val

def is_club_world_cup(competition_name):
    '''Check if competition is Club World Cup'''
    if pd.isna(competition_name):
        return False
    comp_lower = str(competition_name).lower()
    return 'club world cup' in comp_lower or 'fifa club world cup' in comp_lower

def has_cwc_appearances(player_id, matches_df, season_start, season_end):
    '''Check if player has any CWC appearances with minutes > 0 in season'''
    if matches_df is None or matches_df.empty:
        return False
    
    pm = matches_df[matches_df['player_id'] == player_id].copy()
    if pm.empty:
        return False
    
    pm['match_date'] = pd.to_datetime(pm['match_date'], errors='coerce')
    pm = pm.dropna(subset=['match_date'])
    
    start_ts = pd.to_datetime(season_start)
    end_ts = pd.to_datetime(season_end)
    pm = pm[(pm['match_date'] >= start_ts) & (pm['match_date'] <= end_ts)]
    
    pm['minutes_played'] = pd.to_numeric(pm['minutes_played'], errors='coerce').fillna(0)
    pm = pm[pm['minutes_played'] > 0]
    
    if pm.empty:
        return False
    
    cwc_matches = pm[pm['competition'].apply(is_club_world_cup)]
    return len(cwc_matches) > 0

# Helper function to get national team stats by calendar year from player_matches
def get_national_team_stats_by_year(player_id, year, matches_df):
    """Get national team statistics for a specific calendar year from player_matches table"""
    if matches_df.empty:
        return pd.DataFrame()
    
    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg','xa']                                                                                                               
    if not all(col in matches_df.columns for col in required_columns):                                              
        return pd.DataFrame()
    
    # Filter for national team matches (WCQ, Friendlies, Nations League, Euro, World Cup)
    national_competitions = ['WCQ', 'Friendlies (M)', 'UEFA Nations League', 'UEFA Euro', 'World Cup', 
                            'UEFA Euro Qualifying', 'World Cup Qualifying']
    
    # Filter by player, year, and national team competitions
    year_matches = matches_df[
        (matches_df['player_id'] == player_id) &
        (matches_df['match_date'].str.startswith(str(year))) &
        (matches_df['competition'].isin(national_competitions))
    ]
    
    if year_matches.empty:
        return None
    
    # Count starts (matches with 60+ minutes or specific logic - for now, count matches with 45+ minutes as starts)
    starts = len(year_matches[year_matches['minutes_played'] >= 45])
    
    # Aggregate stats
    stats = {
        'games': len(year_matches),
        'starts': starts,
        'goals': year_matches['goals'].sum(),
        'assists': year_matches['assists'].sum(),
        'minutes': year_matches['minutes_played'].sum(),
        'xg': year_matches['xg'].sum(),
        'xa': year_matches['xa'].sum(),
        'shots': year_matches['shots'].sum() if 'shots' in year_matches.columns else 0,
        'shots_on_target': year_matches['shots_on_target'].sum() if 'shots_on_target' in year_matches.columns else 0,
        'competitions': year_matches['competition'].unique().tolist()
    }
    
    return stats

# Helper function to get all national team stats by calendar year for history table
def get_national_team_history_by_calendar_year(player_id, matches_df):
    """Get national team statistics grouped by calendar year from player_matches table"""
    if matches_df.empty:
        return pd.DataFrame()
    
    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg', 'xa']     
    if not all(col in matches_df.columns for col in required_columns):
        return pd.DataFrame()
    
    # Filter for national team matches
    national_competitions = ['WCQ', 'Friendlies (M)', 'UEFA Nations League', 'UEFA Euro', 'World Cup', 
                            'UEFA Euro Qualifying', 'World Cup Qualifying']
    
    national_matches = matches_df[
        (matches_df['player_id'] == player_id) &
        (matches_df['competition'].isin(national_competitions))
    ].copy()
    
    if national_matches.empty:
        return pd.DataFrame()
    
    # Extract year from match_date
    national_matches['year'] = national_matches['match_date'].str[:4]
    
    # Group by year and aggregate
    yearly_stats = national_matches.groupby('year').agg({
        'match_date': 'count',  # games
        'goals': 'sum',
        'assists': 'sum',
        'minutes_played': 'sum',
        'xg': 'sum',
        'xa': 'sum',
        'shots': 'sum',
        'shots_on_target': 'sum'
    }).reset_index()
    
    # Rename columns to match expected format
    yearly_stats.columns = ['season', 'games', 'goals', 'assists', 'minutes', 'xg', 'xa', 'shots', 'shots_on_target']
    
    # Add required columns
    yearly_stats['competition_type'] = 'NATIONAL_TEAM'
    yearly_stats['competition_name'] = 'National Team (All)'
    yearly_stats['yellow_cards'] = 0
    yearly_stats['red_cards'] = 0
    
    # Reorder columns to match comp_stats format
    yearly_stats = yearly_stats[['season', 'competition_type', 'competition_name', 'games', 'goals', 
                                  'assists', 'xg', 'xa', 'shots', 'shots_on_target', 'yellow_cards', 
                                  'red_cards', 'minutes']]
    
    return yearly_stats


def get_season_total_stats_by_date_range(
    player_id,
    start_date,
    end_date,
    matches_df,
    exclude_competitions=None,
    exclude_competition_keywords=None,
):
    """Aggregate player_matches for a date range.

    Args:
        start_date/end_date: inclusive bounds (YYYY-MM-DD)
        exclude_competitions: list of competition names to exclude (e.g. national team comps)

    Returns:
        dict with games, starts, minutes, goals, assists, xg, xa, shots, shots_on_target
    """
    if matches_df is None or matches_df.empty:
        return None

    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg', 'xa']
    if not all(col in matches_df.columns for col in required_columns):
        return None

    pm = matches_df[matches_df['player_id'] == player_id].copy()
    if pm.empty:
        return None

    # Parse date
    pm['match_date'] = pd.to_datetime(pm['match_date'], errors='coerce')
    pm = pm.dropna(subset=['match_date'])

    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    pm = pm[(pm['match_date'] >= start_ts) & (pm['match_date'] <= end_ts)]

    # Season Total rule: count only appearances (minutes_played > 0)
    # This excludes matches where the player was unused on the bench.
    pm['minutes_played'] = pd.to_numeric(pm['minutes_played'], errors='coerce').fillna(0)
    pm = pm[pm['minutes_played'] > 0]

    # Exact competition name exclusions
    if exclude_competitions:
        pm = pm[~pm['competition'].isin(exclude_competitions)]

    # Keyword-based exclusions (case-insensitive substring match)
    if exclude_competition_keywords:
        comp_series = pm['competition'].astype(str)
        mask = pd.Series(False, index=pm.index)
        for kw in exclude_competition_keywords:
            if not kw:
                continue
            mask = mask | comp_series.str.contains(str(kw), case=False, na=False)
        pm = pm[~mask]

        # Exclude Club World Cup matches (separate category)
        cwc_mask = pm['competition'].apply(is_club_world_cup)
        pm = pm[~cwc_mask]

    if pm.empty:
        return None

    starts = int((pm['minutes_played'] >= 45).sum())

    return {
        'games': int(len(pm)),
        'starts': starts,
        'minutes': int(pm['minutes_played'].sum()),
        'goals': int(pm['goals'].sum()),
        'assists': int(pm['assists'].sum()),
        'xg': float(pm['xg'].sum()),
        'xa': float(pm['xa'].sum()),
        'shots': int(pm['shots'].sum()) if 'shots' in pm.columns else 0,
        'shots_on_target': int(pm['shots_on_target'].sum()) if 'shots_on_target' in pm.columns else 0,
    }


st.markdown("""
    <style>
        /* Ukrywa tylko link/element z label "streamlit app" w sidebarze */
        a[data-testid="stSidebarNavLink"] > span[label="streamlit app"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)
# Page config
st.set_page_config(
    page_title="Polish Football Data Hub International",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Centered app title at the top
st.markdown(
    """
    <h1 style='text-align: center; margin-bottom: 0.5em;'>Polish Football Data Hub International</h1>
    """,
    unsafe_allow_html=True
)
# Initialize API client
@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    """Load players data from API."""
    try:
        api_client = get_api_client()
        
        # Pobierz dane graczy
        players_df = api_client.get_all_players()
        
        # Pobierz statystyki competition_stats
        comp_stats_df = api_client.get_all_competition_stats()
        
        # Pobierz goalkeeper_stats
        gk_stats_df = api_client.get_all_goalkeeper_stats()
        
        # Pobierz mecze graczy
        matches_df = api_client.get_all_matches()
        
        # Note: player_season_stats table is deprecated, using competition_stats instead
        stats_df = pd.DataFrame()  # Empty for backward compatibility
        
        return players_df, stats_df, comp_stats_df, gk_stats_df, matches_df
    except Exception as e:
        st.error(f"Error loading data from API: {e}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
# Sidebar - Search
st.sidebar.header("🔎 Player Search")
search_name = st.sidebar.text_input("Enter player name", placeholder="e.g. Lewandowski, Zieliński...")
# Optional filters
st.sidebar.markdown("---")
st.sidebar.subheader("🎛 Filters (Optional)")
# Load data
df, stats_df, comp_stats_df, gk_stats_df, matches_df = load_data()
if df.empty:
    st.warning("No data available. Please sync data first.")
    st.info("Run: python sync_all_players.py")
    st.stop()
# Filters
teams = ['All'] + sorted(df['team'].dropna().unique().tolist())
selected_team = st.sidebar.selectbox("Team", teams)
# Apply filters
filtered_df = df.copy()
# Filtruj po nazwisku
if search_name:
    filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]
# Filtruj po drużynie
if selected_team != 'All':
    filtered_df = filtered_df[filtered_df['team'].fillna('') == selected_team]
# Jeśli nie ma wyszukiwania ANI filtru drużyny, nie pokazuj nic
if not search_name and selected_team == 'All':
    st.info("👆 Enter a player name in the search box OR select a team to view statistics")
    
    # Footer - FBref Attribution (pokazuj też na głównej stronie)
    st.divider()
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 1rem 0; color: #8A8A8A; font-size: 0.875rem;'>
        <p style='margin-bottom: 0.5rem;'>
            📊 <strong>Data Source:</strong> 
            <a href='https://fbref.com/' target='_blank' style='color: #4ECDC4; text-decoration: none;'>
                FBref.com
            </a> (Sports Reference LLC)
        </p>
        <p style='font-size: 0.75rem; color: #B8B8B8; margin-bottom: 0.5rem;'>
            Player statistics powered by FBref - The leading source for football statistics
        </p>
        <p style='font-size: 0.7rem; color: #6A6A6A; margin-bottom: 0;'>
            Polish Football Data Hub International is an independent project and is not affiliated with FBref.com
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()
# Display filtered results
if not filtered_df.empty:
    for idx, row in filtered_df.iterrows():
        # Przywróć pobieranie competition_stats i goalkeeper_stats dla każdej karty zawodnika
        comp_stats = comp_stats_df[comp_stats_df['player_id'] == row['id']].sort_values(['season', 'competition_type'], ascending=False) if not comp_stats_df.empty and 'player_id' in comp_stats_df.columns else pd.DataFrame()
        gk_stats = gk_stats_df[gk_stats_df['player_id'] == row['id']].sort_values(['season', 'competition_type'], ascending=False) if not gk_stats_df.empty and 'player_id' in gk_stats_df.columns else pd.DataFrame()
        # Przywróć pobieranie player_stats, bo jest używane w innych sekcjach
        player_stats = stats_df[stats_df['player_id'] == row['id']].sort_values('season', ascending=False) if not stats_df.empty and 'player_id' in stats_df.columns else pd.DataFrame()
        # ...nowa sekcja 5 kolumn i advanced stats (tylko raz, nie powtarzaj)
        # Tytuł karty
        current_season = ['2025-2026', '2025/2026', 2025]
        season_current = player_stats[player_stats['season'].isin(current_season)] if not player_stats.empty else pd.DataFrame()
        # If goalkeeper, always show 0 goals in card title
        position = str(row.get('position', '') or '').strip().upper()
        is_gk = position in ("GK", "BRAMKARZ", "GOALKEEPER")
        if is_gk:
            goals_current = 0
        else:
            goals_current = safe_int(season_current['goals'].iloc[0]) if not season_current.empty else 0
        card_title = f"⚽ {row['name']} - {row['team'] or 'Unknown Team'}"
        with st.expander(card_title, expanded=(len(filtered_df) <= 3)):
            # Check if player has CWC appearances (minutes > 0)
            season_start = '2025-07-01'
            season_end = '2026-06-30'
            has_cwc = has_cwc_appearances(row['id'], matches_df, season_start, season_end)
            
            # Dynamic column layout: 6 columns if CWC exists, 5 otherwise
            if has_cwc:
                col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])
            else:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                col6 = None  # Placeholder
            
            STATS_HEIGHT = 350 

                                   # --- KOLUMNA 1: LEAGUE STATS ---
            with col1:
                # Górna część: Statystyki w sztywnym pudełku (wysokość = STATS_HEIGHT)
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🏆 League Stats (2025-2026)")
                    
                    found_league = False
                    
                    # 1. Logika dla bramkarzy (GK)
                    if is_gk and not gk_stats.empty:
                        league_seasons = ['2025-2026', '2025/2026']
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(league_seasons)].copy()
                        league_mask = gk_stats_2526['competition_type'].astype(str).str.upper() == 'LEAGUE'
                        league_stats = gk_stats_2526[league_mask]
                        if not league_stats.empty:
                            found_league = True
                            for _, gk_row in league_stats.iterrows():
                                st.markdown(f"**{gk_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(gk_row.get('games')))
                                m2.metric("CS", safe_int(gk_row.get('clean_sheets')))
                                m3.metric("GA", safe_int(gk_row.get('goals_against')))
                    
                    # 2. Logika dla graczy z pola (lub fallback)
                    if not found_league and not comp_stats.empty:
                        league_seasons = ['2025-2026', '2025/2026']
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(league_seasons)].copy()
                        league_mask = comp_stats_2526['competition_type'].astype(str).str.upper() == 'LEAGUE'
                        league_stats = comp_stats_2526[league_mask]
                        if not league_stats.empty:
                            found_league = True
                            for _, comp_row in league_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(comp_row.get('games')))
                                m2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
                                m3.metric("Assists", safe_int(comp_row.get('assists')))

                    if not found_league:
                        st.info("No league stats for 2025-2026")

                # Dolna część: Szczegóły (poza kontenerem, więc zawsze na dole)
                # WAŻNE: To musi być wcięte wewnątrz `with col1`, ale równolegle do `with st.container`
                with st.expander("📊 Details"):
                    details_found = False
                    row_to_show = None
                    is_gk_display = False
                    
                    # Ponowne pobranie danych do wyświetlenia w expanderze
                    if is_gk and not gk_stats.empty:
                         league_seasons = ['2025-2026', '2025/2026']
                         gk_stats_2526 = gk_stats[gk_stats['season'].isin(league_seasons)].copy()
                         league_mask = gk_stats_2526['competition_type'].astype(str).str.upper() == 'LEAGUE'
                         league_stats = gk_stats_2526[league_mask]
                         if not league_stats.empty:
                             row_to_show = league_stats.iloc[0]
                             is_gk_display = True
                             details_found = True

                    if not details_found and not comp_stats.empty:
                         league_seasons = ['2025-2026', '2025/2026']
                         comp_stats_2526 = comp_stats[comp_stats['season'].isin(league_seasons)].copy()
                         league_mask = comp_stats_2526['competition_type'].astype(str).str.upper() == 'LEAGUE'
                         league_stats = comp_stats_2526[league_mask]
                         if not league_stats.empty:
                             row_to_show = league_stats.iloc[0]
                             is_gk_display = False
                             details_found = True
                    
                    if details_found and row_to_show is not None:
                        if is_gk_display:
                            # GK Details - standardized: Games, Starts, Minutes, Saves, SoTA, Save%
                            st.write(f"⚽ **Games:** {safe_int(row_to_show.get('games'))}")
                            st.write(f"🏃 **Starts:** {safe_int(row_to_show.get('games_starts'))}")
                            st.write(f"⏱️ **Minutes:** {safe_int(row_to_show.get('minutes')):,}")
                            st.write(f"🧤 **Saves:** {safe_int(row_to_show.get('saves'))}")
                            st.write(f"🔫 **SoTA:** {safe_int(row_to_show.get('shots_on_target_against'))}")
                            save_pct = row_to_show.get('save_percentage', None)
                            if pd.notna(save_pct):
                                st.write(f"💯 **Save%:** {save_pct:.1f}%")
                            else:
                                st.write(f"💯 **Save%:** -")
                        else:
                            # Outfield player details - ENHANCED with per 90 metrics
                            starts = safe_int(row_to_show.get('games_starts'))
                            minutes = safe_int(row_to_show.get('minutes'))
                            goals = safe_int(row_to_show.get('goals'))
                            assists = safe_int(row_to_show.get('assists'))
                            xg = row_to_show.get('xg', 0.0) if pd.notna(row_to_show.get('xg')) else 0.0
                            xa = row_to_show.get('xa', 0.0) if pd.notna(row_to_show.get('xa')) else 0.0
                            npxg = row_to_show.get('npxg', 0.0) if pd.notna(row_to_show.get('npxg')) else 0.0
                            
                            # Calculate xGI
                            xgi = calculate_xgi(xg, xa)
                            
                            # Calculate per 90 metrics
                            ga_per_90 = calculate_per_90(goals + assists, minutes)
                            xg_per_90 = calculate_per_90(xg, minutes)
                            xa_per_90 = calculate_per_90(xa, minutes)
                            npxg_per_90 = calculate_per_90(npxg, minutes)
                            xgi_per_90 = calculate_per_90(xgi, minutes)
                            
                            # Display stats
                            st.write(f"🏃 **Starts:** {starts}")
                            st.write(f"⏱️ **Minutes:** {minutes:,}")
                            st.write(f"🎯 **Goals:** {goals}")
                            st.write(f"🅰️ **Assists:** {assists}")
                            st.write(f"⚡ **G+A / 90:** {ga_per_90:.2f}")
                            if xgi > 0:
                                st.write(f"📊 **xGI:** {xgi:.2f}")
                            if xg > 0:
                                st.write(f"📊 **xG:** {xg:.2f}")
                            if xa > 0:
                                st.write(f"📊 **xA:** {xa:.2f}")
                            if xg > 0:
                                st.write(f"📈 **xG / 90:** {xg_per_90:.2f}")
                            if xa > 0:
                                st.write(f"📈 **xA / 90:** {xa_per_90:.2f}")
                            if npxg > 0:
                                st.write(f"📊 **npxG / 90:** {npxg_per_90:.2f}")
                            if xgi > 0:
                                st.write(f"📈 **xGI / 90:** {xgi_per_90:.2f}")
                    else:
                        st.write("No details available.")


            # --- KOLUMNA 2: EUROPEAN CUPS ---
            with col2:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🌍 European Cups (2025-2026)")
                    
                    found_euro = False
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup from European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                        if not euro_stats.empty:
                            found_euro = True
                            for _, gk_row in euro_stats.iterrows():
                                st.markdown(f"**{gk_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(gk_row.get('games')))
                                m2.metric("CS", safe_int(gk_row.get('clean_sheets')))
                                m3.metric("GA", safe_int(gk_row.get('goals_against')))
                    
                    if not found_euro and not comp_stats.empty:
                         # Fallback dla graczy z pola lub gdy brak GK stats
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup from European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                        if not euro_stats.empty:
                            found_euro = True
                            for _, comp_row in euro_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(comp_row.get('games')))
                                m2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
                                m3.metric("Assists", safe_int(comp_row.get('assists')))

                    if not found_euro:
                        # Ważne: pusty write lub info, żeby kontener nie był pusty wizualnie
                        st.markdown("<br><br><p style='text-align:center; color:gray'>No matches played</p>", unsafe_allow_html=True)

                with st.expander("📊 Details"):
                    details_found = False
                    euro_stats_to_show = None
                    is_gk_display = False
                    
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup from European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                        if not euro_stats.empty:
                            euro_stats_to_show = euro_stats
                            is_gk_display = True
                            details_found = True
                    
                    if not details_found and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup from European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                        if not euro_stats.empty:
                            euro_stats_to_show = euro_stats
                            is_gk_display = False
                            details_found = True
                    
                    if details_found and euro_stats_to_show is not None:
                        # Show details for ALL European competitions
                        for idx, row_to_show in euro_stats_to_show.iterrows():
                            if len(euro_stats_to_show) > 1:
                                st.markdown(f"### {row_to_show['competition_name']}")
                            else:
                                st.markdown(f"**{row_to_show['competition_name']}**")
                            
                            if is_gk_display:
                                st.write(f"⚽ **Games:** {safe_int(row_to_show.get('games'))}")
                                st.write(f"🏃 **Starts:** {safe_int(row_to_show.get('games_starts'))}")
                                st.write(f"⏱️ **Minutes:** {safe_int(row_to_show.get('minutes')):,}")
                                st.write(f"🧤 **Saves:** {safe_int(row_to_show.get('saves'))}")
                                st.write(f"🔫 **SoTA:** {safe_int(row_to_show.get('shots_on_target_against'))}")
                                save_pct = row_to_show.get('save_percentage', None)
                                if pd.notna(save_pct):
                                    st.write(f"💯 **Save%:** {save_pct:.1f}%")
                                else:
                                    st.write(f"💯 **Save%:** -")
                            else:
                                # Outfield player details - ENHANCED with per 90 metrics
                                starts = safe_int(row_to_show.get('games_starts'))
                                minutes = safe_int(row_to_show.get('minutes'))
                                goals = safe_int(row_to_show.get('goals'))
                                assists = safe_int(row_to_show.get('assists'))
                                xg = row_to_show.get('xg', 0.0) if pd.notna(row_to_show.get('xg')) else 0.0
                                xa = row_to_show.get('xa', 0.0) if pd.notna(row_to_show.get('xa')) else 0.0
                                npxg = row_to_show.get('npxg', 0.0) if pd.notna(row_to_show.get('npxg')) else 0.0
                                
                                # Calculate xGI
                                xgi = calculate_xgi(xg, xa)
                                
                                # Calculate per 90 metrics
                                ga_per_90 = calculate_per_90(goals + assists, minutes)
                                xg_per_90 = calculate_per_90(xg, minutes)
                                xa_per_90 = calculate_per_90(xa, minutes)
                                npxg_per_90 = calculate_per_90(npxg, minutes)
                                xgi_per_90 = calculate_per_90(xgi, minutes)
                                
                                # Display stats
                                st.write(f"🏃 **Starts:** {starts}")
                                st.write(f"⏱️ **Minutes:** {minutes:,}")
                                st.write(f"🎯 **Goals:** {goals}")
                                st.write(f"🅰️ **Assists:** {assists}")
                                st.write(f"⚡ **G+A / 90:** {ga_per_90:.2f}")
                                if xgi > 0:
                                    st.write(f"📊 **xGI:** {xgi:.2f}")
                                if xg > 0:
                                    st.write(f"📊 **xG:** {xg:.2f}")
                                if xa > 0:
                                    st.write(f"📊 **xA:** {xa:.2f}")
                                if xg > 0:
                                    st.write(f"📈 **xG / 90:** {xg_per_90:.2f}")
                                if xa > 0:
                                    st.write(f"📈 **xA / 90:** {xa_per_90:.2f}")
                                if npxg > 0:
                                    st.write(f"📊 **npxG / 90:** {npxg_per_90:.2f}")
                                if xgi > 0:
                                    st.write(f"📈 **xGI / 90:** {xgi_per_90:.2f}")
                            
                            # Add separator between competitions if there are multiple
                            if len(euro_stats_to_show) > 1 and idx < len(euro_stats_to_show) - 1:
                                st.markdown("---")
                    else:
                        st.write("No matches played")
                        # --- KOLUMNA 3: DOMESTIC CUPS ---
            with col3:
                # GÓRA: Statystyki w sztywnym pudełku (wysokość STATS_HEIGHT)
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🏆 Domestic Cups (2025-2026)")
                    
                    found_domestic = False
                    
                    # 1. Logika dla BRAMKARZY (GK)
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        domestic_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        if not domestic_stats.empty:
                            found_domestic = True
                            for _, gk_row in domestic_stats.iterrows():
                                st.markdown(f"**{gk_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(gk_row.get('games')))
                                m2.metric("CS", safe_int(gk_row.get('clean_sheets')))
                                m3.metric("GA", safe_int(gk_row.get('goals_against')))

                    # 2. Logika dla GRACZY Z POLA (lub fallback dla GK, jeśli brak stats bramkarskich)
                    if not found_domestic and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        domestic_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        
                        if not domestic_stats.empty:
                            found_domestic = True
                            for _, comp_row in domestic_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                metric_col1, metric_col2, metric_col3 = st.columns(3)
                                metric_col1.metric("Games", safe_int(comp_row.get('games')))
                                metric_col2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
                                metric_col3.metric("Assists", safe_int(comp_row.get('assists')))
                    
                    # 3. Jeśli brak danych - wyświetl info (żeby kontener nie był pusty)
                    if not found_domestic:
                        st.info("No domestic cup stats for 2025-2026")

                # DÓŁ: Szczegóły (Details) - ZAWSZE POZA KONTENEREM
                with st.expander("📊 Details"):
                    details_found = False
                    row_to_show = None
                    is_gk_display = False
                    
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        domestic_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        if not domestic_stats.empty:
                            row_to_show = domestic_stats.iloc[0]
                            is_gk_display = True
                            details_found = True
                    
                    if not details_found and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        domestic_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        if not domestic_stats.empty:
                            row_to_show = domestic_stats.iloc[0]
                            is_gk_display = False
                            details_found = True

                    if details_found and row_to_show is not None:
                        if is_gk_display:
                            st.write(f"⚽ **Games:** {safe_int(row_to_show.get('games'))}")
                            st.write(f"🏃 **Starts:** {safe_int(row_to_show.get('games_starts'))}")
                            st.write(f"⏱️ **Minutes:** {safe_int(row_to_show.get('minutes')):,}")
                            st.write(f"🧤 **Saves:** {safe_int(row_to_show.get('saves'))}")
                            st.write(f"🔫 **SoTA:** {safe_int(row_to_show.get('shots_on_target_against'))}")
                            save_pct = row_to_show.get('save_percentage', None)
                            if pd.notna(save_pct):
                                st.write(f"💯 **Save%:** {save_pct:.1f}%")
                            else:
                                st.write(f"💯 **Save%:** -")
                        else:
                            # Outfield player details - ENHANCED with per 90 metrics
                            starts = safe_int(row_to_show.get('games_starts'))
                            minutes = safe_int(row_to_show.get('minutes'))
                            goals = safe_int(row_to_show.get('goals'))
                            assists = safe_int(row_to_show.get('assists'))
                            xg = row_to_show.get('xg', 0.0) if pd.notna(row_to_show.get('xg')) else 0.0
                            xa = row_to_show.get('xa', 0.0) if pd.notna(row_to_show.get('xa')) else 0.0
                            npxg = row_to_show.get('npxg', 0.0) if pd.notna(row_to_show.get('npxg')) else 0.0
                            
                            # Calculate xGI
                            xgi = calculate_xgi(xg, xa)
                            
                            # Calculate per 90 metrics
                            ga_per_90 = calculate_per_90(goals + assists, minutes)
                            xg_per_90 = calculate_per_90(xg, minutes)
                            xa_per_90 = calculate_per_90(xa, minutes)
                            npxg_per_90 = calculate_per_90(npxg, minutes)
                            xgi_per_90 = calculate_per_90(xgi, minutes)
                            
                            # Display stats
                            st.write(f"🏃 **Starts:** {starts}")
                            st.write(f"⏱️ **Minutes:** {minutes:,}")
                            st.write(f"🎯 **Goals:** {goals}")
                            st.write(f"🅰️ **Assists:** {assists}")
                            st.write(f"⚡ **G+A / 90:** {ga_per_90:.2f}")
                            if xgi > 0:
                                st.write(f"📊 **xGI:** {xgi:.2f}")
                            if xg > 0:
                                st.write(f"📊 **xG:** {xg:.2f}")
                            if xa > 0:
                                st.write(f"📊 **xA:** {xa:.2f}")
                            if xg > 0:
                                st.write(f"📈 **xG / 90:** {xg_per_90:.2f}")
                            if xa > 0:
                                st.write(f"📈 **xA / 90:** {xa_per_90:.2f}")
                            if npxg > 0:
                                st.write(f"📊 **npxG / 90:** {npxg_per_90:.2f}")
                            if xgi > 0:
                                st.write(f"📈 **xGI / 90:** {xgi_per_90:.2f}")
                    else:
                        st.write("No details available.")

            # KOLUMNA 4: NATIONAL TEAM (Combined - includes WCQ, Friendlies, etc.)
                        # --- KOLUMNA 4: NATIONAL TEAM ---
            with col4:
                # GÓRA: Statystyki w sztywnym pudełku
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🇵🇱 National Team (2025)")
                    
                    national_data_found = False
                    
                    # Zmienne do przechowywania zagregowanych danych (potrzebne też do expandera poniżej)
                    total_games = 0
                    total_minutes = 0
                    total_starts = 0
                    
                    # Zmienne specyficzne dla GK
                    total_ga = 0
                    total_saves = 0
                    total_sota = 0
                    total_cs = 0
                    avg_save_pct = 0.0
                    
                    # Zmienne specyficzne dla graczy z pola
                    total_goals = 0
                    total_assists = 0
                    total_xg = 0.0
                    total_xa = 0.0
                    total_shots = 0
                    total_shots_ot = 0
                    total_yellow = 0
                    total_red = 0
                    comp_display = ""
                    
                    is_gk_stats_display = False # Flaga: czy wyświetlamy dane bramkarskie czy ogólne?

                    # HYBRID APPROACH: Use competition_stats for national team (more complete data)
                    # player_matches has incomplete data (only from August 2025)
                    if not is_gk and not comp_stats.empty:
                        # Use competition_stats with season filters
                        # NOTE: Exclude 2024-2025 Nations League (all matches were in 2024, not 2025)
                        nat_filters = ['2025', 2025]
                        comp_stats_2025 = comp_stats[comp_stats['season'].isin(nat_filters)].copy()
                        national_comp_names = ['WCQ', 'World Cup', 'UEFA Nations League', 'UEFA Euro Qualifying', 'UEFA Euro', 'Friendlies (M)', 'World Cup Qualifying']
                        national_mask = (comp_stats_2025['competition_type'].astype(str).str.upper() == 'NATIONAL_TEAM') | (comp_stats_2025['competition_name'].isin(national_comp_names))
                        national_stats = comp_stats_2025[national_mask]
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = False
                            
                            # Agregacja danych z competition_stats (źródło prawdy)
                            total_games = national_stats['games'].sum()
                            total_starts = national_stats['games_starts'].sum()
                            total_goals = national_stats['goals'].sum()
                            total_assists = national_stats['assists'].sum()
                            total_minutes = national_stats['minutes'].sum()
                            total_xg = national_stats['xg'].sum()
                            total_xa = national_stats['xa'].sum()
                            total_shots = national_stats['shots'].sum()
                            total_shots_ot = national_stats['shots_on_target'].sum()
                            total_yellow = national_stats['yellow_cards'].sum()
                            total_red = national_stats['red_cards'].sum()
                            
                            comp_names = national_stats['competition_name'].unique().tolist()
                            comp_display = ', '.join([name for name in comp_names if pd.notna(name) and name])
                            if comp_display:
                                st.caption(f"*{comp_display}*")
                        else:
                            # FALLBACK (tylko gdy brak danych w competition_stats): rok kalendarzowy z player_matches
                            pm_stats = get_national_team_stats_by_year(row['id'], 2025, matches_df)
                            if pm_stats:
                                national_data_found = True
                                is_gk_stats_display = False
                                total_games = pm_stats.get('games', 0)
                                total_starts = pm_stats.get('starts', 0)
                                total_goals = pm_stats.get('goals', 0)
                                total_assists = pm_stats.get('assists', 0)
                                total_minutes = pm_stats.get('minutes', 0)
                                total_xg = pm_stats.get('xg', 0.0)
                                total_xa = pm_stats.get('xa', 0.0)
                                total_shots = pm_stats.get('shots', 0)
                                total_shots_ot = pm_stats.get('shots_on_target', 0)
                                comp_list = pm_stats.get('competitions', [])
                                comp_display = ', '.join([c for c in comp_list if c])
                                if comp_display:
                                    st.caption(f"*{comp_display}*")
                        
                        if national_data_found:
                            # Metryki z pola
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", safe_int(total_games))
                            m2.metric("Goals", 0 if is_gk else safe_int(total_goals))
                            m3.metric("Assists", safe_int(total_assists))
                    
                    # Fallback for goalkeepers (GK stats not available in player_matches with enough detail)
                    elif is_gk and not gk_stats.empty:
                        # NOTE: Exclude 2024-2025 Nations League (all matches were in 2024, not 2025)
                        # UWAGA: w bazie kwalifikacje WC 2026 bywają zapisane z sezonem = 2026,
                        # mimo że część meczów jest rozgrywana w roku kalendarzowym 2025.
                        # Żeby pokazać w jednym miejscu (2025) zarówno Friendlies 2025 jak i WCQ 2026,
                        # bierzemy oba lata: 2025 i 2026.
                        nat_filters = ['2025', 2025, '2026', 2026]
                        gk_stats_2025 = gk_stats[gk_stats['season'].isin(nat_filters)].copy()
                        national_comp_names = ['WCQ', 'World Cup', 'UEFA Nations League', 'UEFA Euro Qualifying', 'UEFA Euro', 'Friendlies (M)', 'World Cup Qualifying']
                        national_mask = (gk_stats_2025['competition_type'].astype(str).str.upper() == 'NATIONAL_TEAM') | (gk_stats_2025['competition_name'].isin(national_comp_names))
                        national_stats = gk_stats_2025[national_mask]
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = True
                            
                            # Agregacja danych GK (źródło prawdy)
                            total_games = national_stats['games'].sum()
                            total_starts = national_stats['games_starts'].sum()
                            total_minutes = national_stats['minutes'].sum()
                            total_ga = national_stats['goals_against'].sum()
                            total_saves = national_stats['saves'].sum()
                            total_sota = national_stats['shots_on_target_against'].sum()
                            total_cs = national_stats['clean_sheets'].sum()
                            avg_save_pct = (total_saves / total_sota * 100) if total_sota > 0 else 0.0
                            
                            # Nazwy rozgrywek (np. "WCQ, Friendlies")
                            comp_names = national_stats['competition_name'].unique().tolist()
                            comp_display = ', '.join([name for name in comp_names if pd.notna(name) and name])
                            if comp_display:
                                st.caption(f"*{comp_display}*")
                        else:
                            # FALLBACK (tylko gdy brak danych w goalkeeper_stats): rok kalendarzowy z player_matches.
                            # UWAGA: match logi nie mają pełnych statystyk GK (CS/GA/Saves/SoTA), więc pokazujemy
                            # tylko Caps/Starts/Minutes, reszta = 0.
                            pm_stats = get_national_team_stats_by_year(row['id'], 2025, matches_df)
                            if pm_stats:
                                national_data_found = True
                                is_gk_stats_display = True
                                total_games = pm_stats.get('games', 0)
                                total_starts = pm_stats.get('starts', 0)
                                total_minutes = pm_stats.get('minutes', 0)
                                total_cs = 0
                                total_ga = 0
                                total_saves = 0
                                total_sota = 0
                                avg_save_pct = 0.0
                                comp_list = pm_stats.get('competitions', [])
                                comp_display = ', '.join([c for c in comp_list if c])
                                if comp_display:
                                    st.caption(f"*{comp_display}*")
                                st.caption("*GK fallback uses match logs (limited GK details).*")
                        
                        if national_data_found and is_gk_stats_display:
                            # Metryki GK
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", safe_int(total_games))
                            m2.metric("CS", safe_int(total_cs))
                            m3.metric("GA", safe_int(total_ga))
                    
                    # 3. Brak danych
                    if not national_data_found:
                        st.info("No national team stats for 2025")

                # DÓŁ: Szczegóły (Details) - ZAWSZE POZA KONTENEREM
                with st.expander("📊 Details"):
                    if national_data_found:
                        if is_gk_stats_display:
                            # Szczegóły dla GK - standardized
                            st.write(f"⚽ **Games:** {safe_int(total_games)}")
                            st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                            st.write(f"🧤 **Saves:** {safe_int(total_saves)}")
                            st.write(f"🔫 **SoTA:** {safe_int(total_sota)}")
                            st.write(f"💯 **Save%:** {avg_save_pct:.1f}%")
                        else:
                            # Szczegóły dla gracza z pola - ENHANCED
                            st.write(f"⚽ **Games:** {safe_int(total_games)}")
                            st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                            st.write(f"🎯 **Goals:** {safe_int(total_goals)}")
                            st.write(f"🅰️ **Assists:** {safe_int(total_assists)}")
                            if total_xg > 0:
                                st.write(f"📊 **xG:** {total_xg:.2f}")
                            # Note: npxg and penalty_goals need to be aggregated from the query
                            # We'll need to update the aggregation logic above for full details
                            if total_xa > 0:
                                st.write(f"📊 **xAG:** {total_xa:.2f}")
                    else:
                        st.write("No details available.")
                        # --- KOLUMNA 5: SEASON TOTAL (2025-2026) ---
                        # --- KOLUMNA 5: SEASON TOTAL (2025-2026) ---
            with (col6 if has_cwc and col6 is not None else col5):
                # GÓRA: Statystyki w sztywnym pudełku
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🏆 Season Total (2025-2026)")
                    # Season Total = club competitions only (no National Team, no Super Cups)
                    st.caption("Club competitions only (League + Domestic Cups + European Cups). Excludes Club World Cup, National Team, and Super Cups.")
                    # Always exclude national team matches and Super Cups from Season Total
                    include_nt_in_season_total = False

                    # Inicjalizacja wszystkich sum
                    total_games, total_starts, total_minutes = 0, 0, 0
                    total_goals, total_assists, total_xg, total_xa = 0, 0, 0.0, 0.0
                    total_shots, total_sot, total_yellow, total_red = 0, 0, 0, 0
                    
                    # Tylko dla GK
                    total_clean_sheets, total_ga, total_saves, total_sota = 0, 0, 0, 0

                    # KROK 1: Jeśli to bramkarz, sumuj dane z goalkeeper_stats (PRIORYTET)
                    # Season Total 2025/26 = mecze klubowe w przedziale dat 2025-07-01 .. 2026-06-30.
                    # Źródło prawdy dla granicy sezonu (lipiec/czerwiec): player_matches.
                    # Reprezentacja NIE wchodzi do "Season Total" sezonu klubowego.
                    season_start = '2025-07-01'
                    season_end = '2026-06-30'
                    # Exclusions for Season Total:
                    # - National Team competitions
                    # - Super Cups / Supercopa / Supercoppa / UEFA Super Cup etc.
                    national_competitions = [
                        'WCQ',
                        'Friendlies (M)',
                        'UEFA Nations League',
                        'UEFA Euro',
                        'World Cup',
                        'UEFA Euro Qualifying',
                        'World Cup Qualifying',
                    ]
                    super_cup_keywords = [
                        'super cup',
                        'uefa super cup',
                        'supercopa',
                        'supercoppa',
                        'superpuchar',
                        'community shield',
                        'supercup',
                        'dfl-supercup',
                        'supertaca',
                        'supertaça',
                        'trophée des champions',
                        'trofeo de campeones',
                    ]

                    pm_total = get_season_total_stats_by_date_range(
                        player_id=row['id'],
                        start_date=season_start,
                        end_date=season_end,
                        matches_df=matches_df,
                        exclude_competitions=national_competitions,
                        exclude_competition_keywords=super_cup_keywords,
                    )

                    if pm_total:
                        total_games = pm_total['games']
                        total_starts = pm_total['starts']
                        total_minutes = pm_total['minutes']
                        total_goals = pm_total['goals']
                        total_assists = pm_total['assists']
                        total_xg = pm_total['xg']
                        total_xa = pm_total['xa']
                        total_shots = pm_total['shots']
                        total_sot = pm_total['shots_on_target']

                    # Dla bramkarzy: metryki GK (CS/GA/Saves/SoTA) bierzemy z goalkeeper_stats dla sezonu klubowego 2025/26.
                    if is_gk and not gk_stats.empty:
                        club_filters = ['2025-2026', '2025/2026']
                        gk_club = gk_stats[(gk_stats['season'].isin(club_filters)) & (gk_stats['competition_type'] != 'NATIONAL_TEAM')].copy()
                        # Exclude Super Cups from Season Total
                        if not gk_club.empty and 'competition_name' in gk_club.columns:
                            sc_mask = pd.Series(False, index=gk_club.index)
                            for kw in super_cup_keywords:
                                sc_mask = sc_mask | gk_club['competition_name'].astype(str).str.contains(kw, case=False, na=False)
                            gk_club = gk_club[~sc_mask]
                        # Club World Cup jako klubowe – może być zapisane "rokiem" zamiast sezonem
                        if 'competition_name' in gk_stats.columns:
                            gk_cwc = gk_stats[(gk_stats['competition_type'] != 'NATIONAL_TEAM') &
                                              (gk_stats['competition_name'].astype(str).str.contains('Club World Cup', case=False, na=False))]
                        else:
                            gk_cwc = pd.DataFrame()
                        gk_total = pd.concat([gk_club, gk_cwc], ignore_index=True) if (not gk_club.empty or not gk_cwc.empty) else pd.DataFrame()
                        if not gk_total.empty:
                            total_clean_sheets = safe_int(gk_total['clean_sheets'].sum())
                            total_ga = safe_int(gk_total['goals_against'].sum())
                            total_saves = safe_int(gk_total['saves'].sum())
                            total_sota = safe_int(gk_total['shots_on_target_against'].sum())

                    # KROK 3: Wyświetl metryki na bazie zagregowanych danych
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Appearances", safe_int(total_games))
                    
                    if is_gk:
                        m2.metric("CS", safe_int(total_clean_sheets))
                        m3.metric("GA", safe_int(total_ga))
                    else:
                        m2.metric("Goals", safe_int(total_goals))
                        m3.metric("Assists", safe_int(total_assists))
                
                # Dolna część (expander) - użyje tych samych, poprawnie zliczonych zmiennych
                with st.expander("📊 Details"):
                    if is_gk:
                        # GK Season Total Details - standardized
                        st.write(f"⚽ **Games:** {safe_int(total_games)}")
                        st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                        st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                        st.write(f"🧤 **Saves:** {safe_int(total_saves)}")
                        st.write(f"🔫 **SoTA:** {safe_int(total_sota)}")
                    else:
                        # Outfield Player Season Total Details - SIMPLIFIED (only basic stats)
                        st.write(f"⚽ **Total Games:** {safe_int(total_games)}")
                        st.write(f"🏃 **Total Starts:** {safe_int(total_starts)}")
                        st.write(f"⏱️ **Total Minutes:** {safe_int(total_minutes):,}")
                        st.write(f"🎯 **Total Goals:** {safe_int(total_goals)}")
                        st.write(f"🅰️ **Total Assists:** {safe_int(total_assists)}")
                        
                        # Calculate penalty_goals from comp_stats (club comps only, exclude Super Cups)
                        if not comp_stats.empty:
                            club_season_filters = ['2025-2026', '2025/2026']
                            comp_stats_2526 = comp_stats[comp_stats['season'].isin(club_season_filters)].copy()
                            if not comp_stats_2526.empty:
                                # Exclude National Team
                                if 'competition_type' in comp_stats_2526.columns:
                                    comp_stats_2526 = comp_stats_2526[comp_stats_2526['competition_type'] != 'NATIONAL_TEAM']
                                # Exclude Super Cups
                                if 'competition_name' in comp_stats_2526.columns:
                                    sc_mask = pd.Series(False, index=comp_stats_2526.index)
                                    for kw in super_cup_keywords:
                                        sc_mask = sc_mask | comp_stats_2526['competition_name'].astype(str).str.contains(kw, case=False, na=False)
                                    comp_stats_2526 = comp_stats_2526[~sc_mask]

                                total_pen_goals = comp_stats_2526['penalty_goals'].sum() if 'penalty_goals' in comp_stats_2526.columns else 0
                                if total_pen_goals > 0:
                                    st.write(f"⚽ **Total Penalty Goals:** {safe_int(total_pen_goals)}")


            # === ADVANCED PROGRESSION STATS - FOR NON-GOALKEEPERS ===
            # FIX: Only show this section if player actually has data (don't show "not synced" message)
            if str(row['position']).strip().upper() not in ["GK", "BRAMKARZ", "GOALKEEPER"]:
                if not player_stats.empty:
                    season_current = player_stats[player_stats['season'].isin(current_season)]
                    if not season_current.empty:
                        has_data = False
                        # Check if we have any progression stats
                        stat_columns = ['progressive_passes', 'progressive_carries']
                        for col in stat_columns:
                            if col in season_current.columns:
                                val = season_current[col].iloc[0]
                                if pd.notna(val) and val > 0:
                                    has_data = True
                                    break
                        
                        # Only show the section if we have data
                        if has_data:
                            st.write("---")
                            st.write("### 📊 Advanced Progression Stats")
                            st.caption("*Statistics from league competition*")
                            
                            # Progressive stats only
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if 'progressive_passes' in season_current.columns:
                                    prog_passes = season_current['progressive_passes'].iloc[0]
                                    if pd.notna(prog_passes):
                                        st.metric("Progressive Passes", int(prog_passes))
                            with col2:
                                if 'progressive_carries' in season_current.columns:
                                    prog_carries = season_current['progressive_carries'].iloc[0]
                                    if pd.notna(prog_carries):
                                        st.metric("Progressive Carries", int(prog_carries))
                            with col3:
                                if 'progressive_carrying_distance' in season_current.columns:
                                    prog_dist = season_current['progressive_carrying_distance'].iloc[0]
                                    if pd.notna(prog_dist):
                                        st.metric("Prog. Carry Distance", f"{int(prog_dist)}m")
                            with col4:
                                if 'progressive_passes_received' in season_current.columns:
                                    prog_recv = season_current['progressive_passes_received'].iloc[0]
                                    if pd.notna(prog_recv):
                                        st.metric("Prog. Passes Received", int(prog_recv))
            # === SEKCJE ROZSZERZONYCH STATYSTYK Z FBREF ===
            # STRZAŁY
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'shots_total' in season_current.columns:
                    shots_total = season_current['shots_total'].iloc[0]
                    if pd.notna(shots_total) and shots_total > 0:
                        st.write("---")
                        st.subheader("⚽ Shooting Stats")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Shots", int(shots_total))
                        with col2:
                            shots_on_target = season_current['shots_on_target'].iloc[0]
                            if pd.notna(shots_on_target):
                                st.metric("Shots on Target", int(shots_on_target))
                        with col3:
                            accuracy = season_current['shots_on_target_pct'].iloc[0]
                            if pd.notna(accuracy):
                                st.metric("Accuracy", f"{accuracy:.1f}%")
                        with col4:
                            pens = season_current['penalty_kicks_made'].iloc[0]
                            if pd.notna(pens):
                                st.metric("Penalties", int(pens))
            # PODANIA
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'passes_completed' in season_current.columns:
                    passes = season_current['passes_completed'].iloc[0]
                    if pd.notna(passes) and passes > 0:
                        st.write("---")
                        st.subheader("🎯 Passing Stats")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            passes_att = season_current['passes_attempted'].iloc[0]
                            if pd.notna(passes_att):
                                st.metric("Passes", f"{int(passes)}/{int(passes_att)}")
                        with col2:
                            pass_pct = season_current['pass_completion_pct'].iloc[0]
                            if pd.notna(pass_pct):
                                st.metric("Pass Accuracy", f"{pass_pct:.1f}%")
                        with col3:
                            key_passes = season_current['key_passes'].iloc[0]
                            if pd.notna(key_passes):
                                st.metric("Key Passes", int(key_passes))
                        with col4:
                            passes_penalty = season_current['passes_into_penalty_area'].iloc[0]
                            if pd.notna(passes_penalty):
                                st.metric("Into Pen. Area", int(passes_penalty))
            # TWORZENIE AKCJI
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'shot_creating_actions' in season_current.columns:
                    sca = season_current['shot_creating_actions'].iloc[0]
                    if pd.notna(sca) and sca > 0:
                        st.write("---")
                        st.subheader("🎨 Creating Actions")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Shot Creating Actions", int(sca))
                        with col2:
                            gca = season_current['goal_creating_actions'].iloc[0]
                            if pd.notna(gca):
                                st.metric("Goal Creating Actions", int(gca))
            # OBRONA
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'tackles' in season_current.columns:
                    tackles = season_current['tackles'].iloc[0]
                    if pd.notna(tackles) and tackles > 0:
                        st.write("---")
                        st.subheader("🛡️ Defensive Stats")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Tackles", int(tackles))
                        with col2:
                            tackles_won = season_current['tackles_won'].iloc[0]
                            if pd.notna(tackles_won):
                                st.metric("Tackles Won", int(tackles_won))
                        with col3:
                            interceptions = season_current['interceptions'].iloc[0]
                            if pd.notna(interceptions):
                                st.metric("Interceptions", int(interceptions))
                        with col4:
                            blocks = season_current['blocks'].iloc[0]
                            if pd.notna(blocks):
                                st.metric("Blocks", int(blocks))
            # POSIADANIE
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'touches' in season_current.columns:
                    touches = season_current['touches'].iloc[0]
                    if pd.notna(touches) and touches > 0:
                        st.write("---")
                        st.subheader("🏃 Possession Stats")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Touches", int(touches))
                        with col2:
                            dribbles_comp = season_current['dribbles_completed'].iloc[0]
                            dribbles_att = season_current['dribbles_attempted'].iloc[0]
                            if pd.notna(dribbles_comp) and pd.notna(dribbles_att):
                                st.metric("Dribbles", f"{int(dribbles_comp)}/{int(dribbles_att)}")
                        with col3:
                            carries = season_current['carries'].iloc[0]
                            if pd.notna(carries):
                                st.metric("Carries", int(carries))
                        with col4:
                            ball_rec = season_current['ball_recoveries'].iloc[0]
                            if pd.notna(ball_rec):
                                st.metric("Ball Recoveries", int(ball_rec))
            # RÓŻNE
            if not player_stats.empty:
                season_current = player_stats[player_stats['season'].isin(current_season)]
                if not season_current.empty and 'aerials_won' in season_current.columns:
                    aerials = season_current['aerials_won'].iloc[0]
                    if pd.notna(aerials) and aerials > 0:
                        st.write("---")
                        st.subheader("📊 Miscellaneous")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            aerials_lost = season_current['aerials_lost'].iloc[0]
                            if pd.notna(aerials_lost):
                                st.metric("Aerials Won", f"{int(aerials)}/{int(aerials) + int(aerials_lost)}")
                        with col2:
                            fouls_com = season_current['fouls_committed'].iloc[0]
                            if pd.notna(fouls_com):
                                st.metric("Fouls Committed", int(fouls_com))
                        with col3:
                            fouls_drawn = season_current['fouls_drawn'].iloc[0]
                            if pd.notna(fouls_drawn):
                                st.metric("Fouls Drawn", int(fouls_drawn))
                        with col4:
                            offsides = season_current['offsides'].iloc[0]
                            if pd.notna(offsides):
                                st.metric("Offsides", int(offsides))
            # TABELA STATYSTYK HISTORYCZNYCH - ALL COMPETITIONS
            # For goalkeepers, use goalkeeper_stats table; for others, use competition_stats
            is_goalkeeper = str(row.get('position', '')).strip().upper() in ['GK', 'GOALKEEPER', 'BRAMKARZ']
            stats_to_display = gk_stats if (is_goalkeeper and not gk_stats.empty) else comp_stats
            if not stats_to_display.empty and len(stats_to_display) > 0:
                st.write("---")
                st.write("**📊 Season Statistics History (All Competitions)**")
                # Create display dataframe - different columns for goalkeepers vs outfield players
                if is_goalkeeper:
                    import pandas as _pd
                    # Standardized columns for all goalkeepers: Season, Type, Competition, Games, Starts, Minutes, CS, GA, Save%
                    gk_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                    display_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                    if not gk_stats.empty:
                        gk_display = gk_stats.reindex(columns=gk_cols).copy()
                    else:
                        gk_display = _pd.DataFrame(columns=gk_cols)
                    # Add missing competitions from comp_stats as fallback rows so every season/competition appears
                    comp_needed = ['LEAGUE','EUROPEAN_CUP','DOMESTIC_CUP','NATIONAL_TEAM']
                    comp_display = _pd.DataFrame(columns=gk_cols)
                    if not comp_stats.empty:
                        comp_subset = comp_stats[comp_stats['competition_type'].isin(comp_needed)].copy()
                        gk_keys = set((str(r['season']), str(r['competition_type']), str(r['competition_name'])) for _, r in gk_display.iterrows())
                        rows = []
                        for _, r in comp_subset.iterrows():
                            key = (str(r['season']), str(r['competition_type']), str(r['competition_name']))
                            if key in gk_keys:
                                continue
                            rows.append({
                                'season': r['season'],
                                'competition_type': r['competition_type'],
                                'competition_name': r['competition_name'],
                                'games': safe_int(r.get('games')),
                                'games_starts': 0,
                                'minutes': safe_int(r.get('minutes')),
                                'clean_sheets': 0,
                                'goals_against': 0,
                                'save_percentage': _pd.NA,
                            })
                        if rows:
                            comp_display = _pd.DataFrame(rows)
                    season_display = _pd.concat([gk_display, comp_display], ignore_index=True)
                    # Remove DFB Pokal bug rows
                    if not season_display.empty:
                        mask_bad_row = (
                            season_display['competition_name'].str.contains('DFB', na=False) &
                            season_display['competition_name'].str.contains('Pokal', na=False) &
                            (season_display['competition_type'] == 'LEAGUE')
                        )
                        season_display = season_display[~mask_bad_row]
                    # If still empty, fallback entirely to comp_stats (rare)
                    if season_display.empty and not comp_stats.empty:
                        season_display = comp_stats[['season', 'competition_type', 'competition_name', 'games', 'minutes']].copy()
                        season_display['games_starts'] = 0
                        season_display['clean_sheets'] = 0
                        season_display['save_percentage'] = _pd.NA
                        season_display['goals_against'] = 0
                        season_display = season_display[['season','competition_type','competition_name','games','games_starts','minutes','clean_sheets','goals_against','save_percentage']]
                    # Combine National Team rows per season into a single aggregate row
                    if not season_display.empty and 'competition_type' in season_display.columns:
                        national_comp_names = ['WCQ', 'World Cup', 'UEFA Nations League', 'UEFA Euro Qualifying', 'UEFA Euro', 'Friendlies (M)', 'World Cup Qualifying']
                        nt_mask = (season_display['competition_type'] == 'NATIONAL_TEAM') | (season_display['competition_name'].isin(national_comp_names))

                        # UJEDNOLICENIE (GK): w jednym wierszu "National Team (2025)" chcemy mieć:
                        # - Friendlies grane w 2025 (zwykle season=2025)
                        # - WCQ 2026, które bywa zapisane w bazie jako season=2026
                        # Dlatego WCQ 2026 przepinamy na season=2025 PRZED agregacją.
                        if nt_mask.any() and 'competition_name' in season_display.columns:
                            wcq_mask = season_display['competition_name'].astype(str).str.contains('WCQ|World Cup Qualifying', case=False, na=False)
                            season_is_2026 = season_display['season'].astype(str).isin(['2026', '2026-2027', '2026/2027']) | (season_display['season'] == 2026)
                            season_display.loc[nt_mask & wcq_mask & season_is_2026, 'season'] = '2025'

                        if nt_mask.any():
                            nt_agg = season_display[nt_mask].groupby('season', as_index=False).agg({
                                'competition_type': (lambda x: 'NATIONAL_TEAM'),
                                'competition_name': (lambda x: 'National Team (All)'),
                                'games': 'sum',
                                'games_starts': 'sum',
                                'minutes': 'sum',
                                'clean_sheets': 'sum',
                                'goals_against': 'sum',
                                'save_percentage': 'mean',
                            })
                            season_display = _pd.concat([season_display[~nt_mask], nt_agg], ignore_index=True)
                else:
                    # Outfield player stats
                    season_display = comp_stats[['season', 'competition_type', 'competition_name', 'games', 'goals', 'assists', 'xg', 'xa', 'yellow_cards', 'red_cards', 'minutes']].copy()
                    
                    # Aggregate National Team rows per season (WCQ + Friendlies => National Team (All))
                    if not season_display.empty and 'competition_type' in season_display.columns:
                        nt_mask = season_display['competition_type'] == 'NATIONAL_TEAM'
                        if nt_mask.any():
                            nt_agg = season_display[nt_mask].groupby('season', as_index=False).agg({
                                'competition_type': 'first',
                                'competition_name': (lambda x: 'National Team (All)'),
                                'games': 'sum',
                                'goals': 'sum',
                                'assists': 'sum',
                                'xg': 'sum',
                                'xa': 'sum',
                                'yellow_cards': 'sum',
                                'red_cards': 'sum',
                                'minutes': 'sum',
                            })
                            season_display = pd.concat([season_display[~nt_mask], nt_agg], ignore_index=True)
                # Normalize season display
                # IMPORTANT: Keep national team years as-is (2025), don't convert to season format (2025/26)
                def format_season(row):
                    s = str(row['season'])
                    comp_type = row.get('competition_type', '')
                    
                    # Keep national team years as single year (2025, not 2025/26)
                    if comp_type == 'NATIONAL_TEAM' or 'National' in str(comp_type):
                        # Extract just the year
                        if '-' in s:
                            return s.split('-')[0]  # "2025-2026" -> "2025"
                        return s  # "2025" -> "2025"
                    
                    # For club competitions, format as season
                    if s == '2025' or s == '2025-2026' or s == '2026':
                        return '2025/26'
                    elif '-' in s:
                        parts = s.split('-')
                        if len(parts) == 2 and len(parts[0]) == 4:
                            if len(parts[1]) == 4:
                                return f"{parts[0]}/{parts[1][2:]}"
                            else:
                                return f"{parts[0]}/{parts[1]}"
                    return s
                
                season_display['season'] = season_display.apply(format_season, axis=1)

                # --- SUPER CUP LABELING (history table) ---
                # Requirement: Super Cups should appear as separate rows in history, e.g.
                #   "2025-26 Domestic Cups - Supercopa de Espana"
                # They are excluded from Season Total, but remain in Domestic Cups column.
                super_cup_keywords = [
                    'super cup',
                    'uefa super cup',
                    'supercopa',
                    'supercoppa',
                    'superpuchar',
                    'community shield',
                    'supercup',
                    'dfl-supercup',
                    'supertaca',
                    'supertaça',
                    'trophée des champions',
                    'trofeo de campeones',
                ]

                def _format_season_short(season_str: str) -> str:
                    # Input is expected like "2025/26" after format_season
                    s = str(season_str or '')
                    if '/' in s:
                        a, b = s.split('/', 1)
                        b2 = b[-2:] if len(b) >= 2 else b
                        return f"{a}-{b2}"
                    return s

                if 'competition_name' in season_display.columns and 'season' in season_display.columns:
                    comp_series = season_display['competition_name'].astype(str)
                    sc_mask = pd.Series(False, index=season_display.index)
                    for kw in super_cup_keywords:
                        sc_mask = sc_mask | comp_series.str.contains(kw, case=False, na=False)

                    if sc_mask.any():
                        season_display.loc[sc_mask, 'season'] = season_display.loc[sc_mask].apply(
                            lambda r: f"{_format_season_short(r['season'])} Domestic Cups - {r['competition_name']}",
                            axis=1,
                        )

                # FIX: Aggregate duplicate rows after season normalization
                # This happens when we have both "2025" and "2026" in database which both become "2025/26"
                # IMPORTANT: National team rows should NOT be aggregated with club rows
                # National team shows year (2025), clubs show season (2025/26)
                if not season_display.empty:
                    # Group by season, competition_type, competition_name and sum numeric columns
                    if is_goalkeeper:
                        season_display = season_display.groupby(['season', 'competition_type', 'competition_name'], as_index=False).agg({
                            'games': 'sum',
                            'games_starts': 'sum',
                            'minutes': 'sum',
                            'clean_sheets': 'sum',
                            'goals_against': 'sum',
                            'save_percentage': 'mean'
                        })
                    else:
                        season_display = season_display.groupby(['season', 'competition_type', 'competition_name'], as_index=False).agg({
                            'games': 'sum',
                            'goals': 'sum',
                            'assists': 'sum',
                            'xg': 'sum',
                            'xa': 'sum',
                            'yellow_cards': 'sum',
                            'red_cards': 'sum',
                            'minutes': 'sum'
                        })
                # Sort by season (descending) and competition type to group similar competitions together
                # Define competition type order for sorting
                comp_type_order = {'LEAGUE': 1, 'EUROPEAN_CUP': 2, 'DOMESTIC_CUP': 3, 'NATIONAL_TEAM': 4}
                season_display['comp_sort'] = season_display['competition_type'].map(comp_type_order).fillna(5)
                season_display = season_display.sort_values(['season', 'comp_sort'], ascending=[False, True]).reset_index(drop=True)
                season_display = season_display.drop('comp_sort', axis=1)
                # Format competition type for display
                def format_comp_type(ct):
                    if ct == 'LEAGUE':
                        return '🏆 League'
                    elif ct == 'EUROPEAN_CUP':
                        return '🌍 European'
                    elif ct == 'DOMESTIC_CUP':
                        return '🏆 Domestic Cup'
                    elif ct == 'NATIONAL_TEAM':
                        return '🇵🇱 National'
                    else:
                        return ct
                season_display['competition_type'] = season_display['competition_type'].apply(format_comp_type)
                # Round xG and xA to 2 decimals (only for outfield players)
                if 'xg' in season_display.columns:
                    season_display['xg'] = season_display['xg'].apply(lambda x: round(x, 2) if pd.notna(x) else 0.0)
                if 'xa' in season_display.columns:
                    season_display['xa'] = season_display['xa'].apply(lambda x: round(x, 2) if pd.notna(x) else 0.0)
                # Fill NaN values with 0 for display
                season_display = season_display.fillna(0)
                # Convert numeric columns to int where appropriate, only if column exists
                for col in ['games', 'goals', 'clean_sheets', 'assists', 'shots', 'shots_on_target', 'yellow_cards', 'red_cards', 'minutes', 'goals_against']:
                    if col in season_display.columns:
                        season_display[col] = season_display[col].astype(int)
                # Round save_percentage for goalkeepers
                if 'save_percentage' in season_display.columns:
                    season_display['save_percentage'] = season_display['save_percentage'].apply(lambda x: round(x, 1) if pd.notna(x) else 0.0)
                # Rename columns for display
                if is_goalkeeper and not gk_stats.empty:
                    season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Starts', 'Minutes', 'CS', 'GA', 'Save%']
                else:
                    season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Goals', 'Assists', 'xG', 'xA', 'Yellow', 'Red', 'Minutes']
                # --- CLUB WORLD CUP LABELING (history table) ---
                if 'competition_name' in season_display.columns:
                    cwc_mask = season_display['competition_name'].apply(is_club_world_cup)
                    if cwc_mask.any() and 'season' in season_display.columns:
                        season_display.loc[cwc_mask, 'season'] = season_display.loc[cwc_mask, 'season'].astype(str) + ' Club World Cup'

                st.dataframe(season_display, use_container_width=True, hide_index=True)
            elif not player_stats.empty and len(player_stats) > 0:
                # Fallback to old stats if competition_stats not available
                st.write("---")
                st.write("**📊 Season Statistics History**")
                season_display = player_stats[['season', 'team', 'matches', 'goals', 'assists', 'yellow_cards', 'red_cards', 'minutes_played']].copy()
                season_display['season'] = season_display['season'].apply(lambda x: f"{x}/{x+1}")
                season_display.columns = ['Season', 'Team', 'Matches', 'Goals', 'Assists', 'Yellow', 'Red', 'Minutes']
                # --- CLUB WORLD CUP LABELING (history table) ---
                if 'competition_name' in season_display.columns:
                    cwc_mask = season_display['competition_name'].apply(is_club_world_cup)
                    if cwc_mask.any() and 'season' in season_display.columns:
                        season_display.loc[cwc_mask, 'season'] = season_display.loc[cwc_mask, 'season'].astype(str) + ' Club World Cup'

                st.dataframe(season_display, use_container_width=True, hide_index=True)
            # ===== NOWA SEKCJA: MECZE GRACZA ===== 
            # ===== NOWA SEKCJA: MECZE GRACZA ===== 
            player_matches = matches_df[matches_df['player_id'] == row['id']] if not matches_df.empty and 'player_id' in matches_df.columns else pd.DataFrame()
            
            if not player_matches.empty and len(player_matches) > 0:
                st.write("---")
                st.subheader("🏟️ Recent Matches (Season 2025/26)")
                
                # POPRAWKA: konwersja daty i sort malejąco po dacie
                pm = player_matches.copy()
                if pm['match_date'].dtype != 'datetime64[ns]':
                    pm['match_date'] = pd.to_datetime(pm['match_date'], errors='coerce')
                pm = pm.dropna(subset=['match_date'])
                pm = pm.sort_values('match_date', ascending=False)
                
                # Pokaż ostatnie 10 meczów
                recent_matches = pm.head(10)
                for idx_match, match in recent_matches.iterrows():
                    # Ikona wyniku
                    result_str = match['result'] if pd.notna(match['result']) else ''
                    if result_str.startswith('W'):
                        result_icon = "🟢"
                    elif result_str.startswith('D'):
                        result_icon = "🟡"
                    elif result_str.startswith('L'):
                        result_icon = "🔴"
                    else:
                        result_icon = "⚪"
                    # Format daty
                    match_date = pd.to_datetime(match['match_date']).strftime('%d.%m.%Y')
                    # Competition badge
                    comp = match['competition'] if pd.notna(match['competition']) else 'N/A'
                    venue_icon = "🏠" if match['venue'] == 'Home' else "✈️"
                    # Stats
                    goals = safe_int(match.get('goals'))
                    # Force assists to 0 for goalkeepers
                    if is_gk:
                        assists = 0
                    else:
                        assists = safe_int(match.get('assists'))
                    minutes = safe_int(match.get('minutes_played'))
                    # Wyświetl mecz
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                    with col1:
                        st.write(f"{result_icon}")
                    with col2:
                        opponent = match['opponent'] if pd.notna(match['opponent']) else 'Unknown'
                        st.write(f"**{venue_icon} vs {opponent}**")
                        st.caption(f"{comp} • {match_date}")
                    with col3:
                        st.write(f"**{result_str}**")
                        st.caption(f"{minutes}'")
                    with col4:
                        perf = f"{goals}G {assists}A"
                        if goals > 0 or assists > 0:
                            st.write(f"⚽ **{perf}**")
                        else:
                            st.write(f"{perf}")
                        # xG jeśli dostępne
                        if pd.notna(match['xg']) and match['xg'] > 0:
                            st.caption(f"xG: {match['xg']:.2f}")
                    st.write("")  # Odstęp między meczami
    # Download option
    st.write("---")
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name="polish_players.csv",
        mime="text/csv"
    )
else:
    if selected_team != 'All':
        st.warning(f"⚠️ No players found matching '{search_name}' in team '{selected_team}'")
        st.info("💡 Try removing the team filter or changing the search term")
    else:
        st.warning(f"⚠️ No players found matching '{search_name}'")
        st.info("💡 Try a different search term")
# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip**: Use filters to narrow down results or search by player name."
)
# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ========================================
# FOOTER - FBref Attribution
# ========================================
st.divider()
st.markdown("""
<div style='text-align: center; padding: 2rem 0 1rem 0; color: #8A8A8A; font-size: 0.875rem;'>
    <p style='margin-bottom: 0.5rem;'>
        📊 <strong>Data Source:</strong> 
        <a href='https://fbref.com/' target='_blank' style='color: #4ECDC4; text-decoration: none;'>
            FBref.com
        </a> (Sports Reference LLC)
    </p>
    <p style='font-size: 0.75rem; color: #B8B8B8; margin-bottom: 0.5rem;'>
        Player statistics powered by FBref - The leading source for football statistics
    </p>
    <p style='font-size: 0.7rem; color: #6A6A6A; margin-bottom: 0;'>
        Polish Football Data Hub International is an independent project and is not affiliated with FBref.com
    </p>
</div>
""", unsafe_allow_html=True)