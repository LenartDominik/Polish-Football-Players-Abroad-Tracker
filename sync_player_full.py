"""
Full player sync - Competition stats + Match logs for ALL seasons
Usage: python sync_player_full.py "Player Name" [--seasons 2023-2024 2024-2025 2025-2026]
"""
import sys
import asyncio
from datetime import datetime, date
import logging
import argparse

sys.path.append('.')

from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.models.competition_stats import CompetitionStats
from app.backend.models.goalkeeper_stats import GoalkeeperStats
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def sync_competition_stats(scraper: FBrefPlaywrightScraper, db, player: Player):
    """Sync competition stats (season-by-season breakdown)"""
    logger.info(f"🏆 Syncing competition stats for {player.name}")
    
    player_data = await scraper.get_player_by_id(player.api_id, player.name)
    if not player_data or not player_data.get('competition_stats'):
        logger.warning("⚠️ No competition stats found")
        return 0
    
    # Delete existing stats
    db.query(CompetitionStats).filter(CompetitionStats.player_id == player.id).delete()
    db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player.id).delete()
    
    saved_count = 0
    for stat in player_data['competition_stats']:
        try:
            # Check if it's goalkeeper stats (has GK-specific fields)
            is_gk_stat = any(k in stat for k in ['goals_against', 'saves', 'clean_sheets'])
            
            if is_gk_stat:
                # Save as goalkeeper stat
                gk_stat = GoalkeeperStats(
                    player_id=player.id,
                    season=stat.get('season', ''),
                    competition_name=stat.get('competition_name', ''),
                    competition_type=stat.get('competition_type', ''),
                    games=stat.get('games'),
                    games_starts=stat.get('games_starts'),
                    minutes=stat.get('minutes'),
                    goals_against=stat.get('goals_against'),
                    goals_against_per90=stat.get('ga90'),
                    shots_on_target_against=stat.get('sota'),
                    saves=stat.get('saves'),
                    save_percentage=stat.get('save_pct'),
                    wins=stat.get('wins'),
                    draws=stat.get('draws') or stat.get('ties'),
                    losses=stat.get('losses'),
                    clean_sheets=stat.get('clean_sheets'),
                    clean_sheet_percentage=stat.get('clean_sheets_pct'),
                    penalties_attempted=stat.get('pens_att'),
                    penalties_allowed=stat.get('pens_allowed'),
                    penalties_saved=stat.get('pens_saved'),
                    penalties_missed=stat.get('pens_missed'),
                    post_shot_xg=stat.get('psxg')
                )
                db.add(gk_stat)
            else:
                # Save as regular competition stat
                comp_stat = CompetitionStats(
                    player_id=player.id,
                    season=stat.get('season', ''),
                    competition_name=stat.get('competition_name', ''),
                    competition_type=stat.get('competition_type', ''),
                    games=stat.get('games'),
                    games_starts=stat.get('games_starts'),
                    minutes=stat.get('minutes'),
                    goals=stat.get('goals'),
                    assists=stat.get('assists'),
                    penalty_goals=stat.get('penalty_goals'),
                    xg=stat.get('xg'),
                    npxg=stat.get('npxg'),
                    xa=stat.get('xa'),
                    yellow_cards=stat.get('yellow_cards'),
                    red_cards=stat.get('red_cards')
                )
                db.add(comp_stat)
            
            saved_count += 1
        except Exception as e:
            logger.error(f"❌ Error saving stat: {e}")
    
    db.commit()
    logger.info(f"✅ Saved {saved_count} competition stats")
    return saved_count


