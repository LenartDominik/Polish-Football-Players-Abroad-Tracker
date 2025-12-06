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

from sqlalchemy import text
from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.models.competition_stats import CompetitionStats
from app.backend.models.goalkeeper_stats import GoalkeeperStats
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_sequences_if_needed(db):
    """Reset PostgreSQL sequences to avoid ID conflicts after bulk deletes"""
    try:
        # Only run for PostgreSQL databases
        db_url = str(db.bind.url)
        if 'postgresql' in db_url or 'postgres' in db_url:
            logger.info("🔧 Resetting PostgreSQL sequences...")
            db.execute(text("SELECT setval('competition_stats_id_seq', (SELECT COALESCE(MAX(id), 1) FROM competition_stats));"))
            db.execute(text("SELECT setval('goalkeeper_stats_id_seq', (SELECT COALESCE(MAX(id), 1) FROM goalkeeper_stats));"))
            db.execute(text("SELECT setval('player_matches_id_seq', (SELECT COALESCE(MAX(id), 1) FROM player_matches));"))
            db.commit()
            logger.info("✅ Sequences reset successfully")
    except Exception as e:
        logger.warning(f"⚠️ Could not reset sequences (may not be PostgreSQL): {e}")


def get_season_date_range(season: str):
    """Get date range for a season (e.g., 2024-2025 -> July 2024 to June 2025)"""
    if '-' in season:
        year_start = int(season.split('-')[0])
        year_end = int(season.split('-')[1])
        return date(year_start, 7, 1), date(year_end, 6, 30)
    else:
        # Calendar year for national team (e.g., "2024" -> Jan-Dec 2024)
        year = int(season)
        return date(year, 1, 1), date(year, 12, 31)


def fix_missing_minutes_from_matchlogs(db, player: Player):
    """
    Fix missing minutes in competition_stats and goalkeeper_stats by calculating from match logs.
    FBref sometimes doesn't provide minutes data in season stats tables.
    """
    logger.info(f"\n🔧 Checking for missing minutes data...")
    
    # Find all competition stats with 0 minutes but games > 0
    comp_stats_to_fix = db.query(CompetitionStats).filter(
        CompetitionStats.player_id == player.id,
        CompetitionStats.minutes == 0,
        CompetitionStats.games > 0
    ).all()
    
    # Find all goalkeeper stats with 0 minutes but games > 0
    gk_stats_to_fix = db.query(GoalkeeperStats).filter(
        GoalkeeperStats.player_id == player.id,
        GoalkeeperStats.minutes == 0,
        GoalkeeperStats.games > 0
    ).all()
    
    total_to_fix = len(comp_stats_to_fix) + len(gk_stats_to_fix)
    
    if total_to_fix == 0:
        logger.info("✅ No missing minutes data")
        return
    
    logger.info(f"⚠️ Found {total_to_fix} records with missing minutes data ({len(comp_stats_to_fix)} comp + {len(gk_stats_to_fix)} gk)")
    
    fixed_count = 0
    
    # Fix competition stats
    for stat in comp_stats_to_fix:
        # Get date range for this season
        try:
            season_start, season_end = get_season_date_range(stat.season)
        except Exception as e:
            logger.warning(f"Could not parse season {stat.season}: {e}")
            continue
        
        # Get all match logs for this season and competition
        matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player.id,
            PlayerMatch.match_date >= season_start,
            PlayerMatch.match_date <= season_end,
            PlayerMatch.competition.ilike(f"%{stat.competition_name}%")
        ).all()
        
        if not matches:
            continue
        
        # Calculate total minutes
        total_minutes = sum(m.minutes_played or 0 for m in matches)
        
        if total_minutes > 0:
            stat.minutes = total_minutes
            fixed_count += 1
            logger.info(f"  ✅ [COMP] {stat.season} {stat.competition_name}: {total_minutes} min from {len(matches)} matches")
    
    # Fix goalkeeper stats
    for stat in gk_stats_to_fix:
        # Get date range for this season
        try:
            season_start, season_end = get_season_date_range(stat.season)
        except Exception as e:
            logger.warning(f"Could not parse season {stat.season}: {e}")
            continue
        
        # Get all match logs for this season and competition
        matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player.id,
            PlayerMatch.match_date >= season_start,
            PlayerMatch.match_date <= season_end,
            PlayerMatch.competition.ilike(f"%{stat.competition_name}%")
        ).all()
        
        if not matches:
            continue
        
        # Calculate total minutes
        total_minutes = sum(m.minutes_played or 0 for m in matches)
        
        if total_minutes > 0:
            stat.minutes = total_minutes
            fixed_count += 1
            logger.info(f"  ✅ [GK] {stat.season} {stat.competition_name}: {total_minutes} min from {len(matches)} matches")
    
    if fixed_count > 0:
        db.commit()
        logger.info(f"✅ Fixed {fixed_count} records with missing minutes!")


