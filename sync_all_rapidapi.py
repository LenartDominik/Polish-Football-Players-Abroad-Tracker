"""
Sync all players from RapidAPI (one-time manual run)

Usage:
    python sync_all_rapidapi.py
"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.services.rapidapi_client import RapidAPIClient
from app.backend.services.data_mapper import map_player_data, map_competition_stats, map_goalkeeper_stats
from app.backend.utils import get_competition_type
from datetime import date


async def sync_single_player(client, player: Player) -> bool:
    """Sync single player"""
    try:
        print(f"\n🔄 [{player.id}] {player.name}")

        if not player.rapidapi_player_id or not player.rapidapi_team_id:
            print(f"   ⚠️ No RapidAPI IDs - searching...")
            results = await client.search_players(player.name)

            if results:
                chosen = results[0]
                player_info = chosen.get("player", {})
                team_info = chosen.get("statistics", [{}])[0].get("team", {}) if chosen.get("statistics") else {}

                player.rapidapi_player_id = player_info.get("id")
                player.rapidapi_team_id = team_info.get("id")
                print(f"   ✅ Found: player_id={player.rapidapi_player_id}, team_id={player.rapidapi_team_id}")
            else:
                print(f"   ❌ Not found on RapidAPI")
                return False

        if not player.rapidapi_team_id:
            print(f"   ⏭️ Skipping (no team ID)")
            return False

        # Get team data
        team_data = await client.get_team_squad(player.rapidapi_team_id, "2025")
        if not team_data:
            print(f"   ❌ No team data")
            return False

        # Find player in team
        player_data = None
        for p in team_data:
            if p.get("player", {}).get("id") == player.rapidapi_player_id:
                player_data = p
                break

        if not player_data:
            print(f"   ❌ Not in team roster")
            return False

        # Open DB session for this player
        db = SessionLocal()
        try:
            player = db.get(Player, player.id)

            # Update basic info
            mapped = map_player_data(player_data, player)
            if mapped:
                for key, value in mapped.items():
                    if hasattr(player, key):
                        setattr(player, key, value)

            player.last_updated = date.today()

            # Update stats
            if "statistics" in player_data:
                from app.backend.models.competition_stats import CompetitionStats
                from app.backend.models.goalkeeper_stats import GoalkeeperStats

                current_season = "2025-2026"

                # Delete old stats
                db.query(CompetitionStats).filter(
                    CompetitionStats.player_id == player.id,
                    CompetitionStats.season == current_season
                ).delete()

                db.query(GoalkeeperStats).filter(
                    GoalkeeperStats.player_id == player.id,
                    GoalkeeperStats.season == current_season
                ).delete()

                # Add new stats
                stats_saved = 0
                for stat_entry in player_data["statistics"]:
                    league_info = stat_entry.get("league", {})
                    competition_name = league_info.get("name", "Unknown")

                    if not competition_name or competition_name == "Unknown":
                        continue

                    competition_type = get_competition_type(competition_name)

                    if player.is_goalkeeper:
                        gk_stat = map_goalkeeper_stats(
                            {"statistics": [stat_entry]},
                            None,
                            player.id,
                            current_season,
                            competition_name,
                            competition_type
                        )
                        if gk_stat:
                            db.add(gk_stat)
                            stats_saved += 1
                    else:
                        comp_stat = map_competition_stats(
                            {"statistics": [stat_entry]},
                            player.id,
                            current_season,
                            competition_name,
                            competition_type
                        )
                        if comp_stat:
                            db.add(comp_stat)
                            stats_saved += 1

                print(f"   ✅ {stats_saved} stats saved")

            db.commit()
            print(f"   ✅ Success")
            return True

        except Exception as e:
            print(f"   ❌ Error: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def sync_all_players():
    """Sync all players from database"""
    db = SessionLocal()
    try:
        players = db.query(Player.id, Player.name, Player.rapidapi_player_id, Player.rapidapi_team_id).all()
    finally:
        db.close()

    print(f"📋 Found {len(players)} players to sync")

    synced = 0
    failed = 0
    no_ids = 0

    async with RapidAPIClient() as client:
        for p in players:
            player_obj = Player(id=p.id, name=p.name, rapidapi_player_id=p.rapidapi_player_id, rapidapi_team_id=p.rapidapi_team_id)

            if not player_obj.rapidapi_player_id:
                no_ids += 1

            success = await sync_single_player(client, player_obj)

            if success:
                synced += 1
            else:
                failed += 1

            # Small delay to be nice to API
            await asyncio.sleep(1)

    print("\n" + "="*50)
    print(f"✅ Synced: {synced}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️ No RapidAPI IDs: {no_ids}")
    print("="*50)

    # Show API usage
    usage = client.get_usage_report()
    print(f"📡 API Usage: {usage['requests_used']}/{usage['max_requests']}")


if __name__ == "__main__":
    asyncio.run(sync_all_players())
