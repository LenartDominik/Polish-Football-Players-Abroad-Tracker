from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.player import PlayerResponse, PlayerCreate
from ..models.player import Player
from ..models.competition_stats import CompetitionStats
from ..models.goalkeeper_stats import GoalkeeperStats
from ..models.player_match import PlayerMatch
from datetime import date
import logging


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/", response_model=list[PlayerResponse])
def get_all_players(db: Session = Depends(get_db)):
    """Zwraca wszystkich piłkarzy z bazy"""
    try:
        players = db.query(Player).all()
        logger.info(f"Found {len(players)} players in database")
        if players:
            logger.info(f"First player: id={players[0].id}, name={players[0].name}, api_id={players[0].api_id}")
        return players
    except Exception as e:
        logger.error(f"Error getting players: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Zwraca konkretnego piłkarza"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Piłkarz nie znaleziony")
    return player


@router.get("/stats/competition")
def get_all_competition_stats(db: Session = Depends(get_db)):
    """Zwraca wszystkie statystyki competition_stats"""
    try:
        stats = db.query(CompetitionStats).all()
        return [
            {
                "id": s.id,
                "player_id": s.player_id,
                "season": s.season,
                "competition_type": s.competition_type,
                "competition_name": s.competition_name,
                "games": s.games,
                "games_starts": s.games_starts,
                "minutes": s.minutes,
                "goals": s.goals,
                "assists": s.assists,
                "xg": s.xg,
                "npxg": s.npxg,
                "xa": s.xa,
                "penalty_goals": s.penalty_goals,
                "shots": s.shots,
                "shots_on_target": s.shots_on_target,
                "yellow_cards": s.yellow_cards,
                "red_cards": s.red_cards,
            }
            for s in stats
        ]
    except Exception as e:
        logger.error(f"Error getting competition stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/goalkeeper")
def get_all_goalkeeper_stats(db: Session = Depends(get_db)):
    """Zwraca wszystkie statystyki goalkeeper_stats"""
    try:
        stats = db.query(GoalkeeperStats).all()
        return [
            {
                "id": s.id,
                "player_id": s.player_id,
                "season": s.season,
                "competition_type": s.competition_type,
                "competition_name": s.competition_name,
                "games": s.games,
                "games_starts": s.games_starts,
                "minutes": s.minutes,
                "goals_against": s.goals_against,
                "goals_against_per90": s.goals_against_per90,
                "shots_on_target_against": s.shots_on_target_against,
                "saves": s.saves,
                "save_percentage": s.save_percentage,
                "clean_sheets": s.clean_sheets,
                "clean_sheet_percentage": s.clean_sheet_percentage,
                "wins": s.wins,
                "draws": s.draws,
                "losses": s.losses,
                "penalties_attempted": s.penalties_attempted,
                "penalties_allowed": s.penalties_allowed,
                "penalties_saved": s.penalties_saved,
                "penalties_missed": s.penalties_missed,
                "post_shot_xg": s.post_shot_xg,
            }
            for s in stats
        ]
    except Exception as e:
        logger.error(f"Error getting goalkeeper stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/matches")
def get_all_matches(db: Session = Depends(get_db)):
    """Zwraca wszystkie mecze z player_matches"""
    try:
        matches = db.query(PlayerMatch).all()
        return [
            {
                "id": m.id,
                "player_id": m.player_id,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "competition": m.competition,
                "round": m.round,
                "venue": m.venue,
                "opponent": m.opponent,
                "result": m.result,
                "minutes_played": m.minutes_played,
                "goals": m.goals,
                "assists": m.assists,
                "shots": m.shots,
                "shots_on_target": m.shots_on_target,
                "xg": m.xg,
                "xa": m.xa,
                "passes_completed": m.passes_completed,
                "passes_attempted": m.passes_attempted,
                "pass_completion_pct": m.pass_completion_pct,
                "key_passes": m.key_passes,
                "tackles": m.tackles,
                "interceptions": m.interceptions,
                "blocks": m.blocks,
                "touches": m.touches,
                "dribbles_completed": m.dribbles_completed,
                "carries": m.carries,
                "fouls_committed": m.fouls_committed,
                "fouls_drawn": m.fouls_drawn,
                "yellow_cards": m.yellow_cards,
                "red_cards": m.red_cards,
            }
            for m in matches
        ]
    except Exception as e:
        logger.error(f"Error getting matches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OLD ENDPOINTS REMOVED
# ============================================================================
# The following endpoints have been removed as they used deprecated services:
# 
# 1. API-Football integration (football_api.py):
#    - GET /sync/api - Synchronized players from API-Football
#
# 2. Player season stats table (deprecated):
#    - POST /{player_id}/sync/current-season
#    - GET /fbref/search/{player_name}
#    - POST /fbref/sync/{player_name}
#    - POST /fbref/sync-all
#
# These have been replaced by:
# - sync_playwright.py (for individual player sync)
# - sync_all_playwright.py (for bulk sync)
# These scripts write directly to competition_stats and goalkeeper_stats tables.
#
# See CLEANUP_OLD_ENDPOINTS.md for details.

