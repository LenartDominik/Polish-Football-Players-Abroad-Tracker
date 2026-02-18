import logging
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Optional, List
from collections import defaultdict

# --- Biblioteki zewnętrzne ---
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import extract
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Twoje moduły konfiguracyjne i bazodanowe ---
from .config import settings
from .database import engine, Base, SessionLocal

# --- Routery i Serwisy ---
from .routers import players, comparison, matchlogs, live, leaderboard
from .services.rapidapi_client import RapidAPIClient
from .services.data_mapper import (
    map_player_data,
    map_competition_stats,
    map_goalkeeper_stats,
    map_match_logs_from_fixtures,
    normalize_season_for_api
)
from .services.match_logs_sync import sync_all_match_logs
from .services.cache_manager import CacheManager
from .services.rate_limiter import RateLimiter

# --- Modele Bazy Danych ---
from .models.player import Player
from .models.competition_stats import CompetitionStats, CompetitionType
from .models.goalkeeper_stats import GoalkeeperStats
from .models.player_match import PlayerMatch
from .models.cache_store import CacheStore
from .models.api_usage_metrics import ApiUsageMetrics
from .utils import get_competition_type, handle_api_error


logger = logging.getLogger(__name__)


# Global scheduler instance
scheduler = None


# ============================================================================
# RAPIDAPI-BASED SYNC FUNCTIONS
# ============================================================================

