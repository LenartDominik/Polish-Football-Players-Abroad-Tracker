"""
Sync match logs (detailed match statistics) for players
Usage: python sync_match_logs.py "Player Name" [--season YYYY-YYYY]
"""
import sys
import asyncio
from datetime import datetime, date
import logging

sys.path.append('.')

from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.services.fbref_playwright_scraper import FBrefPlaywrightScraper

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Importy na górze (upewnij się, że są):
# from .database import SessionLocal
# from datetime import date, datetime
# from .models import Player, PlayerMatch  (twoje modele)

async def sync_player_matches(scraper: FBrefPlaywrightScraper, player_info: dict, season: str = "2025-2026") -> int:
    """
    Sync match logs for a player.
    Safe for Supabase Port 6543 (Disconnects DB during API calls).
    
    Args:
        scraper: FBref Playwright scraper instance
        player_info: Dict with keys {'id': int, 'name': str, 'api_id': str/None, 'fbref_id': str/None}
        season: Season to sync
    """
    player_id = player_info.get('id')
    player_name = player_info.get('name')
    
    logger.info(f"🏆 Syncing match logs for {player_name} ({season})")
    
    # --- FAZA 1: API (Bez otwartej bazy danych) ---
    
    # 1. Sprawdź ID FBref (najpierw z argumentów, potem szukaj w sieci)
    fbref_id = player_info.get('fbref_id') or player_info.get('api_id')
    
    if not fbref_id:
        logger.warning(f"⚠️ No FBref ID for {player_name}. Searching online...")
        # To może trwać długo, dlatego baza musi być zamknięta!
        try:
            player_data_found = await scraper.search_player(player_name)
            if player_data_found and player_data_found.get('player_id'):
                fbref_id = player_data_found['player_id']
                logger.info(f"✅ Found FBref ID online: {fbref_id}")
                
                # Zapisz znalezione ID do bazy (krótka, osobna transakcja)
                # Otwieramy bazę tylko na moment zapisu ID
                db_temp = SessionLocal()
                try:
                    p = db_temp.get(Player, player_id)
                    if p:
                        p.api_id = fbref_id # lub fbref_id field
                        db_temp.commit()
                except Exception as e:
                    logger.error(f"Failed to save FBref ID: {e}")
                finally:
                    db_temp.close()
            else:
                logger.error(f"❌ Could not find player on FBref")
                return 0
        except Exception as e:
            logger.error(f"Scraper error during search: {e}")
            return 0
            
    # 2. Pobierz logi meczowe (To trwa najdłużej!)
    try:
        match_logs = await scraper.get_player_match_logs(fbref_id, player_name, season)
    except Exception as e:
        logger.error(f"Scraper error getting logs: {e}")
        return 0
        
    if not match_logs:
        logger.warning(f"⚠️ No match logs found for {season}")
        return 0
        
    logger.info(f"📊 Found {len(match_logs)} matches from API. Saving to DB...")
    
    # --- FAZA 2: BAZA DANYCH (Szybki zapis) ---
    
    db = SessionLocal() # Otwieramy sesję dopiero TERAZ
    try:
        # Parse season to get date range
        year_start = int(season.split('-')[0])
        year_end = year_start + 1
        season_start = date(year_start, 7, 1)
        season_end = date(year_end, 6, 30)
        
        # Delete existing matches for this season
        db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player_id,
            PlayerMatch.match_date >= season_start,
            PlayerMatch.match_date <= season_end
        ).delete(synchronize_session=False) # 'fetch' jest wolniejsze, False wystarczy przy nowej sesji
        
        # Preload existing matches for this player to avoid UNIQUE constraint violations
        existing_keys = set()
        for m in db.query(PlayerMatch).filter(PlayerMatch.player_id == player_id).all():
            comp = (m.competition or '').strip()[:100]
            opp = (m.opponent or '').strip()[:100]
            existing_keys.add((m.match_date, comp, opp))

        saved_count = 0
        seen = set()             # wide key (date, competition, opponent)
        seen_narrow = set()      # narrow key (date, opponent) for unique_match_event
        for match_data in match_logs:
            try:
                # Parse and normalize
                match_date_str = match_data.get('match_date')
                match_date = date.today()  # fallback
                if match_date_str:
                    try:
                        match_date = datetime.strptime(match_date_str, '%Y-%m-%d').date()
                    except Exception:
                        try:
                            parts = match_date_str.split('-')
                            if len(parts) == 3:
                                match_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        except Exception:
                            pass  # keep fallback
                competition = (match_data.get('competition') or '').strip()[:100]
                opponent = (match_data.get('opponent') or '').strip()[:100]

                # Skip if already in DB or duplicated within this batch
                key = (match_date, competition, opponent)
                if key in existing_keys or key in seen:
                    continue
                seen.add(key)

                # Create match record
                match = PlayerMatch(
                    player_id=player_id,
                    match_date=match_date,
                    competition=competition,
                    round=(match_data.get('round') or '').strip()[:50],
                    venue=(match_data.get('venue') or '').strip()[:50],
                    opponent=opponent,
                    result=(match_data.get('result') or '').strip()[:20],
                    minutes_played=match_data.get('minutes_played', 0) or 0,
                    goals=match_data.get('goals', 0) or 0,
                    assists=match_data.get('assists', 0) or 0,
                    shots=match_data.get('shots', 0) or 0,
                    shots_on_target=match_data.get('shots_on_target', 0) or 0,
                    xg=float(match_data.get('xg', 0.0) or 0.0),  # cast to float
                    xa=float(match_data.get('xa', 0.0) or 0.0),
                    passes_completed=match_data.get('passes_completed', 0) or 0,
                    passes_attempted=match_data.get('passes_attempted', 0) or 0,
                    pass_completion_pct=float(match_data.get('pass_completion_pct', 0.0) or 0.0),
                    key_passes=match_data.get('key_passes', 0) or 0,
                    tackles=match_data.get('tackles', 0) or 0,
                    interceptions=match_data.get('interceptions', 0) or 0,
                    blocks=match_data.get('blocks', 0) or 0,
                    touches=match_data.get('touches', 0) or 0,
                )
                db.add(match)
                saved_count += 1
            except Exception as e:
                logger.error(f"❌ Error parsing match row: {e}")
        
        db.commit()
        logger.info(f"✅ Saved {saved_count} matches for {player_name}")
        return saved_count
        
    except Exception as e:
        logger.error(f"❌ DB Transaction Error for {player_name}: {e}")
        db.rollback()
        return 0
    finally:
        db.close() 


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print('  python sync_match_logs.py "Robert Lewandowski"')
        print('  python sync_match_logs.py "Michał Helik" --season 2024-2025')
        sys.exit(1)
    player_name = sys.argv[1]
    # Parse season
    season = "2025-2026"
    if '--season' in sys.argv:
        try:
            season_idx = sys.argv.index('--season')
            season = sys.argv[season_idx + 1]
        except:
            pass
    logger.info("=" * 60)
    logger.info(f"SYNC MATCH LOGS: {player_name}")
    logger.info(f"Season: {season}")
    logger.info("=" * 60)
    db = SessionLocal()
    try:
        # Find player
        player = db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).first()
        if not player:
            logger.error(f"❌ Player not found: {player_name}")
            logger.info("💡 Add player first with: python quick_add_player.py")
            sys.exit(1)
        logger.info(f"✅ Found player: {player.name} (ID: {player.id})")
        # Sync matches
        async with FBrefPlaywrightScraper(headless=True, rate_limit_seconds=12.0) as scraper:
            # Convert ORM to dict for sync_player_matches
            player_data = {
                'id': player.id,
                'name': player.name,
                'team': player.team,
                'league': player.league,
                'nationality': player.nationality,
                'position': player.position,
                'last_updated': player.last_updated,
                'fbref_id': getattr(player, 'fbref_id', None),
                'api_id': getattr(player, 'api_id', None)
            }
            matches_count = await sync_player_matches(scraper, player_data, season)
        logger.info("=" * 60)
        if matches_count > 0:
            logger.info(f"✅ SUCCESS: Synced {matches_count} matches")
        else:
            logger.warning(f"⚠️ No matches synced")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
