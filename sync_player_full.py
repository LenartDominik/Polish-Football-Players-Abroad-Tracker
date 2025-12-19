"""
Full player sync - Competition stats + Match logs for ALL seasons
Usage: python sync_player_full.py "Player Name" [--seasons 2023-2024 2024-2025 2025-2026]
"""
import sys
import asyncio
from datetime import datetime, date
import logging
import argparse
import re
from collections import defaultdict 

sys.path.append('.')

from sqlalchemy import text
from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.models.competition_stats import CompetitionStats
from app.backend.models.goalkeeper_stats import GoalkeeperStats
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper

# --- Ujednolicone mapowanie competition_type ---
def get_competition_type(competition_name: str) -> str:
    """Mapuje nazwę rozgrywek na jeden z typów: LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM"""
    if not competition_name:
        return "LEAGUE"
    comp_lower = competition_name.lower()
    # Domestic cups (najpierw, zanim europejskie)
    if any(keyword in comp_lower for keyword in [
        'copa del rey', 'copa', 'pokal', 'coupe', 'coppa',
        'fa cup', 'league cup', 'efl', 'carabao',
        'dfb-pokal', 'dfl-supercup', 'supercopa', 'supercoppa',
        'u.s. open cup', 'puchar', 'krajowy puchar'
    ]):
        return "DOMESTIC_CUP"
    # European competitions
    if any(keyword in comp_lower for keyword in [
        'champions league', 'europa league', 'conference league',
        'uefa', 'champions lg', 'europa lg', 'conf lg', 'ucl', 'uel', 'uecl'
    ]):
        return "EUROPEAN_CUP"
    # National team
    if any(keyword in comp_lower for keyword in [
        'national team', 'reprezentacja', 'international'
    ]):
        return "NATIONAL_TEAM"
    # Default league
    return "LEAGUE"


def normalize_competition_type(raw_type: str, competition_name: str = "") -> str:
    """Normalizuje competition_type do jednego z dozwolonych: LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM"""
    if raw_type is None:
        return get_competition_type(competition_name)
    t = str(raw_type).strip().upper()
    mapping = {
        'LEAGUE': 'LEAGUE',
        'DOMESTIC_CUP': 'DOMESTIC_CUP',
        'EUROPEAN_CUP': 'EUROPEAN_CUP',
        'NATIONAL_TEAM': 'NATIONAL_TEAM',
        'CUP': 'DOMESTIC_CUP',
        'INTERNATIONAL_CUP': 'EUROPEAN_CUP',
    }
    if t in mapping:
        return mapping[t]
    # Fallback na podstawie nazwy rozgrywek
    return get_competition_type(competition_name)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_sequences_if_needed():
    """Reset PostgreSQL sequences (Safe & Independent Session)"""
    db = SessionLocal() 
    try:
        db_url = str(db.bind.url)
        if 'postgresql' in db_url or 'postgres' in db_url:
            # logger.info("🔧 Resetting PostgreSQL sequences...")
            db.execute(text("SELECT setval('competition_stats_id_seq', (SELECT COALESCE(MAX(id), 1) FROM competition_stats));"))
            db.execute(text("SELECT setval('goalkeeper_stats_id_seq', (SELECT COALESCE(MAX(id), 1) FROM goalkeeper_stats));"))
            db.execute(text("SELECT setval('player_matches_id_seq', (SELECT COALESCE(MAX(id), 1) FROM player_matches));"))
            db.commit()
    except Exception as e:
        logger.warning(f"⚠️ Sequence reset warning: {e}")
        db.rollback()
    finally:
        db.close() 

def get_season_date_range(season: str):
    """Get date range for a season (Helper - No DB needed)"""
    if '-' in season:
        try:
            year_start = int(season.split('-')[0])
            year_end = int(season.split('-')[1])
            return date(year_start, 7, 1), date(year_end, 6, 30)
        except:
             return date.today(), date.today()
    else:
        try:
            year = int(season)
            return date(year, 1, 1), date(year, 12, 31)
        except:
             return date.today(), date.today()

