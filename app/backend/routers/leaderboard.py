"""
Leaderboard API Router
Get top players (goals, assists, rating) by league from RapidAPI
"""
import asyncio
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.backend.services.rapidapi_client import RapidAPIClient, LEAGUE_IDS

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


class TopPlayer(BaseModel):
    """Top player in leaderboard"""
    rank: int
    player_id: int
    name: str
    team: str
    team_id: Optional[int] = None
    position: Optional[str] = None
    value: float  # goals, assists, or rating
    nationality: Optional[str] = None


class LeaderboardResponse(BaseModel):
    """Leaderboard response"""
    league_name: str
    league_id: int
    category: str  # "goals", "assists", "rating"
    players: List[TopPlayer]


@router.get("/goals/{league_name}", response_model=LeaderboardResponse)
async def get_top_scorers(league_name: str) -> LeaderboardResponse:
    """
    Get top scorers (goals) for a league

    Available leagues:
    - Premier League
    - La Liga
    - Bundesliga
    - Serie A
    - Ligue 1
    - Eredivisie
    - Primeira Liga
    - Champions League
    - Europa League
    - Conference League
    """
    # Normalize league name
    league_name_normalized = league_name.replace("-", " ").replace("_", " ").title()

    league_id = LEAGUE_IDS.get(league_name_normalized)
    if not league_id:
        raise HTTPException(
            status_code=404,
            detail=f"League '{league_name}' not found. Available: {list(LEAGUE_IDS.keys())}"
        )

    async with RapidAPIClient() as client:
        data = await client.get_top_players_by_goals(league_id)

        if not data:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch data from RapidAPI"
            )

        # Parse response into TopPlayer models
        players = []
        for rank, player in enumerate(data[:20], start=1):  # Top 20
            # Handle different response structures
            player_id = player.get("id") or player.get("player_id") or player.get("player", {}).get("id")
            name = player.get("name") or player.get("player", {}).get("name")
            team = player.get("team") or player.get("team_name") or player.get("team", {}).get("name")
            team_id = player.get("team_id") or player.get("team", {}).get("id")
            position = player.get("position") or player.get("player", {}).get("position")
            goals = player.get("goals") or player.get("total_goals") or 0

            players.append(TopPlayer(
                rank=rank,
                player_id=player_id,
                name=name,
                team=team,
                team_id=team_id,
                position=position,
                value=float(goals),
                nationality=player.get("nationality")
            ))

        return LeaderboardResponse(
            league_name=league_name_normalized,
            league_id=league_id,
            category="goals",
            players=players
        )


@router.get("/assists/{league_name}", response_model=LeaderboardResponse)
async def get_top_assists(league_name: str) -> LeaderboardResponse:
    """
    Get top assist providers for a league

    Available leagues: see /goals/{league_name}
    """
    league_name_normalized = league_name.replace("-", " ").replace("_", " ").title()

    league_id = LEAGUE_IDS.get(league_name_normalized)
    if not league_id:
        raise HTTPException(
            status_code=404,
            detail=f"League '{league_name}' not found. Available: {list(LEAGUE_IDS.keys())}"
        )

    async with RapidAPIClient() as client:
        data = await client.get_top_players_by_assists(league_id)

        if not data:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch data from RapidAPI"
            )

        players = []
        for rank, player in enumerate(data[:20], start=1):
            player_id = player.get("id") or player.get("player_id") or player.get("player", {}).get("id")
            name = player.get("name") or player.get("player", {}).get("name")
            team = player.get("team") or player.get("team_name") or player.get("team", {}).get("name")
            team_id = player.get("team_id") or player.get("team", {}).get("id")
            position = player.get("position") or player.get("player", {}).get("position")
            assists = player.get("assists") or player.get("total_assists") or 0

            players.append(TopPlayer(
                rank=rank,
                player_id=player_id,
                name=name,
                team=team,
                team_id=team_id,
                position=position,
                value=float(assists),
                nationality=player.get("nationality")
            ))

        return LeaderboardResponse(
            league_name=league_name_normalized,
            league_id=league_id,
            category="assists",
            players=players
        )


@router.get("/rating/{league_name}", response_model=LeaderboardResponse)
async def get_top_rated(league_name: str) -> LeaderboardResponse:
    """
    Get top rated players for a league

    Available leagues: see /goals/{league_name}
    """
    league_name_normalized = league_name.replace("-", " ").replace("_", " ").title()

    league_id = LEAGUE_IDS.get(league_name_normalized)
    if not league_id:
        raise HTTPException(
            status_code=404,
            detail=f"League '{league_name}' not found. Available: {list(LEAGUE_IDS.keys())}"
        )

    async with RapidAPIClient() as client:
        data = await client.get_top_players_by_rating(league_id)

        if not data:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch data from RapidAPI"
            )

        players = []
        for rank, player in enumerate(data[:20], start=1):
            player_id = player.get("id") or player.get("player_id") or player.get("player", {}).get("id")
            name = player.get("name") or player.get("player", {}).get("name")
            team = player.get("team") or player.get("team_name") or player.get("team", {}).get("name")
            team_id = player.get("team_id") or player.get("team", {}).get("id")
            position = player.get("position") or player.get("player", {}).get("position")
            rating = player.get("rating") or player.get("avg_rating") or 0.0

            players.append(TopPlayer(
                rank=rank,
                player_id=player_id,
                name=name,
                team=team,
                team_id=team_id,
                position=position,
                value=float(rating),
                nationality=player.get("nationality")
            ))

        return LeaderboardResponse(
            league_name=league_name_normalized,
            league_id=league_id,
            category="rating",
            players=players
        )


@router.get("/all/{league_name}")
async def get_all_leaderboards(league_name: str):
    """
    Get all leaderboards (goals, assists, rating) for a league in one request
    """
    league_name_normalized = league_name.replace("-", " ").replace("_", " ").title()

    league_id = LEAGUE_IDS.get(league_name_normalized)
    if not league_id:
        raise HTTPException(
            status_code=404,
            detail=f"League '{league_name}' not found. Available: {list(LEAGUE_IDS.keys())}"
        )

    async with RapidAPIClient() as client:
        # Fetch all three leaderboards in parallel
        goals, assists, rating = await asyncio.gather(
            client.get_top_players_by_goals(league_id),
            client.get_top_players_by_assists(league_id),
            client.get_top_players_by_rating(league_id),
            return_exceptions=True
        )

        # Handle any exceptions
        if isinstance(goals, Exception):
            goals = []
        if isinstance(assists, Exception):
            assists = []
        if isinstance(rating, Exception):
            rating = []

        return {
            "league_name": league_name_normalized,
            "league_id": league_id,
            "top_scorers": goals or [],
            "top_assists": assists or [],
            "top_rated": rating or []
        }


@router.get("/leagues")
async def get_available_leagues():
    """Get list of available leagues for leaderboard"""
    return {
        "leagues": [
            {"name": name, "id": league_id}
            for name, league_id in LEAGUE_IDS.items()
        ]
    }
