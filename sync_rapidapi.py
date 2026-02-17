"""
Sync single player from RapidAPI

Usage:
    .venv\\Scripts\\python sync_rapidapi.py "Lewandowski"
    .venv\\Scripts\\python sync_rapidapi.py "Lewandowski" --player-id 1
    .venv\\Scripts\\python sync_rapidapi.py "Lewandowski" --games 20 --minutes 1800
"""
import os
import sys
import asyncio
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.competition_stats import CompetitionStats
from app.backend.models.goalkeeper_stats import GoalkeeperStats
from app.backend.models.lineup_cache import LineupCache
from app.backend.services.rapidapi_client import RapidAPIClient, LEAGUE_IDS
from app.backend.utils import get_competition_type, normalize_search
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

# Domestic cup IDs for RapidAPI (may need verification)
CUP_IDS = {
    "Coppa Italia": 557,
    "Copa del Rey": 623,
    "DFB-Pokal": 659,
    "FA Cup": 664,
    "Coupe de France": 670,
    "KNVB Beker": 716,
    "Supercoppa Italiana": 755,
    "DFL-Supercup": 780,
    "Tarczynski Cup": None,  # Polish cup - may not be in RapidAPI
    # Add more cups as needed
}


async def calculate_games_minutes_from_lineups(
    client: RapidAPIClient,
    player_api_id: int,
    team_api_id: int,
    league_id: int,
    db: SessionLocal
) -> tuple[int, int]:
    """
    Calculate games and minutes by analyzing match lineups with caching.

    Workflow:
    1. Check cache for existing data
    2. Get all matches for the league
    3. Filter matches for player's team
    4. For each match, get lineups and check if player played
    5. Calculate minutes from time_in/time_out data
    6. Cache results in database

    Args:
        client: RapidAPIClient instance
        player_api_id: RapidAPI player ID
        team_api_id: RapidAPI team ID
        league_id: League ID from LEAGUE_IDS
        db: Database session for caching

    Returns:
        Tuple of (games, minutes)
    """
    print(f"DEBUG calculate_games_minutes_from_lineups: player_api_id={player_api_id}, team_api_id={team_api_id}, league_id={league_id}")
    logger.info(f"Calculating games/minutes for player {player_api_id}, team {team_api_id}")

    # 1. Check cache first
    cached_data = db.query(LineupCache).filter(
        LineupCache.player_api_id == player_api_id
    ).all()

    games = 0
    total_minutes = 0
    cached_event_ids = set()

    # Sum up cached data
    for cache_entry in cached_data:
        games += 1
        total_minutes += cache_entry.minutes
        cached_event_ids.add(cache_entry.event_id)

    logger.info(f"Found {len(cached_data)} cached entries: {games} games, {total_minutes} minutes")

    # 2. Get all matches for the league
    matches = await client.get_matches_by_league(league_id)

    print(f"  DEBUG: get_matches_by_league({league_id}) returned {len(matches) if matches else 0} matches")

    if not matches:
        logger.warning(f"No matches found for league {league_id}")
        return games, total_minutes

    # 2. Filter matches for player's team
    team_matches = []
    for match in matches:
        # Match structure: {teams: {home: {id, name}, away: {id, name}}, ...}
        teams = match.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        home_id = home.get("id")
        away_id = away.get("id")

        # Convert both to int for comparison (API may return string IDs)
        try:
            home_id_int = int(home_id) if home_id else None
            away_id_int = int(away_id) if away_id else None
            team_id_int = int(team_api_id) if team_api_id else None
        except (ValueError, TypeError):
            continue

        # Debug logging
        if home_id_int == team_id_int or away_id_int == team_id_int:
            team_matches.append(match)
        elif len(team_matches) < 3:  # Log first few non-matches
            logger.info(f"  Skipping: home_id={home_id_int} vs team_id={team_id_int}, away_id={away_id_int} vs team_id={team_id_int}")

    logger.info(f"Found {len(team_matches)} matches for team {team_api_id}")

    logger.info(f"Found {len(team_matches)} matches for team {team_api_id}")

    # Debug: Print first few matches
    for i, m in enumerate(team_matches[:3]):
        logger.info(f"  Match {i+1}: {m.get('home', {}).get('name')} vs {m.get('away', {}).get('name')} (ID: {m.get('id')})")

    # 4. Check each match for player appearance
    new_cache_entries = []
    for match in team_matches:
        event_id = match.get("id") or match.get("eventId") or match.get("eventid")

        if not event_id or event_id in cached_event_ids:
            continue

        # Get home and away team IDs from match (already have teams from outer loop)
        home_id = home.get("id")
        away_id = away.get("id")

        # 5. Get lineups for this match (separate calls for home/away)
        player_minutes = 0

        print(f"  DEBUG: Checking match {event_id}: home_id={home_id} away_id={away_id}")

        # Check home team lineup
        if home_id == team_api_id:
            print(f"    Getting HOME lineup...")
            home_lineup = await client.get_lineup_home(int(event_id))
            if home_lineup and "response" in home_lineup:
                player_minutes = _find_player_minutes(home_lineup["response"], player_api_id)
                print(f"    Player minutes from home lineup: {player_minutes}")
            else:
                print(f"    No home lineup data")

        # Check away team lineup
        if player_minutes == 0 and away_id == team_api_id:
            print(f"    Getting AWAY lineup...")
            away_lineup = await client.get_lineup_away(int(event_id))
            if away_lineup and "response" in away_lineup:
                player_minutes = _find_player_minutes(away_lineup["response"], player_api_id)
                print(f"    Player minutes from away lineup: {player_minutes}")
            else:
                print(f"    No away lineup data")

        if player_minutes > 0:
            games += 1
            total_minutes += player_minutes
            print(f"    Found! games={games}, minutes={total_minutes}")

            # 6. Cache this result
            new_cache_entries.append(LineupCache(
                player_api_id=player_api_id,
                event_id=int(event_id),
                minutes=player_minutes,
                updated_at=datetime.now()
            ))
            cached_event_ids.add(event_id)

    print(f"  DEBUG: Finished loop - games={games}, total_minutes={total_minutes}")

    # Save new cache entries
    if new_cache_entries:
        db.add_all(new_cache_entries)
        db.commit()
        logger.info(f"Cached {len(new_cache_entries)} new lineup entries")

    logger.info(f"Player {player_api_id}: {games} games, {total_minutes} minutes")
    return games, total_minutes


