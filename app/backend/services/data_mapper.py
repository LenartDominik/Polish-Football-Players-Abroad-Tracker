"""
Data Mapper for RapidAPI responses to SQLAlchemy models
Converts RapidAPI JSON data to database model objects
"""
import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from ..models.player import Player
from ..models.competition_stats import CompetitionStats
from ..models.goalkeeper_stats import GoalkeeperStats
from ..models.player_match import PlayerMatch
from ..utils import get_competition_type

logger = logging.getLogger(__name__)


# Field mapping from RapidAPI to database models
RAPIDAPI_FIELD_MAP = {
    # Player fields
    "player_id": "rapidapi_player_id",
    "team_id": "rapidapi_team_id",
    "player_name": "name",
    "team_name": "team",

    # Competition stats fields
    "goals": "goals",
    "assists": "assists",
    "yellowcards": "yellow_cards",
    "redcards": "red_cards",
    "appearances": "games",
    "minutes": "minutes",
    "rating": "rating",  # New field - not in original model

    # Goalkeeper specific
    "saves": "saves",
    "conceded": "goals_against",
    "cleansheets": "clean_sheets",
}


def map_player_data(api_response: Dict, db_player: Player = None) -> Dict:
    """
    Convert RapidAPI player data to Player model attributes

    Handles both response formats:
    - NESTED (player_detail): {player: {name, id, ...}, statistics: [{team: {...}, league: {...}}]}
    - FLAT (team_squad): {id, name, teamId, teamName, position, goals, assists, ...}

    Args:
        api_response: Raw API response for a player
        db_player: Existing Player instance to update (optional)

    Returns:
        Dict of Player model attributes
    """
    if not api_response:
        return None

    mapped = {}

    # Check for FLAT structure first (team_squad response)
    # Flat structure has id/name at top level
    if "id" in api_response and "name" in api_response:
        mapped["name"] = api_response.get("name")
        mapped["rapidapi_player_id"] = api_response.get("id")

        # Team info from flat structure
        if "teamId" in api_response:
            mapped["rapidapi_team_id"] = api_response.get("teamId")
        if "teamName" in api_response:
            mapped["team"] = api_response.get("teamName")

        # Position from flat structure
        if "position" in api_response:
            pos = api_response.get("position", "").upper()
            # Normalize position names
            if "GOALKEEPER" in pos or pos == "GK":
                mapped["position"] = "GK"
            elif "DEFENDER" in pos or pos == "DF" or pos == "D":
                mapped["position"] = "DF"
            elif "MIDFIELDER" in pos or pos == "MF" or pos == "M":
                mapped["position"] = "MF"
            elif "FORWARD" in pos or pos == "FW" or pos == "F" or "ATTACK" in pos:
                mapped["position"] = "FW"

    # NESTED structure (player_detail response)
    elif "player" in api_response:
        player_data = api_response["player"]
        mapped["name"] = player_data.get("name") or player_data.get("firstname", "") + " " + player_data.get("lastname", "")
        mapped["rapidapi_player_id"] = player_data.get("id")
        mapped["position"] = player_data.get("position")  # GK, DF, MF, FW
        mapped["nationality"] = player_data.get("nationality")

    # Team info from nested statistics
    if "statistics" in api_response and len(api_response["statistics"]) > 0:
        stats = api_response["statistics"][0]
        if "team" not in mapped or not mapped.get("team"):
            mapped["team"] = stats.get("team", {}).get("name")
        if "rapidapi_team_id" not in mapped or not mapped.get("rapidapi_team_id"):
            mapped["rapidapi_team_id"] = stats.get("team", {}).get("id")
        if "league" not in mapped:
            mapped["league"] = stats.get("league", {}).get("name")

    mapped["last_updated"] = date.today()

    logger.debug(f"Mapped player data: {mapped.get('name')} -> ID: {mapped.get('rapidapi_player_id')}")
    return mapped


