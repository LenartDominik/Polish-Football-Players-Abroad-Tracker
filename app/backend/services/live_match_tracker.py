"""
Live Match Tracker for Polish Players

Tracks which Polish players are playing in live matches TODAY.

Features:
- Get live matches from RapidAPI
- Check which Polish players are involved
- Return match info with player details
- Cache results for performance
"""
import logging
from typing import List, Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.backend.models.player import Player
from app.backend.services.rapidapi_client import RapidAPIClient

logger = logging.getLogger(__name__)


class LiveMatchTracker:
    """Tracker for live matches involving Polish players"""

    def __init__(self, db: Session):
        """
        Initialize live match tracker

        Args:
            db: Database session
        """
        self.db = db

    async def get_live_matches_with_polish_players(self) -> List[Dict]:
        """
        Get all live matches that feature Polish players

        Returns:
            List of match dicts with Polish player info
        """
        logger.info("🔍 Checking for live matches with Polish players...")

        # Get all players with RapidAPI team IDs
        players = self.db.query(Player).filter(
            and_(
                Player.rapidapi_team_id.isnot(None),
                Player.rapidapi_player_id.isnot(None)
            )
        ).all()

        if not players:
            logger.warning("No players with RapidAPI IDs found")
            return []

        # Create mapping of team_id -> players
        team_to_players = {}
        for player in players:
            team_id = player.rapidapi_team_id
            if team_id not in team_to_players:
                team_to_players[team_id] = []
            team_to_players[team_id].append({
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "rapidapi_player_id": player.rapidapi_player_id
            })

        # Get live matches from RapidAPI
        async with RapidAPIClient() as client:
            live_matches = await client.get_live_matches()

            if not live_matches:
                logger.info("No live matches currently")
                return []

            logger.info(f"Found {len(live_matches)} live matches")

            # Filter for matches with Polish players
            results = []

            for match in live_matches:
                teams = match.get("teams", {})
                home = teams.get("home", {})
                away = teams.get("away", {})

                home_id = home.get("id")
                away_id = away.get("id")

                # Check if home or away team has Polish players
                polish_players = []

                if home_id in team_to_players:
                    for player in team_to_players[home_id]:
                        polish_players.append({
                            **player,
                            "venue": "Home"
                        })

                if away_id in team_to_players:
                    for player in team_to_players[away_id]:
                        polish_players.append({
                            **player,
                            "venue": "Away"
                        })

                if polish_players:
                    # Get match details
                    match_info = {
                        "match_id": match.get("id") or match.get("eventId") or match.get("eventid"),
                        "league": match.get("league", {}).get("name", "Unknown"),
                        "home_team": home.get("name", "Unknown"),
                        "away_team": away.get("name", "Unknown"),
                        "home_score": home.get("score"),
                        "away_score": away.get("score"),
                        "status": match.get("status", {}).get("long", "Unknown"),
                        "minute": match.get("status", {}).get("minute"),
                        "polish_players": polish_players,
                        "polish_player_count": len(polish_players)
                    }
                    results.append(match_info)

            logger.info(f"Found {len(results)} live matches with Polish players")

            return results

    async def get_matches_today(self) -> List[Dict]:
        """
        Get all matches scheduled for today that feature Polish players

        Returns:
            List of today's matches with Polish player info
        """
        today = date.today()
        today_str = today.strftime("%Y%m%d")

        logger.info(f"🔍 Checking for matches on {today_str}...")

        # Get all players with RapidAPI team IDs
        players = self.db.query(Player).filter(
            and_(
                Player.rapidapi_team_id.isnot(None),
                Player.rapidapi_player_id.isnot(None)
            )
        ).all()

        if not players:
            return []

        # Create mapping of team_id -> players
        team_to_players = {}
        for player in players:
            team_id = player.rapidapi_team_id
            if team_id not in team_to_players:
                team_to_players[team_id] = []
            team_to_players[team_id].append({
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position
            })

        # Get matches for today
        results = []

        async with RapidAPIClient() as client:
            matches_today = await client.get_matches_by_date(today_str)

            if not matches_today:
                logger.info(f"No matches found for {today_str}")
                return []

            for match in matches_today:
                teams = match.get("teams", {})
                home = teams.get("home", {})
                away = teams.get("away", {})

                home_id = home.get("id")
                away_id = away.get("id")

                # Check if home or away team has Polish players
                polish_players = []

                if home_id in team_to_players:
                    for player in team_to_players[home_id]:
                        polish_players.append({**player, "venue": "Home"})

                if away_id in team_to_players:
                    for player in team_to_players[away_id]:
                        polish_players.append({**player, "venue": "Away"})

                if polish_players:
                    match_info = {
                        "match_id": match.get("id") or match.get("eventId"),
                        "date": match.get("date") or today_str,
                        "time": match.get("time", "Unknown"),
                        "league": match.get("league", {}).get("name", "Unknown"),
                        "home_team": home.get("name", "Unknown"),
                        "away_team": away.get("name", "Unknown"),
                        "venue": match.get("venue", "Unknown"),
                        "status": match.get("status", {}).get("long", "Scheduled"),
                        "polish_players": polish_players,
                        "polish_player_count": len(polish_players)
                    }
                    results.append(match_info)

            logger.info(f"Found {len(results)} matches today with Polish players")

            return results

    async def check_player_playing_today(self, player_id: int) -> Dict:
        """
        Check if a specific player is playing today

        Args:
            player_id: Player database ID

        Returns:
            Dict with match info if playing, empty dict if not
        """
        player = self.db.get(Player, player_id)

        if not player or not player.rapidapi_team_id:
            return {"playing": False, "reason": "Player not found or no team ID"}

        # Get today's matches
        matches_today = await self.get_matches_today()

        # Check if player's team is playing today
        for match in matches_today:
            if match.get("home_team") == player.team or match.get("away_team") == player.team:
                # Check if player is in the lineup
                for p in match.get("polish_players", []):
                    if p.get("id") == player_id:
                        return {
                            "playing": True,
                            "player": player.name,
                            "team": player.team,
                            "match": match
                        }

                # Team playing but player not in confirmed lineup
                return {
                    "playing": False,
                    "reason": "Team playing but player not in confirmed lineup",
                    "match": match
                }

        return {"playing": False, "reason": "No match scheduled today"}


