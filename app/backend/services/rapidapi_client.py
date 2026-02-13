"""
RapidAPI Client for free-api-live-football-data API
Replaces FBref scraper with professional API data source.

API Documentation: https://rapidapi.com/creativesdev/api/free-api-live-football-data
"""
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class RapidAPIClient:
    """Client for RapidAPI free-api-live-football-data API"""

    BASE_URL = "https://free-api-live-football-data.p.rapidapi.com"

    # API endpoints based on RapidAPI documentation
    ENDPOINTS = {
        "search_players": "/v3/searchplayers",
        "player_detail": "/v3/player-detail-by-player-id",
        "team_squad": "/v3/players-list-all-by-team-id",
        "search_teams": "/v3/search-teams",
        "team_statistics": "/v3/team-statistics",
        "player_statistics": "/v3/player-statistics",
        "fixtures": "/v3/fixtures",
        "fixture_stats": "/v3/fixture-statistics",
    }

    def __init__(self):
        """Initialize RapidAPI client"""
        self.api_key = os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError(
                "RAPIDAPI_KEY not found in environment variables!\n"
                "Please set RAPIDAPI_KEY in .env file.\n"
                "Get your key from: https://rapidapi.com/creativesdev/api/free-api-live-football-data"
            )

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
        }

        # Track API usage (free tier: 100 requests/month)
        self.request_count = 0
        self.max_requests = 100
        self.warning_threshold = 80

        logger.info("RapidAPI client initialized")

    async def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make HTTP request to RapidAPI with error handling and rate tracking

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response or None if error
        """
        self.request_count += 1

        # Warn if approaching limit
        if self.request_count >= self.warning_threshold:
            logger.warning(f"⚠️ API usage: {self.request_count}/{self.max_requests} requests this month")

        if self.request_count >= self.max_requests:
            logger.error(f"❌ API limit reached: {self.request_count}/{self.max_requests} requests")
            return None

        url = f"{self.BASE_URL}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"📡 API Request: {endpoint} (Request #{self.request_count})")
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(f"✅ API Response received")
                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error {e.response.status_code}: {e}")
            return None
        except httpx.TimeoutException:
            logger.error(f"❌ Request timeout: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"❌ Request error: {e}")
            return None

    async def search_players(self, name: str, league: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Search for players by name

        Args:
            name: Player name to search
            league: Optional league ID filter

        Returns:
            List of matching players with id, name, team, etc.
        """
        params = {"search": name}
        if league:
            params["league"] = league

        data = await self._request(self.ENDPOINTS["search_players"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def search_teams(self, name: str) -> Optional[List[Dict]]:
        """
        Search for teams by name

        Args:
            name: Team name to search

        Returns:
            List of matching teams with team_id, name, country, etc.
        """
        params = {"search": name}

        data = await self._request(self.ENDPOINTS["search_teams"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_team_squad(self, team_id: int, season: int = None) -> Optional[List[Dict]]:
        """
        Get all players from a team with their statistics
        This is the MAIN endpoint for efficient sync (all players in one request!)

        Args:
            team_id: RapidAPI team ID
            season: Season year (e.g., 2025 for 2025-26 season)

        Returns:
            List of players with stats: goals, assists, cards, rating, etc.
        """
        params = {"id": team_id}
        if season:
            params["season"] = season

        data = await self._request(self.ENDPOINTS["team_squad"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_player_detail(self, player_id: int) -> Optional[Dict]:
        """
        Get detailed player information

        Args:
            player_id: RapidAPI player ID

        Returns:
            Player details including age, height, nationality, position, etc.
        """
        params = {"id": player_id}

        return await self._request(self.ENDPOINTS["player_detail"], params)

    async def get_player_statistics(
        self,
        player_id: int,
        league_id: int,
        season: int
    ) -> Optional[Dict]:
        """
        Get detailed statistics for a player in a specific league/season

        Args:
            player_id: RapidAPI player ID
            league_id: League ID
            season: Season year (e.g., 2025 for 2025-26)

        Returns:
            Detailed player statistics
        """
        params = {
            "id": player_id,
            "league": league_id,
            "season": season
        }

        data = await self._request(self.ENDPOINTS["player_statistics"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list) and len(data) > 0:
            return data[0]

        return data

    async def get_team_statistics(
        self,
        team_id: int,
        league_id: int,
        season: int
    ) -> Optional[Dict]:
        """
        Get team statistics (useful for calculating goalkeeper stats)

        Args:
            team_id: RapidAPI team ID
            league_id: League ID
            season: Season year

        Returns:
            Team statistics including goals for/against, clean sheets, etc.
        """
        params = {
            "id": team_id,
            "league": league_id,
            "season": season
        }

        return await self._request(self.ENDPOINTS["team_statistics"], params)

    async def get_fixtures(
        self,
        team_id: Optional[int] = None,
        player_id: Optional[int] = None,
        league_id: Optional[int] = None,
        season: int = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Get fixtures/match data for calculating match logs

        Args:
            team_id: Filter by team
            player_id: Filter by player (if API supports)
            league_id: Filter by league
            season: Season year
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of fixtures with match data
        """
        params = {}
        if team_id:
            params["team"] = team_id
        if player_id:
            params["player"] = player_id
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = await self._request(self.ENDPOINTS["fixtures"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_fixture_stats(self, fixture_id: int) -> Optional[Dict]:
        """
        Get detailed statistics for a specific fixture
        Useful for calculating xG and advanced stats

        Args:
            fixture_id: Match fixture ID

        Returns:
            Detailed fixture statistics
        """
        params = {"id": fixture_id}

        return await self._request(self.ENDPOINTS["fixture_stats"], params)

    def get_usage_report(self) -> Dict:
        """
        Get current API usage report

        Returns:
            Dict with usage statistics
        """
        return {
            "requests_used": self.request_count,
            "requests_remaining": max(0, self.max_requests - self.request_count),
            "max_requests": self.max_requests,
            "percentage": round((self.request_count / self.max_requests) * 100, 2)
        }

    async def close(self):
        """Clean up resources"""
        logger.info(f"RapidAPI client closed. Total requests: {self.request_count}")


# Common league IDs for Polish players abroad
LEAGUE_IDS = {
    "Premier League": 39,
    "La Liga": 140,
    "Bundesliga": 78,
    "Serie A": 135,
    "Ligue 1": 61,
    "Eredivisie": 88,
    "Primeira Liga": 94,
    "Belgian Pro League": 96,
    "Scottish Premiership": 98,
    "Super Lig": 203,
    "Champions League": 2,
    "Europa League": 3,
    "Conference League": 5,
}


def get_season_year() -> int:
    """
    Get the season year for API calls
    For 2025-26 season, returns 2025
    For 2024-25 season, returns 2024
    """
    current_date = datetime.now()
    if current_date.month >= 7:
        return current_date.year
    else:
        return current_date.year - 1
