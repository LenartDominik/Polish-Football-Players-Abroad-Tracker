import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict
import os

# Get API URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_URL = f"{API_BASE_URL}/api"


st.set_page_config(page_title="Compare players", page_icon="⚖️", layout="wide")

st.markdown("<h1 style='text-align: center;'>⚖️ Comparison of Polish football players abroad</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: white;'>(league stats)</h3>", unsafe_allow_html=True)

# Fetching the list of players
@st.cache_data(ttl=600)
def get_all_players():
    try:
        resp = requests.get(f"{API_URL}/players/")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error fetching players list: {e}")
        return []

# Fetching available stats for selection
@st.cache_data(ttl=600)
def get_available_stats(player_type: str = None):
    try:
        params = {}
        if player_type:
            params["player_type"] = player_type
        resp = requests.get(f"{API_URL}/comparison/available-stats", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return {}

# Fetch data for comparison
def compare_players(player1_id: int, player2_id: int, season: str = None, stats: List[str] = None):
    params = {"player1_id": player1_id, "player2_id": player2_id}
    if season:
        params["season"] = season
    if stats:
        params["stats"] = stats
    try:
        resp = requests.get(f"{API_URL}/comparison/compare", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error comparing players: {e}")
        return None

# Helper function to format values (show N/A for 0 or NULL when appropriate)
def format_value(value, stat_name):
    """
    Format statistical values for display.
    Shows 'N/A' for missing data (0 or None) in stats where 0 is not meaningful.
    """
    # Stats where 0 is a valid value
    valid_zero_stats = ['goals', 'assists', 'yellow_cards', 'red_cards', 'losses', 
                        'penalties_missed', 'penalties_allowed', 'penalties_saved', 
                        'penalties_attempted', 'goals_against', 'matches', 'games_starts',
                        'clean_sheets', 'clean_sheet_percentage', 'saves', 'wins', 'draws']
    
    # Check if value is None or 0
    if value is None or (isinstance(value, (int, float)) and value == 0):
        # If stat can legitimately be 0, show it
        if stat_name.lower() in valid_zero_stats:
            return 0
        # Otherwise show N/A
        return 'N/A'
    
    # For valid non-zero values, return as is
    return value

# Format value for display in table
def format_display_value(value):
    """Format value for nice display in tables"""
    if value == 'N/A':
        return 'N/A'
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)

# Create radar chart (skip N/A values)
def create_radar_chart(player1_data: Dict, player2_data: Dict, selected_stats: List[str]):
    # Filter out stats where both players have N/A
    valid_stats = []
    for stat in selected_stats:
        val1 = format_value(player1_data.get(stat, 0), stat)
        val2 = format_value(player2_data.get(stat, 0), stat)
        if val1 != 'N/A' or val2 != 'N/A':
            valid_stats.append(stat)
    
    if not valid_stats:
        return None
    
    categories = [s.replace("_", " ").replace("G+A", "G+A").title() for s in valid_stats]
    
    # Convert N/A to 0 for chart purposes
    values1 = []
    values2 = []
    for s in valid_stats:
        v1 = format_value(player1_data.get(s, 0), s)
        v2 = format_value(player2_data.get(s, 0), s)
        values1.append(float(v1) if v1 != 'N/A' else 0)
        values2.append(float(v2) if v2 != 'N/A' else 0)

    # Normalization to 0-100 for better comparison
    max_values = [max(v1,v2) if max(v1,v2) > 0 else 1 for v1,v2 in zip(values1, values2)]
    normalized1 = [v / m * 100 for v,m in zip(values1, max_values)]
    normalized2 = [v / m * 100 for v,m in zip(values2, max_values)]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=normalized1,
        theta=categories,
        fill='toself',
        name=player1_data['name'],
        line_color='#FF6347'
    ))

    fig.add_trace(go.Scatterpolar(
        r=normalized2,
        theta=categories,
        fill='toself',
        name=player2_data['name'],
        line_color='#4682B4'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=True,
        title="Statistics Comparison (Radar)"
    )
    return fig

# Create bar chart (skip N/A values)
def create_bar_chart(player1_data: Dict, player2_data: Dict, selected_stats: List[str]):
    # Filter out stats where both players have N/A
    valid_stats = []
    for stat in selected_stats:
        val1 = format_value(player1_data.get(stat, 0), stat)
        val2 = format_value(player2_data.get(stat, 0), stat)
        if val1 != 'N/A' or val2 != 'N/A':
            valid_stats.append(stat)
    
    if not valid_stats:
        return None
    
    categories = [s.replace("_", " ").replace("G+A", "G+A").title() for s in valid_stats]
    
    # Convert N/A to 0 for chart purposes
    values1 = []
    values2 = []
    for s in valid_stats:
        v1 = format_value(player1_data.get(s, 0), s)
        v2 = format_value(player2_data.get(s, 0), s)
        values1.append(float(v1) if v1 != 'N/A' else 0)
        values2.append(float(v2) if v2 != 'N/A' else 0)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=categories,
        y=values1,
        name=player1_data['name'],
        marker_color='#FF6347'
    ))
    fig.add_trace(go.Bar(
        x=categories,
        y=values2,
        name=player2_data['name'],
        marker_color='#4682B4'
    ))

    fig.update_layout(
        barmode='group',
        title="Statistics Comparison (Bar Chart)",
        xaxis_title="Statistic",
        yaxis_title="Value"
    )
    return fig

# --- UI ---

players = get_all_players()
if not players:
    st.warning("No player data available.")
    st.stop()

player_options = {f"{p['name']} ({p['team']} - {p['league']})": p['id'] for p in players}

