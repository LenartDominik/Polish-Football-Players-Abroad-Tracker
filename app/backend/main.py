import logging
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Optional, List
from collections import defaultdict

# --- Biblioteki zewnętrzne ---
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
import resend
from sqlalchemy import extract
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Twoje moduły konfiguracyjne i bazodanowe ---
from .config import settings 
from .database import engine, Base, SessionLocal

# --- Routery i Serwisy ---
from .routers import players, comparison, matchlogs
from .services.fbref_playwright_scraper import FBrefPlaywrightScraper

# --- Modele Bazy Danych ---
from .models.player import Player
from .models.competition_stats import CompetitionStats, CompetitionType
from .models.goalkeeper_stats import GoalkeeperStats
from .models.player_match import PlayerMatch


logger = logging.getLogger(__name__)


if settings.resend_api_key:
    resend.api_key = settings.resend_api_key
else:
    logger.warning("⚠️ Brak klucza RESEND_API_KEY - powiadomienia e-mail nie będą działać.")

# Tworzenie tabel w bazie na starcie
Base.metadata.create_all(bind=engine)

# Global scheduler instance
scheduler = None


def get_competition_type(competition_name: str) -> str:
    """Determine competition type from competition name"""
    if not competition_name:
        return "LEAGUE"
    
    comp_lower = competition_name.lower()
    
    # National team (CHECK FIRST - before UEFA competitions)
    # This prevents international matches from being classified as European cups
    if any(keyword in comp_lower for keyword in [
        'national team', 'reprezentacja', 'international',
        'friendlies', 'wcq', 'world cup', 'uefa euro', 'copa america'
    ]):
        return "NATIONAL_TEAM"
    
    # Domestic cups (CHECK SECOND - before European competitions)
    # This prevents domestic cups from being classified as European competitions
    if any(keyword in comp_lower for keyword in [
        'copa del rey', 'copa', 'pokal', 'coupe', 'coppa',
        'fa cup', 'league cup', 'efl', 'carabao',
        'dfb-pokal', 'dfl-supercup', 'supercoca', 'supercoppa',
        'u.s. open cup'
    ]):
        return "DOMESTIC_CUP"
    
    # European club competitions
    if any(keyword in comp_lower for keyword in [
        'champions league', 'europa league', 'conference league', 
        'uefa', 'champions lg', 'europa lg', 'conf lg', 'ucl', 'uel', 'uecl'
    ]):
        return "EUROPEAN_CUP"
    
    # Default to league
    return "LEAGUE"


