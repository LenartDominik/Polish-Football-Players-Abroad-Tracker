"""
Poprawiona wersja sync_competition_stats.py
Naprawia:
- Dublowanie sezonów dla MLS/Leagues Cup (wymusza rok kalendarzowy dla pucharów USA)
- Normalizuje nazwy rozgrywek (Major League Soccer -> MLS)
- Grupowanie reprezentacji jako "National Team {season}"
"""
import sys
sys.path.append('.')

from app.backend.database import SessionLocal
from app.backend.models.player import Player
from app.backend.models.player_match import PlayerMatch
from app.backend.models.competition_stats import CompetitionStats
from app.backend.utils import get_competition_type
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_competition_stats_from_matches(player_id: int) -> int:
    """Synchronize competition_stats from player_matches (Safe for Supabase Port 6543)"""
    
    # KROK 1: Otwieramy "prywatną" sesję dla tej funkcji
    db = SessionLocal()
    
    try:
        # Get all matches for player
        matches = db.query(PlayerMatch).filter(
            PlayerMatch.player_id == player_id
        ).all()
        
        if not matches:
            return 0
        
        # Group by season and competition
        stats_dict = defaultdict(lambda: {
            'games': 0, 'goals': 0, 'assists': 0, 'minutes': 0,
            'xg': 0.0, 'xa': 0.0, 'games_starts': 0
        })
        
        # --- KONFIGURACJA: Ligi grające systemem wiosna-jesień (rok kalendarzowy) ---
        calendar_year_leagues = [
    'Veikkausliiga', 'Allsvenskan', 'Eliteserien',
    'MLS', 'Major League Soccer', 
    'Leagues Cup', 'US Open Cup', 'Lamar Hunt U.S. Open Cup', 'Canadian Championship',
    'CONCACAF Champions Cup', 'CONCACAF Champions League', # <--- DODAJ TO
    'J1 League', 'J2 League', 'K League 1', 'Chinese Super League', 'A-League'
]


        international_comps = [
            'WCQ', 'World Cup', 'UEFA Nations League', 
            'UEFA Euro Qualifying', 'UEFA Euro', 
            'Friendlies (M)', 'Copa América', 'Copa America'
        ]

        for match in matches:
            # Skip matches with 0 minutes (bench/unused sub)
            if (match.minutes_played or 0) == 0:
                continue

            year = match.match_date.year
            month = match.match_date.month
            
            # --- NORMALIZACJA NAZWY ---
            # Ujednolicamy nazwę zanim zaczniemy ustalać sezon
            raw_comp = (match.competition or '').strip()
            
            if 'Major League Soccer' in raw_comp or 'MLS' in raw_comp:
                comp_name = 'MLS' # Wszystko co ma "MLS" w nazwie (Playoffs też) spłaszczamy do 'MLS'
            elif 'U.S. Open Cup' in raw_comp:
                comp_name = 'US Open Cup'
            elif 'Leagues Cup' in raw_comp:
                comp_name = 'Leagues Cup'
            elif 'CONCACAF' in raw_comp:
                comp_name = 'CONCACAF Champions Cup'
            else:
                comp_name = raw_comp

            # --- USTALANIE SEZONU ---
            # Domyślny format: Jesień-Wiosna (np. 2025-2026)
            if month >= 7:
                season = f"{year}-{year+1}"
            else:
                season = f"{year-1}-{year}"
            
            # Sprawdź czy to liga kalendarzowa (Wiosna-Jesień) lub rozgrywki międzynarodowe
            # Wtedy sezonem jest po prostu ROK (np. 2025)
            is_calendar_league = (
                comp_name in calendar_year_leagues or 
                any(c in comp_name for c in calendar_year_leagues) # Łapie warianty nazw
            )
            
            if is_calendar_league:
                season = str(year)
            elif comp_name in international_comps or any(ic in comp_name for ic in international_comps):
                # Mecze kadry zawsze po roku kalendarzowym
                season = str(year)
                # Nadpisz nazwę dla kadry
                comp_name = f'National Team {season}'
            
            # Klucz do agregacji
            key = (season, comp_name)
            
            # Agregacja
            stats_dict[key]['games'] += 1
            stats_dict[key]['goals'] += match.goals or 0
            stats_dict[key]['assists'] += match.assists or 0
            stats_dict[key]['minutes'] += match.minutes_played or 0
            stats_dict[key]['xg'] += match.xg or 0.0
            stats_dict[key]['xa'] += match.xa or 0.0
            stats_dict[key]['games_starts'] += 1 if (match.minutes_played or 0) > 45 else 0
        
        # Update competition_stats
        updated = 0
        for (season, competition), stats in stats_dict.items():
            record = db.query(CompetitionStats).filter(
                CompetitionStats.player_id == player_id,
                CompetitionStats.season == season,
                CompetitionStats.competition_name == competition
            ).first()
            
            # Use get_competition_type() function
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
        
        # Zapisz zmiany
        db.commit()
        return updated
    
    except Exception as e:
        logger.error(f"Error syncing competition stats for player {player_id}: {e}")
        db.rollback()
        return 0
        
    finally:
        db.close()

def main():
    logger.info("=" * 60)
    logger.info("SYNCHRONIZACJA COMPETITION_STATS Z PLAYER_MATCHES")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        if len(sys.argv) > 1:
            # Sync specific player
            player_name = sys.argv[1]
            player = db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).first()
            
            if not player:
                logger.error(f"? Player not found: {player_name}")
                sys.exit(1)
            
            players = [player]
            logger.info(f"Syncing: {player.name}")
        else:
            # Sync all players
            players = db.query(Player).all()
            logger.info(f"Syncing all players: {len(players)}")
        
        total_updated = 0
        for player in players:
            updated = sync_competition_stats_from_matches(player.id)
            if updated > 0:
                total_updated += updated
                logger.info(f"? {player.name}: {updated} records updated")
        
        logger.info("=" * 60)
        logger.info(f"? SUCCESS: {total_updated} total records updated")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"? Error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    main()


