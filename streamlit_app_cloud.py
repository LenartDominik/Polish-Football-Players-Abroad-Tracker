"""
Polish Players Tracker International - Streamlit Dashboard
A simple dashboard to browse and filter Polish football players data.
Usage:
    streamlit run streamlit_app_cloud.py

Multi-page app: Check sidebar for additional pages like Compare Players
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent / "app" / "frontend"))
from api_client import get_api_client
import math
import os
import streamlit.components.v1 as components

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
    """
    # Obsługa różnych separatorów
    if '-' in season_str:
        parts = season_str.split('-')
    elif '/' in season_str:
        parts = season_str.split('/')
    else:
        # Single year format
        return [season_str, safe_int(season_str)]
    
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
        safe_int(year_start),           # 2025
        year_end,                       # "2026"
        safe_int(year_end),             # 2026
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
        # If "Friendlies (M)" (Priority 2) contains matches also listed in Priority 3 (WCQ/Euro), it will have >= games and minutes.
        specifics = group[group['competition_name'].apply(lambda x: get_priority(x) == 3)]
        generals = group[group['competition_name'].apply(lambda x: get_priority(x) == 2)]
        
        if not specifics.empty and not generals.empty:
            spec_games = specifics['games'].sum()
            spec_mins = specifics['minutes'].sum()
            
            # Check each 'General/Friendly' row for overlap
            new_generals = []
            for _, gen_row in generals.iterrows():
                # If specific row matches exactly or is a subset of this general row, subtract specific from general.
                if gen_row['games'] >= spec_games and gen_row['minutes'] >= spec_mins:
                    rem_games = gen_row['games'] - spec_games
                    rem_mins = gen_row['minutes'] - spec_mins
                    
                    if rem_games > 0:
                        gen_row = gen_row.copy()
                        gen_row['games'] = rem_games
                        gen_row['minutes'] = rem_mins
                        new_generals.append(pd.DataFrame([gen_row]))
                    # If rem_games == 0, drop the General row.
                else:
                    new_generals.append(pd.DataFrame([gen_row]))
            
            # Reconstruct group
            if not specifics.empty and new_generals:
                valid_gens = [df for df in new_generals if not df.empty]
                if valid_gens:
                    # Use object dtype to avoid FutureWarning during concat
                    objs = [specifics] + valid_gens
                    all_cols = pd.Index([])
                    for o in objs: 
                        all_cols = all_cols.union(o.columns)
                    objs_reindexed = [o.reindex(columns=all_cols).astype(object) for o in objs]
                    group = pd.concat(objs_reindexed, ignore_index=True)
                    group = group.infer_objects()
                else:
                    group = specifics
            elif not specifics.empty:
                group = specifics
            elif new_generals:
                valid_gens = [df for df in new_generals if not df.empty]
                if len(valid_gens) == 1:
                    group = valid_gens[0]
                elif valid_gens:
                    # Use object dtype to avoid FutureWarning during concat
                    all_cols = pd.Index([])
                    for g in valid_gens: 
                        all_cols = all_cols.union(g.columns)
                    objs_reindexed = [g.reindex(columns=all_cols).astype(object) for g in valid_gens]
                    group = pd.concat(objs_reindexed, ignore_index=True)
                    group = group.infer_objects()
                else:
                    group = specifics
            else:
                group = specifics
            
        groups.append(group)
            
    valid_groups = [g for g in groups if not g.empty]
    if not valid_groups:
        return df.drop(columns=['temp_s'], errors='ignore')
        
    if len(valid_groups) == 1:
        result = valid_groups[0]
    else:
        # Use object dtype to avoid FutureWarning during concat
        all_cols = pd.Index([])
        for g in valid_groups: 
            all_cols = all_cols.union(g.columns)
        objs_reindexed = [g.reindex(columns=all_cols).astype(object) for g in valid_groups]
        result = pd.concat(objs_reindexed, ignore_index=True)
        result = result.infer_objects()
        
    if 'temp_s' in result.columns:
        result = result.drop(columns=['temp_s'])
    return result


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
    if matches_df is None or matches_df.empty:
        return {}
    
    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg','xa']                                                                                                               
    if not all(col in matches_df.columns for col in required_columns):                                              
        return {}
    
    # Filter for national team matches (WCQ, Friendlies, Nations League, Euro, World Cup)
    national_competitions = ['WCQ', 'Friendlies (M)', 'UEFA Nations League', 'UEFA Euro', 'World Cup', 
                            'UEFA Euro Qualifying', 'World Cup Qualifying', 'Copa América']
    
    # Filter by player, year, and national team competitions
    year_matches = matches_df[
        (matches_df['player_id'] == player_id) &
        (matches_df['match_date'].astype(str).str.startswith(str(year))) &
        (matches_df['competition'].isin(national_competitions))
    ].copy()
    
    if year_matches.empty:
        return {}
    
    # Count starts (matches with 60+ minutes or specific logic - for now, count matches with 45+ minutes as starts)
    year_matches['minutes_played'] = pd.to_numeric(year_matches['minutes_played'], errors='coerce').fillna(0)
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
    if matches_df is None or matches_df.empty:
        return pd.DataFrame()
    
    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg', 'xa']
    if not all(col in matches_df.columns for col in required_columns):
        return pd.DataFrame()
    
    # National team competitions
    national_competitions = ['WCQ', 'Friendlies (M)', 'UEFA Nations League', 'UEFA Euro', 'World Cup', 
                            'UEFA Euro Qualifying', 'World Cup Qualifying', 'Copa América']
    
    # Filter for player and national team matches
    df = matches_df[
        (matches_df['player_id'] == player_id) &
        (matches_df['competition'].isin(national_competitions))
    ].copy()
    
    if df.empty:
        return pd.DataFrame()
    
    # Extract year from match_date
    df['year'] = pd.to_datetime(df['match_date'], errors='coerce').dt.year
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)
    
    # Aggregate by year
    years = sorted(df['year'].unique(), reverse=True)
    history = []
    
    for year in years:
        year_df = df[df['year'] == year]
        year_df['minutes_played'] = pd.to_numeric(year_df['minutes_played'], errors='coerce').fillna(0)
        starts = len(year_df[year_df['minutes_played'] >= 45])
        
        history.append({
            'season': str(year),
            'competition_type': 'NATIONAL_TEAM',
            'competition_name': 'National Team',
            'games': len(year_df),
            'games_starts': starts,
            'minutes': year_df['minutes_played'].sum(),
            'goals': year_df['goals'].sum(),
            'assists': year_df['assists'].sum(),
            'xg': year_df['xg'].sum(),
            'xa': year_df['xa'].sum()
        })
    
    return pd.DataFrame(history)