async def get_live_summary(db: Session) -> Dict:
    """
    Get a summary of live matches and today's matches with Polish players

    Args:
        db: Database session

    Returns:
        Summary dict with live and today's match info
    """
    tracker = LiveMatchTracker(db)

    # Get live matches
    live_matches = await tracker.get_live_matches_with_polish_players()

    # Get today's matches
    today_matches = await tracker.get_matches_today()

    # Count unique players involved
    live_player_ids = set()
    for match in live_matches:
        for player in match.get("polish_players", []):
            live_player_ids.add(player["id"])

    today_player_ids = set()
    for match in today_matches:
        for player in match.get("polish_players", []):
            today_player_ids.add(player["id"])

    return {
        "timestamp": datetime.now().isoformat(),
        "date": str(date.today()),
        "live_matches": {
            "count": len(live_matches),
            "matches": live_matches,
            "player_count": len(live_player_ids)
        },
        "today_matches": {
            "count": len(today_matches),
            "matches": today_matches,
            "player_count": len(today_player_ids)
        }
    }


async def get_team_live_matches(db: Session, team_name: str) -> List[Dict]:
    """
    Get live matches for a specific team

    Args:
        db: Database session
        team_name: Team name to search for

    Returns:
        List of live matches for this team
    """
    tracker = LiveMatchTracker(db)
    all_live = await tracker.get_live_matches_with_polish_players()

    # Filter by team name (case-insensitive partial match)
    team_matches = []
    team_lower = team_name.lower()

    for match in all_live:
        if (team_lower in match.get("home_team", "").lower() or
            team_lower in match.get("away_team", "").lower()):
            team_matches.append(match)

    return team_matches
