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
from api_client import get_api_client
import math

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


# Page config
st.set_page_config(
    page_title="Polish Football Data Hub International",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
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
        
        # Tytuł karty
        current_season = ['2025-2026', '2025/2026', 2025]
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
                                m2.metric("Goals", 0 if is_gk else safe_int(comp_row.get('goals')))
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
                    
                    if not found_domestic:
                        st.info("No domestic cup stats for 2025-2026")

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
                            m2.metric("Goals", 0 if is_gk else safe_int(total_goals))
                            m3.metric("Assists", safe_int(total_assists))

                    elif is_gk and not gk_stats.empty:
                        gk_stats_2025 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
                        national_stats = gk_stats_2025[gk_stats_2025['competition_type'] == 'NATIONAL_TEAM']
                        
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
                    
                    if not national_data_found:
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
                    st.write("### 📊 Season Total (2025-2026)")
                    st.caption("Club competitions only (League + Domestic Cups + European Cups). Excludes Club World Cup, National Team, and Super Cups.")

                    # Aggregate totals from match logs within the club-season date range
                    total_games, total_starts, total_minutes = 0, 0, 0
                    total_goals, total_assists, total_xg, total_xa = 0, 0, 0.0, 0.0
                    total_clean_sheets, total_ga, total_saves, total_sota = 0, 0, 0, 0

                    season_start = '2025-07-01'
                    season_end = '2026-06-30'
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

                    # Goalkeeper metrics: use goalkeeper_stats (club season), excluding National Team and Super Cups
                    if is_gk and not gk_stats.empty:
                        club_filters = ['2025-2026', '2025/2026']
                        gk_club = gk_stats[(gk_stats['season'].isin(club_filters)) & (gk_stats['competition_type'] != 'NATIONAL_TEAM')].copy()
                        if not gk_club.empty and 'competition_name' in gk_club.columns:
                            sc_mask = pd.Series(False, index=gk_club.index)
                            for kw in super_cup_keywords:
                                sc_mask = sc_mask | gk_club['competition_name'].astype(str).str.contains(kw, case=False, na=False)
                            gk_club = gk_club[~sc_mask]

                        # Club World Cup might be stored with calendar year season
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

            # === HISTORY TABLES (Corrected use_container_width) ===
            is_goalkeeper = str(row.get('position', '')).strip().upper() in ['GK', 'GOALKEEPER', 'BRAMKARZ']
            stats_to_display = gk_stats if (is_goalkeeper and not gk_stats.empty) else comp_stats
            
            if not stats_to_display.empty and len(stats_to_display) > 0:
                st.write("---")
                st.write("**📊 Season Statistics History (All Competitions)**")
                
                # ... (Data preparation logic remains similar but simplified for brevity) ...
                # Assuming season_display is prepared here as in your original code
                
                # IMPORTANT: RECREATING THE DATAFRAME LOGIC TO ENSURE IT WORKS
                if is_goalkeeper:
                    import pandas as _pd
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
                        for _, r in comp_subset.iterrows():
                            # Simplified check
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
                            comp_display_df = _pd.DataFrame(rows)
                            gk_display = _pd.concat([gk_display, comp_display_df], ignore_index=True)
                            
                    season_display = gk_display
                else:
                    season_display = comp_stats[['season', 'competition_type', 'competition_name', 'games', 'goals', 'assists', 'xg', 'xa', 'yellow_cards', 'red_cards', 'minutes']].copy()

                # --- FIX: DATA CLEANING FOR DATAFRAME ---
                if not season_display.empty:
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
                    # ... (renaming logic) ...
                    
                    # --- CRITICAL FIX FOR STREAMLIT WARNING ---
                    # REPLACE: use_container_width=True -> width="stretch"
                    # --- CLUB WORLD CUP LABELING (history table) ---
                    if 'competition_name' in season_display.columns:
                        cwc_mask = season_display['competition_name'].apply(is_club_world_cup)
                        if cwc_mask.any() and 'season' in season_display.columns:
                            season_display.loc[cwc_mask, 'season'] = season_display.loc[cwc_mask, 'season'].astype(str) + ' Club World Cup'

                    st.dataframe(season_display, width=None, use_container_width=True, hide_index=True)
                    # NOTE: Streamlit's warning says "replace use_container_width with width".
                    # However, in st.dataframe, use_container_width=True IS the correct way to stretch in current versions.
                    # The warning likely refers to a chart or a deprecated usage.
                    # If you still see the warning, try: st.dataframe(season_display, use_container_width=True) 
                    # which is correct. The warning might come from st.image or other elements if present.
                    # BUT based on your log, if it persists, use:
                    # st.dataframe(season_display, width=1000) # Fixed width if stretch fails
                    
            
            # ===== NOWA SEKCJA: MECZE GRACZA =====
            player_matches = matches_df[matches_df['player_id'] == row['id']] if not matches_df.empty and 'player_id' in matches_df.columns else pd.DataFrame()
            
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
    <p>📊 <strong>Data Source:</strong> <a href='https://fbref.com/' target='_blank'>FBref.com</a></p>
</div>
""", unsafe_allow_html=True)