"""
Streamlit App - Cloud Version
Wersja dla Streamlit Cloud deployment (musi być w root jako streamlit_app.py)
"""
import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime

# Backend API URL - użyj Streamlit secrets lub environment variable
BACKEND_API_URL = st.secrets.get("BACKEND_API_URL", os.getenv("BACKEND_API_URL", "http://localhost:8000"))

# Page config
st.set_page_config(
    page_title="🇵🇱 Polish Players Tracker",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
        margin-bottom: 2rem;
    }
    .stat-card {
        background-color: #262730;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #404040;
        margin-bottom: 1rem;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #FF4B4B;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #B0B0B0;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🇵🇱 Polish Players Tracker</div>', unsafe_allow_html=True)
st.markdown("### Monitoring 90+ Polish footballers playing abroad")

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Status
    st.subheader("🔗 API Connection")
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.success("✅ Connected")
            st.caption(f"Backend: {BACKEND_API_URL}")
            
            # Show scheduler status if available
            if "scheduler_running" in data:
                if data["scheduler_running"]:
                    st.info("🤖 Scheduler: Active")
                else:
                    st.warning("🤖 Scheduler: Inactive")
        else:
            st.error("❌ API Error")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.caption(f"Backend URL: {BACKEND_API_URL}")
    
    st.divider()
    
    # Filters
    st.subheader("🔍 Filters")
    
    # Season filter
    season = st.selectbox(
        "Season",
        ["2025-2026", "2024-2025", "2023-2024"],
        index=0
    )
    
    # Competition type filter
    competition_type = st.selectbox(
        "Competition Type",
        ["All", "League", "European Cup", "National Team"],
        index=0
    )
    
    # Position filter
    position = st.selectbox(
        "Position",
        ["All", "FW", "MF", "DF", "GK"],
        index=0
    )

# Main content
try:
    # Fetch players from API
    response = requests.get(f"{BACKEND_API_URL}/api/players", timeout=10)
    
    if response.status_code == 200:
        players = response.json()
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Players</div>
                <div class="stat-value">{len(players)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            forwards = len([p for p in players if p.get('position') == 'FW'])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Forwards</div>
                <div class="stat-value">{forwards}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            midfielders = len([p for p in players if p.get('position') == 'MF'])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Midfielders</div>
                <div class="stat-value">{midfielders}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            defenders = len([p for p in players if p.get('position') in ['DF', 'GK']])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Defenders + GK</div>
                <div class="stat-value">{defenders}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Players table
        st.subheader("📋 Players List")
        
        # Filter players
        filtered_players = players
        
        if position != "All":
            filtered_players = [p for p in filtered_players if p.get('position') == position]
        
        # Create DataFrame
        if filtered_players:
            df = pd.DataFrame(filtered_players)
            
            # Select columns to display
            display_columns = ['name', 'team', 'league', 'position', 'nationality']
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                st.dataframe(
                    df[available_columns],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("⚠️ No data columns available")
        else:
            st.info("No players match the selected filters")
        
        # Player details
        st.divider()
        st.subheader("👤 Player Details")
        
        player_names = [p.get('name', 'Unknown') for p in players]
        selected_player_name = st.selectbox("Select a player", player_names)
        
        if selected_player_name:
            selected_player = next((p for p in players if p.get('name') == selected_player_name), None)
            
            if selected_player and 'id' in selected_player:
                player_id = selected_player['id']
                
                # Fetch player details
                detail_response = requests.get(
                    f"{BACKEND_API_URL}/api/players/{player_id}",
                    timeout=10
                )
                
                if detail_response.status_code == 200:
                    player_details = detail_response.json()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Basic Information**")
                        st.write(f"**Name:** {player_details.get('name', 'N/A')}")
                        st.write(f"**Team:** {player_details.get('team', 'N/A')}")
                        st.write(f"**League:** {player_details.get('league', 'N/A')}")
                        st.write(f"**Position:** {player_details.get('position', 'N/A')}")
                        st.write(f"**Nationality:** {player_details.get('nationality', 'N/A')}")
                    
                    with col2:
                        st.markdown("**Statistics**")
                        # Add statistics here when available from API
                        st.info("Detailed statistics coming soon...")
                else:
                    st.error("Failed to load player details")
    else:
        st.error(f"Failed to fetch players (Status: {response.status_code})")
        
except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to backend API")
    st.info(f"Trying to connect to: {BACKEND_API_URL}")
    st.caption("Make sure the backend is running or check BACKEND_API_URL in Streamlit secrets")
    
except requests.exceptions.Timeout:
    st.error("⏱️ Request timeout")
    st.info("Backend is taking too long to respond")
    
except Exception as e:
    st.error(f"❌ Error: {str(e)}")
    st.caption("Please check the backend connection")

# Footer
st.divider()
st.caption(f"🇵🇱 Polish Players Tracker | Backend: {BACKEND_API_URL} | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
