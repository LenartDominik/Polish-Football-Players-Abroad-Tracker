"""API Client for Polish Players Tracker
Handles all communication with the FastAPI backend.
"""
import requests
import pandas as pd
from typing import Optional, List, Dict, Any
import streamlit as st
import os


class APIClient:
    """Client for communicating with the FastAPI backend"""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize API client with base URL"""
        if base_url is None:
            # Try to get from environment or use default
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        self.base_url = base_url.rstrip("/")
        self.timeout = 30  # seconds
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to API with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to API at {self.base_url}. Make sure the backend is running.")
            st.info("💡 Start backend with: `python -m uvicorn app.backend.main:app --reload`")
            return None
        except requests.exceptions.Timeout:
            st.error(f"⏱️ Request timeout after {self.timeout}s")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ API Error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    # ===== PLAYERS ENDPOINTS =====
    
    def get_all_players(self) -> pd.DataFrame:
        """Get all players from API"""
        data = self._make_request("GET", "/api/players/")
        if data is None:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        if not df.empty:
            # Rename columns to match old structure
            column_mapping = {
                'id': 'id',
                'name': 'name',
                'current_club': 'team',
                'current_league': 'league',
                'nationality': 'nationality',
                'position': 'position',
                'last_updated': 'last_updated'
            }
            df = df.rename(columns=column_mapping)
        return df
    
    def get_player(self, player_id: int) -> Optional[Dict]:
        """Get single player by ID"""
        return self._make_request("GET", f"/api/players/{player_id}")
    
    # ===== STATS ENDPOINTS =====
    
    def get_all_competition_stats(self) -> pd.DataFrame:
        """Get all competition stats"""
        data = self._make_request("GET", "/api/players/stats/competition")
        if data is None:
            return pd.DataFrame()
        return pd.DataFrame(data)
    
    def get_all_goalkeeper_stats(self) -> pd.DataFrame:
        """Get all goalkeeper stats"""
        data = self._make_request("GET", "/api/players/stats/goalkeeper")
        if data is None:
            return pd.DataFrame()
        return pd.DataFrame(data)
    
    def get_all_matches(self) -> pd.DataFrame:
        """Get all player matches"""
        data = self._make_request("GET", "/api/players/stats/matches")
        if data is None:
            return pd.DataFrame()
        return pd.DataFrame(data)
    
    # ===== COMPARISON ENDPOINTS =====
    
    def get_player_stats(self, player_id: int) -> Dict[str, pd.DataFrame]:
        """Get all stats for a player (competition_stats, goalkeeper_stats, player_matches)"""
        data = self._make_request("GET", f"/comparison/players/{player_id}/stats")
        if data is None:
            return {
                'competition_stats': pd.DataFrame(),
                'goalkeeper_stats': pd.DataFrame(),
                'player_matches': pd.DataFrame()
            }
        
        return {
            'competition_stats': pd.DataFrame(data.get('competition_stats', [])),
            'goalkeeper_stats': pd.DataFrame(data.get('goalkeeper_stats', [])),
            'player_matches': pd.DataFrame(data.get('player_matches', []))
        }
    
    # ===== MATCHLOGS ENDPOINTS =====
    
    def get_player_matches(
        self, 
        player_id: int,
        competition: Optional[str] = None,
        season: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get matches for a player with optional filters"""
        params = {}
        if competition:
            params['competition'] = competition
        if season:
            params['season'] = season
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if limit:
            params['limit'] = limit
        
        data = self._make_request("GET", f"/api/players/{player_id}/matches", params=params)
        if data is None:
            return pd.DataFrame()
        
        return pd.DataFrame(data)


# Global API client instance
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance"""
    # Check if running locally or in cloud
    api_url = os.getenv("API_BASE_URL")
    
    if api_url is None:
        # Try to detect if we're in Streamlit Cloud
        if os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("IS_STREAMLIT_CLOUD"):
            api_url = os.getenv("RENDER_BACKEND_URL", "https://your-backend.onrender.com")
        else:
            api_url = "http://localhost:8000"
    
    return APIClient(api_url)
