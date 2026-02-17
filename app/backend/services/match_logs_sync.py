"""
Match Logs Sync Service for RapidAPI

Syncs player_matches table from RapidAPI lineups data.
Tracks match-by-match statistics with minutes played for each player.

Key features:
- Incremental sync (only new/updated matches)
- Supports all competition types (LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM)
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.models.lineup_cache import LineupCache
from app.backend.services.rapidapi_client import RapidAPIClient, LEAGUE_IDS

logger = logging.getLogger(__name__)


# Competition type mapping for RapidAPI league IDs
COMPETITION_TYPE_MAP = {
    # Domestic leagues
    39: ("LEAGUE", "Premier League"),
    140: ("LEAGUE", "La Liga"),
    78: ("LEAGUE", "Bundesliga"),
    55: ("LEAGUE", "Serie A"),
    61: ("LEAGUE", "Ligue 1"),
    88: ("LEAGUE", "Eredivisie"),
    94: ("LEAGUE", "Primeira Liga"),
    96: ("LEAGUE", "Belgian Pro League"),
    98: ("LEAGUE", "Scottish Premiership"),
    203: ("LEAGUE", "Super Lig"),

    # European cups
    2: ("EUROPEAN_CUP", "Champions League"),
    3: ("EUROPEAN_CUP", "Europa League"),
    5: ("EUROPEAN_CUP", "Conference League"),
}


def get_competition_info(league_id: int, league_name: str = None) -> tuple:
    """
    Get competition type and name from league ID

    Returns:
        (competition_type, competition_name) tuple
    """
    if league_id in COMPETITION_TYPE_MAP:
        return COMPETITION_TYPE_MAP[league_id]

    # Default detection from league name
    if league_name:
        name_lower = league_name.lower()
        if "cup" in name_lower and "europa" not in name_lower:
            return ("DOMESTIC_CUP", league_name)
        elif any(x in name_lower for x in ["champions", "europa", "conference"]):
            return ("EUROPEAN_CUP", league_name)
        else:
            return ("LEAGUE", league_name)

    # Fallback
    return ("LEAGUE", league_name or "Unknown")


class MatchLogsSync:
    """Service for syncing player match logs from RapidAPI lineups"""

    def __init__(self, db: Session):
        """
        Initialize sync service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.client = None  # Created when needed (async context)

    async def sync_player_match_logs(
        self,
        player: Player,
        season: str = None,
        force_full_sync: bool = False
    ) -> Dict[str, int]:
        """
        Sync all match logs for a player from RapidAPI

        Args:
            player: Player model instance
            season: Season string (e.g., "2025-2026"). Uses current if None.
            force_full_sync: If True, syncs all matches. If False, only new/updated.

        Returns:
            Dict with sync results: {added, updated, skipped, errors}
        """
        if not player.rapidapi_player_id or not player.rapidapi_team_id:
            logger.warning(f"Player {player.name} missing RapidAPI IDs - skipping match logs sync")
            return {"added": 0, "updated": 0, "skipped": 0, "errors": 1}

        logger.info(f"Syncing match logs for {player.name} (ID: {player.id})")

        # Determine current season if not provided
        if not season:
            season = self._get_current_season()

        # Create RapidAPI client
        self.client = RapidAPIClient()

        try:
            # Get league ID from player's league
            league_id = self._get_league_id(player.league)
            if not league_id:
                logger.warning(f"Unknown league '{player.league}' - cannot sync match logs")
                return {"added": 0, "updated": 0, "skipped": 0, "errors": 1}

            # Get all matches for the league/season
            matches = await self.client.get_matches_by_league(league_id, season)

            if not matches:
                logger.warning(f"No matches found for league {league_id}, season {season}")
                return {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

            # Filter matches for player's team
            team_matches = self._filter_team_matches(matches, player.rapidapi_team_id)

            logger.info(f"Found {len(team_matches)} team matches to check for player appearances")

            results = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

            # Process each match
            for match in team_matches:
                result = await self._sync_match_for_player(match, player, force_full_sync)

                if result == "added":
                    results["added"] += 1
                elif result == "updated":
                    results["updated"] += 1
                elif result == "skipped":
                    results["skipped"] += 1
                else:
                    results["errors"] += 1

            logger.info(f"Match logs sync complete for {player.name}: "
                       f"+{results['added']} ~{results['updated']} ={results['skipped']} !{results['errors']}")

            return results

        finally:
            await self.client.close()

    async def _sync_match_for_player(
        self,
        match: Dict,
        player: Player,
        force_full_sync: bool
    ) -> str:
        """
        Sync a single match for a player

        Returns:
            "added", "updated", "skipped", or "error"
        """
        event_id = match.get("id") or match.get("eventId") or match.get("eventid")
        if not event_id:
            return "error"

        # Check if player appeared in this match (from cache or API)
        lineup_data = await self._get_player_lineup_data(event_id, player.rapidapi_player_id)

        if not lineup_data:
            # Player didn't play in this match
            return "skipped"

        # Parse match date
        match_date_str = match.get("date") or match.get("matchDate") or match.get("time")
        match_date = self._parse_match_date(match_date_str)

        if not match_date:
            return "error"

        # Check if record already exists
        existing_match = self.db.query(PlayerMatch).filter(
            and_(
                PlayerMatch.player_id == player.id,
                PlayerMatch.match_date == match_date,
                PlayerMatch.competition == player.league  # Use league as competition name
            )
        ).first()

        # For incremental sync, skip if exists and not forced
        if existing_match and not force_full_sync:
            # Check if data_source is already rapidapi
            if existing_match.data_source == "rapidapi":
                return "skipped"
            # Otherwise, we'll update it

        # Extract match details
        opponent = self._extract_opponent(match, player.rapidapi_team_id)
        venue = self._extract_venue(match, player.rapidapi_team_id)
        result = self._extract_result(match, player.rapidapi_team_id, venue)

        # Build match record
        match_data = {
            "player_id": player.id,
            "match_date": match_date,
            "competition": player.league,
            "round": match.get("round", ""),
            "venue": venue,
            "opponent": opponent,
            "result": result,
            "minutes_played": lineup_data.get("minutes", 0),
            "data_source": "rapidapi"
        }

        # Add stats from lineup if available
        if "stats" in lineup_data:
            stats = lineup_data["stats"]
            match_data.update({
                "goals": stats.get("goals", 0),
                "assists": stats.get("assists", 0),
                "shots": stats.get("shots", 0),
                "yellow_cards": stats.get("yellowCards", 0),
                "red_cards": stats.get("redCards", 0),
            })

        if existing_match:
            # Update existing record
            for key, value in match_data.items():
                if key != "player_id":  # Don't update primary key
                    setattr(existing_match, key, value)
            self.db.commit()
            return "updated"
        else:
            # Create new record
            new_match = PlayerMatch(**match_data)
            self.db.add(new_match)
            self.db.commit()
            return "added"

    async def _get_player_lineup_data(
        self,
        event_id: int,
        player_api_id: int
    ) -> Optional[Dict]:
        """
        Get player lineup data from cache or API

        Returns dict with minutes and optional stats, or None if player didn't play
        """
        # Check cache first
        cached = self.db.query(LineupCache).filter(
            and_(
                LineupCache.player_api_id == player_api_id,
                LineupCache.event_id == event_id
            )
        ).first()

        # Check if cache is fresh (within 24 hours)
        if cached:
            cache_age = (datetime.now() - cached.updated_at).total_seconds() / 3600
            if cache_age < 24:
                # Return cached data if player played (minutes > 0)
                if cached.minutes > 0:
                    return {"minutes": cached.minutes}
                else:
                    return None

        # Fetch from API if cache miss or stale
        if not self.client:
            self.client = RapidAPIClient()

        lineup = await self.client.get_lineup_all(event_id)

        if not lineup:
            return None

        # Search for player in both home and away lineups
        player_data = None

        # Check home team
        home_players = lineup.get("home", {}).get("players", [])
        for player in home_players:
            if player.get("id") == player_api_id:
                player_data = player
                break

        # Check away team if not found
        if not player_data:
            away_players = lineup.get("away", {}).get("players", [])
            for player in away_players:
                if player.get("id") == player_api_id:
                    player_data = player
                    break

        if not player_data:
            # Player not in lineup - cache this fact
            self._cache_lineup_data(event_id, player_api_id, 0)
            return None

        # Extract minutes
        minutes = self._extract_minutes_from_lineup(player_data)

        # Extract stats if available
        stats = {}
        if "statistics" in player_data:
            stats = player_data["statistics"]

        # Update cache
        self._cache_lineup_data(event_id, player_api_id, minutes)

        return {"minutes": minutes, "stats": stats}

    def _cache_lineup_data(self, event_id: int, player_api_id: int, minutes: int):
        """Update lineup cache with player appearance data"""
        existing = self.db.query(LineupCache).filter(
            and_(
                LineupCache.player_api_id == player_api_id,
                LineupCache.event_id == event_id
            )
        ).first()

        if existing:
            existing.minutes = minutes
            existing.updated_at = datetime.now()
            existing.data_source = "rapidapi"
        else:
            new_cache = LineupCache(
                player_api_id=player_api_id,
                event_id=event_id,
                minutes=minutes,
                updated_at=datetime.now(),
                data_source="rapidapi"
            )
            self.db.add(new_cache)

        self.db.commit()

    def _extract_minutes_from_lineup(self, player_data: Dict) -> int:
        """Extract minutes played from lineup player data"""
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

    def _filter_team_matches(self, matches: List[Dict], team_id: int) -> List[Dict]:
        """Filter matches to only those involving the specified team"""
        team_matches = []
        for match in matches:
            teams = match.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})

            home_id = home.get("id")
            away_id = away.get("id")

            if home_id == team_id or away_id == team_id:
                team_matches.append(match)

        return team_matches

    def _get_league_id(self, league_name: str) -> Optional[int]:
        """Get RapidAPI league ID from league name"""
        for league_id, (comp_type, comp_name) in COMPETITION_TYPE_MAP.items():
            if league_name in comp_name or comp_name in league_name:
                return league_id
        return None

    def _get_current_season(self) -> str:
        """Get current season string (e.g., '2025-2026')"""
        current_year = datetime.now().year
        current_month = datetime.now().month

        if current_month >= 7:
            # Season starts in July/August
            return f"{current_year}-{current_year + 1}"
        else:
            # Still in previous season
            return f"{current_year - 1}-{current_year}"

    def _parse_match_date(self, date_str: str) -> Optional[date]:
        """Parse match date from various formats"""
        if not date_str:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_opponent(self, match: Dict, team_id: int) -> str:
        """Extract opponent name from match data"""
        teams = match.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        if home.get("id") == team_id:
            return away.get("name", "Unknown")
        else:
            return home.get("name", "Unknown")

    def _extract_venue(self, match: Dict, team_id: int) -> str:
        """Extract venue (Home/Away) from match data"""
        teams = match.get("teams", {})
        home = teams.get("home", {})

        if home.get("id") == team_id:
            return "Home"
        else:
            return "Away"

    def _extract_result(self, match: Dict, team_id: int, venue: str) -> str:
        """Extract match result (e.g., 'W 3-1', 'L 0-2', 'D 1-1')"""
        teams = match.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        home_score = home.get("score", 0)
        away_score = away.get("score", 0)

        if venue == "Home":
            team_score = home_score
            opponent_score = away_score
        else:
            team_score = away_score
            opponent_score = home_score

        if team_score > opponent_score:
            result_char = "W"
        elif team_score < opponent_score:
            result_char = "L"
        else:
            result_char = "D"

        return f"{result_char} {team_score}-{opponent_score}"


async def sync_all_match_logs(db: Session, force_full_sync: bool = False, level: int = None) -> Dict:
    """
    Sync match logs for all players in database

    Args:
        db: Database session
        force_full_sync: If True, syncs all matches for all players
        level: Filter by player level (1=Top 8 leagues, 2=Lower leagues, None=All)

    Returns:
        Summary dict with total results
    """
    query = db.query(Player).filter(
        and_(
            Player.rapidapi_player_id.isnot(None),
            Player.rapidapi_team_id.isnot(None)
        )
    )

    if level is not None:
        query = query.filter(Player.level == level)

    players = query.all()

    level_desc = f"Level {level}" if level else "All levels"
    logger.info(f"Starting match logs sync for {len(players)} players ({level_desc})")

    total_results = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    for player in players:
        sync_service = MatchLogsSync(db)
        results = await sync_service.sync_player_match_logs(player, force_full_sync=force_full_sync)

        for key in total_results:
            total_results[key] += results[key]

    logger.info(f"Match logs sync complete ({level_desc}): "
               f"+{total_results['added']} ~{total_results['updated']} "
               f"={total_results['skipped']} !{total_results['errors']}")

    return total_results