def save_competition_stats(db, player: Player, stats_list: List[dict], current_season: str = "2025-2026") -> int:
    """
    Save competition statistics to database (current season only)
    Based on sync_playwright.py logic
    """
    saved_count = 0
    
    # Filter for current season stats only - include all season variants (2025-2026, 2026, 2025)
    season_variants = [current_season, current_season.replace("-", "/"), current_season.split("-")[0], current_season.split("-")[-1]]
    current_stats = [s for s in stats_list if s.get('season') in season_variants]
    
    if not current_stats:
        logger.warning(f"No stats found for season {current_season}, using most recent season")
        # Get the most recent season
        if stats_list:
            seasons = [s.get('season', '') for s in stats_list if s.get('season')]
            if seasons:
                latest_season = sorted(seasons)[-1]
                current_stats = [s for s in stats_list if s.get('season') == latest_season]
                current_season = latest_season
    
    # Delete existing stats for this season only
    db.query(CompetitionStats).filter(
        CompetitionStats.player_id == player.id,
        CompetitionStats.season == current_season
    ).delete()
    
    db.query(GoalkeeperStats).filter(
        GoalkeeperStats.player_id == player.id,
        GoalkeeperStats.season == current_season
    ).delete()
    
    # Deduplicate stats by season/competition combination
    seen = set()
    deduplicated_stats = []
    for stat_data in current_stats:
        key = (stat_data.get('season'), stat_data.get('competition_name'))
        if key not in seen:
            seen.add(key)
            deduplicated_stats.append(stat_data)
    
    for stat_data in deduplicated_stats:
        try:
            # Get competition type
            comp_type_raw = stat_data.get('competition_type')
            if comp_type_raw:
                if isinstance(comp_type_raw, str):
                    comp_type = comp_type_raw.upper()
                elif isinstance(comp_type_raw, CompetitionType):
                    comp_type = comp_type_raw.value.upper()
                else:
                    comp_type = get_competition_type(stat_data.get('competition_name', ''))
            else:
                comp_type = get_competition_type(stat_data.get('competition_name', ''))

            if player.is_goalkeeper:
                gk_stat = GoalkeeperStats(
                    player_id=player.id,
                    season=stat_data.get('season', current_season),
                    competition_type=comp_type,
                    competition_name=stat_data.get('competition_name', ''),
                    games=stat_data.get('games', 0) or 0,
                    games_starts=stat_data.get('games_starts', 0) or 0,
                    minutes=stat_data.get('minutes', 0) or 0,
                    goals_against=stat_data.get('goals_against', 0) or 0,
                    goals_against_per90=stat_data.get('ga90', 0.0) or stat_data.get('goals_against_per90', 0.0) or 0.0,
                    shots_on_target_against=stat_data.get('sota', 0) or stat_data.get('shots_on_target_against', 0) or 0,
                    saves=stat_data.get('saves', 0) or 0,
                    save_percentage=stat_data.get('save_pct', 0.0) or 0.0,
                    clean_sheets=stat_data.get('clean_sheets', 0) or 0,
                    clean_sheet_percentage=stat_data.get('clean_sheets_pct', 0.0) or 0.0,
                    wins=stat_data.get('wins', 0) or 0,
                    draws=stat_data.get('draws', 0) or stat_data.get('ties', 0) or 0,
                    losses=stat_data.get('losses', 0) or 0,
                    penalties_attempted=stat_data.get('pens_att', 0) or 0,
                    penalties_allowed=stat_data.get('pens_allowed', 0) or 0,
                    penalties_saved=stat_data.get('pens_saved', 0) or 0,
                    penalties_missed=stat_data.get('pens_missed', 0) or 0,
                    post_shot_xg=stat_data.get('psxg', 0.0) or 0.0
                )
                db.add(gk_stat)
            else:
                comp_stat = CompetitionStats(
                    player_id=player.id,
                    season=stat_data.get('season', current_season),
                    competition_type=comp_type,
                    competition_name=stat_data.get('competition_name', ''),
                    games=stat_data.get('games', 0) or 0,
                    games_starts=stat_data.get('games_starts', 0) or 0,
                    minutes=stat_data.get('minutes', 0) or 0,
                    goals=stat_data.get('goals', 0) or 0,
                    assists=stat_data.get('assists', 0) or 0,
                    xg=stat_data.get('xg', 0.0) or 0.0,
                    xa=stat_data.get('xa', 0.0) or 0.0,
                    yellow_cards=stat_data.get('yellow_cards', 0) or 0,
                    red_cards=stat_data.get('red_cards', 0) or 0,
                )
                db.add(comp_stat)
            
            saved_count += 1
        except Exception as e:
            logger.error(f"  ❌ Error saving stat: {e}")
    
    return saved_count


async def sync_single_player(scraper: FBrefPlaywrightScraper, player_info: dict, current_season: str = "2025-2026") -> bool:
    """
    Sync a single player with full statistics saving.
    Safe for Supabase Port 6543 (Independent Session).
    """
    player_id = player_info.get('id')
    player_name = player_info.get('name')
    
    try:
        # --- FAZA 1: API (Baza zamknięta) ---
        player_data = None
        fbref_id = player_info.get('fbref_id') or player_info.get('api_id')
        
        if fbref_id:
            logger.info(f" 📌 Using FBref ID: {fbref_id}")
            player_data = await scraper.get_player_by_id(fbref_id, player_name)
        else:
            logger.info(f" 🔍 Searching by name: {player_name}")
            player_data = await scraper.search_player(player_name)
        
        if not player_data:
            logger.warning(f" ❌ No data found for {player_name}")
            return False
            
        # --- FAZA 2: BAZA DANYCH (Szybki zapis) ---
        db = SessionLocal() # Otwieramy sesję TERAZ
        try:
            player = db.get(Player, player_id)
            if not player:
                logger.error(f"Player {player_id} disappeared from DB!")
                return False

            # Update player info
            if player_data.get('name'):
                logger.info(f" ✅ Found: {player_data['name']}")
            
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
                        if '-' in s:
                            first = s.split('-')[0]
                            return int(first)
                        return int(s)
                    except Exception:
                        return -1
                # Filter LEAGUE stats and sort by: 1) season start year descending, 2) minutes played descending
                from app.backend.main import get_competition_type, normalize_competition_type
                league_stats = [st for st in player_data['competition_stats'] 
                               if normalize_competition_type(st.get('competition_type'), st.get('competition_name', '')) == 'LEAGUE']
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
            # Apply league/team from latest reliable league stat; do not fallback to API top-level team
            if latest_league_name:
                player.league = latest_league_name
            if latest_league_team:
                player.team = latest_league_team
            
            # Save IDs
            if player_data.get('player_id'):
                if not player.api_id or player.api_id != player_data['player_id']:
                    player.api_id = player_data['player_id']
                if not player.fbref_id:
                    player.fbref_id = player_data['player_id']
            
            player.last_updated = date.today()
            
            # Save competition stats
            if player_data.get('competition_stats'):
                # UWAGA: save_competition_stats musi przyjmować naszą otwartą sesję 'db'
                save_competition_stats(
                    db, 
                    player, 
                    player_data['competition_stats'],
                    current_season=current_season
                )
            
            db.commit() # Zapisujemy zmiany
            return True
            
        except Exception as e:
            logger.error(f" ❌ DB Error syncing {player_name}: {e}", exc_info=True)
            db.rollback()
            return False
        finally:
            db.close() # ZAMYKAMY!

    except Exception as e:
        logger.error(f" ❌ General Error syncing {player_name}: {e}", exc_info=True)
        return False