def map_competition_stats(
    api_response: Dict,
    player_id: int,
    season: str,
    competition_name: str,
    competition_type: str = None
) -> CompetitionStats:
    """
    Convert RapidAPI stats to CompetitionStats model

    Handles two response formats:
    - NESTED: {statistics: [{league: {name: ...}, games: {...}}]}
    - FLAT: {goals, assists, ycards, rcards, rating, games, minutes, ...}

    Args:
        api_response: API response with player statistics
        player_id: Database player ID
        season: Season string (e.g., "2025-2026")
        competition_name: Name of competition
        competition_type: LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM

    Returns:
        CompetitionStats instance
    """
    if not api_response:
        return None

    # Extract stats from API response
    stats_data = None

    # Handle NESTED format: {statistics: [{league: {name: ...}, games: {...}}]}
    if "statistics" in api_response and isinstance(api_response["statistics"], list):
        # Find stats for the requested competition
        for stats in api_response["statistics"]:
            league_name = stats.get("league", {}).get("name", "")
            if competition_name.lower() in league_name.lower() or league_name.lower() in competition_name.lower():
                stats_data = stats.get("games", {}) or stats
                break

    elif "games" in api_response:
        stats_data = api_response["games"]

    # Handle FLAT format: stats directly on api_response
    # If no stats_data found and we have flat stats, use the api_response directly
    if not stats_data and ('goals' in api_response or 'assists' in api_response or 'games' in api_response):
        stats_data = api_response

    if not stats_data:
        # Create minimal stats if no data found
        stats_data = {}

    # Map fields - support both flat and nested formats
    comp_stats = CompetitionStats(
        player_id=player_id,
        season=season,
        competition_name=competition_name,
        competition_type=competition_type or get_competition_type(competition_name),

        # Basic stats - try flat keys first, then nested
        games=int(stats_data.get("games", 0) or stats_data.get("appearances", 0) or 0),
        games_starts=int(stats_data.get("games_starts", 0) or stats_data.get("lineups", 0) or 0),
        minutes=int(stats_data.get("minutes", 0) or 0),

        # Attack stats
        goals=int(stats_data.get("goals", 0) or 0),
        assists=int(stats_data.get("assists", 0) or 0),

        # Cards - support multiple key names
        yellow_cards=int(stats_data.get("yellow_cards", 0) or stats_data.get("ycards", 0) or stats_data.get("yellowcards", 0) or 0),
        red_cards=int(stats_data.get("red_cards", 0) or stats_data.get("rcards", 0) or stats_data.get("redcards", 0) or 0),

        # Shots (may not be in flat format)
        shots=int(stats_data.get("shots", 0) or stats_data.get("shots", {}).get("total", 0) or 0),
        shots_on_target=int(stats_data.get("shots_on_target", 0) or stats_data.get("shots", {}).get("on", 0) or 0),

        # Pass stats (may not be in flat format)
        passes_attempted=int(stats_data.get("passes_attempted", 0) or stats_data.get("passes", {}).get("total", 0) or 0),
        passes_completed=int(stats_data.get("passes_completed", 0) or stats_data.get("passes", {}).get("accuracy", 0) or 0),
    )

    # Calculate pass completion percentage
    if comp_stats.passes_attempted > 0:
        comp_stats.pass_completion_pct = round((comp_stats.passes_completed / comp_stats.passes_attempted) * 100, 2)

    # Note: xG, npxG, xA not provided by RapidAPI - will be set to 0 or None
    comp_stats.xg = 0.0
    comp_stats.npxg = 0.0
    comp_stats.xa = 0.0

    logger.debug(f"Mapped competition stats for player {player_id}: {comp_stats.games} games, {comp_stats.goals} goals")
    return comp_stats