async def sync_competition_stats(scraper: FBrefPlaywrightScraper, db, player: Player):
    """Sync competition stats (season-by-season breakdown)"""
    logger.info(f"🏆 Syncing competition stats for {player.name}")
    
    player_data = await scraper.get_player_by_id(player.api_id, player.name)
    
    # Update player team if found
    if player_data and player_data.get('team'):
        player.team = player_data['team']
        logger.info(f"  👕 Updated team: {player.team}")
        db.add(player)
        db.commit()

    if not player_data or not player_data.get('competition_stats'):
        logger.warning("⚠️ No competition stats found")
        return 0
    
    # Check existing stats first
    existing_comp = db.query(CompetitionStats).filter(CompetitionStats.player_id == player.id).count()
    existing_gk = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player.id).count()
    logger.info(f"📊 Found {existing_comp} existing competition stats and {existing_gk} goalkeeper stats")
    
    # Delete existing stats for this player (ALL seasons)
    deleted_comp = db.query(CompetitionStats).filter(CompetitionStats.player_id == player.id).delete(synchronize_session='fetch')
    deleted_gk = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player.id).delete(synchronize_session='fetch')
    
    logger.info(f"🗑️ Deleted {deleted_comp} competition stats and {deleted_gk} goalkeeper stats")
    
    # Commit the deletes immediately to avoid conflicts
    db.commit()
    
    # Verify deletion
    remaining_comp = db.query(CompetitionStats).filter(CompetitionStats.player_id == player.id).count()
    remaining_gk = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player.id).count()
    logger.info(f"✅ Remaining after delete: {remaining_comp} competition stats and {remaining_gk} goalkeeper stats")
    
    # Reset sequences for PostgreSQL to prevent ID conflicts
    reset_sequences_if_needed(db)
    
    # Deduplicate stats by season/competition combination to prevent duplicates
    seen = set()
    deduplicated_stats = []
    for stat_data in player_data['competition_stats']:
        key = (stat_data.get('season'), stat_data.get('competition_name'), stat_data.get('competition_type'))
        if key not in seen:
            seen.add(key)
            deduplicated_stats.append(stat_data)
        else:
            logger.warning(f"⚠️ Skipping duplicate: {stat_data.get('season')} - {stat_data.get('competition_name')}")
    
    logger.info(f"📊 Processing {len(deduplicated_stats)} unique stats (removed {len(player_data['competition_stats']) - len(deduplicated_stats)} duplicates)")
    
    saved_count = 0
    for stat in deduplicated_stats:
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
    skipped_duplicates = 0
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
            db.flush()  # Try to flush to catch constraint violations
            saved_count += 1
        except Exception as e:
            # Check if it's a duplicate error
            if 'uq_player_match' in str(e) or 'UNIQUE constraint' in str(e) or 'duplicate key' in str(e).lower():
                skipped_duplicates += 1
                db.rollback()  # Rollback the failed transaction
            else:
                logger.error(f"❌ Error saving match: {e}")
                db.rollback()
    
    db.commit()
    
    if skipped_duplicates > 0:
        logger.info(f"⚠️ Skipped {skipped_duplicates} duplicate matches")
    
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
            
            # Delete existing match logs for this player (ALL seasons)
            deleted = db.query(PlayerMatch).filter(PlayerMatch.player_id == player.id).delete(synchronize_session='fetch')
            
            # Commit the deletes immediately to avoid conflicts
            db.commit()
            
            if deleted > 0:
                logger.info(f"🗑️ Deleted {deleted} existing match logs")
            
            # Reset sequences for PostgreSQL to prevent ID conflicts
            reset_sequences_if_needed(db)
            
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
            skipped_duplicates = 0
            for season in seasons_to_sync:
                try:
                    matches = await sync_match_logs_for_season(scraper, db, player, season)
                    total_matches += matches
                except Exception as e:
                    # Check if it's a duplicate error
                    if 'uq_player_match' in str(e) or 'UNIQUE constraint' in str(e):
                        skipped_duplicates += 1
                        logger.warning(f"⚠️ Duplicate match in {season}, skipped")
                    else:
                        logger.error(f"❌ Error syncing {season}: {e}")
            
            # Step 3: Fix missing minutes in competition stats by calculating from match logs
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: Fix Missing Minutes Data")
            logger.info("=" * 80)
            fix_missing_minutes_from_matchlogs(db, player)
            
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
