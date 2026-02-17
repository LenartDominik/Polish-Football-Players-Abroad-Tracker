"""
Live Match API Router

Endpoints for tracking live matches and today's matches
featuring Polish players.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.backend.database import get_db
from app.backend.utils.errors import handle_api_error
from app.backend.services.live_match_tracker import (
    get_live_summary,
    get_team_live_matches,
    LiveMatchTracker
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["Live Matches"])


@router.get("/today")
async def get_today_summary(db: Session = Depends(get_db)):
    """
    Get summary of live matches and today's matches with Polish players

    Returns:
        Summary with live matches, today's matches, and player counts
    """
    try:
        summary = await get_live_summary(db)
        return summary
    except Exception as e:
        handle_api_error(e, context="get_today_summary")


@router.get("/team/{team_name}")
async def get_team_matches(team_name: str, db: Session = Depends(get_db)):
    """
    Get live matches for a specific team

    Args:
        team_name: Team name (partial match supported)

    Returns:
        List of live matches for this team
    """
    try:
        matches = await get_team_live_matches(db, team_name)
        return {
            "team": team_name,
            "live_matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        handle_api_error(e, context="get_team_matches")


@router.get("/live")
async def get_live_matches_only(db: Session = Depends(get_db)):
    """
    Get only currently live matches with Polish players

    Returns:
        List of live matches
    """
    try:
        tracker = LiveMatchTracker(db)
        matches = await tracker.get_live_matches_with_polish_players()
        return {
            "live_matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        handle_api_error(e, context="get_live_matches_only")


@router.get("/scheduled")
async def get_scheduled_today(db: Session = Depends(get_db)):
    """
    Get only scheduled matches for today (not live yet)

    Returns:
        List of today's scheduled matches
    """
    try:
        tracker = LiveMatchTracker(db)
        matches = await tracker.get_matches_today()

        # Filter out live matches
        scheduled = [
            m for m in matches
            if m.get("status") not in ["Live", "In Progress", "Halftime", "HT"]
        ]

        return {
            "scheduled_matches": scheduled,
            "count": len(scheduled)
        }
    except Exception as e:
        handle_api_error(e, context="get_scheduled_today")


@router.get("/player/{player_id}")
async def check_player_today(player_id: int, db: Session = Depends(get_db)):
    """
    Check if a specific player is playing today

    Args:
        player_id: Player database ID

    Returns:
        Player match info for today
    """
    try:
        tracker = LiveMatchTracker(db)
        result = await tracker.check_player_playing_today(player_id)
        return result
    except Exception as e:
        handle_api_error(e, context=f"check_player_today (player_id={player_id})")