def sync_competition_stats_from_matches(player_id: int) -> int:
    """
    Synchronize competition_stats from player_matches.
    Safe for Supabase Port 6543 (Independent Session).
    ONLY counts matches where player actually played (minutes > 0).
    
    IMPORTANT: This function REPLACES competition_stats with data from match logs.
    It deletes old stats that don't have corresponding match logs to avoid stale data.
    """
    db = SessionLocal()
    try:
        # IMPORTANT: Only get matches where player actually played (minutes > 0)
        matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player_id,
            PlayerMatch.minutes_played > 0
        ).all()
        if not matches: return 0
        
        stats_dict = defaultdict(lambda: {
            'games': 0, 'goals': 0, 'assists': 0, 'minutes': 0,
            'xg': 0.0, 'xa': 0.0, 'games_starts': 0
        })
        
        for match in matches:
            year = match.match_date.year
            month = match.match_date.month
            if month >= 7: season = f"{year}-{year+1}"
            else: season = f"{year-1}-{year}"
            
            # For international matches, use calendar year and aggregate ALL into "National Team {year}"
            international_comps = ['WCQ', 'World Cup', 'UEFA Nations League', 'UEFA Euro Qualifying', 'UEFA Euro', 'Friendlies (M)', 'Copa América']
            if match.competition in international_comps:
                season = str(year)
                competition_name = f'National Team {season}'  # All international matches → "National Team {year}"
            else:
                competition_name = match.competition  # Club matches keep their competition name
            
            key = (season, competition_name)
            stats_dict[key]['games'] += 1
            stats_dict[key]['goals'] += match.goals or 0
            stats_dict[key]['assists'] += match.assists or 0
            stats_dict[key]['minutes'] += match.minutes_played or 0
            stats_dict[key]['xg'] += match.xg or 0.0
            stats_dict[key]['xa'] += match.xa or 0.0
            stats_dict[key]['games_starts'] += 1 if (match.minutes_played or 0) > 45 else 0
        
        # CLEANUP: Delete stale national team entries from FBref that don't match actual match logs
        # Example: FBref shows "WCQ 2026" but match logs show WCQ matches in 2025 (aggregated as "National Team 2025")
        # Strategy: Delete ALL national team records that are NOT in our match log aggregation
        # This handles cases like "WCQ 2026" where the year in the name doesn't match actual match dates
        
        match_log_keys = set((season, competition) for (season, competition) in stats_dict.keys())
        
        # Find ALL national team records from FBref
        existing_national = db.query(CompetitionStats).filter(
            CompetitionStats.player_id == player_id,
            CompetitionStats.competition_type == 'NATIONAL_TEAM'
        ).all()
        
        deleted_count = 0
        for record in existing_national:
            key = (record.season, record.competition_name)
            
            # If this exact record is NOT in our match log aggregation, it's stale - delete it
            # This catches:
            # - "WCQ 2026" (7 games) when match logs show WCQ in 2025 → "National Team 2025"
            # - "Friendlies (M) 2025" (0 games) when aggregated into "National Team 2025"
            # - Any other stale FBref entries
            if key not in match_log_keys:
                db.delete(record)
                deleted_count += 1
                logger.info(f"🗑️ Deleted stale national team record: {record.competition_name} ({record.season}) - not in match logs")
        
        if deleted_count > 0:
            db.commit()
            logger.info(f"✅ Cleaned up {deleted_count} stale national team records from FBref")
        
        # Update or create competition_stats from match logs
        # IMPORTANT: We update existing records to preserve xG/npxG from FBref while fixing games/minutes
        updated = 0
        for (season, competition), stats in stats_dict.items():
            record = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_name == competition
            ).first()
            
            # Ujednolicone competition_type
            comp_type = normalize_competition_type(None, competition_name=competition)

            if record:
                # Update existing record - overwrite games/minutes but keep xG/npxG from FBref if available
                record.games = stats['games']
                record.goals = stats['goals']
                record.assists = stats['assists']
                record.minutes = stats['minutes']
                record.games_starts = stats['games_starts']
                # Only update xG/xa if match logs have data (otherwise keep FBref values)
                if stats['xg'] > 0:
                    record.xg = stats['xg']
                if stats['xa'] > 0:
                    record.xa = stats['xa']
            else:
                # Create new record from match logs
                record = CompetitionStats(
                    player_id=player_id, season=season, competition_name=competition, competition_type=comp_type,
                    games=stats['games'], goals=stats['goals'], assists=stats['assists'], minutes=stats['minutes'],
                    xg=stats['xg'], xa=stats['xa'], games_starts=stats['games_starts']
                )
                db.add(record)
            updated += 1
        
        db.commit()
        logger.info(f"✅ Updated {updated} competition_stats from match logs")
        return updated
    except Exception as e:
        logger.error(f"Error syncing competition_stats from matches: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def update_player_team_from_matches(player_id: int):
    """
    Update player's team and league based on ACTUAL match data (where minutes > 0).
    For mid-season transfers, picks the league where they played MOST RECENTLY, not just most minutes.
    """
    db = SessionLocal()
    try:
        player = db.get(Player, player_id)
        if not player:
            return
        
        # Get current season (2025-2026 if we're in 2025 July+ or 2026 before July)
        from datetime import date
        current_year = date.today().year
        current_month = date.today().month
        
        if current_month >= 7:
            season_start = date(current_year, 7, 1)
            season_end = date(current_year + 1, 6, 30)
            current_season = f"{current_year}-{current_year + 1}"
        else:
            season_start = date(current_year - 1, 7, 1)
            season_end = date(current_year, 6, 30)
            current_season = f"{current_year - 1}-{current_year}"
        
        # Get all LEAGUE competitions in current season where player played
        league_comps = db.query(CompetitionStats.competition_name).filter(
            CompetitionStats.player_id == player_id,
            CompetitionStats.season == current_season,
            CompetitionStats.competition_type == 'LEAGUE',
            CompetitionStats.minutes > 0
        ).distinct().all()
        
        if not league_comps:
            logger.info(f"⚠️ No league data with minutes played found for {current_season}")
            return
        
        league_names = [lc[0] for lc in league_comps]
        
        # For each league, find the MOST RECENT match date where player actually played
        league_recent_dates = {}
        for league_name in league_names:
            most_recent_match = db.query(PlayerMatch).filter(
                PlayerMatch.player_id == player_id,
                PlayerMatch.competition == league_name,
                PlayerMatch.match_date >= season_start,
                PlayerMatch.match_date <= season_end,
                PlayerMatch.minutes_played > 0
            ).order_by(PlayerMatch.match_date.desc()).first()
            
            if most_recent_match:
                league_recent_dates[league_name] = most_recent_match.match_date
        
        if not league_recent_dates:
            logger.info(f"⚠️ Could not find recent match dates for leagues")
            return
        
        # Pick the league with the MOST RECENT match (current team)
        current_league = max(league_recent_dates.items(), key=lambda x: x[1])
        best_league_name = current_league[0]
        last_match_date = current_league[1]
        
        # Get stats for this league
        best_league_stats = db.query(CompetitionStats).filter(
            CompetitionStats.player_id == player_id,
            CompetitionStats.season == current_season,
            CompetitionStats.competition_name == best_league_name
        ).first()
        
        # Update player info
        old_team = player.team
        old_league = player.league
        player.league = best_league_name
        
        # Clear team name if league changed (since FBref aggregate data is stale)
        # Team name will show as league name on frontend
        if old_league != player.league:
            # Set team to generic league name since we don't have reliable squad info
            # FIXED: Don't set 'Unknown Team' - team will be updated from FBref API (lines 434-436)
            # player.team = f"{best_league_name} (Unknown Team)"  # OLD BUGGY CODE
            # Team name will be updated in sync_competition_stats from FBref API squad field
            db.add(player)
            db.commit()
            logger.info(f"✅ Updated league based on most recent matches:")
            logger.info(f"   League: {old_league} → {player.league}")
            logger.info(f"   Team: {old_team} → {player.team}")
            logger.info(f"   Last match: {last_match_date}")
            if best_league_stats:
                logger.info(f"   Stats: {best_league_stats.games} games, {best_league_stats.minutes} minutes")
            logger.warning(f"   ⚠️ Team name unknown - FBref aggregate stats are stale for transfers")
        else:
            logger.info(f"✅ League confirmed: {player.league} (last match: {last_match_date})")
            if best_league_stats:
                logger.info(f"   Stats: {best_league_stats.games} games, {best_league_stats.minutes} minutes")
        
    except Exception as e:
        logger.error(f"Error updating team from matches: {e}")
        db.rollback()
    finally:
        db.close()

def fix_missing_minutes_from_matchlogs(player_id: int):
    """Fix missing minutes using match logs (Independent Session)."""
    db = SessionLocal()
    try:
        comp_stats_to_fix = db.query(CompetitionStats).filter(CompetitionStats.player_id == player_id, CompetitionStats.minutes == 0, CompetitionStats.games > 0).all()
        gk_stats_to_fix = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player_id, GoalkeeperStats.minutes == 0, GoalkeeperStats.games > 0).all()
        
        total_to_fix = len(comp_stats_to_fix) + len(gk_stats_to_fix)
        if total_to_fix == 0: return

        fixed_count = 0
        for stat in comp_stats_to_fix:
            try: season_start, season_end = get_season_date_range(stat.season)
            except: continue
            matches = db.query(PlayerMatch).filter(PlayerMatch.player_id == player_id, PlayerMatch.match_date >= season_start, PlayerMatch.match_date <= season_end, PlayerMatch.competition.ilike(f"%{stat.competition_name}%")).all()
            if not matches: continue
            total_minutes = sum(m.minutes_played or 0 for m in matches)
            if total_minutes > 0:
                stat.minutes = total_minutes
                fixed_count += 1
        
        for stat in gk_stats_to_fix:
            try: season_start, season_end = get_season_date_range(stat.season)
            except: continue
            matches = db.query(PlayerMatch).filter(PlayerMatch.player_id == player_id, PlayerMatch.match_date >= season_start, PlayerMatch.match_date <= season_end, PlayerMatch.competition.ilike(f"%{stat.competition_name}%")).all()
            if not matches: continue
            total_minutes = sum(m.minutes_played or 0 for m in matches)
            if total_minutes > 0:
                stat.minutes = total_minutes
                fixed_count += 1
                
        if fixed_count > 0:
            db.commit()
            logger.info(f"✅ Fixed {fixed_count} records with missing minutes!")
    except Exception as e:
        logger.error(f"Error fixing minutes: {e}")
        db.rollback()
    finally:
        db.close()

