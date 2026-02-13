"""
Sync single player from RapidAPI

Usage:
    python sync_rapidapi.py "Lewandowski"
    python sync_rapidapi.py "Lewandowski" --player-id 1
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


async def sync_player_by_name(player_name: str, player_id: int = None):
    """Sync player by name or ID"""
    db = SessionLocal()
    try:
        # Find player
        if player_id:
            player = db.get(Player, player_id)
        else:
            player = db.query(Player).filter(
                Player.name.ilike(f"%{player_name}%")
            ).first()

        if not player:
            print(f"❌ Player not found: {player_name}")
            return False

        print(f"🔄 Syncing: {player.name} (ID: {player.id})")

        if not player.rapidapi_player_id or not player.rapidapi_team_id:
            print(f"⚠️ Missing RapidAPI IDs for {player.name}")
            print(f"   rapidapi_player_id: {player.rapidapi_player_id}")
            print(f"   rapidapi_team_id: {player.rapidapi_team_id}")

            # Try to search
            print(f"🔍 Searching RapidAPI for: {player.name}...")
            async with RapidAPIClient() as client:
                results = await client.search_players(player.name)

                if not results:
                    print("❌ No results found on RapidAPI")
                    return False

                # Use first result
                chosen = results[0]
                player_info = chosen.get("player", {})
                team_info = chosen.get("statistics", [{}])[0].get("team", {}) if chosen.get("statistics") else {}

                player.rapidapi_player_id = player_info.get("id")
                player.rapidapi_team_id = team_info.get("id")

                print(f"✅ Found IDs:")
                print(f"   rapidapi_player_id: {player.rapidapi_player_id}")
                print(f"   rapidapi_team_id: {player.rapidapi_team_id}")

                db.commit()

        # Sync using RapidAPI
        async with RapidAPIClient() as client:
            player_info = {
                "id": player.id,
                "name": player.name,
                "rapidapi_player_id": player.rapidapi_player_id,
                "rapidapi_team_id": player.rapidapi_team_id
            }

            # Get team data
            team_data = await client.get_team_squad(player.rapidapi_team_id, "2025")

            if not team_data:
                print(f"❌ No team data found")
                return False

            # Find player in team
            player_data = None
            for p in team_data:
                if p.get("player", {}).get("id") == player.rapidapi_player_id:
                    player_data = p
                    break

            if not player_data:
                print(f"❌ Player not found in team roster")
                return False

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

                print(f"✅ Saved {stats_saved} competition stats")

            db.commit()
            print(f"✅ Successfully synced {player.name}")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync player from RapidAPI")
    parser.add_argument("name", help="Player name or ID")
    parser.add_argument("--player-id", type=int, help="Direct database ID")

    args = parser.parse_args()

    asyncio.run(sync_player_by_name(args.name, args.player_id))