async def sync_match_logs_for_season(scraper: FBrefPlaywrightScraper, db, player: Player, season: str):
    """Sync match logs for a specific season"""
    logger.info(f"📋 Syncing match logs for {player.name} ({season})")
    
    match_logs = await scraper.get_player_match_logs(player.api_id, player.name, season)
    if not match_logs:
        logger.warning(f"⚠️ No match logs found for {season}")
        return 0
    
    saved_count = 0
    for match_data in match_logs:
        try:
            # Parse date
            match_date_str = match_data.get('match_date')
            if match_date_str:
                try:
                    match_date = datetime.strptime(match_date_str, '%Y-%m-%d').date()
                except:
                    try:
                        parts = match_date_str.split('-')
                        if len(parts) == 3:
                            match_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        else:
                            match_date = date.today()
                    except:
                        match_date = date.today()
            else:
                match_date = date.today()
            
            # Create match record
            match = PlayerMatch(
                player_id=player.id,
                match_date=match_date,
                competition=match_data.get('competition', ''),
                round=match_data.get('round', ''),
                venue=match_data.get('venue', ''),
                opponent=match_data.get('opponent', ''),
                result=match_data.get('result', ''),
                minutes_played=match_data.get('minutes_played', 0) or 0,
                goals=match_data.get('goals', 0) or 0,
                assists=match_data.get('assists', 0) or 0,
                shots=match_data.get('shots', 0) or 0,
                shots_on_target=match_data.get('shots_on_target', 0) or 0,
                xg=match_data.get('xg', 0.0) or 0.0,
                xa=match_data.get('xa', 0.0) or 0.0,
                passes_completed=match_data.get('passes_completed', 0) or 0,
                passes_attempted=match_data.get('passes_attempted', 0) or 0,
                touches=match_data.get('touches', 0) or 0,
                yellow_cards=match_data.get('yellow_cards', 0) or 0,
                red_cards=match_data.get('red_cards', 0) or 0
            )
            db.add(match)
            saved_count += 1
        except Exception as e:
            logger.error(f"❌ Error saving match: {e}")
    
    db.commit()
    logger.info(f"✅ Saved {saved_count} matches for {season}")
    return saved_count


async def main():
    parser = argparse.ArgumentParser(description='Sync full player data (competition stats + match logs)')
    parser.add_argument('player_name', help='Player name to sync')
    parser.add_argument('--seasons', nargs='*', help='Specific seasons to sync match logs (e.g., 2023-2024 2024-2025 2025-2026). If not provided, only syncs current season.')
    parser.add_argument('--all-seasons', action='store_true', help='Sync match logs for ALL seasons found in competition stats')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info(f"FULL SYNC: {args.player_name}")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        # Find player
        player = db.query(Player).filter(Player.name.ilike(f"%{args.player_name}%")).first()
        if not player:
            logger.error(f"❌ Player not found: {args.player_name}")
            sys.exit(1)
        
        logger.info(f"✅ Found player: {player.name} (ID: {player.id})")
        logger.info(f"   FBref ID: {player.api_id}")
        
        async with FBrefPlaywrightScraper(headless=True, rate_limit_seconds=12.0) as scraper:
            # Step 1: Sync competition stats (always)
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: Competition Stats (Season-by-Season)")
            logger.info("=" * 80)
            comp_count = await sync_competition_stats(scraper, db, player)
            
            # Step 2: Sync match logs
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: Match Logs (Match-by-Match)")
            logger.info("=" * 80)
            
            # Delete existing match logs
            deleted = db.query(PlayerMatch).filter(PlayerMatch.player_id == player.id).delete()
            db.commit()
            if deleted > 0:
                logger.info(f"🗑️ Deleted {deleted} existing match logs")
            
            # Determine which seasons to sync
            seasons_to_sync = []
            if args.all_seasons:
                # Get all seasons from competition stats
                comp_stats = db.query(CompetitionStats).filter(CompetitionStats.player_id == player.id).all()
                gk_stats = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player.id).all()
                all_seasons = set()
                for stat in comp_stats + gk_stats:
                    if stat.season and stat.season.strip():
                        all_seasons.add(stat.season)
                seasons_to_sync = sorted(all_seasons, reverse=True)
                logger.info(f"📅 Found {len(seasons_to_sync)} seasons to sync: {seasons_to_sync}")
            elif args.seasons:
                seasons_to_sync = args.seasons
                logger.info(f"📅 Syncing specified seasons: {seasons_to_sync}")
            else:
                seasons_to_sync = ["2025-2026"]
                logger.info(f"📅 Syncing current season only: {seasons_to_sync}")
            
            # Sync match logs for each season
            total_matches = 0
            for season in seasons_to_sync:
                try:
                    matches = await sync_match_logs_for_season(scraper, db, player, season)
                    total_matches += matches
                except Exception as e:
                    logger.error(f"❌ Error syncing {season}: {e}")
            
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ SYNC COMPLETE")
            logger.info(f"   Competition Stats: {comp_count}")
            logger.info(f"   Match Logs: {total_matches}")
            logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