def _find_player_minutes(team_lineup: dict, player_api_id: int) -> int:
    """
    Find player in team lineup and extract minutes played.

    Args:
        team_lineup: Team lineup data from API (response.lineup)
        player_api_id: Player ID to find

    Returns:
        Minutes played (0 if not found or didn't play)
    """
    lineup = team_lineup.get("lineup", {})
    starters = lineup.get("starters", [])

    for player in starters:
        if player.get("id") == player_api_id:
            # Player found in starting lineup
            performance = player.get("performance", {})
            sub_events = performance.get("substitutionEvents", [])

            minutes = 0
            sub_in_time = None
            sub_out_time = None

            # Parse substitution events
            for event in sub_events:
                event_time = event.get("time", 0)
                event_type = event.get("type", "")

                if event_type == "subIn":
                    sub_in_time = event_time
                elif event_type == "subOut":
                    sub_out_time = event_time

            # Calculate minutes based on substitution events
            if sub_out_time is not None:
                # Substituted OUT at sub_out_time
                minutes = sub_out_time
            elif sub_in_time is not None:
                # Substituted IN at sub_in_time - played rest of match
                minutes = 90 - sub_in_time
            else:
                # No substitution events - played full match
                minutes = 90

            return minutes

    return 0


async def sync_player_by_name(player_name: str, player_id: int = None, games: int = None, minutes: int = None, competition: str = None):
    """
    Sync player by name or ID

    Args:
        player_name: Player name to search
        player_id: Direct database ID
        games: Manually set games played (optional)
        minutes: Manually set minutes played (optional)
        competition: Manually set competition name (e.g., 'Serie A', 'Europa League', 'Coppa Italia')
    """
    db = SessionLocal()
    try:
        # Find player
        if player_id:
            player = db.get(Player, player_id)
        else:
            # Normalize Polish characters - DB has "Ziolkowski", user types "Ziółkowski"
            normalized = normalize_search(player_name)
            print(f"   Szukam: '{player_name}' -> znormalizowane: '{normalized}'")

            player = db.query(Player).filter(
                Player.name.ilike(f"%{normalized}%")
            ).first()

        if not player:
            print(f"❌ Player not found: {player_name}")
            return False

        print(f"🔄 Syncing: {player.name} (DB ID: {player.id})")
        print(f"   rapidapi_player_id: {player.rapidapi_player_id}")
        print(f"   rapidapi_team_id: {player.rapidapi_team_id}")

        # If missing RapidAPI IDs, search for them
        if not player.rapidapi_player_id or not player.rapidapi_team_id:
            print(f"🔍 Searching RapidAPI for: {player.name}...")
            async with RapidAPIClient() as client:
                results = await client.search_players(player.name)

                if not results:
                    print("❌ No results found on RapidAPI")
                    return False

                # Use first result
                chosen = results[0]
                player.rapidapi_player_id = int(chosen.get("id"))
                player.rapidapi_team_id = int(chosen.get("teamId"))

                print(f"✅ Found IDs:")
                print(f"   rapidapi_player_id: {player.rapidapi_player_id}")
                print(f"   rapidapi_team_id: {player.rapidapi_team_id}")

                db.commit()

        # Sync using RapidAPI
        async with RapidAPIClient() as client:
            # Get team squad (includes player stats)
            team_data = await client.get_team_squad(player.rapidapi_team_id)

            if not team_data:
                print(f"❌ No team data found")
                return False

            # Find player in team (IDs are ints, compare as ints)
            player_data = None
            for p in team_data:
                squad_id = p.get("id")
                if squad_id == int(player.rapidapi_player_id):
                    player_data = p
                    break

            if not player_data:
                print(f"❌ Player not found in team roster")
                print(f"   Looking for ID: {player.rapidapi_player_id}")
                print(f"   Team has {len(team_data)} players")
                return False

            print(f"✅ Found player in team data")
            goals = player_data.get('goals', 0)
            assists = player_data.get('assists', 0)
            print(f"   Name: {player_data.get('name')}")
            print(f"   Goals: {goals}")
            print(f"   Assists: {assists}")
            print(f"   G+A: {goals + assists}")
            print(f"   Penalties: {player_data.get('penalties', 0)}")
            print(f"   Yellow Cards: {player_data.get('ycards', 0)}")
            print(f"   Red Cards: {player_data.get('rcards', 0)}")
            print(f"   Rating: {player_data.get('rating')}")

            # Update basic player info
            player.last_updated = date.today()

            # Update stats from team squad data
            # Note: RapidAPI team_squad returns aggregated stats (goals, assists, cards, rating)
            # Detect competition from --competition parameter or player's league field
            current_season = "2025-2026"

            # Use --competition parameter if provided, otherwise use player's league
            if competition:
                # User specified competition manually
                competition_name = competition
                print(f"   Using manual competition: {competition_name}")
            else:
                # Auto-detect from player's league field
                player_league = (player.league or "").strip()
                if not player_league:
                    competition_name = "La Liga"  # Fallback
                else:
                    competition_name = player_league

            competition_type = get_competition_type(competition_name)

            # Get league_id from either LEAGUE_IDS or CUP_IDS
            league_id = LEAGUE_IDS.get(competition_name) or CUP_IDS.get(competition_name)
            if not league_id:
                print(f"   WARNING: Unknown competition '{competition_name}', using default")
                league_id = 87  # Default to La Liga

            print(f"   DEBUG: competition_name={competition_name}, league_id={league_id}")

            # Get existing stats to preserve games/minutes
            existing_stats = None
            if not player.is_goalkeeper:
                existing_stats = db.query(CompetitionStats).filter(
                    CompetitionStats.player_id == player.id,
                    CompetitionStats.season == current_season,
                    CompetitionStats.competition_name == competition_name
                ).first()
            else:
                existing_stats = db.query(GoalkeeperStats).filter(
                    GoalkeeperStats.player_id == player.id,
                    GoalkeeperStats.season == current_season,
                    GoalkeeperStats.competition_name == competition_name
                ).first()

            # Determine games and minutes to use
            existing_games = existing_stats.games if existing_stats else 0
            existing_minutes = existing_stats.minutes if existing_stats else 0

            final_games = 0
            final_minutes = 0

            # Use manual values if provided
            if games is not None:
                final_games = games
                final_minutes = minutes if minutes is not None else (games * 90)
            elif existing_games > 0:
                # Use existing value from database
                final_games = existing_games
                final_minutes = existing_minutes
            else:
                # Calculate from lineups (API intensive!)
                print(f"🔍 Calculating games/minutes from match lineups...")
                print(f"   This may take a while and use many API requests...")
                calculated_games, calculated_minutes = await calculate_games_minutes_from_lineups(
                    client,
                    int(player.rapidapi_player_id),
                    int(player.rapidapi_team_id),
                    league_id,
                    db
                )
                final_games = calculated_games
                final_minutes = calculated_minutes

            # Delete old stats for current season
            if not player.is_goalkeeper:
                db.query(CompetitionStats).filter(
                    CompetitionStats.player_id == player.id,
                    CompetitionStats.season == current_season,
                    CompetitionStats.competition_name == competition_name
                ).delete()
            else:
                db.query(GoalkeeperStats).filter(
                    GoalkeeperStats.player_id == player.id,
                    GoalkeeperStats.season == current_season,
                    GoalkeeperStats.competition_name == competition_name
                ).delete()

            # Create new stats entry
            if not player.is_goalkeeper:
                # Map API fields to CompetitionStats model
                # Available: goals, assists, penalties, ycards, rcards, rating
                # NOT available: games, minutes, shots, xg, xa (TODO: get from match data)
                goals = player_data.get("goals", 0)
                assists = player_data.get("assists", 0)

                new_stats = CompetitionStats(
                    player_id=player.id,
                    season=current_season,
                    competition_name=competition_name,
                    competition_type=competition_type,
                    # Basic stats
                    games=final_games,
                    games_starts=0,  # Not available in API
                    minutes=final_minutes,
                    goals=goals,
                    assists=assists,
                    # Cards
                    yellow_cards=player_data.get("ycards", 0),
                    red_cards=player_data.get("rcards", 0),
                    # Penalties
                    penalty_goals=player_data.get("penalties", 0),
                    # Advanced stats (not available, set to 0)
                    xg=0.0,  # TODO: Expected Goals - needs separate data source
                    npxg=0.0,  # Non-penalty xG
                    xa=0.0,  # TODO: Expected Assists - needs separate data source
                    shots=0,  # Not available in API
                    shots_on_target=0,  # Not available in API
                )
                db.add(new_stats)
            else:
                # Goalkeeper stats - limited data from this endpoint
                new_stats = GoalkeeperStats(
                    player_id=player.id,
                    season=current_season,
                    competition_name=competition_name,
                    competition_type=competition_type,
                    goals_conceded=0,  # Not available in team_squad
                    clean_sheets=0,  # Not available in team_squad
                )
                db.add(new_stats)

            db.commit()
            print(f"✅ Successfully synced {player.name}")
            print(f"   Season: {current_season}")
            print(f"   Competition: {competition_name}")
            print(f"   Games: {final_games}")
            print(f"   Minutes: {final_minutes}")

            # Calculate and display G+A/90 if we have data
            if final_minutes > 0:
                ga_per_90 = round((goals + assists) / final_minutes * 90, 2)
                print(f"   G+A/90: {ga_per_90}")
            elif final_games > 0:
                ga_per_90 = round((goals + assists) / final_games, 2)
                print(f"   G+A/90 (est.): {ga_per_90} (using games, assuming 90min/game)")
            else:
                print(f"   G+A/90: N/A (no games/minutes data)")

            print()
            if final_games == 0:
                print("⚠️  Set games using: --games N (e.g., --games 20)")
                print("   G+A/90 requires games or minutes to calculate.")
            print("   Note: xG/xA not available in this API - set to 0")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