def get_season_total_stats_by_date_range(
    player_id,
    start_date,
    end_date,
    matches_df,
    exclude_competitions=None,
    exclude_competition_keywords=None,
):
    """Aggregate player_matches for a date range.

    Returns dict with games, starts, minutes, goals, assists, xg, xa.
    """
    if matches_df is None or matches_df.empty:
        return None

    required_columns = ['player_id', 'match_date', 'competition', 'minutes_played', 'goals', 'assists', 'xg', 'xa']
    if not all(col in matches_df.columns for col in required_columns):
        return None

    pm = matches_df[matches_df['player_id'] == player_id].copy()
    if pm.empty:
        return None

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
    }


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



# SEO Meta Tags Injection (Invisible in UI but visible to bots)
# Moving to the top of the app flow
st.markdown(
    """
    <div style="display:none" id="seo-tags">
        <meta name="google-site-verification" content="0ZLLXAHagxMIf2Db4Dfh2PLJog9BGrhPIBmH51mi1dM" />
        <meta name="description" content="Detailed statistics and analytics for Polish football players abroad. Compare performance across leagues worldwide.">
    </div>
    """,
    unsafe_allow_html=True
)

# Ukrywanie domyślnych elementów
st.markdown("""
    <style>
        /* Ukrywa tylko link/element z label "streamlit app" w sidebarze */
        a[data-testid="stSidebarNavLink"] > span[label="streamlit app"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# Centered app title at the top
st.markdown(
    """
    <h1 style='text-align: center; margin-bottom: 0.5em;'>Polish Football Players Abroad - Stats Tracker</h1>
    """,
    unsafe_allow_html=True
)

# Initialize API client
@st.cache_data(ttl=3600, show_spinner=False)
def load_player_matches_for_card(player_id, season="2025-2026"):
    """Load matches for a specific player (lazy loading)."""
    try:
        api_client = get_api_client()
        # Fetch matches for current season (includes international matches for invalid year-range)
        # Limit to 1000 to be safe, though one season won't exceed that
        return api_client.get_player_matches(player_id, season=season, limit=1000)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_player_stats(player_id, stats_type='competition'):
    """Load stats for a specific player (lazy loading)."""
    try:
        api_client = get_api_client()
        if stats_type == 'goalkeeper':
            return api_client.get_goalkeeper_stats(player_id)
        else:
            return api_client.get_competition_stats(player_id)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    """Load players data from API."""
    try:
        api_client = get_api_client()

        # Pobierz dane graczy (limit=500 to get all players)
        players_df = api_client.get_all_players(limit=500)
        
        # Disable global stats fetching to save egress/bandwidth
        comp_stats_df = pd.DataFrame() 
        gk_stats_df = pd.DataFrame()
        matches_df = pd.DataFrame() 
        
        # Note: player_season_stats table is deprecated
        stats_df = pd.DataFrame() 
        
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
    st.info("Run: python sync_player_full.py \"Player Name\"")
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
    # Valid assumption: Name implies everything before the last " ("
    if " (" in selected_player_str:
        selected_player_name = selected_player_str.rsplit(" (", 1)[0]
    else:
        selected_player_name = selected_player_str
        
    filtered_df = filtered_df[filtered_df['name'] == selected_player_name]

# Jeśli nie ma wyszukiwania ANI filtru drużyny ANI gracza, nie pokazuj nic
if not search_name and selected_team == 'All' and selected_player_str == 'All':
    st.info("👆 Enter a player name, select a team, or choose a player to view statistics")
    
    # Footer - Data Source Attribution
    st.divider()
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 1rem 0; color: #8A8A8A; font-size: 0.875rem;'>
        <p style='margin-bottom: 0.5rem;'>
            📊 <strong>Data Source:</strong>
            <a href='https://rapidapi.com/creativesdev/api/free-api-live-football-data' target='_blank' style='color: #4ECDC4; text-decoration: none;'>
                RapidAPI Football API
            </a> (free-api-live-football-data)
        </p>
        <p style='font-size: 0.7rem; color: #6A6A6A; margin-bottom: 0;'>
            Polish Football Players Abroad is an independent project for educational purposes
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# Display filtered results
if not filtered_df.empty:
    # --- PAGINACJA (Optymalizacja Supabase) ---
    ITEMS_PER_PAGE = 5
    total_players = len(filtered_df)
    
    if total_players > ITEMS_PER_PAGE:
        total_pages = math.ceil(total_players / ITEMS_PER_PAGE)
        
        col_pag1, col_pag2 = st.columns([3, 1])
        with col_pag1:
            st.info(f"⚡ Found {total_players} players. Showing {ITEMS_PER_PAGE} per page to optimize database usage.")
        with col_pag2:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
            
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        
        # Slice the dataframe for current page
        filtered_df_page = filtered_df.iloc[start_idx:end_idx]
    else:
        filtered_df_page = filtered_df

    for idx, row in filtered_df_page.iterrows():
        # LAZY LOAD STATS for this player only
        # This fixes the missing data issue caused by global limit
        comp_stats = load_player_stats(row['id'], 'competition')
        if not comp_stats.empty:
             comp_stats['season'] = comp_stats['season'].astype(str).str.strip()
             comp_stats['competition_type'] = comp_stats['competition_type'].astype(str).str.strip().str.upper()
             comp_stats = comp_stats.sort_values(['season', 'competition_type'], ascending=False)
        
        gk_stats = load_player_stats(row['id'], 'goalkeeper')
        if not gk_stats.empty:
             gk_stats['season'] = gk_stats['season'].astype(str).str.strip()
             gk_stats['competition_type'] = gk_stats['competition_type'].astype(str).str.strip().str.upper()
             gk_stats = gk_stats.sort_values(['season', 'competition_type'], ascending=False)
        
        # Przywróć pobieranie player_stats, bo jest używane w innych sekcjach
        player_stats = stats_df[stats_df['player_id'] == row['id']].sort_values('season', ascending=False) if not stats_df.empty and 'player_id' in stats_df.columns else pd.DataFrame()
        
        # LAZY LOAD MATCHES for this player only
        # This drastically reduces egress by not loading 100MB of matches for all players
        matches_df_player = load_player_matches_for_card(row['id'], "2025-2026")
        
        # Tytuł karty
        current_season = ['2025-2026', '2025/2026', '2025']
        season_current = player_stats[player_stats['season'].isin(current_season)] if not player_stats.empty else pd.DataFrame()
        
        # If goalkeeper, always show 0 goals in card title
        is_gk = str(row['position']).strip().upper() in ["GK", "BRAMKARZ", "GOALKEEPER"]
        if is_gk:
            goals_current = 0
        else:
            goals_current = safe_int(season_current['goals'].iloc[0]) if not season_current.empty else 0
            
        card_title = f"⚽ {row['name']} - {row['team'] or 'Unknown Team'}"
        
        with st.expander(card_title, expanded=(len(filtered_df) <= 3)):
            # Check if player has CWC appearances (minutes > 0)
            season_start = '2025-07-01'
            season_end = '2026-06-30'
            has_cwc = has_cwc_appearances(row['id'], matches_df_player, season_start, season_end)
            
            # Dynamic column layout: 6 columns if CWC exists, 5 otherwise
            if has_cwc:
                col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])
            else:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                col6 = None  # Placeholder
            
            STATS_HEIGHT = 350 

            # --- KOLUMNA 1: LEAGUE STATS ---
            with col1:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🏆 League Stats (2025-2026)")
                    
                    found_league = False
                    
                    # 1. Logika dla bramkarzy (GK)
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        league_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'LEAGUE']
                        if not league_stats.empty:
                            found_league = True
                            for _, gk_row in league_stats.iterrows():
                                st.markdown(f"**{gk_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", safe_int(gk_row.get('games')))
                                m2.metric("CS", safe_int(gk_row.get('clean_sheets')))
                                m3.metric("GA", safe_int(gk_row.get('goals_against')))
                    
                    # 2. Logika dla graczy z pola
                    if not found_league and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        league_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'LEAGUE']
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
                                    m2.metric("Goals", safe_int(comp_row.get('goals')))
                                    m3.metric("Assists", safe_int(comp_row.get('assists')))

                    if not found_league:
                        st.info("No league stats for 2025-2026")

                with st.expander("📊 Details"):
                    details_found = False
                    row_to_show = None
                    is_gk_display = False
                    
                    if is_gk and not gk_stats.empty:
                         gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                         league_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'LEAGUE']
                         if not league_stats.empty:
                             row_to_show = league_stats.iloc[0]
                             is_gk_display = True
                             details_found = True

                    if not details_found and not comp_stats.empty:
                         comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                         league_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'LEAGUE']
                         if not league_stats.empty:
                             row_to_show = league_stats.iloc[0]
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
                            starts = safe_int(row_to_show.get('games_starts'))
                            minutes = safe_int(row_to_show.get('minutes'))
                            goals = safe_int(row_to_show.get('goals'))
                            assists = safe_int(row_to_show.get('assists'))
                            xg = row_to_show.get('xg', 0.0) if pd.notna(row_to_show.get('xg')) else 0.0
                            xa = row_to_show.get('xa', 0.0) if pd.notna(row_to_show.get('xa')) else 0.0
                            npxg = row_to_show.get('npxg', 0.0) if pd.notna(row_to_show.get('npxg')) else 0.0
                            xgi = calculate_xgi(xg, xa)
                            
                            ga_per_90 = calculate_per_90(goals + assists, minutes)
                            xg_per_90 = calculate_per_90(xg, minutes)
                            xa_per_90 = calculate_per_90(xa, minutes)
                            npxg_per_90 = calculate_per_90(npxg, minutes)
                            xgi_per_90 = calculate_per_90(xgi, minutes)
                            
                            st.write(f"🏃 **Starts:** {starts}")
                            st.write(f"⏱️ **Minutes:** {minutes:,}")
                            st.write(f"🎯 **Goals:** {goals}")
                            st.write(f"🅰️ **Assists:** {assists}")
                            st.write(f"⚡ **G+A / 90:** {ga_per_90:.2f}")
                            if xgi > 0: st.write(f"📊 **xGI:** {xgi:.2f}")
                            if xg > 0: st.write(f"📊 **xG:** {xg:.2f}")
                            if xa > 0: st.write(f"📊 **xA:** {xa:.2f}")
                            if xg > 0: st.write(f"📈 **xG / 90:** {xg_per_90:.2f}")
                            if xa > 0: st.write(f"📈 **xA / 90:** {xa_per_90:.2f}")
                            if npxg > 0: st.write(f"📊 **npxG / 90:** {npxg_per_90:.2f}")
                            if xgi > 0: st.write(f"📈 **xGI / 90:** {xgi_per_90:.2f}")
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
                        # Robust filtering
                        current_season_filters = ['2025-2026', '2025/2026', '2025', 2025]
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(current_season_filters)]
                        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        # Exclude Club World Cup and Leagues Cup from International/European Cups
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
                        # Exclude Club World Cup and Leagues Cup from International/European Cups
                        if not euro_stats.empty:
                            euro_stats = euro_stats[~euro_stats['competition_name'].apply(is_club_world_cup)]
                            euro_stats = euro_stats[~euro_stats['competition_name'].str.contains('Leagues Cup', case=False, na=False)]
                        if not euro_stats.empty:
                            euro_stats_to_show = euro_stats
                            is_gk_display = is_gk
                            details_found = True
                    
                    if details_found and euro_stats_to_show is not None:
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
                            else:
                                starts = safe_int(row_to_show.get('games_starts'))
                                minutes = safe_int(row_to_show.get('minutes'))
                                goals = safe_int(row_to_show.get('goals'))
                                assists = safe_int(row_to_show.get('assists'))
                                xg = row_to_show.get('xg', 0.0) if pd.notna(row_to_show.get('xg')) else 0.0
                                xa = row_to_show.get('xa', 0.0) if pd.notna(row_to_show.get('xa')) else 0.0
                                
                                st.write(f"🏃 **Starts:** {starts}")
                                st.write(f"⏱️ **Minutes:** {minutes:,}")
                                st.write(f"🎯 **Goals:** {goals}")
                                st.write(f"🅰️ **Assists:** {assists}")
                                if xg > 0: st.write(f"📊 **xG:** {xg:.2f}")
                                if xa > 0: st.write(f"📊 **xA:** {xa:.2f}")
                            
                            if len(euro_stats_to_show) > 1 and idx < len(euro_stats_to_show) - 1:
                                st.markdown("---")
                    else:
                        st.write("No matches played")

            # --- KOLUMNA 3: DOMESTIC CUPS ---
            with col3:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🏆 Domestic Cups (2025-2026)")
                    
                    found_domestic = False

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

                    if not found_domestic and not comp_stats.empty:
                        # Ensure robust filtering
                        current_season_filters = ['2025-2026', '2025/2026', '2025', 2025]
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(current_season_filters)]
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(current_season_filters)]
                        domestic_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        if domestic_stats.empty:
                            # Fallback: Check for 'CUP' in name if type check fails
                            domestic_stats = comp_stats_2526[comp_stats_2526['competition_name'].str.contains('Cup|Puchar|Pokal|Copa', case=False, na=False)]
                        
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
                    
                    if not found_domestic:
                        st.info("No domestic cup stats for 2025-2026")

                with st.expander("📊 Details"):
                    details_found = False
                    row_to_show = None
                    is_gk_display = False
                    
                    current_season_filters = ['2025-2026', '2025/2026', '2025', 2025]
                    
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(current_season_filters)]
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
                        else:
                            starts = safe_int(row_to_show.get('games_starts'))
                            minutes = safe_int(row_to_show.get('minutes'))
                            goals = safe_int(row_to_show.get('goals'))
                            assists = safe_int(row_to_show.get('assists'))
                            st.write(f"🏃 **Starts:** {starts}")
                            st.write(f"⏱️ **Minutes:** {minutes:,}")
                            st.write(f"🎯 **Goals:** {goals}")
                            st.write(f"🅰️ **Assists:** {assists}")
                    else:
                        st.write("No details available.")

            # --- KOLUMNA 4: NATIONAL TEAM ---
            with col4:
                with st.container(height=STATS_HEIGHT, border=False):
                    st.write("### 🇵🇱 National Team (2025)")
                    
                    national_data_found = False
                    
                    total_games = 0
                    total_minutes = 0
                    total_starts = 0
                    total_ga = 0
                    total_saves = 0
                    total_sota = 0
                    total_cs = 0
                    avg_save_pct = 0.0
                    total_goals = 0
                    total_assists = 0
                    total_xg = 0.0
                    total_xa = 0.0
                    comp_display = ""
                    
                    is_gk_stats_display = False

                    if not is_gk and not comp_stats.empty:
                        comp_stats_2025 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
                        national_stats = comp_stats_2025[comp_stats_2025['competition_type'] == 'NATIONAL_TEAM']
                        # Clean/Deduplicate
                        national_stats = clean_national_team_stats(national_stats)
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = False
                            
                            total_games = national_stats['games'].sum()
                            total_starts = national_stats['games_starts'].sum()
                            total_goals = national_stats['goals'].sum()
                            total_assists = national_stats['assists'].sum()
                            total_minutes = national_stats['minutes'].sum()
                            total_xg = national_stats['xg'].sum()
                            total_xa = national_stats['xa'].sum()
                            
                            comp_names = national_stats['competition_name'].unique().tolist()
                            comp_display = ', '.join([name for name in comp_names if pd.notna(name) and name])
                            if comp_display:
                                st.caption(f"*{comp_display}*")
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", safe_int(total_games))
                            if is_gk:
                                m2.metric("CS", safe_int(total_cs))
                                m3.metric("GA", safe_int(total_ga))
                            else:
                                m2.metric("Goals", safe_int(total_goals))
                                m3.metric("Assists", safe_int(total_assists))

                    elif is_gk and not gk_stats.empty:
                        gk_stats_2025 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
                        national_stats = gk_stats_2025[gk_stats_2025['competition_type'] == 'NATIONAL_TEAM']
                        # Clean/Deduplicate
                        national_stats = clean_national_team_stats(national_stats)
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = True
                            
                            total_games = national_stats['games'].sum()
                            total_starts = national_stats['games_starts'].sum()
                            total_minutes = national_stats['minutes'].sum()
                            total_ga = national_stats['goals_against'].sum()
                            total_saves = national_stats['saves'].sum()
                            total_sota = national_stats['shots_on_target_against'].sum()
                            total_cs = national_stats['clean_sheets'].sum()
                            avg_save_pct = (total_saves / total_sota * 100) if total_sota > 0 else 0.0
                            
                            comp_names = national_stats['competition_name'].unique().tolist()
                            comp_display = ', '.join([name for name in comp_names if pd.notna(name) and name])
                            if comp_display:
                                st.caption(f"*{comp_display}*")
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", safe_int(total_games))
                            m2.metric("CS", safe_int(total_cs))
                            m3.metric("GA", safe_int(total_ga))
                        else:
                            # FALLBACK (tylko gdy brak danych w goalkeeper_stats): rok kalendarzowy z player_matches.
                            pm_stats = get_national_team_stats_by_year(row['id'], 2025, matches_df_player)
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
                    
                    if not national_data_found:
                        # Final field player fallback
                        pm_stats = get_national_team_stats_by_year(row['id'], 2025, matches_df_player)
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
                            comp_list = pm_stats.get('competitions', [])
                            comp_display = ', '.join([c for c in comp_list if c])
                            if comp_display:
                                st.caption(f"*{comp_display}*")
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", safe_int(total_games))
                            m2.metric("Goals", safe_int(total_goals))
                            m3.metric("Assists", safe_int(total_assists))
                        else:
                            st.info("No national team stats for 2025")

                with st.expander("📊 Details"):
                    if national_data_found:
                        if is_gk_stats_display:
                            st.write(f"⚽ **Games:** {safe_int(total_games)}")
                            st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                            st.write(f"🧤 **Saves:** {safe_int(total_saves)}")
                            st.write(f"🔫 **SoTA:** {safe_int(total_sota)}")
                            st.write(f"💯 **Save%:** {avg_save_pct:.1f}%")
                        else:
                            st.write(f"⚽ **Games:** {safe_int(total_games)}")
                            st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                            st.write(f"🎯 **Goals:** {safe_int(total_goals)}")
                            st.write(f"🅰️ **Assists:** {safe_int(total_assists)}")
                            if total_xg > 0: st.write(f"📊 **xG:** {total_xg:.2f}")
                            if total_xa > 0: st.write(f"📊 **xAG:** {total_xa:.2f}")
                    else:
                        st.write("No details available.")
            # --- KOLUMNA 5: SEASON TOTAL (CLUB ONLY) ---
            with (col6 if has_cwc and col6 is not None else col5):
                with st.container(height=STATS_HEIGHT, border=False):
                    is_mls = row.get('league') == 'MLS'
                    st.write("### 📊 Season Total (2025-2026)")
                    
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

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Appearances", safe_int(total_games))
                    
                    if is_gk:
                        m2.metric("CS", safe_int(total_clean_sheets))
                        m3.metric("GA", safe_int(total_ga))
                    else:
                        m2.metric("Goals", safe_int(total_goals))
                        m3.metric("Assists", safe_int(total_assists))
                
                with st.expander("📊 Details"):
                    if is_gk:
                        st.write(f"⚽ **Games:** {safe_int(total_games)}")
                        st.write(f"🏃 **Starts:** {safe_int(total_starts)}")
                        st.write(f"⏱️ **Minutes:** {safe_int(total_minutes):,}")
                        st.write(f"🧤 **Saves:** {safe_int(total_saves)}")
                        st.write(f"🔫 **SoTA:** {safe_int(total_sota)}")
                    else:
                        st.write(f"⚽ **Total Games:** {safe_int(total_games)}")
                        st.write(f"🏃 **Total Starts:** {safe_int(total_starts)}")
                        st.write(f"⏱️ **Total Minutes:** {safe_int(total_minutes):,}")
                        st.write(f"🎯 **Total Goals:** {safe_int(total_goals)}")
                        st.write(f"🅰️ **Total Assists:** {safe_int(total_assists)}")

            # === ADVANCED PROGRESSION STATS ===
            if str(row['position']).strip().upper() not in ["GK", "BRAMKARZ", "GOALKEEPER"]:
                if not player_stats.empty:
                    season_current = player_stats[player_stats['season'].isin(current_season)]
                    if not season_current.empty:
                        has_data = False
                        stat_columns = ['progressive_passes', 'progressive_carries']
                        for col in stat_columns:
                            if col in season_current.columns:
                                val = season_current[col].iloc[0]
                                if pd.notna(val) and val > 0:
                                    has_data = True
                                    break
                        
                        if has_data:
                            st.write("---")
                            st.write("### 📊 Advanced Progression Stats")
                            st.caption("*Statistics from league competition*")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if 'progressive_passes' in season_current.columns:
                                    prog_passes = season_current['progressive_passes'].iloc[0]
                                    if pd.notna(prog_passes):
                                        st.metric("Progressive Passes", safe_int(prog_passes))
                            with col2:
                                if 'progressive_carries' in season_current.columns:
                                    prog_carries = season_current['progressive_carries'].iloc[0]
                                    if pd.notna(prog_carries):
                                        st.metric("Progressive Carries", safe_int(prog_carries))
                            with col3:
                                if 'progressive_carrying_distance' in season_current.columns:
                                    prog_dist = season_current['progressive_carrying_distance'].iloc[0]
                                    if pd.notna(prog_dist):
                                        st.metric("Prog. Carry Distance", f"{safe_int(prog_dist)}m")
                            with col4:
                                if 'progressive_passes_received' in season_current.columns:
                                    prog_recv = season_current['progressive_passes_received'].iloc[0]
                                    if pd.notna(prog_recv):
                                        st.metric("Prog. Passes Received", safe_int(prog_recv))

            # === HISTORY TABLES ===
            is_goalkeeper = str(row.get('position', '')).strip().upper() in ['GK', 'GOALKEEPER', 'BRAMKARZ']
            
            # Combine competition stats with national team history from match logs
            nat_history = get_national_team_history_by_calendar_year(row['id'], matches_df_player)
            
            if is_goalkeeper:
                objs = [df for df in [gk_stats, nat_history] if not df.empty]
                if objs:
                    import pandas as _pd
                    # Safe Concat
                    all_cols = pd.Index([])
                    for o in objs: all_cols = all_cols.union(o.columns)
                    objs_reindexed = [o.reindex(columns=all_cols).astype(object) for o in objs]
                    stats_to_display = _pd.concat(objs_reindexed, ignore_index=True)
                    stats_to_display = stats_to_display.infer_objects()
                else:
                    stats_to_display = _pd.DataFrame()
            else:
                objs = [df for df in [comp_stats, nat_history] if not df.empty]
                if objs:
                    import pandas as _pd
                    # Safe Concat
                    all_cols = pd.Index([])
                    for o in objs: all_cols = all_cols.union(o.columns)
                    objs_reindexed = [o.reindex(columns=all_cols).astype(object) for o in objs]
                    stats_to_display = _pd.concat(objs_reindexed, ignore_index=True)
                    stats_to_display = stats_to_display.infer_objects()
                else:
                    stats_to_display = _pd.DataFrame()
            
            if not stats_to_display.empty and len(stats_to_display) > 0:
                st.write("---")
                st.write("**📊 Season Statistics History (All Competitions)**")
                
                # ... (Data preparation logic remains similar but simplified for brevity) ...
                # Assuming season_display is prepared here as in your original code
                
                # IMPORTANT: RECREATING THE DATAFRAME LOGIC TO ENSURE IT WORKS
                if is_goalkeeper:
                    import pandas as _pd
                    # Standardized columns for all goalkeepers (ordered exactly as requested)
                    gk_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                    
                    if not gk_stats.empty:
                        gk_display = gk_stats.reindex(columns=gk_cols).copy()
                    else:
                        gk_display = _pd.DataFrame(columns=gk_cols)
                        
                    # Add fallback rows from comp_stats
                    comp_needed = ['LEAGUE','EUROPEAN_CUP','DOMESTIC_CUP','NATIONAL_TEAM']
                    if not comp_stats.empty:
                        comp_subset = comp_stats[comp_stats['competition_type'].isin(comp_needed)].copy()
                        rows = []

                        # Klucze istniejące już w gk_display (żeby nie dodawać duplikatów z comp_stats)
                        gk_keys = set()
                        # Dodatkowy set dla sezonów, w których już są dane reprezentacyjne (żeby uniknąć dubli typu WCQ vs National Team)
                        gk_nt_seasons = set()
                        
                        if not gk_display.empty and 'season' in gk_display.columns and 'competition_type' in gk_display.columns:
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
                            
                            # Check if exists (exact match)
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
                        comp_display_df = _pd.DataFrame(rows) if rows else _pd.DataFrame(columns=gk_cols)
                        if not comp_display_df.empty:
                            if gk_display.empty:
                                gk_display = comp_display_df
                            else:
                                # Ensure both have same columns for clean concat
                                objs = [df for df in [gk_display, comp_display_df] if not df.empty]
                                if objs:
                                    all_cols = pd.Index([])
                                    for o in objs: 
                                        all_cols = all_cols.union(o.columns)
                                    objs_reindexed = [o.reindex(columns=all_cols).astype(object) for o in objs]
                                    gk_display = _pd.concat(objs_reindexed, ignore_index=True)
                                    gk_display = gk_display.infer_objects()
                            
                        # --- AGGREGATION: GROUP NATIONAL TEAM STATS FOR GK ---
                        # Logic: Filter NT rows and group by season (normalizing WCQ 2026 -> 2025)
                        if not gk_display.empty:
                            ntm = (gk_display['competition_type'] == 'NATIONAL_TEAM') | \
                                  (gk_display['competition_name'].fillna('').astype(str).str.contains(r'\bWorld Cup\b|UEFA Euro|\bEuro Qualifying\b|Nations League|Reprezentacja|Eliminacje', case=False)) | \
                                  (gk_display['competition_name'].apply(lambda x: str(x) in ['WCQ', 'Friendlies (M)', 'World Cup Qualifying', 'UEFA Euro Qualifying', 'National Team', 'National Team (All)']))
                            
                            if ntm.any():
                                nt_df = gk_display[ntm].copy()
                                club_df = gk_display[~ntm].copy()
                                
                                # Normalize seasons for NT (specifically WCQ 2026 -> 2025 if present)
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
                                nt_df = nt_df.rename(columns={'season': 'original_season', 'season_group': 'season'})
                                nt_df = clean_national_team_stats(nt_df)
                                nt_df = nt_df.rename(columns={'season': 'season_group', 'original_season': 'season'})
                                
                                # Group and Aggregate
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
                                
                                # Recalculate Save %
                                if 'saves' in nt_grouped.columns and 'shots_on_target_against' in nt_grouped.columns:
                                    nt_grouped['save_percentage'] = nt_grouped.apply(
                                        lambda x: (x['saves'] / x['shots_on_target_against'] * 100) if x['shots_on_target_against'] > 0 else 0.0, 
                                        axis=1
                                    )
                                
                                # Recombine with Club stats
                                club_df_clean = club_df.copy()
                                nt_grouped_clean = nt_grouped.copy()
                                
                                # Use position-based is_goalkeeper for consistent layout
                                
                                objs = [df for df in [club_df_clean, nt_grouped_clean] if not df.empty]
                                if objs:
                                    # Use object dtype to avoid FutureWarning during concat
                                    all_cols = pd.Index([])
                                    for o in objs:
                                        all_cols = all_cols.union(o.columns)
                                    objs_reindexed = [o.reindex(columns=all_cols).astype(object) for o in objs]
                                    gk_display = _pd.concat(objs_reindexed, ignore_index=True)
                                    gk_display = gk_display.infer_objects()
                                elif not nt_grouped_clean.empty:
                                    gk_display = nt_grouped_clean
                                else:
                                    gk_display = club_df_clean
                                    
                        # Filter out potential summary rows
                        if not gk_display.empty:
                            gk_display = gk_display[gk_display['season'].astype(str).str.contains(r'\d', regex=True)]
                            gk_display = gk_display.sort_values(by='season', ascending=False)
                            # -----------------------------------------------------

                    season_display = gk_display
                else:
                    season_display = comp_stats[['season', 'competition_type', 'competition_name', 'games', 'goals', 'assists', 'xg', 'xa', 'yellow_cards', 'red_cards', 'minutes']].copy()

                # --- FIX: DATA CLEANING FOR DATAFRAME ---
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
                    # --- SUPER CUP LABELING (history table) ---
                    # Requirement: Super Cups should NOT be part of the club season total.
                    # They should appear as separate history rows labeled like:
                    #   "2025-26 Domestic Cups - Supercopa de Espana"
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

                    def _format_club_season_short(season_val) -> str:
                        s = str(season_val or '')
                        # Common cases: 2025-2026 or 2025/2026
                        if '-' in s:
                            a, b = s.split('-', 1)
                            return f"{a}-{b[-2:]}" if len(b) >= 2 else s
                        if '/' in s:
                            a, b = s.split('/', 1)
                            return f"{a}-{b[-2:]}" if len(b) >= 2 else s
                        # Fallback: return as-is (e.g. calendar year)
                        return s

                    if 'competition_name' in season_display.columns:
                        sc_mask = pd.Series(False, index=season_display.index)
                        comp_series = season_display['competition_name'].astype(str)
                        for kw in super_cup_keywords:
                            sc_mask = sc_mask | comp_series.str.contains(kw, case=False, na=False)

                        if sc_mask.any() and 'season' in season_display.columns:
                            season_display.loc[sc_mask, 'season'] = season_display.loc[sc_mask].apply(
                                lambda r: f"{_format_club_season_short(r['season'])} Domestic Cups - {r['competition_name']}",
                                axis=1,
                            )

                            # Make sure labeled Super Cups don't get aggregated into other seasons
                            # by keeping the unique season label.

                    # 1. Fill NaNs with 0 for numeric columns
                    numeric_cols = ['games', 'goals', 'assists', 'clean_sheets', 'goals_against', 'minutes', 'yellow_cards', 'red_cards']
                    for col in numeric_cols:
                        if col in season_display.columns:
                            season_display[col] = season_display[col].fillna(0)
                            # Apply safe_int to ensure no floats in integer columns
                            season_display[col] = season_display[col].apply(safe_int)
                    
                    # 2. Round floats
                    float_cols = ['xg', 'xa', 'save_percentage']
                    for col in float_cols:
                        if col in season_display.columns:
                            season_display[col] = season_display[col].apply(lambda x: round(x, 2) if pd.notna(x) else 0.0)

                    # 3. Rename columns for display
                    if is_goalkeeper:
                        # Ordered exactly as requested
                        expected_gk_cols = ['season', 'competition_type', 'competition_name', 'games', 'games_starts', 'minutes', 'clean_sheets', 'goals_against', 'save_percentage']
                        
                        for col in expected_gk_cols:
                            if col not in season_display.columns:
                                season_display[col] = 0
                                
                        season_display = season_display[expected_gk_cols]
                        season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Starts', 'Minutes', 'CS', 'GA', 'Save%']
                    else:
                        # Field player columns
                        expected_field_cols = ['season', 'competition_type', 'competition_name', 'games', 'goals', 'assists', 'xg', 'xa', 'yellow_cards', 'red_cards', 'minutes']
                        
                        for col in expected_field_cols:
                            if col not in season_display.columns:
                                season_display[col] = 0
                                
                        season_display = season_display[expected_field_cols]
                        season_display.columns = ['Season', 'Type', 'Competition', 'Games', 'Goals', 'Assists', 'xG', 'xA', 'Yellow', 'Red', 'Minutes']
                    
                    # --- CLUB WORLD CUP LABELING (history table) ---
                    if 'competition_name' in season_display.columns:
                        cwc_mask = season_display['competition_name'].apply(is_club_world_cup)
                        if cwc_mask.any() and 'season' in season_display.columns:
                            season_display.loc[cwc_mask, 'season'] = season_display.loc[cwc_mask, 'season'].astype(str) + ' Club World Cup'

                    st.dataframe(season_display, width='stretch', hide_index=True)
                    
            
            # ===== NOWA SEKCJA: MECZE GRACZA =====
            # Use lazy-loaded matches (matches_df_player) instead of empty global matches_df
            player_matches = matches_df_player
            
            if not player_matches.empty and len(player_matches) > 0:
                st.write("---")
                st.subheader("🏟️ Recent Matches (Season 2025/26)")
                
                pm = player_matches.copy()
                if pm['match_date'].dtype != 'datetime64[ns]':
                    pm['match_date'] = pd.to_datetime(pm['match_date'], errors='coerce')
                pm = pm.dropna(subset=['match_date'])
                pm = pm.sort_values('match_date', ascending=False)
                
                recent_matches = pm.head(10)
                for idx_match, match in recent_matches.iterrows():
                    result_str = match['result'] if pd.notna(match['result']) else ''
                    if result_str.startswith('W'): result_icon = "🟢"
                    elif result_str.startswith('D'): result_icon = "🟡"
                    elif result_str.startswith('L'): result_icon = "🔴"
                    else: result_icon = "⚪"
                    
                    match_date = pd.to_datetime(match['match_date']).strftime('%d.%m.%Y')
                    comp = match['competition'] if pd.notna(match['competition']) else 'N/A'
                    venue_icon = "🏠" if match['venue'] == 'Home' else "✈️"
                    
                    goals = safe_int(match.get('goals'))
                    assists = 0 if is_gk else safe_int(match.get('assists'))
                    minutes = safe_int(match.get('minutes_played'))
                    
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
                    st.write("")

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
    else:
        st.warning(f"⚠️ No players found matching '{search_name}'")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip**: Use filters to narrow down results.")

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.divider()
st.markdown("""
<div style='text-align: center; padding: 2rem 0 1rem 0; color: #8A8A8A; font-size: 0.875rem;'>
    <p>📊 <strong>Data Source:</strong> <a href='https://rapidapi.com/creativesdev/api/free-api-live-football-data' target='_blank'>RapidAPI Football API</a></p>
</div>
""", unsafe_allow_html=True)

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
        # st.success(f"GA4 OK: {GA_ID}")  # potwierdzenie
    except Exception as e:
        st.error(f"GA4 błąd: {e}")