async def sync_single_player_api(client: RapidAPIClient, player_info: dict, current_season: str = "2025-2026") -> bool:
    """
    Sync a single player using RapidAPI (Safe for Supabase Port 6543).

    Args:
        client: RapidAPI client instance
        player_info: Dict with player data (id, name, rapidapi_player_id, rapidapi_team_id)
        current_season: Season to sync (e.g., "2025-2026")

    Returns:
        True if successful, False otherwise
    """
    player_id = player_info.get('id')
    player_name = player_info.get('name')

    try:
        # --- PHASE 1: API CALLS (Database closed) ---

        # If player has RapidAPI IDs, use team squad endpoint (most efficient)
        rapidapi_player_id = player_info.get('rapidapi_player_id')
        rapidapi_team_id = player_info.get('rapidapi_team_id')

        if rapidapi_team_id:
            # Get all players from team in one request
            season_year = normalize_season_for_api(current_season)
            team_data = await client.get_team_squad(rapidapi_team_id, season_year)

            if not team_data:
                logger.warning(f"  ⚠️ No team data found for {player_name}")
                return False

            # Find our player in team roster
            player_data = None
            for p in team_data:
                # Team squad data is flat - id is at top level, not nested under 'player'
                if p.get('id') == rapidapi_player_id:
                    player_data = p
                    break

            if not player_data:
                logger.warning(f"  ⚠️ Player {player_name} not found in team roster")
                return False

        elif rapidapi_player_id:
            # Fallback: Get individual player details
            player_data = await client.get_player_detail(rapidapi_player_id)

            if not player_data:
                logger.warning(f"  ⚠️ No player data found for {player_name}")
                return False
        else:
            logger.warning(f"  ⚠️ No RapidAPI IDs for {player_name}, need to search first")
            return False

        # --- PHASE 2: DATABASE (Quick write) ---
        db = SessionLocal()
        try:
            player = db.get(Player, player_id)
            if not player:
                logger.error(f"Player {player_id} disappeared from DB!")
                return False

            # Update player basic info using mapper
            mapped_data = map_player_data(player_data, player)
            if mapped_data:
                for key, value in mapped_data.items():
                    if hasattr(player, key):
                        setattr(player, key, value)

            player.last_updated = date.today()

            # Get competition stats from API response
            # Handle two formats:
            # 1. NESTED (player_detail): {statistics: [{league: {name: ...}, games: {...}}]}
            # 2. FLAT (team_squad): {goals, assists, ycards, rcards, rating, ...} - aggregated stats
            stats_saved = 0

            # Delete old competition stats for this season
            db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == current_season
            ).delete(synchronize_session=False)

            db.query(GoalkeeperStats).filter(
                GoalkeeperStats.player_id == player_id,
                GoalkeeperStats.season == current_season
            ).delete(synchronize_session=False)

            # Check if nested statistics array exists (player_detail format)
            if 'statistics' in player_data and isinstance(player_data['statistics'], list):
                # Create new stats entries for each competition
                for stat_entry in player_data['statistics']:
                    league_info = stat_entry.get('league', {})
                    competition_name = league_info.get('name', 'Unknown')

                    if not competition_name or competition_name == 'Unknown':
                        continue

                    competition_type = get_competition_type(competition_name)

                    # Check if goalkeeper
                    if player.is_goalkeeper:
                        gk_stat = map_goalkeeper_stats(
                            {'statistics': [stat_entry]},
                            None,
                            player_id,
                            current_season,
                            competition_name,
                            competition_type
                        )
                        if gk_stat:
                            db.add(gk_stat)
                            stats_saved += 1
                    else:
                        comp_stat = map_competition_stats(
                            {'statistics': [stat_entry]},
                            player_id,
                            current_season,
                            competition_name,
                            competition_type
                        )
                        if comp_stat:
                            db.add(comp_stat)
                            stats_saved += 1

            # FLAT structure (team_squad format) - aggregated stats at top level
            # Create single competition stats entry using player's league
            elif 'goals' in player_data or 'assists' in player_data:
                # Use player's league as competition name (from Player model)
                competition_name = player.league or 'Unknown'
                competition_type = get_competition_type(competition_name)

                # Check if goalkeeper
                if player.is_goalkeeper:
                    # Map flat stats to goalkeeper format
                    gk_stat = GoalkeeperStats(
                        player_id=player_id,
                        season=current_season,
                        competition_name=competition_name,
                        competition_type=competition_type,
                        games=int(player_data.get('games', 0) or 0),
                        games_starts=int(player_data.get('lineups', 0) or player_data.get('games_starts', 0) or 0),
                        minutes=int(player_data.get('minutes', 0) or 0),
                        goals_against=int(player_data.get('conceded', 0) or player_data.get('goals_against', 0) or 0),
                        saves=int(player_data.get('saves', 0) or 0),
                        clean_sheets=int(player_data.get('cleansheets', 0) or player_data.get('clean_sheets', 0) or 0),
                    )
                    db.add(gk_stat)
                    stats_saved += 1
                else:
                    # Map flat stats to competition stats format
                    comp_stat = CompetitionStats(
                        player_id=player_id,
                        season=current_season,
                        competition_name=competition_name,
                        competition_type=competition_type,
                        games=int(player_data.get('games', 0) or player_data.get('appearances', 0) or 0),
                        games_starts=int(player_data.get('lineups', 0) or player_data.get('games_starts', 0) or 0),
                        minutes=int(player_data.get('minutes', 0) or 0),
                        goals=int(player_data.get('goals', 0) or 0),
                        assists=int(player_data.get('assists', 0) or 0),
                        yellow_cards=int(player_data.get('ycards', 0) or player_data.get('yellowcards', 0) or 0),
                        red_cards=int(player_data.get('rcards', 0) or player_data.get('redcards', 0) or 0),
                    )
                    db.add(comp_stat)
                    stats_saved += 1

            if stats_saved > 0:
                logger.info(f"  ✅ Saved {stats_saved} competition stats for {player_name}")

            db.commit()
            return True

        except Exception as e:
            logger.error(f"  ❌ DB Error syncing {player_name}: {e}", exc_info=True)
            db.rollback()
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"  ❌ General Error syncing {player_name}: {e}", exc_info=True)
        return False