async def sync_player_multiple_competitions(
    player_name: str,
    player_id: int = None,
    competitions_str: str = None,
    games_str: str = None,
    minutes_str: str = None,
    goals_str: str = None,
    assists_str: str = None
):
    """
    Sync player across multiple competitions in one API call and DB transaction.

    More efficient than multiple single-competition syncs.

    Args:
        player_name: Player name to search
        player_id: Direct database ID
        competitions_str: Comma-separated competitions: "Serie A,Coppa Italia,Champions League"
        games_str: Comma-separated games: "5,1,2"
        minutes_str: Comma-separated minutes: "300,90,180"
        goals_str: Comma-separated goals (optional): "2,0,1"
        assists_str: Comma-separated assists (optional): "1,0,0"
    """
    if not competitions_str:
        print("❌ --competitions required for multi-competition sync")
        return False

    # Parse comma-separated lists
    competitions = [c.strip() for c in competitions_str.split(',')]
    games_list = [int(g.strip()) for g in games_str.split(',')] if games_str else None
    minutes_list = [int(m.strip()) for m in minutes_str.split(',')] if minutes_str else None
    goals_list = [int(g.strip()) for g in goals_str.split(',')] if goals_str else None
    assists_list = [int(a.strip()) for a in assists_str.split(',')] if assists_str else None

    if len(competitions) != len(games_list) if games_list else True:
        print(f"❌ Mismatch: {len(competitions)} competitions vs {len(games_list) if games_list else 0} games")
        return False
    if len(competitions) != len(minutes_list) if minutes_list else True:
        print(f"❌ Mismatch: {len(competitions)} competitions vs {len(minutes_list) if minutes_list else 0} minutes")
        return False

    db = SessionLocal()
    try:
        # Find player
        if player_id:
            player = db.get(Player, player_id)
        else:
            # Normalize Polish characters - DB has "Ziolkowski", user types "Ziółkowski"
            normalized = normalize_search(player_name)
            print(f"   Szukam: '{player_name}' -> znormalizowane: '{normalized}'")

            player = db.query(Player).filter(
                Player.name.ilike(f"%{normalized}%")
            ).first()

        if not player:
            print(f"❌ Player not found: {player_name}")
            return False

        print(f"🔄 Syncing: {player.name} (DB ID: {player.id})")
        print(f"   Competitions: {competitions}")
        print()

        # API call ONCE for team data (goals, assists, cards)
        async with RapidAPIClient() as client:
            team_data = await client.get_team_squad(player.rapidapi_team_id)

            if team_data:
                # Find player in team
                player_data = None
                for p in team_data:
                    if int(p.get("id")) == int(player.rapidapi_player_id):
                        player_data = p
                        break

                if player_data:
                    api_goals = player_data.get('goals', 0)
                    api_assists = player_data.get('assists', 0)
                    api_ycards = player_data.get('ycards', 0)
                    api_rcards = player_data.get('rcards', 0)
                    print(f"📊 API data: {api_goals} goals, {api_assists} assists, {api_ycards} yellow cards\n")
                else:
                    print("⚠️  Player not in team squad, using provided stats only\n")
            else:
                print("⚠️  No API data available, using provided stats\n")

            # Sync each competition
            current_season = "2025-2026"
            synced_count = 0

            for i, competition_name in enumerate(competitions):
                print(f"📁 Syncing: {competition_name}")

                # Get or create stats entry
                existing = db.query(CompetitionStats).filter(
                    CompetitionStats.player_id == player.id,
                    CompetitionStats.season == current_season,
                    CompetitionStats.competition_name == competition_name
                ).first()

                if not existing:
                    existing = CompetitionStats(
                        player_id=player.id,
                        season=current_season,
                        competition_name=competition_name,
                        competition_type=get_competition_type(competition_name),
                    )
                    db.add(existing)

                # Update values
                if games_list and i < len(games_list):
                    existing.games = games_list[i]
                if minutes_list and i < len(minutes_list):
                    existing.minutes = minutes_list[i]
                if goals_list and i < len(goals_list):
                    existing.goals = goals_list[i]
                elif team_data:
                    existing.goals = api_goals
                if assists_list and i < len(assists_list):
                    existing.assists = assists_list[i]
                elif team_data:
                    existing.assists = api_assists
                if team_data:
                    existing.yellow_cards = api_ycards
                    existing.red_cards = api_rcards

                db.commit()
                synced_count += 1

                # Show summary
                ga = existing.goals or 0
                asst = existing.assists or 0
                print(f"   ✅ {existing.games} games, {existing.minutes} min, {ga} goals, {asst} assists")

            player.last_updated = date.today()
            db.commit()

            print()
            print(f"✅ Synced {synced_count} competitions for {player.name}")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync player from RapidAPI")
    parser.add_argument("name", help="Player name or ID")
    parser.add_argument("--player-id", type=int, help="Direct database ID")

    # Single competition mode
    parser.add_argument("--games", type=int, help="Manually set games played")
    parser.add_argument("--minutes", type=int, help="Manually set minutes played")
    parser.add_argument("--competition", type=str, help="Competition name (e.g., 'Serie A', 'Europa League', 'Coppa Italia')")

    # Multiple competitions mode (more efficient - single API call)
    parser.add_argument("--competitions", type=str, help="Multiple competitions: 'Serie A,Coppa Italia,Champions League'")
    parser.add_argument("--games-list", type=str, help="Games for each competition: '5,1,2' (same order as --competitions)")
    parser.add_argument("--minutes-list", type=str, help="Minutes for each competition: '300,90,180' (same order as --competitions)")
    parser.add_argument("--goals-list", type=str, help="Goals for each competition: '2,0,1' (optional, uses API if not provided)")
    parser.add_argument("--assists-list", type=str, help="Assists for each competition: '1,0,0' (optional, uses API if not provided)")

    args = parser.parse_args()

    # Multiple competitions mode
    if args.competitions:
        asyncio.run(sync_player_multiple_competitions(
            args.name,
            args.player_id,
            args.competitions,
            args.games_list,
            args.minutes_list,
            args.goals_list,
            args.assists_list
        ))
    else:
        # Single competition mode
        asyncio.run(sync_player_by_name(args.name, args.player_id, args.games, args.minutes, args.competition))
