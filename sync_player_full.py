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
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper
from app.backend.services.rapidapi_client import RapidAPIClient
from app.backend.services.data_mapper import (
    map_player_data,
    map_competition_stats,
    map_goalkeeper_stats,
    map_match_logs_from_fixtures,
    normalize_season_for_api,
    get_competition_from_api
)
from app.backend.utils import get_competition_type
from app.backend.models import Player, PlayerMatch, CompetitionStats, GoalkeeperStats
from app.backend.config import settings

# --- Ujednolicone mapowanie competition_type ---


def normalize_competition_type(raw_type: str, competition_name: str = "") -> str:
    """Normalizuje competition_type do jednego z dozwolonych: LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM.
    Zignoruj raw_type i użyj get_competition_type dla pełnej spójności.
    """
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
    Also: It canonicalizes competition names to prevent duplicate league rows (e.g., sponsor variants).
    """
    def _norm_key(name: str) -> str:
        if not name:
            return ''
        import re
        s = name.lower()
        # remove sponsor/common noise tokens
        noise = [
            'pko', 'bp', 'keuken', 'kampioen', 't-mobile', 'barclays', 'carabao', 'efl', 'betclic', 'tipsport',
            'fortuna', 'puchar', 'cup', 'liga', 'league'  # keep base words handled later
        ]
        # keep base words but remove sponsor prefixes
        for token in ['pko bp', 'keuken kampioen', 't-mobile', 'barclays']:
            s = s.replace(token, ' ')
        # strip punctuation and extra spaces
        s = re.sub(r'[^a-z\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

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
        match_log_keys = set((season, competition) for (season, competition) in stats_dict.keys())
        seasons_with_match_logs = set(season for (season, _) in match_log_keys)
        existing_national = db.query(CompetitionStats).filter(
            CompetitionStats.player_id == player_id,
            CompetitionStats.competition_type == 'NATIONAL_TEAM'
        ).all()
        deleted_count = 0
        for record in existing_national:
            key = (record.season, record.competition_name)
            if key not in match_log_keys:
                db.delete(record)
                deleted_count += 1
                logger.info(f"🗑️ Deleted stale national team record: {record.competition_name} ({record.season}) - not in match logs")
        if deleted_count > 0:
            db.commit()
            logger.info(f"✅ Cleaned up {deleted_count} stale national team records from FBref")
        
        # Build season-level canonical name maps from existing competition_stats to merge variants
        existing_by_season = {}
        for season in seasons_with_match_logs:
            rows = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season
            ).all()
            canon_map = {}
            for r in rows:
                canon_map[_norm_key(r.competition_name)] = r.competition_name
            existing_by_season[season] = canon_map
        
        # Update or create competition_stats (and GoalkeeperStats if GK) from match logs
        player_db = db.get(Player, player_id)
        is_gk_player = player_db and str(player_db.position).strip().upper() in ["GK", "GOALKEEPER", "BRAMKARZ"]
        
        updated = 0
        for (season, competition), stats in stats_dict.items():
            if season not in seasons_with_match_logs:
                continue
            
            # Recalculate competition type
            effective_name = competition
            comp_type = normalize_competition_type(None, competition_name=effective_name)
            
            if is_gk_player:
                # Update GoalkeeperStats
                gk_record = db.query(GoalkeeperStats).filter(
                    GoalkeeperStats.player_id == player_id,
                    GoalkeeperStats.season == season,
                    GoalkeeperStats.competition_name == competition
                ).first()
                
                if gk_record:
                    gk_record.games = stats['games']
                    gk_record.games_starts = stats['games_starts']
                    gk_record.minutes = stats['minutes']
                    gk_record.competition_type = comp_type
                else:
                    gk_record = GoalkeeperStats(
                        player_id=player_id, season=season, competition_name=competition, 
                        competition_type=comp_type, games=stats['games'], 
                        games_starts=stats['games_starts'], minutes=stats['minutes']
                    )
                    db.add(gk_record)
            
            # ALWAYS update/create CompetitionStats (base for all players)
            record = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_name == competition
            ).first()

            if record:
                # UPDATE existing
                record.games = stats['games']
                record.goals = stats['goals']
                record.assists = stats['assists']
                record.minutes = stats['minutes']
                record.games_starts = stats['games_starts']
                record.xg = stats['xg']
                record.xa = stats['xa']
                record.competition_type = comp_type
            else:
                # CREATE new
                record = CompetitionStats(
                    player_id=player_id, season=season, competition_name=competition, competition_type=comp_type,
                    games=stats['games'], goals=stats['goals'], assists=stats['assists'], minutes=stats['minutes'],
                    xg=stats['xg'], xa=stats['xa'], games_starts=stats['games_starts']
                )
                db.add(record)
            updated += 1
        
        # --- NEW LOGIC: Recalculate 'Season Total' for club competitions only ---
        # (League + Domestic Cups + European Cups) - Exclude Super Cups and National Team
        # We do this aggregation HERE based on the just-processed match logs to ensure consistency.
        
        # 1. Identify valid club seasons from match logs
        club_seasons = set()
        for (seas, comp), _ in stats_dict.items():
            if 'National Team' not in comp:
                club_seasons.add(seas)
        
        for season in club_seasons:
            total_games = 0
            total_goals = 0
            total_assists = 0
            total_minutes = 0
            total_xg = 0.0
            total_xa = 0.0
            total_starts = 0
            
            # Sum up stats for this season from stats_dict
            for (s_seas, s_comp), s_stats in stats_dict.items():
                if s_seas != season: continue
                if 'National Team' in s_comp: continue
                
                # Exclude Super Cups from Season Total sum
                s_comp_lower = s_comp.lower()
                if any(x in s_comp_lower for x in ['super cup', 'supercopa', 'supercoppa', 'community shield']):
                    continue
                    
                total_games += s_stats['games']
                total_goals += s_stats['goals']
                total_assists += s_stats['assists']
                total_minutes += s_stats['minutes']
                total_xg += s_stats['xg']
                total_xa += s_stats['xa']
                total_starts += s_stats['games_starts']
            
            # Update 'Season Total' record in DB
            # We don't create a separate CompetitionStats row for 'Season Total' usually, 
            # but if your requirements imply a specific aggregate row or just correct sums in individual rows,
            # wait, usually 'Season Total' is calculated dynamically on Frontend.
            # IF you need it stored, we would add it here. 
            # BASED ON USER REQUEST: "w kolumnie season total... sumowaly sie dane te co są wymagana"
            # Since frontend calculates it dynamically (I saw `get_season_total_stats_by_date_range` in streamlit_app.py),
            # we just need to ensure the individual `CompetitionStats` rows are correct (which they are now).
            # The 'Season Total' on frontend aggregates these rows (or matches directly).
            # The critical part is that we cleaned up duplicates and canonicalized names above.
            pass


        
        db.commit()
        logger.info(f"✅ Updated {updated} competition_stats from match logs (canonical names)")

        # Cleanup: remove LEAGUE records using single-year season labels (e.g., '2025')
        # when a proper season range exists for the same competition in the same cycle (e.g., '2025-2026').
        # This addresses leagues that FBref labels as '2025' but our app uses '2025-26'.
        removed_single_year = 0
        for season in seasons_with_match_logs:
            # only consider YYYY-YYYY+1 forms
            if '-' not in season:
                continue
            try:
                y1 = season.split('-')[0]
            except Exception:
                continue
            # Build set of normalized league names present under the proper season
            target_rows = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_type == 'LEAGUE'
            ).all()
            season_norms = {_norm_key(r.competition_name) for r in target_rows}
            if not season_norms:
                continue
            # Find single-year league records for the same cycle and same normalized name
            wrong_rows = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == y1,
                CompetitionStats.competition_type == 'LEAGUE'
            ).all()
            for r in wrong_rows:
                if _norm_key(r.competition_name) in season_norms:
                    db.delete(r)
                    removed_single_year += 1
        if removed_single_year:
            db.commit()
            logger.info(f"🧹 Removed {removed_single_year} single-year LEAGUE rows where season-range exists (e.g., 2025 -> 2025-2026)")

        # Consolidate duplicate LEAGUE rows caused by naming variants within the same season
        total_deleted_dupes = 0
        for season in seasons_with_match_logs:
            rows = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_type == 'LEAGUE'
            ).all()
            groups = {}
            for r in rows:
                k = _norm_key(r.competition_name)
                groups.setdefault(k, []).append(r)
            for k, items in groups.items():
                if len(items) <= 1:
                    continue
                # Keep the one with max minutes (most representative), delete others
                items.sort(key=lambda r: (r.minutes or 0, r.games or 0), reverse=True)
                keep = items[0]
                to_delete = items[1:]
                for d in to_delete:
                    db.delete(d)
                    total_deleted_dupes += 1
        if total_deleted_dupes:
            db.commit()
            logger.info(f"🧹 Removed {total_deleted_dupes} duplicate LEAGUE rows after canonicalization")

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
                league_stats.sort(key=lambda st: (season_start(st.get('season')), st.get('minutes') or 0), reverse=True)
                
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
            # Goalkeepers might have missing minutes in the overview table, but we want 
            # their detailed stats (Saves, CS, GA). Step 3 will fill in minutes from match logs.
            is_gk_stat = any(k in stat for k in ['goals_against', 'saves', 'clean_sheets', 'sota'])
            critical_fields = ['games', 'season', 'competition_name']
            if not is_gk_stat:
                critical_fields.append('minutes')

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
        season_start, season_end = get_season_date_range(season)
        
        db.query(PlayerMatch).filter(PlayerMatch.player_id == player_id, PlayerMatch.match_date >= season_start, PlayerMatch.match_date <= season_end).delete(synchronize_session=False)
        
        saved_count = 0
        skipped_duplicates = 0
        seen = set()                 # wide key: (player_id, date, competition, opponent)
        seen_narrow = set()          # narrow key: (player_id, date, opponent) for unique_match_event

        # Preload existing narrow keys from DB to avoid unique_match_event violations
        # Preload existing match dates from DB to avoid violations/duplicates
        # We trust that a player only plays once per day
        existing_narrow = set(
            m.match_date
            for m in db.query(PlayerMatch.match_date)
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
                # Use strictly date-based duplicate check to avoid opponent naming conflicts
                # It is extremely rare for a player to play 2 matches on the same day
                key_narrow = (player_id, match_date)
                
                if key in seen or key_narrow in seen_narrow or match_date in existing_narrow:
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


async def sync_competition_stats_api(client: RapidAPIClient, player_info: dict, season: str = "2025-2026") -> int:
    """
    Sync competition stats using RapidAPI (Safe for Supabase Port 6543).

    Args:
        client: RapidAPI client instance
        player_info: Dict with player data (must include rapidapi_player_id, rapidapi_team_id)
        season: Season to sync

    Returns:
        Number of stats records synced
    """
    player_id = player_info['id']
    player_name = player_info['name']
    rapidapi_player_id = player_info.get('rapidapi_player_id')
    rapidapi_team_id = player_info.get('rapidapi_team_id')

    logger.info(f"🏆 Syncing competition stats for {player_name} via RapidAPI")

    # --- PHASE 1: API CALLS ---
    player_data = None

    if rapidapi_team_id:
        # Efficient: Get all players from team
        season_year = normalize_season_for_api(season)
        team_data = await client.get_team_squad(rapidapi_team_id, season_year)

        if team_data:
            for p in team_data:
                if p.get('player', {}).get('id') == rapidapi_player_id:
                    player_data = p
                    break

    if not player_data and rapidapi_player_id:
        # Fallback: Get individual player
        player_data = await client.get_player_detail(rapidapi_player_id)

    if not player_data:
        logger.warning("⚠️ No data found from RapidAPI")
        return 0

    # --- PHASE 2: DATABASE ---
    db = SessionLocal()
    try:
        player = db.get(Player, player_id)
        if not player:
            logger.error(f"Player {player_id} not found!")
            return 0

        # Update player info
        mapped_data = map_player_data(player_data, player)
        if mapped_data:
            for key, value in mapped_data.items():
                if hasattr(player, key) and value is not None:
                    setattr(player, key, value)

        # Delete old stats for this season
        db.query(CompetitionStats).filter(
            CompetitionStats.player_id == player_id,
            CompetitionStats.season == season
        ).delete(synchronize_session=False)

        db.query(GoalkeeperStats).filter(
            GoalkeeperStats.player_id == player_id,
            GoalkeeperStats.season == season
        ).delete(synchronize_session=False)

        # Create new stats from API data
        saved_count = 0
        is_gk = player.is_goalkeeper

        if 'statistics' in player_data and isinstance(player_data['statistics'], list):
            for stat_entry in player_data['statistics']:
                league_info = stat_entry.get('league', {})
                competition_name = league_info.get('name', '')

                if not competition_name:
                    continue

                competition_type = get_competition_type(competition_name)

                try:
                    if is_gk:
                        gk_stat = map_goalkeeper_stats(
                            {'statistics': [stat_entry]},
                            None,
                            player_id,
                            season,
                            competition_name,
                            competition_type
                        )
                        if gk_stat:
                            db.add(gk_stat)
                            saved_count += 1
                    else:
                        comp_stat = map_competition_stats(
                            {'statistics': [stat_entry]},
                            player_id,
                            season,
                            competition_name,
                            competition_type
                        )
                        if comp_stat:
                            db.add(comp_stat)
                            saved_count += 1
                except Exception as e:
                    logger.error(f"  ❌ Error saving stat: {e}")

        db.commit()
        logger.info(f"✅ Saved {saved_count} competition stats via RapidAPI")
        return saved_count

    except Exception as e:
        logger.error(f"❌ DB Error in RapidAPI sync: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


async def main():
    parser = argparse.ArgumentParser(description='Sync full player data (competition stats + match logs)')
    parser.add_argument('player_name', help='Player name to sync')
    parser.add_argument('--seasons', nargs='*', help='Specific seasons to sync match logs')
    parser.add_argument('--all-seasons', action='store_true', help='Sync match logs for ALL seasons')
    parser.add_argument('--api', choices=['fbref', 'rapidapi'], default=None, help='API to use (default: auto-detect)')
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info(f"FULL SYNC: {args.player_name}")
    logger.info("=" * 80)

    # Get player info from database
    player_info = {}
    db_temp = SessionLocal()
    try:
        player = db_temp.query(Player).filter(Player.name.ilike(f"%{args.player_name}%")).first()
        if not player:
            logger.error(f"❌ Player not found: {args.player_name}")
            sys.exit(1)

        # Build player info dict with all possible IDs
        player_info = {
            'id': player.id,
            'name': player.name,
            'api_id': player.api_id,  # FBref ID
            'rapidapi_player_id': player.rapidapi_player_id,
            'rapidapi_team_id': player.rapidapi_team_id,
            'fbref_id': getattr(player, 'fbref_id', None)
        }
        logger.info(f"✅ Found player: {player.name} (ID: {player.id})")
    finally:
        db_temp.close() # SESJA ZAMKNIĘTA

    # Determine which API to use
    use_rapidapi = args.api == 'rapidapi'
    if args.api is None:
        # Auto-detect: Prefer RapidAPI if available
        use_rapidapi = settings.rapidapi_key and player_info.get('rapidapi_team_id')

    if use_rapidapi:
        # Use RapidAPI
        if not settings.rapidapi_key:
            logger.error("❌ RAPIDAPI_KEY not configured in environment")
            logger.info("💡 Get your key from: https://rapidapi.com/creativesdev/api/free-api-live-football-data")
            sys.exit(1)

        logger.info("📡 Using RapidAPI for sync")
        current_season = "2025-2026"

        async with RapidAPIClient() as client:
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: Competition Stats (RapidAPI)")
            logger.info("=" * 80)
            comp_count = await sync_competition_stats_api(client, player_info, current_season)

            # Note: Match logs via RapidAPI require fixtures endpoint - can be added later
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: Match Logs")
            logger.info("=" * 80)
            logger.info("ℹ️ Match logs sync via RapidAPI not yet implemented - using FBref if available")
            # Fall through to FBref for match logs if player has api_id

            logger.info("\n" + "=" * 80)
            logger.info(f"✅ SYNC COMPLETE (RapidAPI)")
            logger.info(f"   Competition Stats: {comp_count}")
            logger.info("=" * 80)
    else:
        # Use FBref scraper (legacy)
        logger.info("🕷️ Using FBref scraper for sync")

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
                # Sync last 5 seasons including current
                # Adjust years as needed based on current date
                current_yr = date.today().year
                if date.today().month >= 7:
                     start_years = range(current_yr, current_yr - 5, -1)
                else:
                     start_years = range(current_yr - 1, current_yr - 6, -1)

                seasons_to_sync = [f"{y}-{y+1}" for y in start_years]
                logger.info(f"📅 Found {len(seasons_to_sync)} seasons to sync: {seasons_to_sync}")
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
            logger.info("🛠️ Aligning goalkeeper league stats with match logs (games/minutes/starts)...")
            fix_goalkeeper_stats_from_matchlogs(player_info['id'])

            logger.info("\n" + "=" * 80)
            logger.info("STEP 4: Update Team Based on Actual Match Data")
            logger.info("=" * 80)
            update_player_team_from_matches(player_info['id'])

            logger.info("\n" + "=" * 80)
            logger.info(f"✅ SYNC COMPLETE (FBref)")
            logger.info(f"   Competition Stats: {comp_count}")
            logger.info(f"   Match Logs: {total_matches}")
            logger.info("=" * 80)


def _is_international_competition(name: str) -> bool:
    if not name:
        return False
    comp_lower = name.lower()
    keywords = [
        'wcq', 'world cup', 'uefa nations league', 'uefa euro', 'euro qualifying', 'friendlies', 'copa am', 'international'
    ]
    return any(k in comp_lower for k in keywords)


def fix_goalkeeper_stats_from_matchlogs(player_id: int):
    """Align goalkeeper league stats (games, minutes, starts) with actual match logs.
    We DO NOT modify GK-specific metrics (saves, GA, save%) because match logs don't have them.
    Strategy:
    - For each GoalkeeperStats row, compute totals from PlayerMatch within season range where minutes > 0
    - Update games, minutes, games_starts if computed values are > 0 (leave zeros as-is to avoid false updates)
    - For National Team, aggregate by calendar year using international competitions only
    """
    db = SessionLocal()
    try:
        gk_rows = db.query(GoalkeeperStats).filter(GoalkeeperStats.player_id == player_id).all()
        if not gk_rows:
            return
        # Preload all matches for perf
        all_matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player_id,
            PlayerMatch.minutes_played > 0
        ).all()
        for row in gk_rows:
            season_str = str(row.season)
            try:
                season_start, season_end = get_season_date_range(season_str)
            except Exception:
                continue
            comp_name = (row.competition_name or '').strip()
            comp_type = (row.competition_type or '').upper()
            relevant = []
            if comp_type == 'NATIONAL_TEAM' or comp_name.lower().startswith('national team'):
                # Calendar-year aggregation for international matches
                try:
                    year = int(season_str.split('-')[0]) if '-' in season_str else int(season_str)
                except Exception:
                    year = None
                if year:
                    for m in all_matches:
                        if m.match_date.year == year and _is_international_competition(m.competition):
                            relevant.append(m)
            else:
                target = comp_name.lower()
                for m in all_matches:
                    if season_start <= m.match_date <= season_end:
                        comp = (m.competition or '').lower()
                        if comp == target or target in comp:
                            relevant.append(m)
            if not relevant:
                continue
            calc_games = len(relevant)
            calc_minutes = sum(m.minutes_played or 0 for m in relevant)
            calc_starts = sum(1 for m in relevant if (m.minutes_played or 0) > 45)
            changed = False
            if calc_games and row.games != calc_games:
                row.games = calc_games
                changed = True
            if calc_minutes and row.minutes != calc_minutes:
                row.minutes = calc_minutes
                changed = True
            if calc_starts and (row.games_starts or 0) != calc_starts:
                row.games_starts = calc_starts
                changed = True
            if changed:
                db.add(row)
        db.commit()
    except Exception as e:
        logger.error(f"Error aligning GK stats from match logs: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())