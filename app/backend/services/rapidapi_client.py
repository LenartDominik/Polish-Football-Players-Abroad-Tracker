"""
RapidAPI Client for free-api-live-football-data API

API Documentation: https://rapidapi.com/creativesdev/api/free-api-live-football-data
"""
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load .env file to ensure RAPIDAPI_KEY is available
load_dotenv()

logger = logging.getLogger(__name__)


class RapidAPIClient:
    """Client for RapidAPI free-api-live-football-data API"""

    BASE_URL = "https://free-api-live-football-data.p.rapidapi.com"

    # Alternative URL if primary fails
    FALLBACK_URL = "https://api-football-v1.p.rapidapi.com"

    # API endpoints based on RapidAPI documentation
    # Parameter names: 'search', 'playerid', 'teamid', 'leagueid', 'date', 'eventid'
    #
    # NOTE: Player stats are included in team_squad endpoint:
    # - goals, assists, cards, rating, etc.
    # - games/minutes must be calculated from match lineups
    ENDPOINTS = {
        # Players
        "search_players": "/football-players-search",
        "player_detail": "/football-get-player-detail",
        "team_squad": "/football-get-list-player",  # includes player stats
        "top_players_goals": "/football-get-top-players-by-goals",  # leaderboard goals
        "top_players_assists": "/football-get-top-players-by-assists",  # leaderboard assists
        "top_players_rating": "/football-get-top-players-by-rating",  # leaderboard rating
        # Teams
        "search_teams": "/football-teams-search",
        "get_teams_by_league": "/football-get-list-all-team",
        "team_statistics": "/football-league-team",
        "all_seasons": "/football-league-all-seasons",
        # Matches
        "search_matches": "/football-matches-search",
        "matches_by_date": "/football-get-matches-by-date",
        "matches_by_date_and_league": "/football-get-matches-by-date-and-league",
        "matches_by_league": "/football-get-all-matches-by-league",
        "matches_live": "/football-current-live",
        # Match Details (eventid parameter)
        "match_detail": "/football-get-match-detail",
        "match_score": "/football-get-match-score",
        "match_status": "/football-get-match-status",
        "match_all_stats": "/football-get-match-all-stats",
        "match_event_stats": "/football-get-match-event-all-stats",
        # Lineups (for calculating games/minutes) - CORRECTED ENDPOINTS
        "lineup_home": "/football-get-hometeam-lineup",  # home team lineup by event_id
        "lineup_away": "/football-get-awayteam-lineup",  # away team lineup by event_id
        "lineup_all": "/football-get-allteam-lineup",  # full lineup both teams
    }

    def __init__(self, rate_limiter=None):
        """Initialize RapidAPI client

        Args:
            rate_limiter: Optional RateLimiter instance for usage tracking
        """
        # Support both RAPIDAPI_KEY and RAPIDAPI_FOOTBALL_KEY
        self.api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("RAPIDAPI_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError(
                "RAPIDAPI_KEY not found in environment variables!\n"
                "Please set RAPIDAPI_KEY or RAPIDAPI_FOOTBALL_KEY in .env file.\n"
                "Get your key from: https://rapidapi.com/creativesdev/api/free-api-live-football-data"
            )

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
        }

        # Optional rate limiter for persistent usage tracking
        self.rate_limiter = rate_limiter

        # Track API usage (free tier: 100 requests/month)
        self.request_count = 0
        self.max_requests = int(os.getenv("RAPIDAPI_MONTHLY_QUOTA", "100"))
        self.warning_threshold = int(os.getenv("RAPIDAPI_WARNING_THRESHOLD", "80"))

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

                # Record usage in rate limiter if available
                if self.rate_limiter:
                    # Extract endpoint name from path for tracking
                    endpoint_name = endpoint.strip("/").replace("/", "_")
                    if hasattr(self.rate_limiter, 'record_request_async'):
                        await self.rate_limiter.record_request_async(
                            endpoint=endpoint_name,
                            status_code=200
                        )
                    else:
                        self.rate_limiter.record_request(
                            endpoint=endpoint_name,
                            status_code=200
                        )

                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error {e.response.status_code}: {e}")

            # Record failed request in rate limiter if available
            if self.rate_limiter:
                endpoint_name = endpoint.strip("/").replace("/", "_")
                if hasattr(self.rate_limiter, 'record_request_async'):
                    await self.rate_limiter.record_request_async(
                        endpoint=endpoint_name,
                        status_code=e.response.status_code
                    )
                else:
                    self.rate_limiter.record_request(
                        endpoint=endpoint_name,
                        status_code=e.response.status_code
                    )

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

        # API returns: {"status": "success", "response": {"suggestions": [...]}}
        if data and "response" in data:
            suggestions = data["response"].get("suggestions")
            if suggestions:
                return suggestions
        # Fallback for other response formats
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

    async def get_player_stats_by_name(self, player_name: str) -> Optional[Dict]:
        """
        Get player statistics by searching name and filtering from team squad.
        This returns only the specific player's stats, not the whole team.

        Args:
            player_name: Player name to search

        Returns:
            Player dict with stats: goals, assists, cards, rating, etc.
            Returns None if player not found.
        """
        # First search for the player to get their team
        search_results = await self.search_players(player_name)

        if not search_results or len(search_results) == 0:
            logger.warning(f"Player '{player_name}' not found in search")
            return None

        # Get first matching result
        result = search_results[0]

        # Search response structure: {id, teamId, teamName, name, ...}
        # IDs can be int or string
        team_id = None
        player_id = None

        # Try different possible response structures
        if "teamId" in result:
            # Flat structure: {id, teamId, teamName, ...}
            team_id = int(result["teamId"]) if not isinstance(result["teamId"], int) else result["teamId"]
            player_id = int(result["id"]) if isinstance(result["id"], str) and result["id"].isdigit() else result["id"]
        elif "team" in result and isinstance(result["team"], dict):
            # Nested structure: {id, team: {id}, ...}
            team_id = result["team"].get("id")
            player_id = result.get("id")
        elif "statistics" in result and len(result["statistics"]) > 0:
            # Stats structure: {player: {id}, statistics: [{team: {id}}]}
            stats = result["statistics"][0]
            if "team" in stats and isinstance(stats["team"], dict):
                team_id = stats["team"].get("id")
            if "player" in result:
                player_id = result["player"].get("id")

        if not team_id:
            logger.warning(f"No team_id found for player '{player_name}'. Result keys: {list(result.keys())}")
            return None

        logger.info(f"Found player '{player_name}': ID={player_id}, TeamID={team_id}")

        # Now get the full team squad with stats
        squad = await self.get_team_squad(team_id)

        if not squad:
            logger.warning(f"Could not get squad for team_id {team_id}")
            return None

        # Filter to find the specific player
        for player in squad:
            # Match by player_id if we have it (handle both int and string)
            squad_id = player.get("id")
            if player_id:
                # Convert both to int for comparison
                try:
                    if int(squad_id) == int(player_id):
                        return player
                except (ValueError, TypeError):
                    pass
            # Or match by name
            if player.get("name") == player_name:
                return player

        logger.warning(f"Player '{player_name}' (ID: {player_id}) not found in squad")
        return None

    async def get_team_squad(self, team_id: int, season: int = None) -> Optional[List[Dict]]:
        """
        Get all players from a team with their statistics
        This is the MAIN endpoint for efficient sync (all players in one request!)

        Args:
            team_id: RapidAPI team ID
            season: Season year (e.g., 2025 for 2025-26 season) - NOT USED by API

        Returns:
            List of players with full stats including:
            - Basic: id, name, shirtNumber, position, height, age, dateOfBirth
            - Stats: goals, assists, ycards, rcards, rating, transferValue
            - Role/position info
        """
        params = {"teamid": team_id}
        # Note: This API endpoint doesn't accept season parameter

        data = await self._request(self.ENDPOINTS["team_squad"], params)

        # API returns: {"status":"success","response":{"list":{"squad":[...]}}}
        # Squad contains: [{title: "coach", members: [...]}, {title: "keepers", members: [...]}, ...]
        # Need to flatten all members into a single list
        if data and "response" in data:
            squad_data = data["response"].get("list", {}).get("squad", [])
            if squad_data:
                # Flatten all members from each group (coach, keepers, defenders, etc.)
                all_players = []
                for group in squad_data:
                    members = group.get("members", [])
                    all_players.extend(members)
                return all_players
        # Fallback for other response formats
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
        params = {"playerid": player_id}

        return await self._request(self.ENDPOINTS["player_detail"], params)

    async def get_top_players_by_goals(self, league_id: int) -> Optional[List[Dict]]:
        """
        Get top scorers (goals) for a league - LEADERBOARD

        Args:
            league_id: League ID (e.g., 55 for Serie A, 39 for Premier League)

        Returns:
            List of players with goals, team, position, etc.
        """
        params = {"leagueid": league_id}
        data = await self._request(self.ENDPOINTS["top_players_goals"], params)

        if data and "response" in data:
            return data["response"]
        elif data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_top_players_by_assists(self, league_id: int) -> Optional[List[Dict]]:
        """
        Get top assist providers for a league - LEADERBOARD

        Args:
            league_id: League ID (e.g., 55 for Serie A, 39 for Premier League)

        Returns:
            List of players with assists, team, position, etc.
        """
        params = {"leagueid": league_id}
        data = await self._request(self.ENDPOINTS["top_players_assists"], params)

        if data and "response" in data:
            return data["response"]
        elif data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_top_players_by_rating(self, league_id: int) -> Optional[List[Dict]]:
        """
        Get top rated players for a league - LEADERBOARD

        Args:
            league_id: League ID (e.g., 55 for Serie A, 39 for Premier League)

        Returns:
            List of players with rating, team, position, etc.
        """
        params = {"leagueid": league_id}
        data = await self._request(self.ENDPOINTS["top_players_rating"], params)

        if data and "response" in data:
            return data["response"]
        elif data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    # NOTE: get_player_statistics removed - player stats are included in get_team_squad() endpoint
    # Use get_team_squad(team_id) to get all players with their statistics

    async def get_team_statistics(
        self,
        team_id: int,
        league_id: int = None,
        season: int = None
    ) -> Optional[Dict]:
        """
        Get team statistics (useful for calculating goalkeeper stats)

        Args:
            team_id: RapidAPI team ID
            league_id: League ID (NOT USED by this API endpoint)
            season: Season year (NOT USED by this API endpoint)

        Returns:
            Team statistics including goals for/against, clean sheets, etc.
        """
        params = {"teamid": team_id}

        return await self._request(self.ENDPOINTS["team_statistics"], params)

    async def get_teams_by_league(self, league_id: int) -> Optional[List[Dict]]:
        """
        Get all teams in a league

        Args:
            league_id: League ID (e.g., 39 for Premier League, 140 for La Liga)

        Returns:
            List of teams with team_id, name, country, etc.
        """
        params = {"leagueid": league_id}

        data = await self._request(self.ENDPOINTS["get_teams_by_league"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def search_matches(self, search_term: str) -> Optional[List[Dict]]:
        """
        Search for matches by search term

        Args:
            search_term: Search term (e.g., team name, player name)

        Returns:
            List of matching matches
        """
        params = {"search": search_term}

        data = await self._request(self.ENDPOINTS["search_matches"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_matches_by_date(self, date: str) -> Optional[List[Dict]]:
        """
        Get matches for a specific date (format: YYYYMMDD)

        Args:
            date: Date in YYYYMMDD format (e.g., "20241107")

        Returns:
            List of matches for that date
        """
        params = {"date": date}

        data = await self._request(self.ENDPOINTS["matches_by_date"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_matches_by_date_and_league(self, date: str, league_id: int) -> Optional[List[Dict]]:
        """
        Get matches for a specific date and league

        Args:
            date: Date in YYYYMMDD format (e.g., "20241107")
            league_id: League ID

        Returns:
            List of matches for that date in that league
        """
        params = {"date": date, "leagueid": league_id}

        data = await self._request(self.ENDPOINTS["matches_by_date_and_league"], params)

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_live_matches(self) -> Optional[List[Dict]]:
        """
        Get all currently live matches

        Returns:
            List of live matches
        """
        data = await self._request(self.ENDPOINTS["matches_live"])

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_matches_by_league(self, league_id: int, season: str = "2025-2026") -> Optional[List[Dict]]:
        """
        Get all matches for a specific league

        Args:
            league_id: League ID
            season: Season string (e.g., "2025-2026")

        Returns:
            List of all matches in the league
        """
        params = {"leagueid": league_id, "season": season}

        data = await self._request(self.ENDPOINTS["matches_by_league"], params)

        # API returns: {"status": "success", "response": {"matches": [...]}}
        if data and "response" in data:
            matches = data["response"].get("matches")
            if matches:
                return matches
        # Fallback for other response formats
        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    async def get_all_seasons(self) -> Optional[List[Dict]]:
        """
        Get all available seasons for leagues

        Returns:
            List of seasons
        """
        data = await self._request(self.ENDPOINTS["all_seasons"])

        if data and "results" in data:
            return data["results"]
        elif data and isinstance(data, list):
            return data

        return None

    # Match detail functions (use eventid parameter)
    async def get_match_detail(self, event_id: int) -> Optional[Dict]:
        """
        Get detailed information for a specific match

        Args:
            event_id: Match event ID

        Returns:
            Detailed match information
        """
        params = {"eventid": event_id}

        return await self._request(self.ENDPOINTS["match_detail"], params)

    async def get_match_score(self, event_id: int) -> Optional[Dict]:
        """
        Get the score for a specific match

        Args:
            event_id: Match event ID

        Returns:
            Match score information
        """
        params = {"eventid": event_id}

        return await self._request(self.ENDPOINTS["match_score"], params)

    async def get_match_status(self, event_id: int) -> Optional[Dict]:
        """
        Get the status for a specific match

        Args:
            event_id: Match event ID

        Returns:
            Match status (e.g., "FT", "LIVE", "NS")
        """
        params = {"eventid": event_id}

        return await self._request(self.ENDPOINTS["match_status"], params)

    async def get_match_all_stats(self, event_id: int) -> Optional[Dict]:
        """
        Get all statistics for a specific match

        Args:
            event_id: Match event ID

        Returns:
            All match statistics
        """
        params = {"eventid": event_id}

        return await self._request(self.ENDPOINTS["match_all_stats"], params)

    async def get_match_event_stats(self, event_id: int) -> Optional[Dict]:
        """
        Get event statistics for a specific match

        Args:
            event_id: Match event ID

        Returns:
            Match event statistics
        """
        params = {"eventid": event_id}

        return await self._request(self.ENDPOINTS["match_event_stats"], params)

    async def get_lineup_home(self, event_id: int) -> Optional[Dict]:
        """
        Get home team lineup for a match

        Args:
            event_id: Match event ID

        Returns:
            Home team lineup with players, positions, and times
        """
        params = {"eventid": event_id}
        return await self._request(self.ENDPOINTS["lineup_home"], params)

    async def get_lineup_away(self, event_id: int) -> Optional[Dict]:
        """
        Get away team lineup for a match

        Args:
            event_id: Match event ID

        Returns:
            Away team lineup with players, positions, and times
        """
        params = {"eventid": event_id}
        return await self._request(self.ENDPOINTS["lineup_away"], params)

    async def get_lineup_all(self, event_id: int) -> Optional[Dict]:
        """
        Get full lineup for both teams

        Args:
            event_id: Match event ID

        Returns:
            Full lineup with home and away teams
        """
        params = {"eventid": event_id}
        return await self._request(self.ENDPOINTS["lineup_all"], params)

    async def calculate_player_games_minutes(
        self,
        player_id: int,
        team_id: int,
        league_id: int,
        season: str = None
    ) -> Dict[str, int]:
        """
        Calculate games played and minutes for a player by analyzing match lineups.

        This is API-intensive! Use sparingly.
        Consider caching results in database.

        Args:
            player_id: RapidAPI player ID
            team_id: RapidAPI team ID
            league_id: League ID (from LEAGUE_IDS)
            season: Season string (optional, uses current if not provided)

        Returns:
            Dict with 'games' and 'minutes' keys
        """
        logger.info(f"Calculating games/minutes for player {player_id}, team {team_id}")

        games = 0
        total_minutes = 0

        # Get all matches for the league
        matches = await self.get_matches_by_league(league_id)

        if not matches:
            logger.warning(f"No matches found for league {league_id}")
            return {"games": 0, "minutes": 0}

        # Filter matches for player's team
        team_matches = []
        for match in matches:
            teams = match.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})

            if home.get("id") == team_id or away.get("id") == team_id:
                team_matches.append(match)

        logger.info(f"Found {len(team_matches)} matches for team")

        # Check each match for player appearance
        for match in team_matches:
            event_id = match.get("id") or match.get("eventId") or match.get("eventid")

            if not event_id:
                continue

            # Get lineup for this match
            lineup = await self.get_lineup_all(event_id)

            if not lineup:
                continue

            # Check if player is in home or away lineup
            player_found = False
            minutes = 0

            # Check home team
            home_players = lineup.get("home", {}).get("players", [])
            for player in home_players:
                if player.get("id") == player_id:
                    player_found = True
                    # Calculate minutes from time_in/time_out or use 90 if played
                    if player.get("played"):
                        minutes = self._extract_minutes(player)
                    break

            # Check away team if not found
            if not player_found:
                away_players = lineup.get("away", {}).get("players", [])
                for player in away_players:
                    if player.get("id") == player_id:
                        player_found = True
                        if player.get("played"):
                            minutes = self._extract_minutes(player)
                        break

            if player_found and minutes > 0:
                games += 1
                total_minutes += minutes

        logger.info(f"Player {player_id}: {games} games, {total_minutes} minutes")
        return {"games": games, "minutes": total_minutes}

    def _extract_minutes(self, player_data: Dict) -> int:
        """
        Extract minutes played from player lineup data.

        Args:
            player_data: Player data from lineup

        Returns:
            Minutes played
        """
        # Try explicit minutes field
        if "minutes" in player_data:
            return int(player_data["minutes"])

        # Try time_in/time_out
        time_in = player_data.get("time_in", 0)
        time_out = player_data.get("time_out", 90)

        if isinstance(time_in, str):
            time_in = int(time_in.replace("'", ""))
        if isinstance(time_out, str):
            time_out = int(time_out.replace("'", ""))

        return max(0, time_out - time_in)

    async def get_lineup_cached(
        self,
        event_id: int,
        cache_manager=None
    ) -> Optional[Dict]:
        """
        Get lineup with optional caching support.

        Args:
            event_id: Match event ID
            cache_manager: Optional CacheManager instance for caching

        Returns:
            Full lineup with home and away teams, or None if error
        """
        if cache_manager:
            from app.backend.services.cache_manager import cached_lineup_fetch
            return await cached_lineup_fetch(cache_manager, self, event_id)

        # Fallback to direct API call without cache
        return await self.get_lineup_all(event_id)

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

    async def __aenter__(self):
        """Async context manager support"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup"""
        await self.close()


# Common league IDs for Polish players abroad
LEAGUE_IDS = {
    "Premier League": 39,
    "La Liga": 140,
    "Bundesliga": 78,
    "Serie A": 55,  # CORRECTED: 55 is Serie A (not 135 - that was Greek Super League)
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