def send_matchlogs_notification_email(synced: int, failed: int, total: int, total_matches: int, duration_minutes: float, failed_players: List[str]):
    """
    Wysyła raport e-mail przez API Resend po zakończeniu synchronizacji matchlogów.
    """
    # Sprawdzenie konfiguracji
    if not settings.resend_api_key or not settings.email_to:
        print("⚠️ Pominięto wysyłkę: Brak klucza API lub adresu docelowego.") 
        return

    # Obliczenia do treści maila
    success_rate = (synced / total * 100) if total > 0 else 0
    status_emoji = "✅" if failed == 0 else "⚠️" if success_rate >= 80 else "❌"
    
    failed_list_html = ""
    if failed_players:
        failed_list_html = f"<h3>❌ Problemy z graczami ({len(failed_players)}):</h3><ul>"
        for p in failed_players:
            failed_list_html += f"<li>{p}</li>"
        failed_list_html += "</ul>"

    html_content = f"""
    <h2>{status_emoji} Raport Synchronizacji Matchlogów</h2>
    <p><strong>Data:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Czas trwania:</strong> {duration_minutes:.1f} min</p>
    <hr>
    <h3>Statystyki:</h3>
    <ul>
        <li><strong>Wszyscy gracze:</strong> {total}</li>
        <li><strong>Zsynchronizowano:</strong> {synced} ({success_rate:.1f}%)</li>
        <li><strong>Błędy:</strong> {failed}</li>
        <li><strong>Pobrane mecze:</strong> {total_matches}</li>
    </ul>
    {failed_list_html}
    <hr>
    <p><small>Wysłano z Polish Football Data Hub (Render + Resend)</small></p>
    """
    
    print(f"📧 Próba wysyłki z: {settings.email_from} do: {settings.email_to}") # Logowanie dla pewności

    resend.Emails.send({
        "from": settings.email_from, 
        "to": settings.email_to,
        "subject": f"{status_emoji} Sync Report: {total_matches} Matches ({synced}/{total} Players)",
        "html": html_content
    })
    
    logger.info(f"✅ E-mail (Matchlogs) wysłany pomyślnie na: {settings.email_to}")



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
        <p><small>Powiadomienie z Polish Football Data Hub</small></p>
        """

        resend.Emails.send({
            "from": settings.email_from, 
            "to": settings.email_to,
            "subject": f"{status_emoji} Sync Update: {synced}/{total} Players Updated",
            "html": html_content
        })
        
        logger.info(f"✅ E-mail (Basic Sync) wysłany pomyślnie na: {settings.email_to}")

    except Exception as e:
        logger.error(f"❌ Błąd wysyłki maila (Basic Sync): {e}")


        

async def sync_player_matchlogs(scraper: FBrefPlaywrightScraper, db, player: Player, season: str = "2025-2026") -> int:
    """
    Sync match logs for a single player
    
    Args:
        scraper: FBref Playwright scraper instance
        db: Database session
        player: Player object
        season: Season to sync (default: 2025-2026)
    
    Returns:
        Number of matches synced
    """
    try:
        # Get FBref ID
        fbref_id = None
        if hasattr(player, 'fbref_id') and player.fbref_id:
            fbref_id = player.fbref_id
        elif player.api_id:
            fbref_id = player.api_id
        
        if not fbref_id:
            logger.warning(f"  ⚠️ No FBref ID for {player.name}, skipping matchlogs")
            return 0
        
        # Get match logs
        match_logs = await scraper.get_player_match_logs(fbref_id, player.name, season)
        
        if not match_logs:
            logger.info(f"  ℹ️ No match logs found for {season}")
            return 0
        
        logger.info(f"  📊 Found {len(match_logs)} matches")
        
        # Parse season to get date range (e.g., 2025-2026 = July 1, 2025 to June 30, 2026)
        from datetime import date
        year_start = int(season.split('-')[0])
        year_end = year_start + 1
        season_start = date(year_start, 7, 1)
        season_end = date(year_end, 6, 30)
        
        # Delete existing matches for this player and season only
        db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player.id,
            PlayerMatch.match_date >= season_start,
            PlayerMatch.match_date <= season_end
        ).delete(synchronize_session='fetch')
        
        # Save matches
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
                    minutes_played=match_data.get('minutes', 0) or 0,
                    goals=match_data.get('goals', 0) or 0,
                    assists=match_data.get('assists', 0) or 0,
                    shots=match_data.get('shots', 0) or 0,
                    shots_on_target=match_data.get('shots_on_target', 0) or 0,
                    xg=match_data.get('xg', 0.0) or 0.0,
                    xa=match_data.get('xa', 0.0) or 0.0,
                    passes_completed=match_data.get('passes_completed', 0) or 0,
                    passes_attempted=match_data.get('passes_attempted', 0) or 0,
                    pass_completion_pct=match_data.get('pass_completion_pct', 0.0) or 0.0,
                    key_passes=match_data.get('key_passes', 0) or 0,
                    tackles=match_data.get('tackles', 0) or 0,
                    interceptions=match_data.get('interceptions', 0) or 0,
                    blocks=match_data.get('blocks', 0) or 0,
                    touches=match_data.get('touches', 0) or 0,
                    dribbles_completed=match_data.get('dribbles_completed', 0) or 0,
                    carries=match_data.get('carries', 0) or 0,
                    fouls_committed=match_data.get('fouls_committed', 0) or 0,
                    fouls_drawn=match_data.get('fouls_drawn', 0) or 0,
                    yellow_cards=match_data.get('yellow_cards', 0) or 0,
                    red_cards=match_data.get('red_cards', 0) or 0
                )
                
                db.add(match)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"  ❌ Error saving match: {e}")
        
        db.commit()
        logger.info(f"  ✅ Saved {saved_count} matches")
        
        return saved_count
        
    except Exception as e:
        logger.error(f"  ❌ Error syncing match logs: {e}")
        db.rollback()
        return 0




def sync_competition_stats_from_matches(db, player_id: int) -> int:
    """
    Synchronize competition_stats from player_matches
    Ensures both tables have consistent data
    """
    try:
        from collections import defaultdict
        
        matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player_id
        ).all()
        
        if not matches:
            return 0
        
        stats_dict = defaultdict(lambda: {
            'games': 0, 'goals': 0, 'assists': 0, 'minutes': 0,
            'xg': 0.0, 'xa': 0.0, 'games_starts': 0
        })
        
        for match in matches:
            year = match.match_date.year
            month = match.match_date.month
            
            if month >= 7:
                season = f"{year}-{year+1}"
            else:
                season = f"{year-1}-{year}"
            
            international_comps = ['WCQ', 'World Cup', 'UEFA Nations League', 
                                   'UEFA Euro Qualifying', 'UEFA Euro', 
                                   'Friendlies (M)', 'Copa América']
            if match.competition in international_comps:
                # Use calendar year for all international matches
                season = str(year)
            
            # Group national team matches under "National Team {season}"
            if match.competition in international_comps:
                competition_name = f'National Team {season}'
            else:
                competition_name = match.competition
            
            key = (season, competition_name)
            stats_dict[key]['games'] += 1
            stats_dict[key]['goals'] += match.goals or 0
            stats_dict[key]['assists'] += match.assists or 0
            stats_dict[key]['minutes'] += match.minutes_played or 0
            stats_dict[key]['xg'] += match.xg or 0.0
            stats_dict[key]['xa'] += match.xa or 0.0
            stats_dict[key]['games_starts'] += 1 if (match.minutes_played or 0) > 45 else 0
        
        updated = 0
        for (season, competition), stats in stats_dict.items():
            record = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_name == competition
            ).first()
            
            comp_type = get_competition_type(competition)
            
            if record:
                record.games = stats['games']
                record.goals = stats['goals']
                record.assists = stats['assists']
                record.minutes = stats['minutes']
                record.xg = stats['xg']
                record.xa = stats['xa']
                record.games_starts = stats['games_starts']
                record.competition_type = comp_type  # Update type as well
            else:
                record = CompetitionStats(
                    player_id=player_id,
                    season=season,
                    competition_name=competition,
                    competition_type=comp_type,
                    games=stats['games'],
                    goals=stats['goals'],
                    assists=stats['assists'],
                    minutes=stats['minutes'],
                    xg=stats['xg'],
                    xa=stats['xa'],
                    games_starts=stats['games_starts']
                )
                db.add(record)
            
            updated += 1
        
        db.commit()
        return updated
    
    except Exception as e:
        logger.error(f"Error syncing competition_stats: {e}")
        return 0


async def scheduled_sync_all_players():
    """
    Scheduled task to sync all players (Safe for Port 6543).
    """
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("🔄 SCHEDULED SYNC - Starting automatic player synchronization")
    logger.info(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 1. Pobieramy listę graczy (tylko dane, bez sesji ORM)
    players_data = []
    
    # Krótka sesja tylko na odczyt listy
    db = SessionLocal()
    try:
        # Pobieramy ID, Name, API_ID, FBREF_ID
        all_players = db.query(Player.id, Player.name, Player.api_id, Player.fbref_id).all()
        for p in all_players:
            players_data.append({
                "id": p.id,
                "name": p.name,
                "api_id": p.api_id,
                "fbref_id": p.fbref_id
            })
    except Exception as e:
        logger.error(f"❌ Failed to fetch players list: {e}")
        return
    finally:
        db.close() # ZAMYKAMY BAZĘ

    if not players_data:
        logger.warning("⚠️ No players found in database")
        return
        
    logger.info(f"📋 Found {len(players_data)} players to sync")
    
    synced = 0
    failed = 0
    failed_players = []
    
    # 2. Uruchamiamy scrapera (TU NIE MA OTWARTEJ SESJI DB!)
    try:
        async with FBrefPlaywrightScraper(headless=True, rate_limit_seconds=6.0) as scraper:
            
            for idx, p_data in enumerate(players_data, 1):
                logger.info(f"\n[{idx}/{len(players_data)}] 🔄 Syncing: {p_data['name']}")
                
                try:
                    # Wywołujemy bezpieczną funkcję (przekazujemy słownik p_data)
                    # Zakładam, że w main.py masz już nową wersję sync_single_player
                    success = await sync_single_player(scraper, p_data)
                    
                    if success:
                        synced += 1
                        logger.info(f"✅ Successfully synced {p_data['name']}")
                    else:
                        failed += 1
                        failed_players.append(p_data['name'])
                        logger.warning(f"❌ Failed to sync {p_data['name']}")
                        
                except Exception as e:
                    logger.error(f"❌ Exception during sync for {p_data['name']}: {e}")
                    failed += 1
                    failed_players.append(p_data['name'])

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        logger.info("=" * 60)
        logger.info("✅ SCHEDULED SYNC COMPLETE")
        logger.info(f"📊 Results: {synced} synced, {failed} failed out of {len(players_data)} total")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")
        logger.info("=" * 60)
        
        # Send email notification
        send_sync_notification_email(synced, failed, len(players_data), duration, failed_players)
        
    except Exception as e:
        logger.error(f"❌ Scheduled sync failed: {e}", exc_info=True)



async def scheduled_sync_matchlogs():
    """
    Scheduled task to sync match logs for all players.
    Safe for Supabase Port 6543 (Independent Sessions).
    """
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("📋 SCHEDULED MATCHLOGS SYNC - Starting automatic match logs synchronization")
    logger.info(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 1. Pobieramy listę graczy (ID, Names, API_IDs)
    players_data = []
    
    # Krótka sesja tylko na odczyt listy
    db = SessionLocal()
    try:
        all_players = db.query(Player.id, Player.name, Player.api_id, Player.fbref_id).all()
        for p in all_players:
            if (p.fbref_id) or p.api_id:
                players_data.append({
                    "id": p.id,
                    "name": p.name,
                    "fbref_id": p.fbref_id,
                    "api_id": p.api_id
                })
    except Exception as e:
        logger.error(f"❌ Failed to fetch players list: {e}")
        return
    finally:
        db.close() # ZAMYKAMY BAZĘ

    if not players_data:
        logger.warning("⚠️ No players found in database (or no suitable IDs)")
        return
        
    logger.info(f"📋 Found {len(players_data)} players with FBref ID to sync match logs")
    
    synced = 0
    failed = 0
    failed_players = []
    total_matches = 0

    # 2. Uruchamiamy scrapera (TU NIE MA OTWARTEJ SESJI DB!)
    try:
        async with FBrefPlaywrightScraper(headless=True, rate_limit_seconds=12.0) as scraper:
            
            for idx, p_data in enumerate(players_data, 1):
                logger.info(f"\n[{idx}/{len(players_data)}] 📋 Syncing match logs: {p_data['name']}")
                
                try:
                    # Wywołujemy bezpieczną funkcję, przekazując SŁOWNIK (p_data), a nie sesję
                    # Upewnij się, że w main.py masz funkcję sync_player_matchlogs, 
                    # która przyjmuje (scraper, player_info, season) - naprawiliśmy ją wcześniej.
                    
                    matches_count = await sync_player_matchlogs(scraper, p_data, season="2025-2026")
                    
                    if matches_count >= 0: # 0 to też sukces (brak nowych meczy)
                        synced += 1
                        total_matches += matches_count
                        if matches_count > 0:
                            logger.info(f"✅ Successfully synced {matches_count} matches for {p_data['name']}")
                        else:
                            logger.info(f"ℹ️ No new matches for {p_data['name']}")
                    else:
                        # Jeśli funkcja zwraca -1 w przypadku błędu (zależnie jak ją zdefiniowałeś)
                        raise Exception("Sync returned error code")

                except Exception as e:
                    failed += 1
                    failed_players.append(p_data['name'])
                    logger.warning(f"❌ Failed to sync match logs for {p_data['name']}: {e}")

        # Podsumowanie i wysyłka maila
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        logger.info("=" * 60)
        logger.info("✅ SCHEDULED MATCHLOGS SYNC COMPLETE")
        logger.info(f"📊 Results: {synced} players synced, {total_matches} total matches, {failed} failed out of {len(players_data)} total")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")
        logger.info("=" * 60)
        
        send_matchlogs_notification_email(synced, failed, len(players_data), total_matches, duration, failed_players)
        
    except Exception as e:
        logger.error(f"❌ Scheduled matchlogs sync CRITICAL FAILURE: {e}", exc_info=True)
        try:
            duration = (datetime.now() - start_time).total_seconds() / 60
            send_matchlogs_notification_email(0, 1, 1, 0, duration, ["CRITICAL ERROR - Check logs"])
        except:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    
    logger.info("🚀 Aplikacja startuje...")
    
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        logger.info("📅 Initializing scheduler...")
        
        # Get timezone from config (default: Europe/Warsaw)
        from .config import settings
        timezone_str = settings.scheduler_timezone
        
        # Create AsyncIO scheduler with timezone
        scheduler = AsyncIOScheduler(timezone=timezone_str)
        
        # Schedule sync twice a week:
        # - Thursday at 06:00 (day after Wednesday Champions League matches)
        # - Monday at 06:00 (day after weekend league matches)
        scheduler.add_job(
            scheduled_sync_all_players,
            CronTrigger(day_of_week='thu,mon', hour=6, minute=0, timezone=timezone_str),
            id='sync_all_players',
            name='Sync all players statistics',
            replace_existing=True
        )
        
        # Schedule matchlogs sync once a week:
        # - Tuesday at 07:00 (gives time after Monday stats sync)
        scheduler.add_job(
            scheduled_sync_matchlogs,
            CronTrigger(day_of_week='tue', hour=7, minute=0, timezone=timezone_str),
            id='sync_matchlogs',
            name='Sync all players match logs',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Scheduler uruchomiony")
        logger.info(f"📅 Stats sync schedule: Thursday & Monday at 06:00 ({timezone_str})")
        logger.info(f"📅 Matchlogs sync schedule: Tuesday at 07:00 ({timezone_str})")
        logger.info("📅 Next stats sync: " + str(scheduler.get_job('sync_all_players').next_run_time))
        logger.info("📅 Next matchlogs sync: " + str(scheduler.get_job('sync_matchlogs').next_run_time))
    else:
        logger.info("⏸️ Scheduler disabled (set ENABLE_SCHEDULER=true to enable)")
    
    yield
    
    logger.info("🛑 Aplikacja się wyłącza...")
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler zatrzymany")

app = FastAPI(
    title="Polish Football Data Hub International - API",
    description="""
    🇵🇱 **Polish Football Data Hub International API** - Real-time monitoring of 90+ Polish footballers playing abroad.
    
    ## 📊 Data Source & Attribution
    
    All player statistics are sourced from **[FBref.com](https://fbref.com/)** (Sports Reference LLC).
    
    **What we provide from FBref:**
    - ⚽ Player statistics (goals, assists, xG, xA, minutes, shots, passes)
    - 📋 Match logs (detailed game-by-game performance)
    - 🏆 Competition data (leagues, cups, international matches)
    - 🧤 Goalkeeper statistics (saves, clean sheets, goals against)
    
    **Our commitment:**
    - ✅ **Rate Limiting**: 12-second delay between requests (respects server load)
    - ✅ **Clear Attribution**: FBref credited in UI, API, and documentation
    - ✅ **Non-Commercial**: Educational/portfolio project
    - ✅ **Respectful Scraping**: Following best practices and Terms of Service
    
    ## ⚖️ Legal Notice
    
    **This is an EDUCATIONAL, NON-COMMERCIAL project.**
    
    - **Usage:** Educational and portfolio purposes ONLY
    - **NOT for commercial use** without proper licensing from FBref
    - **Full Legal Notice:** See `docs/LEGAL_NOTICE.md` in repository
    
    **Disclaimer:** This project is independent and not affiliated with FBref.com or Sports Reference LLC.  
    For official statistics, visit [FBref.com](https://fbref.com/)
    
    ---
    
    ## ✨ Features
    
    - 🕸️ **Automated scraping** from FBref.com using Playwright
    - 📊 **Comprehensive statistics**: Goals, assists, xG, xA, npxG, minutes, cards, penalty goals
    - 🥅 **Goalkeeper stats**: Saves, clean sheets, save percentage, penalties
    - 🏆 **Competition breakdown**: League, European Cups, National Team, Domestic Cups
    - 🤖 **Automated scheduler**: Stats sync 2x/week (Mon/Thu 6:00 AM), Matchlogs sync 1x/week (Tue 7:00 AM)
    - 📧 **Email notifications**: HTML reports after each sync
    - ⚡ **Rate limiting**: 12s between requests (FBref ToS compliant)
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
    - **GitHub**: [Full Documentation](https://github.com/LenartDominik/Polish-Football-Data-Hub-International)
    
    ## 🔄 Automated Data Sync
    
    - **Player Stats**: Monday & Thursday at 06:00 (Europe/Warsaw)
    - **Match Logs**: Tuesday at 07:00 (Europe/Warsaw)
    - Automatic updates keep data fresh from FBref.com
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Polish-Football-Data-Hub-International",
        "url": "https://github.com/LenartDominik/Polish-Football-Data-Hub-International",
    },
    license_info={
        "name": "Educational Use Only (Non-Commercial)",
        "url": "https://github.com/LenartDominik/Polish-Football-Data-Hub-International/blob/master/LEGAL_NOTICE.md",
    },
)

# --- NOWE ENDPOINTY DLA CRON-JOB.ORG ---

@app.post("/api/trigger-sync-stats", tags=["Scheduler"])
async def trigger_sync_stats(
    background_tasks: BackgroundTasks, 
    token: str = Query(...)
):
    """
    Ręczne wyzwalanie synchronizacji statystyk (dla zewnętrznego crona).
    """
    # Pobieramy hasło ze zmiennych środowiskowych
    expected_token = os.getenv("CRON_SECRET")
    
    # Jeśli zmienna nie jest ustawiona w Renderze, blokujemy dostęp (bezpiecznik)
    if not expected_token:
        logger.error("❌ CRON_SECRET not set in environment variables!")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if token != expected_token:
        logger.warning("⚠️ Nieudana autoryzacja endpointu crona (Stats)")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info("🚀 [API] Otrzymano poprawne żądanie synchronizacji STATYSTYK")
    
    # Uruchomienie zadania w tle
    background_tasks.add_task(scheduled_sync_all_players)
    
    return {
        "message": "✅ Synchronizacja statystyk rozpoczęta w tle",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/trigger-sync-matchlogs", tags=["Scheduler"])
async def trigger_sync_matchlogs(
    background_tasks: BackgroundTasks, 
    token: str = Query(...)
):
    """
    Ręczne wyzwalanie synchronizacji logów meczowych (dla zewnętrznego crona).
    """
    expected_token = os.getenv("CRON_SECRET")
    
    if not expected_token:
        logger.error("❌ CRON_SECRET not set in environment variables!")
        raise HTTPException(status_code=500, detail="Server misconfiguration")
    
    if token != expected_token:
        logger.warning("⚠️ Nieudana autoryzacja endpointu crona (Matchlogs)")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info("🚀 [API] Otrzymano poprawne żądanie synchronizacji MATCHLOGS")
    
    # Uruchomienie zadania w tle
    background_tasks.add_task(scheduled_sync_matchlogs)
    
    return {
        "message": "✅ Synchronizacja logów meczowych rozpoczęta w tle",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/", tags=["Root"])
def root():
    """
    Welcome endpoint - API information and quick links
    
    Returns basic information about the API and available endpoints.
    """
    return {
        "message": "🇵🇱 Welcome to Polish Football Data Hub International API",
        "status": "operational",
        "data_source": {
            "name": "FBref.com",
            "provider": "Sports Reference LLC",
            "url": "https://fbref.com/",
            "attribution": "All player statistics sourced from FBref.com",
            "disclaimer": "This project is independent and not affiliated with FBref.com"
        },
        "features": [
            "🤖 Automated scheduler (stats 2x/week, matchlogs 1x/week)",
            "📧 Email notifications",
            "🕸️ Playwright web scraping",
            "📊 90+ Polish players tracking",
            "🏆 Competition breakdown (League/Europe/National Team/Domestic Cups)",
            "🥅 Dedicated goalkeeper statistics",
            "📋 Detailed match logs tracking",
            "⚡ Rate limiting (12s between requests - FBref ToS compliant)",
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
            "stats_sync_schedule": "Monday & Thursday at 06:00 (Europe/Warsaw)",
            "matchlogs_sync_schedule": "Tuesday at 07:00 (Europe/Warsaw)",
            "next_stats_sync": str(scheduler.get_job('sync_all_players').next_run_time) if scheduler and scheduler.running else "Scheduler disabled",
            "next_matchlogs_sync": str(scheduler.get_job('sync_matchlogs').next_run_time) if scheduler and scheduler.running else "Scheduler disabled"
        },
        "links": {
            "github": "https://github.com/LenartDominik/Polish-Football-Data-Hub-International",
            "fbref": "https://fbref.com",
            "legal_notice": "See LEGAL_NOTICE.md - Educational use only",
            "license": "Educational Use Only (Non-Commercial)",
            "credits": "See CREDITS.md for full attribution",
            "deployment_guide": "See RENDER_DEPLOYMENT.md"
        },
        "legal": {
            "usage": "Educational and portfolio purposes ONLY",
            "commercial_use": "NOT allowed without FBref license",
            "data_attribution": "All statistics © FBref.com (Sports Reference LLC)",
            "full_terms": "https://github.com/LenartDominik/Polish-Football-Data-Hub-International/blob/main/LEGAL_NOTICE.md"
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

@app.get("/test-email")
async def test_email_sending():
    """
    Uruchamia wysyłkę próbnego maila przez Resend.
    """
    try:
        # Wywołujemy Twoją funkcję z przykładowymi danymi
        send_matchlogs_notification_email(
            synced=5, 
            failed=1, 
            total=6, 
            total_matches=12, 
            duration_minutes=0.5, 
            failed_players=["Testowy Gracz (Error)"]
        )
        return {"status": "success", "message": "Mail wysłany! Sprawdź skrzynkę odbiorczą."}
    except Exception as e:
        return {"status": "error", "message": f"Błąd: {str(e)}"}

# Rejestracja routerów z prefixem /api
app.include_router(players.router, prefix="/api")                                                     
app.include_router(comparison.router, prefix="/api")                                                    
app.include_router(matchlogs.router, prefix="/api")