def send_sync_notification_email(synced: int, failed: int, total: int, duration_minutes: float, failed_players: List[str]):
    """
    Wysyła raport o ogólnej synchronizacji graczy (Basic Stats) przez API Resend.
    """
    if not settings.resend_api_key or not settings.email_to:
        logger.warning("⚠️ Pominięto wysyłkę e-maila (Basic Sync): Brak konfiguracji Resend.")
        return

    try:
        success_rate = (synced / total * 100) if total > 0 else 0
        status_emoji = "✅" if failed == 0 else "⚠️" if success_rate >= 80 else "❌"

        failed_list_html = ""
        if failed_players:
            failed_list_html = f"<h3>❌ Nieudane ({len(failed_players)}):</h3><ul>"
            for p in failed_players:
                failed_list_html += f"<li>{p}</li>"
            failed_list_html += "</ul>"

        html_content = f"""
        <h2>{status_emoji} Raport Synchronizacji (Podstawowe Dane)</h2>
        <p><strong>Data:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Czas:</strong> {duration_minutes:.1f} min</p>
        <hr>
        <ul>
            <li><strong>Gracze razem:</strong> {total}</li>
            <li><strong>Sukces:</strong> {synced} ({success_rate:.1f}%)</li>
            <li><strong>Błędy:</strong> {failed}</li>
        </ul>
        {failed_list_html}
        <hr>
        <p><small>Powiadomienie z Polish Football Players Abroad</small></p>
        """

        # resend.Emails.send({
        #     "from": settings.email_from,
        #     "to": settings.email_to,
        #     "subject": f"{status_emoji} Sync Update: {synced}/{total} Players Updated",
        #     "html": html_content
        # })

        logger.info(f"✅ E-mail (Basic Sync) wysłany pomyślnie na: {settings.email_to}")

    except Exception as e:
        logger.error(f"❌ Błąd wysyłki maila (Basic Sync): {e}")