def map_goalkeeper_stats(
    api_response: Dict,
    player_id: int,
    season: str,
    competition_name: str,
    competition_type: str = None,
    team_stats_response: Dict = None
) -> GoalkeeperStats:
    """
    Convert RapidAPI stats to GoalkeeperStats model

    Handles two response formats:
    - NESTED: {statistics: [{league: {name: ...}, games: {...}, goals: {...}}]}
    - FLAT: {goals, assists, ycards, rcards, saves, cleansheets, conceded, ...}

    Note: RapidAPI may not provide all GK stats. Use team_stats_response
    to calculate clean sheets and goals against from team data.

    Args:
        api_response: API response with player statistics
        team_stats_response: Optional team statistics for calculating GK stats
        player_id: Database player ID
        season: Season string
        competition_name: Name of competition
        competition_type: Competition type

    Returns:
        GoalkeeperStats instance
    """
    if not api_response:
        return None

    stats_data = {}

    # Handle NESTED format
    if "statistics" in api_response and isinstance(api_response["statistics"], list):
        for stats in api_response["statistics"]:
            league_name = stats.get("league", {}).get("name", "")
            if competition_name.lower() in league_name.lower() or league_name.lower() in competition_name.lower():
                stats_data = stats.get("goals", {}) or {}
                # Also get games data
                if "games" in stats:
                    stats_data.update(stats["games"])
                break

    elif "games" in api_response:
        stats_data = api_response["games"]

    # Handle FLAT format - stats directly on api_response
    if not stats_data and ('goals' in api_response or 'saves' in api_response or 'cleansheets' in api_response):
        stats_data = api_response

    # Build goalkeeper stats
    gk_stats = GoalkeeperStats(
        player_id=player_id,
        season=season,
        competition_name=competition_name,
        competition_type=competition_type or get_competition_type(competition_name),

        # Games and minutes - support multiple key names
        games=int(stats_data.get("games", 0) or stats_data.get("appearances", 0) or 0),
        games_starts=int(stats_data.get("games_starts", 0) or stats_data.get("lineups", 0) or 0),
        minutes=int(stats_data.get("minutes", 0) or 0),

        # Goals conceded - support multiple key names
        goals_against=int(stats_data.get("goals_against", 0) or stats_data.get("conceded", 0) or 0),
    )

    # Calculate goals against per 90
    if gk_stats.minutes > 0:
        gk_stats.goals_against_per90 = round((gk_stats.goals_against / gk_stats.minutes) * 90, 2)

    # Use team stats to calculate clean sheets if not provided
    if team_stats_response:
        # Calculate clean sheets from team clean sheets data
        team_clean_sheets = team_stats_response.get("clean_sheet", {}).get("total", 0) or 0
        gk_stats.clean_sheets = min(team_clean_sheets, gk_stats.games)

        # Saves - if not provided directly, estimate from shots on target against
        if "saves" not in stats_data:
            shots_on_target_against = team_stats_response.get("shots", {}).get("on_target", {}).get("total", 0) or 0
            goals = gk_stats.goals_against
            gk_stats.saves = max(0, shots_on_target_against - goals)

        # Calculate save percentage
        if gk_stats.saves > 0 and gk_stats.goals_against > 0:
            total_shots = gk_stats.saves + gk_stats.goals_against
            gk_stats.save_percentage = round((gk_stats.saves / total_shots) * 100, 2) if total_shots > 0 else 0.0
    else:
        # Use direct stats if available - support multiple key names
        gk_stats.saves = int(stats_data.get("saves", 0) or 0)
        gk_stats.clean_sheets = int(stats_data.get("clean_sheets", 0) or stats_data.get("cleansheets", 0) or 0)

        # Save percentage
        if gk_stats.saves > 0:
            total_shots = gk_stats.saves + gk_stats.goals_against
            gk_stats.save_percentage = round((gk_stats.saves / total_shots) * 100, 2) if total_shots > 0 else 0.0

    logger.debug(f"Mapped goalkeeper stats for player {player_id}: {gk_stats.games} games, {gk_stats.clean_sheets} CS")
    return gk_stats