async def sync_competition_stats(scraper: FBrefPlaywrightScraper, player_info: dict) -> int:
    """Sync competition stats (Safe for Port 6543 - API First, DB Second)."""
    player_id = player_info['id']
    player_name = player_info['name']
    player_api_id = player_info.get('api_id')
    
    logger.info(f"🏆 Syncing competition stats for {player_name}")
    
    # --- FAZA 1: API ---
    try:
        player_data = await scraper.get_player_by_id(player_api_id, player_name)
        # DEBUG: Log what API returns
        logger.info(f"🔍 DEBUG API Response - Top-level team: {player_data.get('team')}")
        if player_data.get('competition_stats'):
            logger.info(f"🔍 DEBUG API Response - Total competition_stats: {len(player_data['competition_stats'])}")
            league_stats = [s for s in player_data['competition_stats'] if 'LEAGUE' in str(s.get('competition_type', '')).upper()]
            logger.info(f"🔍 DEBUG API Response - LEAGUE stats count: {len(league_stats)}")
            for ls in league_stats[:3]:  # Show first 3
                logger.info(f"   Season: {ls.get('season')}, Squad: {ls.get('squad')}, League: {ls.get('competition_name')}")
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return 0

    if not player_data or not player_data.get('competition_stats'):
        logger.warning("⚠️ No competition stats found")
        return 0

    # --- FAZA 2: BAZA DANYCH ---
    db = SessionLocal()
    try:
        player = db.get(Player, player_id)
        if player:
            # Prefer setting team from the most recent LEAGUE stat with non-empty 'squad'
            # For players who transferred mid-season, pick the team with MOST GAMES in current season
            latest_league_team = None
            latest_league_name = None
            if player_data.get('competition_stats'):
                def season_start(s: str) -> int:
                    if not s:
                        return -1
                    s = str(s).strip()
                    try:
                        # Formats: YYYY-YYYY, YYYY-YY, or YYYY
                        if '-' in s:
                            first = s.split('-')[0]
                            return int(first)
                        return int(s)
                    except Exception:
                        return -1
                # Filter league stats only
                league_stats = [st for st in player_data['competition_stats'] if normalize_competition_type(st.get('competition_type'), st.get('competition_name', '')) == 'LEAGUE']
                
                # Sort by: 1) season start year descending, 2) minutes played descending (better indicator than games)
                league_stats.sort(key=lambda st: (season_start(st.get('season')), st.get('minutes', 0)), reverse=True)
                
                # Pick the first one with non-empty squad (most recent season, most minutes played)
                for st in league_stats:
                    squad = (st.get('squad') or '').strip()
                    comp_name = (st.get('competition_name') or '').strip()
                    if squad:
                        latest_league_team = squad
                        latest_league_name = comp_name
                        logger.info(f"🔧 Selected team: {squad} from {comp_name} ({st.get('season')}) - {st.get('games', 0)} games, {st.get('minutes', 0)} minutes")
                        break
            # Apply league/team from latest reliable league stat; fallback to API top-level team
            if latest_league_name:
                player.league = latest_league_name
            if latest_league_team:
                # Only update team if current team is empty or contains 'Unknown'
                # This prevents overwriting manually corrected teams with stale FBref data
                if not player.team or 'Unknown' in player.team or player.team == latest_league_name:
                    player.team = latest_league_team
                else:
                    logger.info(f"   ⚠️ Keeping existing team: {player.team} (FBref shows: {latest_league_team})")
            # Do not fallback to API top-level team to avoid overwriting with stale values
            db.add(player)
        
        db.query(CompetitionStats).filter(CompetitionStats.player_id == player_id).delete(synchronize_session=False)
        db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player_id).delete(synchronize_session=False)
        
        seen = set()
        deduplicated_stats = []
        for stat_data in player_data['competition_stats']:
            key = (stat_data.get('season'), stat_data.get('competition_name'), stat_data.get('competition_type'))
            if key not in seen:
                seen.add(key)
                deduplicated_stats.append(stat_data)
        
        saved_count = 0
        for stat in deduplicated_stats:
            # Skip stats with ANY None values (incomplete/corrupted data from FBref)
            # Common for youth teams (PL2, reserves) or when FBref scraping fails
            critical_fields = ['games', 'minutes', 'season', 'competition_name']
            if any(stat.get(field) is None for field in critical_fields):
                logger.warning(f"⚠️ Skipping incomplete stat: {stat.get('season')} {stat.get('competition_name')} {stat.get('competition_type')} (missing: {[f for f in critical_fields if stat.get(f) is None]})")
                continue

            # Also skip if numeric fields are invalid (prevent comparison errors)
            try:
                int(stat.get('games', 0) or 0)
                int(stat.get('minutes', 0) or 0)
            except (TypeError, ValueError):
                logger.warning(f"⚠️ Skipping stat with invalid numeric values: {stat.get('season')} {stat.get('competition_name')}")
                continue


            try:
                is_gk_stat = any(k in stat for k in ['goals_against', 'saves', 'clean_sheets'])
                normalized_type = normalize_competition_type(stat.get('competition_type'), stat.get('competition_name', ''))
                if is_gk_stat:
                    gk_stat = GoalkeeperStats(
                        player_id=player_id, season=stat.get('season', ''), competition_name=stat.get('competition_name', ''), competition_type=normalized_type,
                        games=stat.get('games'), games_starts=stat.get('games_starts'), minutes=stat.get('minutes'), goals_against=stat.get('goals_against'),
                        goals_against_per90=stat.get('ga90'), shots_on_target_against=stat.get('sota'), saves=stat.get('saves'), save_percentage=stat.get('save_pct'),
                        wins=stat.get('wins'), draws=stat.get('draws') or stat.get('ties'), losses=stat.get('losses'), clean_sheets=stat.get('clean_sheets'),
                        clean_sheet_percentage=stat.get('clean_sheets_pct'), penalties_attempted=stat.get('pens_att'), penalties_allowed=stat.get('pens_allowed'),
                        penalties_saved=stat.get('pens_saved'), penalties_missed=stat.get('pens_missed'), post_shot_xg=stat.get('psxg')
                    )
                    db.add(gk_stat)
                else:
                    comp_stat = CompetitionStats(
                        player_id=player_id, season=stat.get('season', ''), competition_name=stat.get('competition_name', ''), competition_type=normalized_type,
                        games=stat.get('games'), games_starts=stat.get('games_starts'), minutes=stat.get('minutes'), goals=stat.get('goals'),
                        assists=stat.get('assists'), penalty_goals=stat.get('penalty_goals'), xg=stat.get('xg'), npxg=stat.get('npxg'),
                        xa=stat.get('xa'), yellow_cards=stat.get('yellow_cards'), red_cards=stat.get('red_cards')
                    )
                    db.add(comp_stat)
                saved_count += 1
            except Exception as e: logger.error(f"❌ Error saving stat: {e}")
            
        db.commit()
        logger.info(f"✅ Saved {saved_count} competition stats")
        return saved_count
    except Exception as e:
        logger.error(f"❌ DB Error in competition stats: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

async def sync_match_logs_for_season(scraper: FBrefPlaywrightScraper, player_info: dict, season: str) -> int:
    """Sync match logs for a specific season (Safe for Port 6543)."""
    player_id = player_info['id']
    player_name = player_info['name']
    api_id = player_info.get('api_id')
    
    logger.info(f"📋 Syncing match logs for {player_name} ({season})")
    
    # --- FAZA 1: API ---
    try:
        match_logs = await scraper.get_player_match_logs(api_id, player_name, season)
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return 0
        
    if not match_logs:
        logger.warning(f"⚠️ No match logs found for {season}")
        return 0
    
    # --- FAZA 2: BAZA ---
    db = SessionLocal()
    try:
        year_start = int(season.split('-')[0])
        year_end = year_start + 1
        season_start = date(year_start, 7, 1)
        season_end = date(year_end, 6, 30)
        
        db.query(PlayerMatch).filter(PlayerMatch.player_id == player_id, PlayerMatch.match_date >= season_start, PlayerMatch.match_date <= season_end).delete(synchronize_session=False)
        
        saved_count = 0
        skipped_duplicates = 0
        seen = set()                 # wide key: (player_id, date, competition, opponent)
        seen_narrow = set()          # narrow key: (player_id, date, opponent) for unique_match_event

        # Preload existing narrow keys from DB to avoid unique_match_event violations
        existing_narrow = set(
            (m.match_date, (m.opponent or '').strip()[:100])
            for m in db.query(PlayerMatch.match_date, PlayerMatch.opponent)
                        .filter(PlayerMatch.player_id == player_id)
                        .all()
        )
        
        for match_data in match_logs:
            try:
                match_date_str = match_data.get('match_date')
                match_date = date.today()
                if match_date_str:
                    try:
                        match_date = datetime.strptime(match_date_str, '%Y-%m-%d').date()
                    except Exception:
                        pass
                # Normalize opponent (remove known prefixes like 'nl', 'de', 'es' attached to country names)
                competition = (match_data.get('competition') or '').strip()[:100]
                raw_opp = (match_data.get('opponent') or '').strip()
                opponent = re.sub(r'^[a-z]{2}', '', raw_opp).strip()[:100]
                key = (player_id, match_date, competition, opponent)
                key_narrow = (player_id, match_date, opponent)
                if key in seen or key_narrow in seen_narrow or (match_date, opponent) in existing_narrow:
                    skipped_duplicates += 1
                    continue
                seen.add(key)
                seen_narrow.add(key_narrow)
                
                match = PlayerMatch(
                    player_id=player_id, match_date=match_date, competition=competition, round=(match_data.get('round') or '').strip()[:50],
                    venue=(match_data.get('venue') or '').strip()[:50], opponent=opponent, result=(match_data.get('result') or '').strip()[:20],
                    minutes_played=match_data.get('minutes_played', 0) or 0, goals=match_data.get('goals', 0) or 0, assists=match_data.get('assists', 0) or 0,
                    shots=match_data.get('shots', 0) or 0, shots_on_target=match_data.get('shots_on_target', 0) or 0, xg=float(match_data.get('xg', 0.0) or 0.0),
                    xa=float(match_data.get('xa', 0.0) or 0.0), passes_completed=match_data.get('passes_completed', 0) or 0, passes_attempted=match_data.get('passes_attempted', 0) or 0,
                    touches=match_data.get('touches', 0) or 0, yellow_cards=match_data.get('yellow_cards', 0) or 0, red_cards=match_data.get('red_cards', 0) or 0
                )
                db.add(match)
                saved_count += 1
            except Exception as e:
                if 'uq_player_match' in str(e) or 'UNIQUE constraint' in str(e) or 'unique_match_event' in str(e):
                    skipped_duplicates += 1
                else:
                    logger.error(f"❌ Row error: {e}")

        db.commit()
        if skipped_duplicates > 0:
            logger.info(f"⚠️ Skipped {skipped_duplicates} duplicate matches")
        logger.info(f"✅ Saved {saved_count} matches for {season}")
        return saved_count
    except Exception as e:
        logger.error(f"❌ DB Error matchlogs: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

async def main():
    parser = argparse.ArgumentParser(description='Sync full player data (competition stats + match logs)')
    parser.add_argument('player_name', help='Player name to sync')
    parser.add_argument('--seasons', nargs='*', help='Specific seasons to sync match logs')
    parser.add_argument('--all-seasons', action='store_true', help='Sync match logs for ALL seasons')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info(f"FULL SYNC: {args.player_name}")
    logger.info("=" * 80)
    
    player_info = {}
    db_temp = SessionLocal()
    try:
        player = db_temp.query(Player).filter(Player.name.ilike(f"%{args.player_name}%")).first()
        if not player:
            logger.error(f"❌ Player not found: {args.player_name}")
            sys.exit(1)
        player_info = {'id': player.id, 'name': player.name, 'api_id': player.api_id}
        logger.info(f"✅ Found player: {player.name} (ID: {player.id})")
    finally:
        db_temp.close() # SESJA ZAMKNIĘTA

    async with FBrefPlaywrightScraper(headless=True, rate_limit_seconds=12.0) as scraper:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Competition Stats")
        logger.info("=" * 80)
        comp_count = await sync_competition_stats(scraper, player_info)
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Match Logs")
        logger.info("=" * 80)
        reset_sequences_if_needed()
        
        seasons_to_sync = []
        if args.all_seasons:
            # Hardcoded: Always sync these 3 seasons (current, previous, 2 years back)
            seasons_to_sync = ['2025-2026', '2024-2025', '2023-2024']
            logger.info(f"📅 Found {len(seasons_to_sync)} seasons to sync")
        elif args.seasons: seasons_to_sync = args.seasons
        else: seasons_to_sync = ["2025-2026"]
            
        total_matches = 0
        for season in seasons_to_sync:
            matches = await sync_match_logs_for_season(scraper, player_info, season)
            total_matches += matches
            
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Aggregation & Fixes")
        logger.info("=" * 80)
        logger.info("🔄 Aggregating competition stats from match logs...")
        sync_competition_stats_from_matches(player_info['id'])
        logger.info("🔧 Fixing missing minutes...")
        fix_missing_minutes_from_matchlogs(player_info['id'])
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Update Team Based on Actual Match Data")
        logger.info("=" * 80)
        update_player_team_from_matches(player_info['id'])
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ SYNC COMPLETE")
        logger.info(f"   Competition Stats: {comp_count}")
        logger.info(f"   Match Logs: {total_matches}")
        logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())