async def scheduled_sync_all_players_api():
    """
    Scheduled task to sync all players via RapidAPI.
    Implements hybrid sync strategy:
    - Level 1 players (Top leagues): 2x/week (Thursday + Sunday at 23:00)
    - Level 2 players (Lower leagues): 1x/week (Sunday at 23:00)

    Top leagues: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Süper Lig

    Uses team-based sync for efficiency (get_team_squad returns all players at once).
    """
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("🔄 SCHEDULED API SYNC - Starting RapidAPI synchronization")
    logger.info(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Get current day of week to determine which players to sync
    current_day = start_time.strftime("%A").lower()  # monday, tuesday, etc.
    is_priority_day = current_day in ['thursday', 'sunday']

    # Get all players from database
    players_data = []
    db = SessionLocal()
    try:
        # Get all players with their RapidAPI IDs and level
        all_players = db.query(
            Player.id,
            Player.name,
            Player.rapidapi_player_id,
            Player.rapidapi_team_id,
            Player.level
        ).all()

        for p in all_players:
            players_data.append({
                "id": p.id,
                "name": p.name,
                "rapidapi_player_id": p.rapidapi_player_id,
                "rapidapi_team_id": p.rapidapi_team_id,
                "is_priority": p.level == 1  # Level 1 = Top leagues (2x/week)
            })
    except Exception as e:
        logger.error(f"❌ Failed to fetch players list: {e}")
        return
    finally:
        db.close()

    if not players_data:
        logger.warning("⚠️ No players found in database")
        return

    # Filter players based on day
    if is_priority_day:
        # Sync all players on priority days
        players_to_sync = players_data
        logger.info(f"📋 Priority day - syncing ALL {len(players_to_sync)} players")
    else:
        # Only sync non-priority players on non-priority days
        players_to_sync = [p for p in players_data if not p.get('is_priority')]
        logger.info(f"📋 Non-priority day - syncing {len(players_to_sync)} non-priority players")

    # Group players by team for efficient API calls
    teams_to_sync = {}
    players_without_team = []

    for p_data in players_to_sync:
        team_id = p_data.get('rapidapi_team_id')
        if team_id:
            if team_id not in teams_to_sync:
                teams_to_sync[team_id] = []
            teams_to_sync[team_id].append(p_data)
        else:
            players_without_team.append(p_data)

    logger.info(f"📊 Sync strategy: {len(teams_to_sync)} teams, {len(players_without_team)} individual players")

    synced = 0
    failed = 0
    failed_players = []

    # Initialize RapidAPI client
    if not settings.rapidapi_key:
        logger.error("❌ RAPIDAPI_KEY not configured in environment")
        return

    try:
        async with RapidAPIClient() as client:
            current_season = "2025-2026"

            # Sync by team (most efficient - one API call per team)
            for team_id, team_players in teams_to_sync.items():
                logger.info(f"\n🏆 Syncing team ID {team_id} ({len(team_players)} players)")

                try:
                    season_year = normalize_season_for_api(current_season)
                    team_data = await client.get_team_squad(team_id, season_year)

                    if not team_data:
                        logger.warning(f"  ⚠️ No data for team {team_id}")
                        for p in team_players:
                            failed += 1
                            failed_players.append(p['name'])
                        continue

                    # Process each player from this team
                    for player_info in team_players:
                        player_id = player_info['id']
                        player_name = player_info['name']

                        # Find this player in team data
                        # Team squad data is flat - id is at top level, not nested
                        player_data = None
                        for p in team_data:
                            if p.get('id') == player_info.get('rapidapi_player_id'):
                                player_data = p
                                break

                        if not player_data:
                            logger.warning(f"  ⚠️ {player_name} not found in team roster")
                            failed += 1
                            failed_players.append(player_name)
                            continue

                        # Sync this player
                        success = await sync_single_player_api(client, player_info, current_season)

                        if success:
                            synced += 1
                        else:
                            failed += 1
                            failed_players.append(player_name)

                except Exception as e:
                    logger.error(f"  ❌ Error syncing team {team_id}: {e}")
                    for p in team_players:
                        failed += 1
                        if p['name'] not in failed_players:
                            failed_players.append(p['name'])

            # Sync players without team ID individually
            if players_without_team:
                logger.info(f"\n👤 Syncing {len(players_without_team)} individual players")
                for player_info in players_without_team:
                    logger.info(f"  🔄 Syncing: {player_info['name']}")
                    try:
                        success = await sync_single_player_api(client, player_info, current_season)
                        if success:
                            synced += 1
                        else:
                            failed += 1
                            failed_players.append(player_info['name'])
                    except Exception as e:
                        logger.error(f"  ❌ Error: {e}")
                        failed += 1
                        if player_info['name'] not in failed_players:
                            failed_players.append(player_info['name'])

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        logger.info("=" * 60)
        logger.info("✅ SCHEDULED API SYNC COMPLETE")
        logger.info(f"📊 Results: {synced} synced, {failed} failed out of {len(players_to_sync)} total")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")

        # Show API usage
        if client:
            usage = client.get_usage_report()
            logger.info(f"📡 API Usage: {usage['requests_used']}/{usage['max_requests']} ({usage['percentage']}%)")
        logger.info("=" * 60)

        # Send email notification
        send_sync_notification_email(synced, failed, len(players_to_sync), duration, failed_players)

    except Exception as e:
        logger.error(f"❌ Scheduled API sync failed: {e}", exc_info=True)


# ============================================================================
# NEW SCHEDULER JOBS - Match Logs, Cache, Quota
# ============================================================================

async def scheduled_match_logs_sync_level_1():
    """
    Scheduled task to sync player match logs for Level 1 players (Top 8 leagues).
    Runs Thursday & Sunday at 23:00.

    Syncs player_matches table from RapidAPI lineups.
    """
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("📋 MATCH LOGS SYNC - Level 1 (Top 8 Leagues)")
    logger.info(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        results = await sync_all_match_logs(db, level=1)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        logger.info("=" * 60)
        logger.info("✅ MATCH LOGS SYNC COMPLETE (Level 1)")
        logger.info(f"📊 Results: +{results['added']} ~{results['updated']} ={results['skipped']} !{results['errors']}")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Match logs sync failed: {e}", exc_info=True)
    finally:
        db.close()


async def scheduled_match_logs_sync_level_2():
    """
    Scheduled task to sync player match logs for Level 2 players (Lower leagues).
    Runs Sunday at 23:00.

    Syncs player_matches table from RapidAPI lineups.
    """
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("📋 MATCH LOGS SYNC - Level 2 (Lower Leagues)")
    logger.info(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        results = await sync_all_match_logs(db, level=2)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        logger.info("=" * 60)
        logger.info("✅ MATCH LOGS SYNC COMPLETE (Level 2)")
        logger.info(f"📊 Results: +{results['added']} ~{results['updated']} ={results['skipped']} !{results['errors']}")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Match logs sync failed: {e}", exc_info=True)
    finally:
        db.close()


async def scheduled_cache_cleanup():
    """
    Scheduled task to clean up expired cache entries.
    Runs daily at 03:00.

    Removes expired entries from cache_store table.
    """
    logger.info("=" * 60)
    logger.info("🧹 CACHE CLEANUP - Starting")
    logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        cache_manager = CacheManager(db)

        # Get stats before cleanup
        stats_before = cache_manager.get_stats()

        # Clean up expired entries
        removed = cache_manager.cleanup_expired()

        # Get stats after cleanup
        stats_after = cache_manager.get_stats()

        logger.info(f"✅ CACHE CLEANUP COMPLETE")
        logger.info(f"📊 Removed: {removed} expired entries")
        logger.info(f"📊 Cache size: {stats_before['cache_size']} → {stats_after['cache_size']}")

        # Also clean up old API usage metrics (keep 90 days)
        rate_limiter = RateLimiter(db)
        metrics_removed = rate_limiter.cleanup_old_metrics(days_to_keep=90)

        if metrics_removed > 0:
            logger.info(f"📊 Removed: {metrics_removed} old API usage metrics entries")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Cache cleanup failed: {e}", exc_info=True)
    finally:
        db.close()


async def scheduled_quota_check():
    """
    Scheduled task to check API quota usage and send alerts.
    Runs daily at 12:00.

    Checks daily and monthly usage against quotas.
    """
    logger.info("=" * 60)
    logger.info("📊 QUOTA CHECK - Starting")
    logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        rate_limiter = RateLimiter(db)

        # Get full usage report
        report = rate_limiter.get_full_report()

        logger.info(f"📊 Daily Usage: {report['daily']['requests']}/{report['daily']['quota']} "
                   f"({report['daily']['percentage']}%)")
        logger.info(f"📊 Monthly Usage: {report['monthly']['requests']}/{report['monthly']['quota']} "
                   f"({report['monthly']['percentage']}%)")

        # Log usage by endpoint
        by_endpoint = report.get('by_endpoint', {})
        if by_endpoint:
            logger.info("📊 Usage by endpoint:")
            for endpoint, count in sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   - {endpoint or 'other'}: {count} requests")

        # Check if alerts needed
        daily_pct = report['daily']['percentage']
        monthly_pct = report['monthly']['percentage']

        if daily_pct >= 80:
            logger.warning(f"⚠️ DAILY QUOTA ALERT: {daily_pct}% used!")

        if monthly_pct >= 90:
            logger.error(f"🚨 MONTHLY QUOTA CRITICAL: {monthly_pct}% used!")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Quota check failed: {e}", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

    logger.info("🚀 Aplikacja startuje...")

    # Create database tables (non-blocking)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.warning(f"⚠️ Could not verify database tables: {e}")
        logger.warning("   Tables should already exist. Continuing startup...")

    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        logger.info("📅 Initializing scheduler...")

        # Get timezone from config (default: Europe/Warsaw)
        from .config import settings
        timezone_str = settings.scheduler_timezone

        # Create AsyncIO scheduler with timezone
        scheduler = AsyncIOScheduler(timezone=timezone_str)

        # RapidAPI-based sync with hybrid schedule:
        # - Level 1 players (Top 8 leagues): 2x/week (Thursday & Sunday at 23:00)
        # - Level 2 players (Lower leagues): 1x/week (Sunday at 23:00)
        scheduler.add_job(
            scheduled_sync_all_players_api,
            CronTrigger(day_of_week='thu,sun', hour=23, minute=0, timezone=timezone_str),
            id='sync_all_players_api',
            name='Sync all players via RapidAPI (hybrid schedule)',
            replace_existing=True
        )
        logger.info("✅ RapidAPI sync configured:")
        logger.info(f"   📅 Schedule: Thursday & Sunday at 23:00 ({timezone_str})")
        logger.info(f"   📊 Level 1 (Top 8 leagues): 2x/week, Level 2 (Lower): 1x/week (Sunday)")

        # NEW: Match logs sync - Level 1 (Top 8 leagues) - Thu & Sun at 23:00
        scheduler.add_job(
            scheduled_match_logs_sync_level_1,
            CronTrigger(day_of_week='thu,sun', hour=23, minute=0, timezone=timezone_str),
            id='match_logs_sync_level_1',
            name='Sync Level 1 match logs (Top 8 leagues)',
            replace_existing=True
        )
        logger.info("✅ Match logs sync (Level 1) configured:")
        logger.info(f"   📅 Schedule: Thursday & Sunday at 23:00 ({timezone_str})")
        logger.info(f"   📊 Top 8 leagues only")

        # NEW: Match logs sync - Level 2 (Lower leagues) - Sunday at 23:00
        scheduler.add_job(
            scheduled_match_logs_sync_level_2,
            CronTrigger(day_of_week='sun', hour=23, minute=0, timezone=timezone_str),
            id='match_logs_sync_level_2',
            name='Sync Level 2 match logs (Lower leagues)',
            replace_existing=True
        )
        logger.info("✅ Match logs sync (Level 2) configured:")
        logger.info(f"   📅 Schedule: Sunday at 23:00 ({timezone_str})")
        logger.info(f"   📊 Lower leagues only")

        # NEW: Cache cleanup - Daily at 03:00
        scheduler.add_job(
            scheduled_cache_cleanup,
            CronTrigger(hour=3, minute=0, timezone=timezone_str),
            id='cache_cleanup',
            name='Clean up expired cache entries',
            replace_existing=True
        )
        logger.info("✅ Cache cleanup configured:")
        logger.info(f"   📅 Schedule: Daily at 03:00 ({timezone_str})")

        # NEW: Quota check - Daily at 12:00
        scheduler.add_job(
            scheduled_quota_check,
            CronTrigger(hour=12, minute=0, timezone=timezone_str),
            id='quota_check',
            name='Check API quota usage',
            replace_existing=True
        )
        logger.info("✅ Quota check configured:")
        logger.info(f"   📅 Schedule: Daily at 12:00 ({timezone_str})")

        scheduler.start()
        logger.info("✅ Scheduler uruchomiony")
        logger.info("📅 Next API sync: " + str(scheduler.get_job('sync_all_players_api').next_run_time))
    else:
        logger.info("⏸️ Scheduler disabled (set ENABLE_SCHEDULER=true to enable)")

    yield

    logger.info("🛑 Aplikacja się wyłącza...")

    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler zatrzymany")

app = FastAPI(
    title="Polish Football Players Abroad - API",
    description="""
    🇵🇱 **Polish Football Players Abroad API** - Real-time monitoring of 90+ Polish footballers playing abroad.

    ## 📊 Data Source

    All player statistics are sourced from **RapidAPI Football API**.

    **What we provide:**
    - ⚽ Player statistics (goals, assists, shots, passes, cards)
    - 🏆 Competition data (leagues, cups, international matches)
    - 🥅 Goalkeeper statistics (saves, clean sheets, goals against)

    **Our commitment:**
    - ✅ **Efficient API Usage**: Team-based sync reduces API calls
    - ✅ **Hybrid Schedule**: Top leagues 2x/week, lower leagues 1x/week
    - ✅ **Non-Commercial**: Educational/portfolio project

    ## ⚖️ Legal Notice

    **This is an EDUCATIONAL, NON-COMMERCIAL project.**

    - **Usage:** Educational and portfolio purposes ONLY
    - **NOT for commercial use** without proper licensing from RapidAPI
    - **Full Legal Notice:** See `docs/LEGAL_NOTICE.md` in repository

    ---

    ## ✨ Features

    - 🔄 **API-based sync** via RapidAPI
    - 📊 **Comprehensive statistics**: Goals, assists, shots, passes, cards
    - 🥅 **Goalkeeper stats**: Saves, clean sheets, goals against
    - 🏆 **Competition breakdown**: League, European Cups, National Team, Domestic Cups
    - 🤖 **Automated scheduler**: Level 1 (2x/week), Level 2 (1x/week)
    - 📧 **Email notifications**: HTML reports after each sync
    - ⚡ **Rate limiting**: Efficient team-based sync strategy
    - 💾 **Database**: Supabase PostgreSQL (500MB free tier, cloud-ready)

    ## 🚀 Quick Start

    1. **Browse Players**: `/api/players` - Get all tracked players
    2. **Player Details**: `/api/players/{id}` - Detailed statistics for specific player
    3. **Compare Players**: `/api/comparison/compare` - Side-by-side player comparison
    4. **Match Logs**: `/api/matchlogs/{player_id}` - Game-by-game performance data
    5. **Health Check**: `/health` - Monitor API status

    ## 📚 Documentation

    - **Swagger UI**: Interactive API testing (you're viewing it now!)
    - **ReDoc**: Alternative documentation at `/redoc`
    - **GitHub**: [Full Documentation](https://github.com/LenartDominik/Polish-Football-Players-Abroad)

    ## 🔄 Automated Data Sync

    - **Level 1 Players (Top 8 leagues)**: Thursday & Sunday at 23:00 (Europe/Warsaw)
    - **Level 2 Players (Lower leagues)**: Sunday at 23:00 (Europe/Warsaw)
    - Automatic updates keep data fresh via RapidAPI
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Polish Football Players Abroad",
        "url": "https://github.com/LenartDominik/Polish-Football-Players-Abroad",
    },
    license_info={
        "name": "Educational Use Only (Non-Commercial)",
        "url": "https://github.com/LenartDominik/Polish-Football-Players-Abroad/blob/master/LEGAL_NOTICE.md",
    },
)

# Add GZip compression middleware for responses >= 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/", tags=["Root"])
def root():
    """
    Welcome endpoint - API information and quick links

    Returns basic information about the API and available endpoints.
    """
    return {
        "message": "🇵🇱 Welcome to Polish Football Players Abroad API",
        "status": "operational",
        "data_source": {
            "name": "RapidAPI Football API",
            "attribution": "Player statistics sourced from RapidAPI",
            "disclaimer": "This project is independent and uses RapidAPI services"
        },
        "features": [
            "🔄 API-based sync via RapidAPI",
            "📊 90+ Polish players tracking",
            "🏆 Competition breakdown (League/Europe/National Team/Domestic Cups)",
            "🥅 Dedicated goalkeeper statistics",
            "🤖 Automated scheduler (Level 1: 2x/week, Level 2: 1x/week)",
            "📧 Email notifications",
            "☁️ Cloud deployment ready"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "players": "/api/players",
            "comparison": "/api/comparison/compare",
            "matchlogs": "/api/matchlogs"
        },
        "scheduler": {
            "enabled": os.getenv("ENABLE_SCHEDULER", "false").lower() == "true",
            "jobs": {
                "player_stats_sync": "Thursday & Sunday at 23:00 (Level 1: 2x/week, Level 2: 1x/week)",
                "match_logs_sync_level_1": "Thursday & Sunday at 23:00 (Top 8 leagues)",
                "match_logs_sync_level_2": "Sunday at 23:00 (Lower leagues)",
                "cache_cleanup": "Daily at 03:00",
                "quota_check": "Daily at 12:00"
            },
            "next_runs": {
                "player_stats_sync": str(scheduler.get_job('sync_all_players_api').next_run_time) if scheduler and scheduler.running and scheduler.get_job('sync_all_players_api') else "N/A",
                "match_logs_sync_level_1": str(scheduler.get_job('match_logs_sync_level_1').next_run_time) if scheduler and scheduler.running and scheduler.get_job('match_logs_sync_level_1') else "N/A",
                "match_logs_sync_level_2": str(scheduler.get_job('match_logs_sync_level_2').next_run_time) if scheduler and scheduler.running and scheduler.get_job('match_logs_sync_level_2') else "N/A",
                "cache_cleanup": str(scheduler.get_job('cache_cleanup').next_run_time) if scheduler and scheduler.running and scheduler.get_job('cache_cleanup') else "N/A",
                "quota_check": str(scheduler.get_job('quota_check').next_run_time) if scheduler and scheduler.running and scheduler.get_job('quota_check') else "N/A"
            }
        },
        "links": {
            "github": "https://github.com/LenartDominik/Polish-Football-Players-Abroad",
            "legal_notice": "See LEGAL_NOTICE.md - Educational use only",
            "license": "Educational Use Only (Non-Commercial)",
            "credits": "See CREDITS.md for full attribution",
            "deployment_guide": "See RENDER_DEPLOYMENT.md"
        },
        "legal": {
            "usage": "Educational and portfolio purposes ONLY",
            "commercial_use": "NOT allowed without proper licensing",
            "full_terms": "https://github.com/LenartDominik/Polish-Football-Players-Abroad/blob/main/LEGAL_NOTICE.md"
        },
    "database":  {
        "type": "PostgreSQL",
        "provider": "Supabase",
        "tier": "Free (500MB storage, 2GB transfer/month)",
        "features": ["Automatic backups", "Connection pooling", "Cloud-ready"]
    }
}

@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint for monitoring

    Returns the operational status of the API.
    Useful for uptime monitoring services like UptimeRobot, Pingdom, etc.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running if scheduler else False
    }


@app.post("/api/search-update-player/{player_id}", tags=["Sync"])
async def search_and_update_player(player_id: int, search_name: str = Query(None, description="Custom search name (optional, defaults to player.name)")):
    """
    Wyszukaj gracza na RapidAPI i zaktualizuj jego ID

    Uycie: POST /api/search-update-player/123?search_name=Lewandowski
    """
    from .database import SessionLocal

    db = SessionLocal()
    try:
        player = db.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Use provided search name or player's name
        name_to_search = search_name or player.name

        # Search on RapidAPI
        async with RapidAPIClient() as client:
            results = await client.search_players(name_to_search)

            if not results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No players found on RapidAPI for: {name_to_search}"
                )

            # Try to find exact match
            # API returns flat structure: {id, teamId, teamName, name, ...}
            exact_match = None
            for result in results:
                # Try flat structure first (RapidAPI actual response)
                result_name = result.get("name", "")
                if not result_name:
                    # Fallback to nested structure for compatibility
                    result_name = result.get("player", {}).get("name", "")
                if result_name.lower() == name_to_search.lower():
                    exact_match = result
                    break

            # If no exact match, return first result
            chosen = exact_match or results[0]

            # Extract IDs from result - handle both flat and nested structures
            # Flat structure: {id, teamId, teamName, name}
            # Nested structure: {player: {id}, statistics: [{team: {id, name}}]}
            rapidapi_player_id = chosen.get("id") or chosen.get("player", {}).get("id")
            rapidapi_team_id = chosen.get("teamId") or chosen.get("statistics", [{}])[0].get("team", {}).get("id")
            team_name = chosen.get("teamName") or chosen.get("statistics", [{}])[0].get("team", {}).get("name")

            if not rapidapi_player_id:
                raise HTTPException(
                    status_code=500,
                    detail="Could not extract player ID from RapidAPI response"
                )

            # Update database
            player.rapidapi_player_id = rapidapi_player_id
            if rapidapi_team_id:
                player.rapidapi_team_id = rapidapi_team_id
            if team_name:
                player.team = team_name

            db.commit()

            return {
                "status": "success",
                "message": f"Updated RapidAPI IDs for {player.name}",
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "rapidapi_player_id": rapidapi_player_id,
                    "rapidapi_team_id": rapidapi_team_id,
                    "team": team_name
                },
                "search_results_count": len(results),
                "timestamp": datetime.now().isoformat()
            }
    finally:
        db.close()


@app.post("/api/sync-player/{player_id}", tags=["Sync"])
async def sync_single_player_endpoint(player_id: int):
    """
    Ręcznie zsynchronizuj pojedynczego gracza z RapidAPI

    Uycie: POST /api/sync-player/123
    """
    from .database import SessionLocal

    db = SessionLocal()
    try:
        player = db.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Prepare player info
        player_info = {
            "id": player.id,
            "name": player.name,
            "rapidapi_player_id": player.rapidapi_player_id,
            "rapidapi_team_id": player.rapidapi_team_id
        }

        if not player_info.get("rapidapi_player_id") and not player_info.get("rapidapi_team_id"):
            raise HTTPException(
                status_code=400,
                detail="Player does not have RapidAPI IDs configured. Please add rapidapi_player_id and rapidapi_team_id to database."
            )

        # Sync using RapidAPI
        async with RapidAPIClient() as client:
            success = await sync_single_player_api(client, player_info)

            if success:
                return {
                    "status": "success",
                    "message": f"Player {player.name} synced successfully",
                    "player_id": player_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to sync player from RapidAPI"
                )
    finally:
        db.close()


@app.post("/api/sync-all", tags=["Sync"])
async def sync_all_players_endpoint():
    """
    Ręcznie zsynchronizuj wszystkich graczy z RapidAPI

    Uycie: POST /api/sync-all
    """
    try:
        # Run in background to avoid timeout
        import asyncio
        asyncio.create_task(scheduled_sync_all_players_api())

        return {
            "status": "started",
            "message": "Sync all players task started in background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rejestracja routerów z prefixem /api
app.include_router(players.router, prefix="/api")
app.include_router(comparison.router, prefix="/api")
app.include_router(matchlogs.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(leaderboard.router)  # Already has /api/leaderboard prefix

# Force reload trigger - 2026-02-17 00:35
