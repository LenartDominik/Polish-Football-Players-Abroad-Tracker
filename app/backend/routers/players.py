from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from datetime import date
from app.backend.database import get_db
from app.backend.schemas.player import PlayerResponse, PlayerCreate
from app.backend.models.player import Player
from app.backend.models.competition_stats import CompetitionStats
from app.backend.models.goalkeeper_stats import GoalkeeperStats
from app.backend.models.player_match import PlayerMatch
from app.backend.services.cache_manager import CacheManager, generate_cache_key
from app.backend.utils.errors import handle_api_error

logger = logging.getLogger(__name__)

# ... reszta kodu bez zmian ...


router = APIRouter(prefix="/players", tags=["players"])

@router.get("/", response_model=list[PlayerResponse])
def get_all_players(
    db: Session = Depends(get_db),
    name: str | None = None,
    team: str | None = None,
    league: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Zwraca listę piłkarzy z opcjonalnymi filtrami i paginacją to limit payload size."""
    try:
        # Try cache first for common queries
        cache_manager = CacheManager(db)
        cache_key = generate_cache_key("players_list", name=name, team=team, league=league, limit=limit, offset=offset)

        # For small result sets, use cache
        if limit <= 100:
            cached_data = cache_manager.get_sync("players_list", cache_key)
            if cached_data is not None:
                logger.info(f"Cache HIT for players list, returning {len(cached_data)} players")
                return cached_data

        # Cache miss or large query - fetch from database
        query = db.query(Player)
        if name:
            query = query.filter(Player.name.ilike(f"%{name}%"))
        if team:
            query = query.filter(Player.team.ilike(f"%{team}%"))
        if league:
            query = query.filter(Player.league.ilike(f"%{league}%"))
        query = query.order_by(Player.id.asc()).offset(max(offset, 0)).limit(max(min(limit, 1000), 1))
        players = query.all()

        logger.info(f"Returning {len(players)} players (limit={limit}, offset={offset})")

        # Cache small result sets - convert to dict for JSON serialization
        if limit <= 100 and players:
            players_data = [PlayerResponse.model_validate(p).model_dump(mode='json') for p in players]
            cache_manager.set_sync("players_list", cache_key, players_data)

        return players
    except Exception as e:
        handle_api_error(e, context="get_all_players")

@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Zwraca konkretnego piłkarza"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Piłkarz nie znaleziony")
    return player


@router.get("/stats/competition")
def get_all_competition_stats(
    db: Session = Depends(get_db),
    player_id: int | None = None,
    season: str | None = None,
    competition_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """Zwraca statystyki competition_stats z opcjonalnymi filtrami i limitem.
    Domyślnie ogranicza odpowiedź, aby zmniejszyć transfer.
    """
    try:
        query = db.query(CompetitionStats)
        if player_id:
            query = query.filter(CompetitionStats.player_id == player_id)
        if season:
            query = query.filter(CompetitionStats.season == season)
        if competition_type:
            query = query.filter(CompetitionStats.competition_type.ilike(f"%{competition_type}%"))
        query = query.order_by(CompetitionStats.id.desc()).offset(max(offset, 0)).limit(max(min(limit, 1000), 1))
        stats = query.all()
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
                "ga_plus": s.ga_plus,  # Goals + Assists
                "ga_per_90": s.ga_per_90,  # (Goals + Assists) per 90 minutes
                "xg": s.xg,
                "npxg": s.npxg,
                "xa": s.xa,
                "xg_xa": s.xg_xa,  # xG + xA
                "penalty_goals": s.penalty_goals,
                "shots": s.shots,
                "shots_on_target": s.shots_on_target,
                "yellow_cards": s.yellow_cards,
                "red_cards": s.red_cards,
            }
            for s in stats
        ]
    except Exception as e:
        handle_api_error(e, context="get_all_competition_stats")


@router.get("/stats/goalkeeper")
def get_all_goalkeeper_stats(
    db: Session = Depends(get_db),
    player_id: int | None = None,
    season: str | None = None,
    competition_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """Zwraca statystyki goalkeeper_stats z opcjonalnymi filtrami i limitem.
    Domyślnie ogranicza odpowiedź, aby zmniejszyć transfer.
    """
    try:
        query = db.query(GoalkeeperStats)
        if player_id:
            query = query.filter(GoalkeeperStats.player_id == player_id)
        if season:
            query = query.filter(GoalkeeperStats.season == season)
        if competition_type:
            query = query.filter(GoalkeeperStats.competition_type.ilike(f"%{competition_type}%"))
        query = query.order_by(GoalkeeperStats.id.desc()).offset(max(offset, 0)).limit(max(min(limit, 1000), 1))
        stats = query.all()
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
            }
            for s in stats
        ]
    except Exception as e:
        handle_api_error(e, context="get_all_goalkeeper_stats")


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
        handle_api_error(e, context="get_all_matches")

