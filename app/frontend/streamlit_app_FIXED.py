"""Polish Players Tracker - Streamlit Dashboard
A simple dashboard to browse and filter Polish football players data.
Usage:
    streamlit run app/frontend/streamlit_app.py
"""
import streamlit as st
import pandas as pd
# # import sqlite3  # REMOVED - using API now  # REMOVED - using API now
from pathlib import Path
from api_client import get_api_client

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
        is_gk = str(row['position']).strip().upper() in ["GK", "BRAMKARZ", "GOALKEEPER"]
        if is_gk:
            goals_current = 0
        else:
            goals_current = int(season_current['goals'].iloc[0]) if not season_current.empty else 0
        card_title = f"⚽ {row['name']} - {row['team'] or 'Unknown Team'}"
        with st.expander(card_title, expanded=(len(filtered_df) <= 3)):
            # Oblicz statystyki RAZ
            season_filter = ['2025-2026', '2025/2026']
            league_games = league_goals = league_assists = league_cs = league_ga = 0
            euro_games = euro_goals = euro_assists = euro_cs = euro_ga = 0
            domestic_games = domestic_goals = domestic_assists = domestic_cs = domestic_ga = 0
            national_games = national_goals = national_assists = national_cs = national_ga = 0
            
            if is_gk and not gk_stats.empty:
                gk_l = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'LEAGUE')]
                if not gk_l.empty:
                    league_games, league_cs, league_ga = int(gk_l['games'].sum()), int(gk_l['clean_sheets'].sum()), int(gk_l['goals_against'].sum())
            elif not comp_stats.empty:
                c_l = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'LEAGUE')]
                if not c_l.empty:
                    league_games, league_goals, league_assists = int(c_l['games'].sum()), int(c_l['goals'].sum()), int(c_l['assists'].sum())
            
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
            
            if is_gk and not gk_stats.empty:
                gk_d = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'DOMESTIC_CUP')]
                if not gk_d.empty:
                    domestic_games, domestic_cs, domestic_ga = int(gk_d['games'].sum()), int(gk_d['clean_sheets'].sum()), int(gk_d['goals_against'].sum())
            elif not comp_stats.empty:
                c_d = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'DOMESTIC_CUP')]
                if not c_d.empty:
                    domestic_games, domestic_goals, domestic_assists = int(c_d['games'].sum()), int(c_d['goals'].sum()), int(c_d['assists'].sum())
            
            if is_gk and not gk_stats.empty:
                gk_n = gk_stats[(gk_stats['season'].isin(season_filter)) & (gk_stats['competition_type'] == 'NATIONAL_TEAM')]
                if not gk_n.empty:
                    national_games, national_cs, national_ga = int(gk_n['games'].sum()), int(gk_n['clean_sheets'].sum()), int(gk_n['goals_against'].sum())
            elif not comp_stats.empty:
                c_n = comp_stats[(comp_stats['season'].isin(season_filter)) & (comp_stats['competition_type'] == 'NATIONAL_TEAM')]
                if not c_n.empty:
                    national_games, national_goals, national_assists = int(c_n['games'].sum()), int(c_n['goals'].sum()), int(c_n['assists'].sum())
            
            total_games = league_games + euro_games + domestic_games + national_games
            total_goals = league_goals + euro_goals + domestic_goals + national_goals
            total_assists = league_assists + euro_assists + domestic_assists + national_assists
            total_cs = league_cs + euro_cs + domestic_cs + national_cs
            total_ga = league_ga + euro_ga + domestic_ga + national_ga
            
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
            
            STATS_HEIGHT = 350 

                                   # --- KOLUMNA 1: LEAGUE STATS ---
            with col1:
                # Górna część: Statystyki w sztywnym pudełku (wysokość = STATS_HEIGHT)
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
                                m1.metric("Games", int(gk_row.get('games', 0) or 0))
                                m2.metric("CS", int(gk_row.get('clean_sheets', 0) or 0))
                                m3.metric("GA", int(gk_row.get('goals_against', 0) or 0))
                    
                    # 2. Logika dla graczy z pola (lub fallback)
                    if not found_league and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        league_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'LEAGUE']
                        if not league_stats.empty:
                            found_league = True
                            for _, comp_row in league_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", int(comp_row['games'] or 0))
                                m2.metric("Goals", 0 if is_gk else int(comp_row['goals'] or 0))
                                m3.metric("Assists", int(comp_row['assists'] or 0))

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
                            # GK Details - standardized: Games, Starts, Minutes, Saves, SoTA, Save%
                            st.write(f"⚽ **Games:** {int(row_to_show.get('games', 0) or 0)}")
                            st.write(f"🏃 **Starts:** {int(row_to_show.get('games_starts', 0) or 0)}")
                            st.write(f"⏱️ **Minutes:** {int(row_to_show.get('minutes', 0) or 0):,}")
                            st.write(f"🧤 **Saves:** {int(row_to_show.get('saves', 0) or 0)}")
                            st.write(f"🔫 **SoTA:** {int(row_to_show.get('shots_on_target_against', 0) or 0)}")
                            save_pct = row_to_show.get('save_percentage', None)
                            if pd.notna(save_pct):
                                st.write(f"💯 **Save%:** {save_pct:.1f}%")
                            else:
                                st.write(f"💯 **Save%:** -")
                        else:
                            # Outfield player details - ENHANCED with per 90 metrics
                            starts = int(row_to_show.get('games_starts', 0) or 0)
                            minutes = int(row_to_show.get('minutes', 0) or 0)
                            goals = int(row_to_show.get('goals', 0) or 0)
                            assists = int(row_to_show.get('assists', 0) or 0)
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
                        if not euro_stats.empty:
                            found_euro = True
                            for _, gk_row in euro_stats.iterrows():
                                st.markdown(f"**{gk_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", int(gk_row.get('games', 0) or 0))
                                m2.metric("CS", int(gk_row.get('clean_sheets', 0) or 0))
                                m3.metric("GA", int(gk_row.get('goals_against', 0) or 0))
                    
                    if not found_euro and not comp_stats.empty:
                         # Fallback dla graczy z pola lub gdy brak GK stats
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        if not euro_stats.empty:
                            found_euro = True
                            for _, comp_row in euro_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Games", int(comp_row['games'] or 0))
                                m2.metric("Goals", 0 if is_gk else int(comp_row['goals'] or 0))
                                m3.metric("Assists", int(comp_row['assists'] or 0))

                    if not found_euro:
                        # Ważne: pusty write lub info, żeby kontener nie był pusty wizualnie
                        st.markdown("<br><br><p style='text-align:center; color:gray'>No matches played</p>", unsafe_allow_html=True)

                with st.expander("📊 Details"):
                    details_found = False
                    row_to_show = None
                    is_gk_display = False
                    
                    if is_gk and not gk_stats.empty:
                        gk_stats_2526 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = gk_stats_2526[gk_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        if not euro_stats.empty:
                            row_to_show = euro_stats.iloc[0]
                            is_gk_display = True
                            details_found = True
                    
                    if not details_found and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        euro_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'EUROPEAN_CUP']
                        if not euro_stats.empty:
                            row_to_show = euro_stats.iloc[0]
                            is_gk_display = False
                            details_found = True
                    
                    if details_found and row_to_show is not None:
                        if is_gk_display:
                            st.write(f"⚽ **Games:** {int(row_to_show.get('games', 0) or 0)}")
                            st.write(f"🏃 **Starts:** {int(row_to_show.get('games_starts', 0) or 0)}")
                            st.write(f"⏱️ **Minutes:** {int(row_to_show.get('minutes', 0) or 0):,}")
                            st.write(f"🧤 **Saves:** {int(row_to_show.get('saves', 0) or 0)}")
                            st.write(f"🔫 **SoTA:** {int(row_to_show.get('shots_on_target_against', 0) or 0)}")
                            save_pct = row_to_show.get('save_percentage', None)
                            if pd.notna(save_pct):
                                st.write(f"💯 **Save%:** {save_pct:.1f}%")
                            else:
                                st.write(f"💯 **Save%:** -")
                        else:
                            # Outfield player details - ENHANCED with per 90 metrics
                            starts = int(row_to_show.get('games_starts', 0) or 0)
                            minutes = int(row_to_show.get('minutes', 0) or 0)
                            goals = int(row_to_show.get('goals', 0) or 0)
                            assists = int(row_to_show.get('assists', 0) or 0)
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
                                m1.metric("Games", int(gk_row.get('games', 0) or 0))
                                m2.metric("CS", int(gk_row.get('clean_sheets', 0) or 0))
                                m3.metric("GA", int(gk_row.get('goals_against', 0) or 0))

                    # 2. Logika dla GRACZY Z POLA (lub fallback dla GK, jeśli brak stats bramkarskich)
                    if not found_domestic and not comp_stats.empty:
                        comp_stats_2526 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', 2025, '2025'])]
                        domestic_stats = comp_stats_2526[comp_stats_2526['competition_type'] == 'DOMESTIC_CUP']
                        
                        if not domestic_stats.empty:
                            found_domestic = True
                            for _, comp_row in domestic_stats.iterrows():
                                st.markdown(f"**{comp_row['competition_name']}**")
                                metric_col1, metric_col2, metric_col3 = st.columns(3)
                                metric_col1.metric("Games", int(comp_row['games'] or 0))
                                metric_col2.metric("Goals", 0 if is_gk else int(comp_row['goals'] or 0))
                                metric_col3.metric("Assists", int(comp_row['assists'] or 0))
                    
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
                            st.write(f"⚽ **Games:** {int(row_to_show.get('games', 0) or 0)}")
                            st.write(f"🏃 **Starts:** {int(row_to_show.get('games_starts', 0) or 0)}")
                            st.write(f"⏱️ **Minutes:** {int(row_to_show.get('minutes', 0) or 0):,}")
                            st.write(f"🧤 **Saves:** {int(row_to_show.get('saves', 0) or 0)}")
                            st.write(f"🔫 **SoTA:** {int(row_to_show.get('shots_on_target_against', 0) or 0)}")
                            save_pct = row_to_show.get('save_percentage', None)
                            if pd.notna(save_pct):
                                st.write(f"💯 **Save%:** {save_pct:.1f}%")
                            else:
                                st.write(f"💯 **Save%:** -")
                        else:
                            # Outfield player details - ENHANCED with per 90 metrics
                            starts = int(row_to_show.get('games_starts', 0) or 0)
                            minutes = int(row_to_show.get('minutes', 0) or 0)
                            goals = int(row_to_show.get('goals', 0) or 0)
                            assists = int(row_to_show.get('assists', 0) or 0)
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
                        comp_stats_2025 = comp_stats[comp_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
                        national_stats = comp_stats_2025[comp_stats_2025['competition_type'] == 'NATIONAL_TEAM']
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = False
                            
                            # Agregacja danych z pola
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
                            
                            # Metryki z pola
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", int(total_games))
                            m2.metric("Goals", 0 if is_gk else int(total_goals))
                            m3.metric("Assists", int(total_assists))
                    
                    # Fallback for goalkeepers (GK stats not available in player_matches with enough detail)
                    elif is_gk and not gk_stats.empty:
                        # NOTE: Exclude 2024-2025 Nations League (all matches were in 2024, not 2025)
                        gk_stats_2025 = gk_stats[gk_stats['season'].isin(['2025-2026', '2025/2026', '2026', 2026, '2025', 2025])]
                        national_stats = gk_stats_2025[gk_stats_2025['competition_type'] == 'NATIONAL_TEAM']
                        
                        if not national_stats.empty:
                            national_data_found = True
                            is_gk_stats_display = True
                            
                            # Agregacja danych GK
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
                            
                            # Metryki GK
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Caps", int(total_games))
                            m2.metric("CS", int(total_cs))
                            m3.metric("GA", int(total_ga))
                    
                    # 3. Brak danych
                    if not national_data_found:
                        st.info("No national team stats for 2025")

                # DÓŁ: Szczegóły (Details) - ZAWSZE POZA KONTENEREM
                with st.expander("📊 Details"):
                    if national_data_found:
                        if is_gk_stats_display:
                            # Szczegóły dla GK - standardized
                            st.write(f"⚽ **Games:** {int(total_games)}")
                            st.write(f"🏃 **Starts:** {int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {int(total_minutes):,}")
                            st.write(f"🧤 **Saves:** {int(total_saves)}")
                            st.write(f"🔫 **SoTA:** {int(total_sota)}")
                            st.write(f"💯 **Save%:** {avg_save_pct:.1f}%")
                        else:
                            # Szczegóły dla gracza z pola - ENHANCED
                            st.write(f"⚽ **Games:** {int(total_games)}")
                            st.write(f"🏃 **Starts:** {int(total_starts)}")
                            st.write(f"⏱️ **Minutes:** {int(total_minutes):,}")
                            st.write(f"🎯 **Goals:** {int(total_goals)}")
                            st.write(f"🅰️ **Assists:** {int(total_assists)}")
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
                                'games': int(r['games'] or 0),
                                'games_starts': 0,
                                'minutes': int(r['minutes'] or 0),
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
                        nt_mask = season_display['competition_type'] == 'NATIONAL_TEAM'
                        if nt_mask.any():
                            nt_agg = season_display[nt_mask].groupby('season', as_index=False).agg({
                                'competition_type': 'first',
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
                def format_season(s):
                    s = str(s)
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
                season_display['season'] = season_display['season'].apply(format_season)
                
                # FIX: Aggregate duplicate rows after season normalization
                # This happens when we have both "2025" and "2026" in database which both become "2025/26"
                # We need to SUM them, not just keep one
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
                st.dataframe(season_display, use_container_width=True, hide_index=True)
            elif not player_stats.empty and len(player_stats) > 0:
                # Fallback to old stats if competition_stats not available
                st.write("---")
                st.write("**📊 Season Statistics History**")
                season_display = player_stats[['season', 'team', 'matches', 'goals', 'assists', 'yellow_cards', 'red_cards', 'minutes_played']].copy()
                season_display['season'] = season_display['season'].apply(lambda x: f"{x}/{x+1}")
                season_display.columns = ['Season', 'Team', 'Matches', 'Goals', 'Assists', 'Yellow', 'Red', 'Minutes']
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
                    goals = int(match['goals']) if pd.notna(match['goals']) else 0
                    # Force assists to 0 for goalkeepers
                    if is_gk:
                        assists = 0
                    else:
                        assists = int(match['assists']) if pd.notna(match['assists']) else 0
                    minutes = int(match['minutes_played']) if pd.notna(match['minutes_played']) else 0
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



