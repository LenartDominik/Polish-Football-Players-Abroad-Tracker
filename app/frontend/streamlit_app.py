"""Polish Football Players Abroad - Streamlit Dashboard
A simple dashboard to browse and filter Polish football players data.
Usage:
    streamlit run app/frontend/streamlit_app.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import os
import streamlit.components.v1 as components

current = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(os.path.dirname(current))
sys.path.append(parent)

from app.frontend.api_client import get_api_client


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

def get_full_position(pos):
    """Convert position abbreviations to full names."""
    if not pos or pd.isna(pos):
        return "Unknown"
    
    mapping = {
        "GK": "Goalkeeper",
        "DF": "Defender",
        "MF": "Midfielder",
        "FW": "Forward",
        "BRAMKARZ": "Goalkeeper",
        "OBROŃCA": "Defender",
        "POMOCNIK": "Midfielder",
        "NAPASTNIK": "Forward"
    }
    
    parts = [p.strip().upper() for p in str(pos).split(',')]
    full_parts = [mapping.get(p, p.capitalize()) for p in parts]
    return ", ".join(full_parts)


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
    # 1. Sprawdź, czy DataFrame w ogóle istnieje
    if matches_df is None or matches_df.empty:
        return False
    
    # 2. POPRAWKA: Sprawdź, czy nazwa 'player_id' znajduje się w liście kolumn
    if 'player_id' not in matches_df.columns:
        return False
    
    # Dalej bez zmian...
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
        return {}
    
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


def clean_national_team_stats(df):
    """
    Deduplicate National Team statistics.
    If a season has both summary rows ('National Team', 'Reprezentacja', 'National Team (All)')
    and detailed rows ('WCQ', 'UEFA Euro', 'Friendlies', etc.), keep only the detailed rows.
    """
    if df is None or df.empty:
        return df
    
    # Standardize names for comparison
    def is_summary(name):
        n = str(name).lower().strip()
        # Checks if name starts with summary keywords or matches specific labels
        summary_keywords = ['national team', 'reprezentacja', 'national team (all)']
        return any(n.startswith(kw) for kw in summary_keywords)
    
    # Group by normalized season to check for duplicates
    df_copy = df.copy()
    
    # Internal normalization for grouping
    def get_norm_s(row):
        s = str(row.get('season', ''))
        c = str(row.get('competition_name', '')).lower()
        # Map WCQ 2026 to 2025 for grouping
        if '2026' in s and ('wcq' in c or 'qualify' in c or 'eliminacje' in c):
            return '2025'
        if '-' in s: return s.split('-')[0]
        if '/' in s: return s.split('/')[0]
        return s

    df_copy['temp_s'] = df_copy.apply(get_norm_s, axis=1)
    
    # Define priorities
    def get_priority(name):
        n = str(name).lower()
        if any(k in n for k in ['wcq', 'world cup', 'euro', 'nations league', 'eliminacje']): return 3 # Specific
        if 'friendly' in n: return 2 # General
        if is_summary(name): return 1 # Summary
        return 0

    groups = []
    # Process each normalized season group
    for _, group in df_copy.groupby('temp_s'):
        if len(group) <= 1:
            groups.append(group)
            continue
            
        group = group.copy()
        # 1. Drop obvious summaries if we have anything else
        has_any_details = group['competition_name'].apply(lambda x: get_priority(x) > 1).any()
        if has_any_details:
            group = group[~group['competition_name'].apply(is_summary)]
        
        if len(group) <= 1:
            groups.append(group)
            continue

        # 2. Smart Overlap Detection:
        # If "Friendlies (M)" (Priority 2) contains matches also listed in Priority 3 (WCQ/Euro), 
        # it will have >= games and minutes than Priority 3.
        specifics = group[group['competition_name'].apply(lambda x: get_priority(x) == 3)]
        generals = group[group['competition_name'].apply(lambda x: get_priority(x) == 2)]
        
        if not specifics.empty and not generals.empty:
            spec_games = specifics['games'].sum()
            spec_mins = specifics['minutes'].sum()
            
            # Check each 'General/Friendly' row for overlap
            new_generals = []
            for _, gen_row in generals.iterrows():
                # If specific row matches exactly or is a subset of this general row, 
                # subtract specific from general to see what's left.
                if gen_row['games'] >= spec_games and gen_row['minutes'] >= spec_mins:
                    rem_games = gen_row['games'] - spec_games
                    rem_mins = gen_row['minutes'] - spec_mins
                    
                    if rem_games > 0:
                        gen_row = gen_row.copy()
                        gen_row['games'] = rem_games
                        gen_row['minutes'] = rem_mins
                        # Keep other stats proportional if necessary, but usually friendlies 0 mins etc.
                        new_generals.append(pd.DataFrame([gen_row]))
                    # If rem_games == 0, this whole General row was just a container for the Specifics. DROP.
                else:
                    new_generals.append(pd.DataFrame([gen_row]))
            
            # Reconstruct group
            if not specifics.empty and new_generals:
                valid_generals = [df for df in new_generals if not df.empty]
                if valid_generals:
                    # Ensure same columns and use object dtype to avoid FutureWarning
                    objs = [specifics] + valid_generals
                    all_cols = specifics.columns
                    for obj in valid_generals:
                        all_cols = all_cols.union(obj.columns)
                    objs = [obj.reindex(columns=all_cols).astype(object) for obj in objs]
                    group = pd.concat(objs, ignore_index=True)
                    group = group.infer_objects()
                else:
                    group = specifics
            elif not specifics.empty:
                group = specifics
            elif new_generals:
                valid_generals = [df for df in new_generals if not df.empty]
                if len(valid_generals) == 1:
                    group = valid_generals[0]
                elif valid_generals:
                    # Ensure same columns and use object dtype to avoid FutureWarning
                    all_cols = valid_generals[0].columns
                    for obj in valid_generals[1:]:
                        all_cols = all_cols.union(obj.columns)
                    objs = [obj.reindex(columns=all_cols).astype(object) for obj in valid_generals]
                    group = pd.concat(objs, ignore_index=True)
                    group = group.infer_objects()
                else:
                    group = specifics # which is empty
            else:
                group = specifics # both empty
            
        groups.append(group)
            
    valid_groups = [g for g in groups if not g.empty]
    if not valid_groups:
        return df.drop(columns=['temp_s'], errors='ignore')
        
    if len(valid_groups) == 1:
        result = valid_groups[0]
    else:
        # Ensure same columns before concat and use object dtype to avoid FutureWarning
        all_cols = valid_groups[0].columns
        for g in valid_groups[1:]:
            all_cols = all_cols.union(g.columns)
        objs = [g.reindex(columns=all_cols).astype(object) for g in valid_groups]
        result = pd.concat(objs, ignore_index=True)
        result = result.infer_objects()
        
    if 'temp_s' in result.columns:
        result = result.drop(columns=['temp_s'])
    return result


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
    page_title="Polish Football Players Abroad - Stats & Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/LenartDominik/Polish-Football-Players-Abroad',
        'About': "# Polish Football Players Abroad\nTrack and compare statistics of Polish football players playing abroad."
    }
)




# SEO Meta Tags Injection
st.markdown(
    """
    <div style="display:none;">
        <!-- Google Search Console Verification -->
        <meta name="google-site-verification" content="0ZLLXAHagxMIf2Db4Dfh2PLJog9BGrhPIBmH51mi1dM" />
        
        <meta name="description" content="Detailed statistics and analytics for Polish football players playing abroad. Compare performance across leagues worldwide, including top European divisions and MLS.">
        <meta name="keywords" content="Polish football abroad, Polacy za granicą, football stats, Polish players tracker, Lewandowski, Zieliński, football analytics">
        <meta name="author" content="Polish Football Players Abroad">
    </div>
    """,
    unsafe_allow_html=True
)

# Centered app title at the top
st.markdown(
    """
    <h1 style='text-align: center; margin-bottom: 0.5em;'>Polish Football Players Abroad - Stats Tracker</h1>
    """,
    unsafe_allow_html=True
)

# Initialize API client

# Cached helpers for lazy per-player fetches
@st.cache_data(ttl=600, show_spinner=False)
def get_player_competition_stats_cached(player_id: int, season: str | None = None, competition_type: str | None = None) -> pd.DataFrame:
    """Fetch ALL competition stats for a player (all seasons, all competition types)"""
    api_client = get_api_client()
    df = api_client.get_competition_stats(player_id=player_id, season=season, competition_type=competition_type, limit=500)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_player_goalkeeper_stats_cached(player_id: int, season: str | None = None, competition_type: str | None = None) -> pd.DataFrame:
    """Fetch ALL goalkeeper stats for a player (all seasons, all competition types)"""
    api_client = get_api_client()
    df = api_client.get_goalkeeper_stats(player_id=player_id, season=season, competition_type=competition_type, limit=500)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_player_matchlogs_cached(player_id: int, season: str = "2025-2026", limit: int = 200, _cache_version: int = 2) -> pd.DataFrame:
    """Fetch matchlogs for a player. _cache_version forces cache invalidation when changed."""
    api_client = get_api_client()
    df = api_client.get_player_matches(player_id=player_id, season=season, limit=limit)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    """Load minimal data from API to reduce bandwidth usage.
    Only fetch players list initially; fetch heavy stats lazily per player when needed.
    """
    try:
        api_client = get_api_client()
        
        # Fetch only players (small payload)
        players_df = api_client.get_all_players()
        
        # FIX: Create DataFrames with explicit columns to prevent KeyError in filtering functions
        # This ensures that checks like "if 'player_id' in df" or "df['player_id']" work correctly even if empty.
        
        comp_stats_df = pd.DataFrame(columns=[
            'id', 'player_id', 'season', 'competition_type', 'competition_name', 
            'games', 'minutes', 'goals', 'assists', 'xg', 'xa'
        ])
        
        gk_stats_df = pd.DataFrame(columns=[
            'id', 'player_id', 'season', 'competition_type', 'competition_name',
            'clean_sheets', 'save_percentage', 'goals_against'
        ])
        
        matches_df = pd.DataFrame(columns=[
            'id', 'player_id', 'match_date', 'competition', 'opponent',
            'minutes_played', 'goals', 'assists'
        ])
        
        # Deprecated player_season_stats remains empty for backward compatibility
        stats_df = pd.DataFrame()
        
        return players_df, stats_df, comp_stats_df, gk_stats_df, matches_df
        
    except Exception as e:
        st.error(f"Error loading data from API: {e}")
        import traceback
        st.error(traceback.format_exc())
        
        # Return empty DataFrames with columns to prevent crashes downstream
        empty_players = pd.DataFrame(columns=['id', 'name', 'team', 'league'])
        empty_matches = pd.DataFrame(columns=['player_id'])
        return empty_players, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), empty_matches

# Sidebar - Search
st.sidebar.header("🔎 Player Search")
search_name = st.sidebar.text_input("Enter player name", placeholder="e.g. Lewandowski, Zieliński...")

# If there is a search term, fetch filtered players from API (server-side filter), else use initial df
api_client = get_api_client()
if search_name and len(search_name.strip()) >= 1:
    # Debounce-like behavior is limited in Streamlit; keep it simple
    try:
        df = api_client.get_all_players(name=search_name.strip(), limit=200)
    except Exception:
        pass

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
# Filters
teams = ['All'] + sorted(df['team'].dropna().unique().tolist())
selected_team = st.sidebar.selectbox("Team", teams)

# Players list (sorted names first, then prepended with 'All')
raw_players = [f"{row['name']} ({get_full_position(row.get('position'))})" for _, row in df.dropna(subset=['name']).iterrows()]
players_list = ['All'] + sorted(list(set(raw_players)))
selected_player_str = st.sidebar.selectbox("Player (optional)", players_list)

# Apply filters
filtered_df = df.copy()

# Filtruj po nazwisku
if search_name:
    filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False, na=False)]

# Filtruj po drużynie
if selected_team != 'All':
    filtered_df = filtered_df[filtered_df['team'].fillna('') == selected_team]

# Filtruj po wybraniu gracza z listy
if selected_player_str != 'All':
    # Extract name from string "Name (Position)"
    if " (" in selected_player_str:
        selected_player_name = selected_player_str.rsplit(" (", 1)[0]
    else:
        selected_player_name = selected_player_str
        
    filtered_df = filtered_df[filtered_df['name'] == selected_player_name]

# Jeśli nie ma wyszukiwania ANI filtru drużyny ANI gracza, nie pokazuj nic
if not search_name and selected_team == 'All' and selected_player_str == 'All':
    st.info("👆 Enter a player name, select a team, or choose a player to view statistics")
    
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
            Polish Football Players Abroad is an independent project and is not affiliated with FBref.com
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# Display filtered results
if not filtered_df.empty:
    for idx, row in filtered_df.iterrows():
        player_id = int(row['id'])
        # Leniwe pobieranie: per gracz
        position = str(row.get('position', '') or '').strip().upper()
        is_gk = position in ("GK", "BRAMKARZ", "GOALKEEPER")
        # Domyślny sezon i typ rozgrywek dla minimalnego transferu
        # Fetch ALL stats for this player (all seasons, all competition types)
        # This enables: 5 columns display + Season Statistics History with multiple seasons
        if is_gk:
            gk_stats = get_player_goalkeeper_stats_cached(player_id)  # No filters - get all
            comp_stats = get_player_competition_stats_cached(player_id)  # Also fetch for fallback
        else:
            comp_stats = get_player_competition_stats_cached(player_id)  # No filters - get all
            gk_stats = pd.DataFrame()
        
        # Matchlogs - fetch current season only (for Recent Matches display)
        matches_df = get_player_matchlogs_cached(player_id, season='2025-2026', limit=100)
        
        # Player season stats (deprecated) – pozostaje puste
        player_stats = pd.DataFrame()
        
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
                                if is_gk:
                                    m2.metric("CS", 0)
                                    m3.metric("GA", 0)
                                else:
                                    m2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
                                    m3.metric("Assists", safe_int(comp_row.get('assists')))

                    if not found_league:
                        st.info("No league stats for 2025-2026")

                # Dolna część: Szczegóły (poza kontenerem, więc zawsze na dole)
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
                             is_gk_display = is_gk
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

            # --- KOLUMNA 2: EUROPEAN / INTERNATIONAL CUPS ---
            with col2:
                with st.container(height=STATS_HEIGHT, border=False):
                    cups_header = "### 🌍 International Cups (2025-2026)" if row.get('league') == 'MLS' else "### 🌍 European Cups (2025-2026)"
                    st.write(cups_header)
                    
                    found_euro = False
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup from European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                            euro_stats = euro_stats[~euro_stats['competition_name'].str.contains('Leagues Cup', case=False, na=False)]
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
                            euro_stats = euro_stats[~euro_stats['competition_name'].str.contains('Leagues Cup', case=False, na=False)]
                        if not euro_stats.empty:
                            found_euro = True
                            for _, comp_row in euro_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(comp_row.get('games')))
                                if is_gk:
                                    m2.metric("CS", 0)
                                    m3.metric("GA", 0)
                                else:
                                    m2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
                                    m3.metric("Assists", safe_int(comp_row.get('assists')))

                    if not found_euro:
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
                            euro_stats = euro_stats[~euro_stats['competition_name'].str.contains('Leagues Cup', case=False, na=False)]
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
                            euro_stats = euro_stats[~euro_stats['competition_name'].str.contains('Leagues Cup', case=False, na=False)]
                        if not euro_stats.empty:
                            euro_stats_to_show = euro_stats
                            is_gk_display = is_gk
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
                                if is_gk:
                                    metric_col2.metric("CS", 0)
                                    metric_col3.metric("GA", 0)
                                else:
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
                            is_gk_display = is_gk
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
                        # Clean/Deduplicate
                        national_stats = clean_national_team_stats(national_stats)
                        
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
                            if is_gk:
                                m2.metric("CS", 0)
                                m3.metric("GA", 0)
                            else:
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
                        # Clean/Deduplicate
                        national_stats = clean_national_team_stats(national_stats)
                        
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
                            if total_xa > 0:
                                st.write(f"📊 **xAG:** {total_xa:.2f}")
                    else:
                        st.write("No details available.")

            # --- KOLUMNA 5: SEASON TOTAL (2025-2026) ---
            with (col6 if has_cwc and col6 is not None else col5):
                # GÓRA: Statystyki w sztywnym pudełku
                with st.container(height=STATS_HEIGHT, border=False):
                    is_mls = row.get('league') == 'MLS'
                    st.write("### 🏆 Season Total (2025-2026)")
                    
                    if is_mls:
                        caption = "Club competitions only (League + Domestic Cups + International Cups). Excludes National Team and Super Cups."
                    else:
                        caption = "Club competitions only (League + Domestic Cups + European Cups). Excludes Club World Cup, National Team, and Super Cups."
                    st.caption(caption)

                    # --- SUMMATION LOGIC FROM COMP_STATS (FOR CONSISTENCY) ---
                    total_games, total_starts, total_minutes = 0, 0, 0
                    total_goals, total_assists, total_xg, total_xa = 0, 0, 0.0, 0.0
                    total_clean_sheets, total_ga, total_saves, total_sota = 0, 0, 0, 0
                    
                    # Filtering for club season
                    current_season_filters = ['2025-2026', '2025/2026', '2025', 2025]
                    super_cup_keywords = [
                        'super cup', 'uefa super cup', 'supercopa', 'supercoppa', 'superpuchar',
                        'community shield', 'supercup', 'dfl-supercup', 'supertaca', 'supertaça',
                        'trophée des champions', 'trofeo de campeones'
                    ]

                    # 1. Outfield stats
                    if not comp_stats.empty:
                        # Filter for season
                        club_total_df = comp_stats[comp_stats['season'].isin(current_season_filters)].copy()
                        # Exclude National Team
                        club_total_df = club_total_df[club_total_df['competition_type'] != 'NATIONAL_TEAM']
                        # Exclude Super Cups
                        if not club_total_df.empty and 'competition_name' in club_total_df.columns:
                            sc_mask = pd.Series(False, index=club_total_df.index)
                            for kw in super_cup_keywords:
                                sc_mask = sc_mask | club_total_df['competition_name'].astype(str).str.contains(kw, case=False, na=False)
                            club_total_df = club_total_df[~sc_mask]
                        
                        if not club_total_df.empty:
                            total_games = int(club_total_df['games'].sum())
                            total_starts = int(club_total_df['games_starts'].sum())
                            total_minutes = int(club_total_df['minutes'].sum())
                            total_goals = int(club_total_df['goals'].sum())
                            total_assists = int(club_total_df['assists'].sum())
                            total_xg = float(club_total_df['xg'].sum())
                            total_xa = float(club_total_df['xa'].sum())

                    # 2. Goalkeeper stats
                    if is_gk and not gk_stats.empty:
                        gk_club_total = gk_stats[gk_stats['season'].isin(current_season_filters)].copy()
                        gk_club_total = gk_club_total[gk_club_total['competition_type'] != 'NATIONAL_TEAM']
                        if not gk_club_total.empty and 'competition_name' in gk_club_total.columns:
                            sc_mask = pd.Series(False, index=gk_club_total.index)
                            for kw in super_cup_keywords:
                                sc_mask = sc_mask | gk_club_total['competition_name'].astype(str).str.contains(kw, case=False, na=False)
                            gk_club_total = gk_club_total[~sc_mask]
                        
                        if not gk_club_total.empty:
                            total_clean_sheets = int(gk_club_total['clean_sheets'].sum())
                            total_ga = int(gk_club_total['goals_against'].sum())
                            total_saves = int(gk_club_total['saves'].sum())
                            total_sota = int(gk_club_total['shots_on_target_against'].sum())
                            # If outfield stats were empty, use GK minutes/starts
                            if total_minutes == 0:
                                total_games = int(gk_club_total['games'].sum())
                                total_starts = int(gk_club_total['games_starts'].sum())
                                total_minutes = int(gk_club_total['minutes'].sum())

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
                            club_season_filters = ['2025-2026', '2025/2026', '2025', 2025]
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
                        # FIX: Only show this section if player actually has data (don't show "not synced" message)
            if str(row['position']).strip().upper() not in ["GK", "BRAMKARZ", "GOALKEEPER"]:
                if not player_stats.empty:
                    # Pobieramy wszystkie wiersze dla obecnego sezonu
                    season_current_raw = player_stats[player_stats['season'].isin(current_season)].copy()
                    
                    if not season_current_raw.empty:
                        # Definiujemy kolumny, które chcemy zsumować
                        cols_to_sum = [
                            'progressive_passes', 'progressive_carries', 'progressive_carrying_distance', 'progressive_passes_received',
                            'shots_total', 'shots_on_target', 'penalty_kicks_made',
                            'passes_completed', 'passes_attempted', 'key_passes', 'passes_into_penalty_area',
                            'shot_creating_actions', 'goal_creating_actions',
                            'tackles', 'tackles_won', 'interceptions', 'blocks',
                            'touches', 'dribbles_completed', 'dribbles_attempted', 'carries', 'ball_recoveries',
                            'aerials_won', 'aerials_lost', 'fouls_committed', 'fouls_drawn', 'offsides'
                        ]
                        
                        # Konwertujemy na liczby i sumujemy (agregacja wierszy Liga + Puchary + Kadra)
                        agg_stats = {}
                        for col in cols_to_sum:
                            if col in season_current_raw.columns:
                                # Konwersja na numeric + suma
                                val = pd.to_numeric(season_current_raw[col], errors='coerce').sum()
                                agg_stats[col] = val
                            else:
                                agg_stats[col] = 0

                        # Specjalne obliczenia dla procentów (średnia ważona byłaby idealna, ale tu uprościmy: obliczamy na podstawie sum)
                        # Shots Accuracy
                        if agg_stats['shots_total'] > 0:
                            agg_stats['shots_on_target_pct'] = (agg_stats['shots_on_target'] / agg_stats['shots_total']) * 100
                        else:
                            agg_stats['shots_on_target_pct'] = 0.0

                        # Pass Accuracy
                        if agg_stats['passes_attempted'] > 0:
                            agg_stats['pass_completion_pct'] = (agg_stats['passes_completed'] / agg_stats['passes_attempted']) * 100
                        else:
                            agg_stats['pass_completion_pct'] = 0.0


                        # === WYŚWIETLANIE METRYK (Korzystamy z agg_stats zamiast iloc[0]) ===

                        # --- Progressive Stats ---
                        has_prog_data = any(agg_stats[k] > 0 for k in ['progressive_passes', 'progressive_carries', 'progressive_carrying_distance'])
                        if has_prog_data:
                            st.write("---")
                            st.write("### 📊 Advanced Progression Stats")
                            st.caption("*Aggregated statistics (League + Cups + National Team)*")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if agg_stats['progressive_passes'] > 0:
                                    st.metric("Progressive Passes", int(agg_stats['progressive_passes']))
                            with col2:
                                if agg_stats['progressive_carries'] > 0:
                                    st.metric("Progressive Carries", int(agg_stats['progressive_carries']))
                            with col3:
                                if agg_stats['progressive_carrying_distance'] > 0:
                                    st.metric("Prog. Carry Distance", f"{int(agg_stats['progressive_carrying_distance'])}m")
                            with col4:
                                if agg_stats['progressive_passes_received'] > 0:
                                    st.metric("Prog. Passes Received", int(agg_stats['progressive_passes_received']))

                        # --- Shooting Stats ---
                        if agg_stats['shots_total'] > 0:
                            st.write("---")
                            st.subheader("⚽ Shooting Stats")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Shots", int(agg_stats['shots_total']))
                            with col2:
                                st.metric("Shots on Target", int(agg_stats['shots_on_target']))
                            with col3:
                                st.metric("Accuracy", f"{agg_stats['shots_on_target_pct']:.1f}%")
                            with col4:
                                if agg_stats['penalty_kicks_made'] > 0:
                                    st.metric("Penalties", int(agg_stats['penalty_kicks_made']))

                        # --- Passing Stats ---
                        if agg_stats['passes_completed'] > 0:
                            st.write("---")
                            st.subheader("🎯 Passing Stats")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Passes", f"{int(agg_stats['passes_completed'])}/{int(agg_stats['passes_attempted'])}")
                            with col2:
                                st.metric("Pass Accuracy", f"{agg_stats['pass_completion_pct']:.1f}%")
                            with col3:
                                st.metric("Key Passes", int(agg_stats['key_passes']))
                            with col4:
                                st.metric("Into Pen. Area", int(agg_stats['passes_into_penalty_area']))

                        # --- Creating Actions ---
                        if agg_stats['shot_creating_actions'] > 0:
                            st.write("---")
                            st.subheader("🎨 Creating Actions")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Shot Creating Actions", int(agg_stats['shot_creating_actions']))
                            with col2:
                                st.metric("Goal Creating Actions", int(agg_stats['goal_creating_actions']))

                        # --- Defensive Stats ---
                        if agg_stats['tackles'] > 0:
                            st.write("---")
                            st.subheader("🛡️ Defensive Stats")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Tackles", int(agg_stats['tackles']))
                            with col2:
                                st.metric("Tackles Won", int(agg_stats['tackles_won']))
                            with col3:
                                st.metric("Interceptions", int(agg_stats['interceptions']))
                            with col4:
                                st.metric("Blocks", int(agg_stats['blocks']))

                        # --- Possession Stats ---
                        if agg_stats['touches'] > 0:
                            st.write("---")
                            st.subheader("🏃 Possession Stats")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Touches", int(agg_stats['touches']))
                            with col2:
                                st.metric("Dribbles", f"{int(agg_stats['dribbles_completed'])}/{int(agg_stats['dribbles_attempted'])}")
                            with col3:
                                st.metric("Carries", int(agg_stats['carries']))
                            with col4:
                                st.metric("Ball Recoveries", int(agg_stats['ball_recoveries']))

                        # --- Miscellaneous ---
                        if agg_stats['aerials_won'] > 0:
                            st.write("---")
                            st.subheader("📊 Miscellaneous")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Aerials Won", f"{int(agg_stats['aerials_won'])}/{int(agg_stats['aerials_won']) + int(agg_stats['aerials_lost'])}")
                            with col2:
                                st.metric("Fouls Committed", int(agg_stats['fouls_committed']))
                            with col3:
                                st.metric("Fouls Drawn", int(agg_stats['fouls_drawn']))
                            with col4:
                                st.metric("Offsides", int(agg_stats['offsides']))

            
            # TABELA STATYSTYK HISTORYCZNYCH - ALL COMPETITIONS
            # For goalkeepers, use goalkeeper_stats table; for others, use competition_stats
            is_goalkeeper = str(row.get('position', '')).strip().upper() in ['GK', 'GOALKEEPER', 'BRAMKARZ']
            stats_to_display = gk_stats if (is_goalkeeper and not gk_stats.empty) else comp_stats
            
            if not stats_to_display.empty and len(stats_to_display) > 0:
                st.write("---")
                st.write("**📊 Season Statistics History (All Competitions)**")
                
                # --- Create display dataframe (zmienne muszą być widoczne dla obu ścieżek) ---
                rows = []  
                gk_display = pd.DataFrame()
                comp_display = pd.DataFrame()

                if is_goalkeeper:
                    # Standardized columns for all goalkeepers (ordered exactly as requested)
                    gk_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                    
                    if not gk_stats.empty:
                        gk_display = gk_stats.reindex(columns=gk_cols).copy()
                    else:
                        gk_display = pd.DataFrame(columns=gk_cols)
                    
                    # Add missing competitions from comp_stats as fallback rows
                    comp_needed = ['LEAGUE','EUROPEAN_CUP','DOMESTIC_CUP','NATIONAL_TEAM']
                    if not comp_stats.empty:
                        comp_subset = comp_stats[comp_stats['competition_type'].isin(comp_needed)].copy()
                        # Klucze istniejące już w gk_display
                        # Klucze istniejące już w gk_display (żeby nie dodawać duplikatów z comp_stats)
                        gk_keys = set()
                        # Dodatkowy set dla sezonów, w których już są dane reprezentacyjne (żeby uniknąć dubli typu WCQ vs National Team)
                        gk_nt_seasons = set()
                        
                        if not gk_display.empty:
                            # Tworzymy unikalne klucze dla istniejących wierszy
                            for _, r in gk_display.iterrows():
                                s = str(r['season'])
                                ct = str(r['competition_type'])
                                cn = str(r.get('competition_name', ''))
                                gk_keys.add((s, ct, cn))
                                
                                # Jeśli to wiersz reprezentacyjny, zapamiętaj sezon
                                if ct == 'NATIONAL_TEAM' or 'National Team' in cn or 'Reprezentacja' in cn or 'WCQ' in cn or 'Euro' in cn:
                                    gk_nt_seasons.add(s)
                        
                        for _, r in comp_subset.iterrows():
                            s = str(r['season'])
                            ct = str(r['competition_type'])
                            cn = str(r.get('competition_name', ''))

                            # Check if exists
                            key = (s, ct, cn)
                            if key in gk_keys:
                                continue
                            
                            # Check if exists (loose NT match)
                            # Jeśli dodajemy wiersz reprezentacyjny, sprawdź czy dla tego sezonu już coś mamy w gk_nt_seasons
                            is_nt_row = (ct == 'NATIONAL_TEAM' or 'National Team' in cn or 'Reprezentacja' in cn or 'WCQ' in cn)
                            if is_nt_row and s in gk_nt_seasons:
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
                                'save_percentage': None,
                            })
                else:
                    # LOGIKA DLA GRACZY Z POLA (OUTFIELD PLAYERS)
                    # Tutaj przypisujemy comp_stats do comp_display, żeby dalsza część kodu miała na czym pracować
                    if not comp_stats.empty:
                        comp_display = comp_stats.copy()
                    
                # --- KONIEC BLOKU TWORZENIA DANYCH ---
                
                # Teraz zmienna `rows` istnieje (może być pusta dla gracza z pola)
                # Zmienne `gk_display` i `comp_display` też istnieją.
                
                # 1. Przygotowanie danych (Rows -> DataFrame)
                if rows:
                    comp_display_from_rows = pd.DataFrame(rows)
                    # Jeśli mamy już comp_display (z bloku else), to je łączymy, jeśli nie - używamy tego z rows
                    if comp_display.empty:
                        comp_display = comp_display_from_rows
                    else:
                        if not comp_display_from_rows.empty:
                            # Robust merge for comp_display
                            all_cols = comp_display.columns.union(comp_display_from_rows.columns)
                            objs = [
                                comp_display.reindex(columns=all_cols).astype(object),
                                comp_display_from_rows.reindex(columns=all_cols).astype(object)
                            ]
                            comp_display = pd.concat(objs, ignore_index=True)

                # 2. Bezpieczne łączenie (Fix na FutureWarning)
                dfs_to_concat = [df for df in [gk_display, comp_display] if not df.empty]
                
                if dfs_to_concat:
                    if len(dfs_to_concat) == 1:
                        season_display = dfs_to_concat[0]
                    else:
                        # Ensure same columns before concat and use object dtype to avoid FutureWarning
                        all_cols = dfs_to_concat[0].columns
                        for df in dfs_to_concat[1:]:
                            all_cols = all_cols.union(df.columns)
                        objs = [df.reindex(columns=all_cols).astype(object) for df in dfs_to_concat]
                        season_display = pd.concat(objs, ignore_index=True)
                        # Optional: convert back to more specific dtypes
                        season_display = season_display.infer_objects()
                else:
                    season_display = pd.DataFrame()

                # --- AGGREGATION: GROUP NATIONAL TEAM STATS FOR GK ---
                if is_goalkeeper and not season_display.empty:
                    # Ensure season_display is the base
                    # ... logic checked below ...
                    pass

                if not season_display.empty:

                    # --- AGGREGATION: GROUP NATIONAL TEAM STATS FOR GK ---
                    if is_goalkeeper and not season_display.empty:
                        # Ensure season_display is the base
                        gk_display = season_display
                        
                        # Narrow down NT rows - avoid catching "Europa League" with "Euro" or club "Friendly"
                        # Use word boundaries or specific prefixes
                        ntm = (gk_display['competition_type'] == 'NATIONAL_TEAM') | \
                              (gk_display['competition_name'].fillna('').astype(str).str.contains(r'\bWorld Cup\b|UEFA Euro|\bEuro Qualifying\b|Nations League|Reprezentacja|Eliminacje', case=False)) | \
                              (gk_display['competition_name'].apply(lambda x: str(x) in ['WCQ', 'Friendlies (M)', 'World Cup Qualifying', 'UEFA Euro Qualifying', 'National Team', 'National Team (All)']))
                        
                        if ntm.any():
                            nt_df = gk_display[ntm].copy()
                            club_df = gk_display[~ntm].copy()
                            
                            # Normalize seasons for NT
                            def normalize_nt_season(row):
                                s = str(row['season'])
                                c = str(row['competition_name'])
                                if '2026' in s and ('WCQ' in c or 'Qualifying' in c):
                                    return '2025'
                                if '-' in s:
                                    return s.split('-')[0]
                                if '/' in s:
                                    return s.split('/')[0]
                                return s

                            nt_df['season_group'] = nt_df.apply(normalize_nt_season, axis=1)
                            
                            # --- FIX DOUBLE COUNTING ---
                            # Before aggregating, check if we have both SUMMARY rows (e.g. "National Team") 
                            # and DETAILED rows (e.g. "WCQ") for the same season group.
                            # Use shared helper (renaming season for compatibility)
                            nt_df = nt_df.rename(columns={'season': 'original_season', 'season_group': 'season'})
                            nt_df = clean_national_team_stats(nt_df)
                            nt_df = nt_df.rename(columns={'season': 'season_group', 'original_season': 'season'})
                            # ---------------------------
                            
                            agg_funcs = {
                                'games': 'sum',
                                'games_starts': 'sum',
                                'minutes': 'sum',
                                'clean_sheets': 'sum',
                                'goals_against': 'sum',
                                'saves': 'sum',
                                'shots_on_target_against': 'sum'
                            }
                            available_funcs = {k: v for k,v in agg_funcs.items() if k in nt_df.columns}
                            
                            nt_grouped = nt_df.groupby('season_group').agg(available_funcs).reset_index()
                            nt_grouped = nt_grouped.rename(columns={'season_group': 'season'})
                            nt_grouped['competition_type'] = 'NATIONAL_TEAM'
                            nt_grouped['competition_name'] = 'National Team'
                            
                            if 'saves' in nt_grouped.columns and 'shots_on_target_against' in nt_grouped.columns:
                                nt_grouped['save_percentage'] = nt_grouped.apply(
                                    lambda x: (x['saves'] / x['shots_on_target_against'] * 100) if x['shots_on_target_against'] > 0 else 0.0, 
                                    axis=1
                                )
                            
                            if not club_df.empty and not nt_grouped.empty:
                                # Ensure same columns and use object dtype to avoid FutureWarning
                                all_cols = club_df.columns.union(nt_grouped.columns)
                                objs = [
                                    club_df.reindex(columns=all_cols).astype(object),
                                    nt_grouped.reindex(columns=all_cols).astype(object)
                                ]
                                gk_display = pd.concat(objs, ignore_index=True)
                                gk_display = gk_display.infer_objects()
                            elif not nt_grouped.empty:
                                gk_display = nt_grouped
                            else:
                                gk_display = club_df
                            
                             # Filter out potential summary rows (Season 'All', 'Career' etc.)
                            gk_display = gk_display[gk_display['season'].astype(str).str.contains(r'\d', regex=True)]
                            
                            gk_display = gk_display.sort_values(by='season', ascending=False)
                            season_display = gk_display
                elif dfs_to_concat:
                    # Fallback if valid dfs existed but concat produced empty? unlikely
                     season_display = pd.concat(dfs_to_concat, ignore_index=True)
                else:
                    season_display = pd.DataFrame()

                # --- FIX: DATA CLEANING FOR DATAFRAME ---
                # 3. Główna logika przetwarzania (jeśli są dane)
                if not season_display.empty:
                    # Dynamic mapping for competition types based on league
                    if row.get('league') == 'MLS':
                        type_mapping = {
                            'LEAGUE': 'League',
                            'EUROPEAN_CUP': 'International Cup',
                            'DOMESTIC_CUP': 'Domestic Cup',
                            'NATIONAL_TEAM': 'National Team'
                        }
                    else:
                        type_mapping = {
                            'LEAGUE': 'League',
                            'EUROPEAN_CUP': 'European Cup',
                            'DOMESTIC_CUP': 'Domestic Cup',
                            'NATIONAL_TEAM': 'National Team'
                        }
                    
                    if 'competition_type' in season_display.columns:
                        season_display['competition_type'] = season_display['competition_type'].map(type_mapping).fillna(season_display['competition_type'])
                        # Specific override for Leagues Cup to be Domestic Cup
                        if 'competition_name' in season_display.columns:
                            is_leagues_cup = season_display['competition_name'].str.contains('Leagues Cup', case=False, na=False)
                            season_display.loc[is_leagues_cup, 'competition_type'] = 'Domestic Cup'
                    # Usuwanie błędnych wierszy DFB Pokal oznaczonych jako LEAGUE
                    if 'competition_name' in season_display.columns:
                        mask_bad_row = (
                            season_display['competition_name'].str.contains('DFB', na=False) &
                            season_display['competition_name'].str.contains('Pokal', na=False) &
                            (season_display['competition_type'] == 'LEAGUE')
                        )
                        season_display = season_display[~mask_bad_row]

                    # Fallback: Jeśli po czyszczeniu tabela jest pusta, użyj surowych danych comp_stats
                    if season_display.empty and not comp_stats.empty:
                        season_display = comp_stats.copy()
                        # Upewniamy się, że kluczowe kolumny istnieją (inicjalizacja zerami jeśli brak)
                        required_cols = ['games_starts', 'clean_sheets', 'goals_against', 'save_percentage', 'goals', 'assists', 'xg', 'xa']
                        for col in required_cols:
                            if col not in season_display.columns:
                                season_display[col] = 0

                    # Typ gracza (Bramkarz vs Gracz z pola) ustalony wcześniej na podstawie pozycji (is_goalkeeper)

                    # 4. Agregacja Reprezentacji (National Team)
                    if 'competition_type' in season_display.columns:
                        national_comp_names = ['WCQ', 'World Cup', 'UEFA Nations League', 'UEFA Euro Qualifying', 'UEFA Euro', 'Friendlies (M)', 'World Cup Qualifying']
                        nt_mask = (season_display['competition_type'] == 'NATIONAL_TEAM') | (season_display['competition_name'].isin(national_comp_names))

                        # Fix na lata (np. WCQ 2026 grane w 2025 -> przypisz do sezonu 2025)
                        if nt_mask.any() and 'competition_name' in season_display.columns:
                            wcq_mask = season_display['competition_name'].astype(str).str.contains('WCQ|World Cup Qualifying', case=False, na=False)
                            season_is_2026 = season_display['season'].astype(str).isin(['2026', '2026-2027', '2026/2027']) | (season_display['season'] == 2026)
                            season_display.loc[nt_mask & wcq_mask & season_is_2026, 'season'] = '2025'

                        if nt_mask.any():
                            # Rozdzielamy dane
                            nt_df = season_display[nt_mask].copy()
                            club_df = season_display[~nt_mask].copy()

                            if is_goalkeeper:
                                # Logika dla BRAMKARZA
                                agg_rules = {
                                    'competition_type': (lambda x: 'NATIONAL_TEAM'),
                                    'competition_name': (lambda x: 'National Team (All)'),
                                    'games': 'sum',
                                    'games_starts': 'sum',
                                    'minutes': 'sum',
                                    'clean_sheets': 'sum',
                                    'goals_against': 'sum',
                                    'save_percentage': 'mean'
                                }
                            else:
                                # Logika dla GRACZA Z POLA (Outfield)
                                agg_rules = {
                                    'competition_type': (lambda x: 'NATIONAL_TEAM'),
                                    'competition_name': (lambda x: 'National Team (All)'),
                                    'games': 'sum',
                                    'minutes': 'sum',
                                    'goals': 'sum',
                                    'assists': 'sum',
                                    'xg': 'sum',
                                    'xa': 'sum',
                                    'yellow_cards': 'sum',
                                    'red_cards': 'sum'
                                }

                            # Filtrujemy reguły agregacji (tylko kolumny, które faktycznie istnieją)
                            final_agg_rules = {k: v for k, v in agg_rules.items() if k in nt_df.columns}

                            # Grupujemy i łączymy
                            if final_agg_rules and not nt_df.empty:
                                nt_agg = nt_df.groupby('season', as_index=False).agg(final_agg_rules)
                                if not club_df.empty and not nt_agg.empty:
                                    # Ensure same columns and use object dtype to avoid FutureWarning
                                    all_cols = club_df.columns.union(nt_agg.columns)
                                    objs = [
                                        club_df.reindex(columns=all_cols).astype(object),
                                        nt_agg.reindex(columns=all_cols).astype(object)
                                    ]
                                    season_display = pd.concat(objs, ignore_index=True)
                                    season_display = season_display.infer_objects()
                                elif not nt_agg.empty:
                                    season_display = nt_agg
                                else:
                                    season_display = club_df

                    # 5. Formatowanie nazwy sezonu (np. 2025-2026 -> 2025/26)
                    def format_season(row):
                        s = str(row['season'])
                        comp_type = str(row.get('competition_type', ''))
                        
                        # Dla kadry zostawiamy sam rok (np. "2025")
                        if comp_type == 'NATIONAL_TEAM' or 'National' in comp_type:
                            if '-' in s:
                                return s.split('-')[0]
                            return s
                        
                        # Dla klubów formatujemy na XX/YY
                        if s == '2025' or s == '2025-2026' or s == '2026':
                            return '2025/26'
                        elif '-' in s:
                            parts = s.split('-')
                            if len(parts) == 2 and len(parts[0]) == 4:
                                # Np. 2023-2024 -> 2023/24
                                suffix = parts[1][2:] if len(parts[1]) == 4 else parts[1]
                                return f"{parts[0]}/{suffix}"
                        return s

                    if 'season' in season_display.columns:
                        season_display['season'] = season_display.apply(format_season, axis=1)

                    # 6. Finalne czyszczenie typów (Fix na FutureWarning: Downcasting)
                    season_display = season_display.fillna(0).infer_objects(copy=False)

                    # --- SUPER CUP LABELING (history table) ---
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
                    if not season_display.empty:
                        # Group by season, competition_type, competition_name and sum numeric columns
                                            # FIX: Aggregate duplicate rows after season normalization
                        if is_goalkeeper:
                        # Sprawdzamy, które kolumny bramkarskie faktycznie istnieją
                            gk_aggs = {
                                'games': 'sum',
                                'games_starts': 'sum',
                                'minutes': 'sum',
                                'clean_sheets': 'sum',
                                'goals_against': 'sum',
                                'save_percentage': 'mean'
                            }
                            valid_gk_aggs = {k: v for k, v in gk_aggs.items() if k in season_display.columns}
                            
                            if valid_gk_aggs:
                                season_display = season_display.groupby(['season', 'competition_type', 'competition_name'], as_index=False).agg(valid_gk_aggs)
                        else:
                            # Sprawdzamy, które kolumny dla graczy z pola faktycznie istnieją
                            mappings = [
                                ('games', ['Games', 'games', 'matches', 'Matches']),
                                ('goals', ['Goals', 'goals']),
                                ('assists', ['Assists', 'assists']),
                                ('xg', ['xG', 'xg', 'Xg']),
                                ('xa', ['xA', 'xa', 'Xa']),
                                ('yellow_cards', ['Yellow', 'yellow_cards', 'yellow']),
                                ('red_cards', ['Red', 'red_cards', 'red']),
                                ('minutes', ['Minutes', 'minutes', 'Minutes Played'])
                            ]

                            final_aggs = {}

                            for target_col, candidates in mappings:
                                # Szukamy pierwszej pasującej kolumny
                                found_col = next((c for c in candidates if c in season_display.columns), None)
                                
                                if found_col:
                                    # Konwertujemy na liczbę (naprawia błąd typów!)
                                    # Używamy target_col jako ujednoliconej nazwy
                                    season_display[target_col] = pd.to_numeric(season_display[found_col], errors='coerce').fillna(0)
                                    final_aggs[target_col] = 'sum'

                            if final_aggs:
                                season_display = season_display.groupby(['season', 'competition_type', 'competition_name'], as_index=False).agg(final_aggs)
                            else:
                                season_display = season_display.drop_duplicates(subset=['season', 'competition_type', 'competition_name'])

                        # Sort by season (descending) and competition type
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
                    
                    # Convert numeric columns to int where appropriate
                    for col in ['games', 'goals', 'clean_sheets', 'assists', 'shots', 'shots_on_target', 'yellow_cards', 'red_cards', 'minutes', 'goals_against']:
                        if col in season_display.columns:
                            season_display[col] = season_display[col].astype(int)
                    
                    # Round save_percentage for goalkeepers
                    if 'save_percentage' in season_display.columns:
                        season_display['save_percentage'] = season_display['save_percentage'].apply(lambda x: round(x, 1) if pd.notna(x) else 0.0)
                    
                    if is_goalkeeper:
                        # Oczekujemy 9 kolumn dla bramkarza (ordered exactly as requested)
                        expected_gk_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                        
                        # Reorder columns to ensure exact sequence: season, type, name, games, starts, minutes, cs, ga, save%
                        for col in expected_gk_cols:
                            if col not in season_display.columns:
                                season_display[col] = 0
                        
                        season_display = season_display[expected_gk_cols]
                        season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Starts', 'Minutes', 'CS', 'GA', 'Save%']

                    else:
                        # Oczekujemy 11 kolumn dla gracza z pola
                        # Musimy upewnić się, że season_display ma dokładnie te kolumny, których oczekujemy
                        field_cols_order = ['season', 'competition_type', 'competition_name', 'games', 'goals', 'assists', 'xg', 'xa', 'yellow_cards', 'red_cards', 'minutes']
                        
                        # Tworzymy nowy DF tylko z istniejących kolumn w odpowiedniej kolejności
                        # Brakujące kolumny wypełniamy zerami, żeby pasowało do 11 nazw
                        for col in field_cols_order:
                            if col not in season_display.columns:
                                season_display[col] = 0
                        
                        # Reorganizujemy kolejność, żeby pasowała do listy nazw
                        season_display = season_display[field_cols_order]
                        
                        # Teraz mamy pewność, że jest 11 kolumn -> zmieniamy nazwy
                        season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Goals', 'Assists', 'xG', 'xA', 'Yellow', 'Red', 'Minutes']
                    
                    # --- CLUB WORLD CUP LABELING (history table) ---
                    if 'Competition' in season_display.columns:
                        cwc_mask = season_display['Competition'].apply(is_club_world_cup)
                        if cwc_mask.any() and 'Season' in season_display.columns:
                            season_display.loc[cwc_mask, 'Season'] = season_display.loc[cwc_mask, 'Season'].astype(str) + ' Club World Cup'

                    st.dataframe(season_display, width='stretch', hide_index=True)
                elif not player_stats.empty and len(player_stats) > 0:
                    # Fallback to old stats if competition_stats not available
                    st.write("---")
                    st.write("**📊 Season Statistics History**")
                    season_display = player_stats[['season', 'team', 'matches', 'goals', 'assists', 'yellow_cards', 'red_cards', 'minutes_played']].copy()
                    season_display['season'] = season_display['season'].apply(lambda x: f"{x}/{x+1}")
                    season_display.columns = ['Season', 'Team', 'Matches', 'Goals', 'Assists', 'Yellow', 'Red', 'Minutes']
                    st.dataframe(season_display, width='stretch', hide_index=True)
            
                        # ===== NOWA SEKCJA: MECZE GRACZA ===== 
            # Use already lazy-loaded matches_df from line 490 (no need to filter again)
            player_matches = matches_df
            
            if not player_matches.empty and len(player_matches) > 0:
                st.write("---")
                st.subheader("🏟️ Recent Matches (Season 2025/26)")
                
                # POPRAWKA: konwersja daty i sort malejąco po dacie
                pm = player_matches.copy()
                # Bezpieczna konwersja daty
                if 'match_date' in pm.columns:
                    pm['match_date'] = pd.to_datetime(pm['match_date'], errors='coerce')
                    pm = pm.dropna(subset=['match_date'])
                    pm = pm.sort_values('match_date', ascending=False)
                
                # Pokaż ostatnie 10 meczów
                recent_matches = pm.head(10)

                for idx_match, match in recent_matches.iterrows():
                    # --- DEFINICJE ZMIENNYCH DLA POJEDYNCZEGO MECZU ---
                    
                    # 1. Wynik meczu i ikona
                    raw_result = match.get('result', '')
                    result_str = str(raw_result) if pd.notna(raw_result) else ''
                    
                    if result_str.startswith('W'):
                        result_icon = "🟢"
                    elif result_str.startswith('D'):
                        result_icon = "🟡"
                    elif result_str.startswith('L'):
                        result_icon = "🔴"
                    else:
                        result_icon = "⚪"
                    
                    # 2. Format daty
                    match_date_str = ""
                    if pd.notna(match.get('match_date')):
                        match_date_str = pd.to_datetime(match['match_date']).strftime('%d.%m.%Y')
                    
                    # 3. Podstawowe dane meczowe
                    comp = match.get('competition', 'N/A')
                    venue_icon = "🏠" if match.get('venue') == 'Home' else "✈️"
                    opponent = match.get('opponent', 'Unknown')
                    
                    # 4. Statystyki liczbowe (bezpieczne pobieranie)
                    def safe_get_int(val):
                        try:
                            return int(val) if pd.notna(val) else 0
                        except:
                            return 0

                    goals = safe_get_int(match.get('goals'))
                    # Force assists to 0 for goalkeepers if variable exists, else assume False
                    local_is_gk = locals().get('is_goalkeeper', False) # Bezpiecznik
                    assists = 0 if local_is_gk else safe_get_int(match.get('assists'))
                    minutes = safe_get_int(match.get('minutes_played'))
                    
                    # --- WYŚWIETLANIE WIERSZA MECZU ---
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                    
                    with col1:
                        st.write(f"{result_icon}")
                        st.caption(f"{match_date_str}")
                    
                    with col2:
                        st.write(f"**{venue_icon} vs {opponent}**")
                        st.caption(f"{comp}")

                    with col3:
                        # Tutaj używamy result_str (np. "W 2-1" lub sam wynik jeśli masz go osobno)
                        # Jeśli result_str to tylko "W", "L", "D", to może być mało informacyjne.
                        # Zakładam, że w kolumnie 'result' masz coś w stylu "W 3-1"
                        st.write(f"**{result_str}**")
                        st.caption(f"{minutes}'")

                    with col4:
                        perf = f"{goals}G {assists}A"
                        # Wyróżnienie gola/asysty
                        if goals > 0 or assists > 0:
                            st.write(f"⚽ **{perf}**")
                        else:
                            st.write(f"{perf}")
                        
                        # xG jeśli dostępne
                        xg_val = match.get('xg')
                        if pd.notna(xg_val) and isinstance(xg_val, (int, float)) and xg_val > 0:
                            st.caption(f"xG: {xg_val:.2f}")

                    st.divider()


    # --- KONIEC PĘTLI FOR ---
    # Kod poniżej wykonuje się raz, po wyświetleniu wszystkich meczów.
    # Wcięcie musi pasować do poziomu, na którym zaczęła się pętla (lub blok if, w którym była pętla).
    
    # Download option
    st.write("---")
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name="polish_players.csv",
        mime="text/csv"
    )

# Blok ELSE dla głównego warunku (np. if not filtered_df.empty:)
# Musi być na samym początku linii (lub wciśnięty tak samo jak odpowiadający mu IF)
else:
    if selected_team != 'All':
        st.warning(f"⚠️ No players found matching '{search_name}' in team '{selected_team}'")
        st.info("💡 Try removing the team filter or changing the search term")
    else:
        st.warning(f"⚠️ No players found matching '{search_name}'")
        st.info("💡 Try a different search term")

# --- Elementy Sidebar i Footer (zawsze widoczne, brak wcięć) ---

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 Tip: Use filters to narrow down results or search by player name."
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
        Polish Football Players Abroad is an independent project and is not affiliated with FBref.com
    </p>
</div>
""", unsafe_allow_html=True)

# Google Analytics 4
GA_ID = os.getenv("GA_ID", "").strip('"\'') 
if GA_ID.startswith("G-"):
    try:
        components.html(
            f"""
            <script async src="https://www.google-analytics.com/gtag/js?id={GA_ID}"></script>
            <script>
                window.dataLayer = window.dataLayer || [];
                function gtag(){{dataLayer.push(arguments);}}
                gtag('js', new Date());
                gtag('config', '{GA_ID}');
            </script>
            """,
            height=0
        )
        st.success(f"GA4 OK: {GA_ID}")  # potwierdzenie
    except Exception as e:
        st.error(f"GA4 błąd: {e}")