def map_match_logs_from_fixtures(
    fixtures: List[Dict],
    player_id: int,
    player_stats: Dict = None
) -> List[PlayerMatch]:
    """
    Convert RapidAPI fixtures to PlayerMatch records

    Args:
        fixtures: List of fixture/match data from API
        player_id: Database player ID
        player_stats: Optional player stats for filling in match details

    Returns:
        List of PlayerMatch instances
    """
    if not fixtures:
        return []

    matches = []

    for fixture in fixtures:
        try:
            # Parse match date
            match_date_str = fixture.get("date", {})
            if isinstance(match_date_str, dict):
                match_date_str = match_date_str.get("date", match_date_str.get("iso", ""))

            match_date = None
            if match_date_str:
                try:
                    match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00")).date()
                except:
                    pass

            if not match_date:
                continue

            # Get match info
            competition = fixture.get("league", {}).get("name", "")
            round_info = fixture.get("league", {}).get("round", "")

            # Determine opponent and venue
            home_team = fixture.get("teams", {}).get("home", {}).get("name", "")
            away_team = fixture.get("teams", {}).get("away", {}).get("name", "")
            venue = "Home" if fixture.get("teams", {}).get("home", {}).get("id") == player_stats.get("team", {}).get("id") else "Away"

            # Determine opponent
            player_team_id = player_stats.get("team", {}).get("id") if player_stats else None
            if player_team_id:
                opponent = away_team if venue == "Home" else home_team
            else:
                opponent = away_team  # Default

            # Match result
            scores = fixture.get("score", {})
            home_score = scores.get("fulltime", {}).get("home", 0)
            away_score = scores.get("fulltime", {}).get("away", 0)
            result = f"{home_score}-{away_score}"

            # Get player statistics for this match (if available in fixture)
            goals = 0
            assists = 0
            yellow_cards = 0
            red_cards = 0
            minutes = 0

            # Some APIs include player stats per fixture
            if "players" in fixture:
                players_data = fixture["players"]
                # Find the player in the fixture data
                for side in ["home", "away"]:
                    for player in players_data.get(side, []):
                        if player.get("player", {}).get("id") == player_stats.get("player", {}).get("id"):
                            stats = player.get("statistics", {})
                            goals = stats.get("goals", 0) or 0
                            assists = stats.get("assists", 0) or 0
                            yellow_cards = stats.get("yellowcards", 0) or 0
                            red_cards = stats.get("redcards", 0) or 0
                            minutes = stats.get("minutes", 0) or 0
                            break

            # Create match record
            match = PlayerMatch(
                player_id=player_id,
                match_date=match_date,
                competition=competition,
                round=round_info,
                venue=venue,
                opponent=opponent,
                result=result,
                minutes_played=minutes,
                goals=goals,
                assists=assists,
                yellow_cards=yellow_cards,
                red_cards=red_cards,
            )

            matches.append(match)

        except Exception as e:
            logger.warning(f"Error mapping fixture to match: {e}")
            continue

    logger.debug(f"Mapped {len(matches)} fixtures to PlayerMatch records")
    return matches


def get_competition_from_api(api_league_data: Dict) -> tuple:
    """
    Extract competition name and type from API league data

    Args:
        api_league_data: League data from API response

    Returns:
        Tuple of (competition_name, competition_type)
    """
    if not api_league_data:
        return ("Unknown", "LEAGUE")

    league_name = api_league_data.get("name", "Unknown")
    league_type = get_competition_type(league_name)

    return (league_name, league_type)


def calculate_season_from_date(date_obj: date) -> str:
    """
    Calculate season string from a date
    July 2025 - June 2026 = "2025-2026"
    January 2025 = "2024-2025"
    """
    year = date_obj.year
    month = date_obj.month

    if month >= 7:
        return f"{year}-{year + 1}"
    else:
        return f"{year - 1}-{year}"


def normalize_season_for_api(season: str) -> int:
    """
    Convert database season format to API season year
    "2025-2026" -> 2025
    "2024-2025" -> 2024
    """
    if "-" in season:
        return int(season.split("-")[0])
    return int(season)