# Create a mapping of player_id to position
player_positions = {p['id']: p.get('position', 'Unknown') for p in players}

col1, col2 = st.columns(2)

with col1:
    player1_name = st.selectbox("Select first player", options=list(player_options.keys()))
with col2:
    player2_name = st.selectbox("Select second player", options=[name for name in player_options.keys() if name != player1_name])

# Check if both players are the same type
player1_id = player_options[player1_name]
player2_id = player_options[player2_name]
player1_pos = player_positions.get(player1_id, '')
player2_pos = player_positions.get(player2_id, '')

# FIXED: Handle both "GK" and "Goalkeeper"
is_player1_gk = player1_pos in ["Goalkeeper", "GK"] if player1_pos else False
is_player2_gk = player2_pos in ["Goalkeeper", "GK"] if player2_pos else False

if is_player1_gk != is_player2_gk:
    st.error("⚠️ You cannot compare goalkeepers with field players! Please select two goalkeepers or two field players.")
    st.stop()

season = st.selectbox("Season", options=["2025-26 (Current)", "2024-25", "2023-24", "2022-23"])
# Default to 2025-2026 season
if season == "2025-26 (Current)":
    season = None  # None triggers backend to use 2025-2026
else:
    # Convert format from "2024-25" to "2024-2025"
    if "-" in season and len(season) == 7:
        parts = season.split("-")
        season = f"20{parts[0][-2:]}-20{parts[1]}"

# Determine player type and get appropriate stats
player_type = "goalkeeper" if is_player1_gk else "field_player"
available_stats = get_available_stats(player_type)

st.markdown("### Select statistics to compare")

if is_player1_gk:
    # Goalkeeper stats
    st.info("🧤 Comparing goalkeepers")
    gk_specific_stats = available_stats.get("goalkeeper_specific", [])
    penalties_stats = available_stats.get("penalties", [])
    performance_stats = available_stats.get("performance", [])
    general_stats = available_stats.get("general", [])
    
    selected_stats = []
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**Goalkeeper Stats**")
        for stat in gk_specific_stats:
            if st.checkbox(stat["label"], value=True, key=f"gk_{stat['key']}"):
                selected_stats.append(stat["key"])
    
    with col2:
        st.markdown("**Penalties**")
        for stat in penalties_stats:
            if st.checkbox(stat["label"], value=True, key=f"pen_{stat['key']}"):
                selected_stats.append(stat["key"])
    
    with col3:
        st.markdown("**Performance**")
        for stat in performance_stats:
            if st.checkbox(stat["label"], value=False, key=f"perf_{stat['key']}"):
                selected_stats.append(stat["key"])
    
    with col4:
        st.markdown("**General**")
        for stat in general_stats:
            if st.checkbox(stat["label"], value=True, key=f"gen_{stat['key']}"):
                selected_stats.append(stat["key"])
else:
    # Field player stats
    st.info("⚽ Comparing field players")
    offensive_stats = available_stats.get("offensive", [])
    defensive_stats = available_stats.get("defensive", [])
    general_stats = available_stats.get("general", [])
    
    selected_stats = []
    
    col_off, col_def, col_gen = st.columns(3)
    
    with col_off:
        st.markdown("**Offensive**")
        for stat in offensive_stats:
            # All offensive stats default to True now (removed shots)
            if st.checkbox(stat["label"], value=True, key=f"off_{stat['key']}"):
                selected_stats.append(stat["key"])
    
    with col_def:
        st.markdown("**Defensive**")
        for stat in defensive_stats:
            if st.checkbox(stat["label"], value=False, key=f"def_{stat['key']}"):
                selected_stats.append(stat["key"])
    
    with col_gen:
        st.markdown("**General**")
        for stat in general_stats:
            if st.checkbox(stat["label"], value=True, key=f"gen_{stat['key']}"):
                selected_stats.append(stat["key"])

if st.button("Compare Players"):
    if len(selected_stats) < 3:
        st.warning("Please select at least 3 statistics to compare")
    else:
        comparison = compare_players(player1_id, player2_id, season, selected_stats)
        if comparison:
            st.markdown(f"## Comparison: {comparison['player1']['name']} vs {comparison['player2']['name']}")
            
            # Check if there are any N/A values
            has_na = False
            for stat in selected_stats:
                v1 = format_value(comparison['player1'].get(stat, 0), stat)
                v2 = format_value(comparison['player2'].get(stat, 0), stat)
                if v1 == 'N/A' or v2 == 'N/A':
                    has_na = True
                    break
            
            if has_na:
                st.info("ℹ️ Some statistics show 'N/A' - this means data is not available from FBref.")
            
            radar_fig = create_radar_chart(comparison['player1'], comparison['player2'], selected_stats)
            bar_fig = create_bar_chart(comparison['player1'], comparison['player2'], selected_stats)
            
            if radar_fig:
                st.plotly_chart(radar_fig, use_container_width=True)
            if bar_fig:
                st.plotly_chart(bar_fig, use_container_width=True)
            
            # Display raw data in table with N/A formatting
            player1_values = []
            player2_values = []
            for s in selected_stats:
                v1 = format_value(comparison['player1'].get(s, 0), s)
                v2 = format_value(comparison['player2'].get(s, 0), s)
                player1_values.append(format_display_value(v1))
                player2_values.append(format_display_value(v2))
            
            df_compare = pd.DataFrame({
                "Statistic": [s.replace("_", " ").replace("G+A", "G+A").title() for s in selected_stats],
                comparison['player1']['name']: player1_values,
                comparison['player2']['name']: player2_values,
            })
            st.dataframe(df_compare, use_container_width=True)

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
