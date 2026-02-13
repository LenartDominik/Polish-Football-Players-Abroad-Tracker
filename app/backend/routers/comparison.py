from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from typing import List, Optional
from app.backend.config import settings

DATABASE_URL = settings.database_url

router = APIRouter(prefix="/comparison", tags=["comparison"])

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@router.get("/players/{player_id}/stats")
async def get_player_stats(player_id: int, season: Optional[str] = None):
    """
    Gets all statistics for a single player
    """
    db = SessionLocal()
    try:
        params = {"player_id": player_id}

        query_str = """
        SELECT
            p.name,
            p.position,
            p.team,
            p.league,
            cs.season,
            SUM(cs.games) AS matches,
            SUM(cs.goals) AS goals,
            SUM(cs.assists) AS assists,
            SUM(cs.yellow_cards) AS yellow_cards,
            SUM(cs.red_cards) AS red_cards,
            SUM(cs.minutes) AS minutes_played,
            SUM(cs.xg) AS "xG",
            SUM(cs.xa) AS "xA",
            SUM(cs.games_starts) AS games_starts
        FROM players p
        LEFT JOIN competition_stats cs ON p.id = cs.player_id
        WHERE p.id = :player_id
        """

        if season:
            query_str += " AND cs.season = :season"
            params["season"] = season

        query_str += " GROUP BY p.name, p.position, p.team, p.league, cs.season"

        result = pd.read_sql(text(query_str), db.bind, params=params)

        if result.empty:
            raise HTTPException(status_code=404, detail="Player not found")

        return result.to_dict(orient="records")

    finally:
        db.close()


@router.get("/compare")
async def compare_players(
    player1_id: int = Query(..., description="ID of first player"),
    player2_id: int = Query(..., description="ID of second player"),
    season: Optional[str] = Query(None, description="Season to compare (e.g. 2025-26)"),
    stats: Optional[List[str]] = Query(
        None, 
        description="List of statistics to compare (default: all)"
    )
):
    """
    Compares statistics of two players.
    Goalkeepers can only be compared with other goalkeepers.
    Field players can only be compared with other field players.
    """
    db = SessionLocal()
    try:
        # First, check positions of both players
        position_query = """
        SELECT id, name, position
        FROM players
        WHERE id IN (:player1_id, :player2_id)
        """
        
        positions_df = pd.read_sql(
            text(position_query), 
            db.bind, 
            params={"player1_id": player1_id, "player2_id": player2_id}
        )
        
        if len(positions_df) < 2:
            raise HTTPException(
                status_code=404,
                detail="One or both players not found"
            )
        
        player1_pos = positions_df[positions_df['id'] == player1_id]['position'].values[0]
        player2_pos = positions_df[positions_df['id'] == player2_id]['position'].values[0]
        
        # Check if goalkeeper - handle both "GK" and "Goalkeeper"
        is_player1_gk = player1_pos in ["Goalkeeper", "GK"] if player1_pos else False
        is_player2_gk = player2_pos in ["Goalkeeper", "GK"] if player2_pos else False
        
        # Check if trying to compare goalkeeper with field player
        if is_player1_gk != is_player2_gk:
            raise HTTPException(
                status_code=400,
                detail="Goalkeepers can only be compared with other goalkeepers. Please select two goalkeepers or two field players."
            )
        
        # If both are goalkeepers, use goalkeeper_stats table
        if is_player1_gk and is_player2_gk:
            query = """
SELECT 
    p.id,
    p.name,
    p.position,
    p.team,
    p.league,
    SUM(gs.games) AS matches,
    SUM(gs.games_starts) AS games_starts,
    SUM(gs.minutes) AS minutes_played,
    SUM(gs.goals_against) AS goals_against,
    ROUND(CAST(AVG(gs.goals_against_per90) AS NUMERIC), 2) AS goals_against_per90,
    SUM(gs.shots_on_target_against) AS shots_on_target_against,
    SUM(gs.saves) AS saves,
    ROUND(CAST(AVG(gs.save_percentage) AS NUMERIC), 2) AS save_percentage,
    SUM(gs.clean_sheets) AS clean_sheets,
    ROUND(CAST(AVG(gs.clean_sheet_percentage) AS NUMERIC), 2) AS clean_sheet_percentage,
    SUM(gs.wins) AS wins,
    SUM(gs.draws) AS draws,
    SUM(gs.losses) AS losses,
    COALESCE(SUM(gs.penalties_attempted), 0) AS penalties_attempted,
    COALESCE(SUM(gs.penalties_allowed), 0) AS penalties_allowed,
    COALESCE(SUM(gs.penalties_saved), 0) AS penalties_saved,
    COALESCE(SUM(gs.penalties_missed), 0) AS penalties_missed
FROM players p
INNER JOIN goalkeeper_stats gs ON p.id = gs.player_id
WHERE p.id IN (:player1_id, :player2_id)
    AND gs.competition_type = 'LEAGUE'
"""
        else:
            # For field players, use competition_stats table
            # G+A/90 - ONLY with actual minutes (NO estimation)
            query = """
SELECT 
    p.id,
    p.name,
    p.position,
    p.team,
    p.league,
    SUM(cs.games) AS matches,
    SUM(cs.goals) AS goals,
    SUM(cs.assists) AS assists,
    SUM(cs.yellow_cards) AS yellow_cards,
    SUM(cs.red_cards) AS red_cards,
    SUM(cs.minutes) AS minutes_played,
    SUM(cs.xg) AS "xG",
    SUM(cs.xa) AS "xA",
    SUM(cs.games_starts) AS games_starts,
    CASE 
        WHEN SUM(cs.minutes) > 0 
        THEN ROUND(CAST((SUM(cs.goals) + SUM(cs.assists)) * 90.0 / SUM(cs.minutes) AS NUMERIC), 2)
        ELSE NULL
    END AS "G+A_per_90"
FROM players p
INNER JOIN competition_stats cs ON p.id = cs.player_id
WHERE p.id IN (:player1_id, :player2_id)
    AND cs.competition_type = 'LEAGUE'
"""

        params = {
            "player1_id": player1_id,
            "player2_id": player2_id
        }

        if season:
            query += " AND " + ("gs" if is_player1_gk else "cs") + ".season = :season"
            params["season"] = season
        else:
            # Use latest season (2025-2026 or 2025) - default for comparison, ONLY LEAGUE stats
            query += " AND " + ("gs" if is_player1_gk else "cs") + ".season IN ('2025-2026', '2025/2026', '2025')"

        # Group by player info only (not season) to sum all LEAGUE games from that season
        query += " GROUP BY p.id, p.name, p.position, p.team, p.league"

        df = pd.read_sql(text(query), db.bind, params=params)
        
        # Replace NaN with None for JSON serialization
        import numpy as np
        df = df.replace({np.nan: None})

        if df.empty or len(df) < 2:
            raise HTTPException(
                status_code=404, 
                detail="Data not found for one or both players"
            )
        
        if stats:
            available_cols = ['id', 'name', 'position', 'team', 'league'] + stats
            df = df[[col for col in available_cols if col in df.columns]]

        return {
            "player1": df[df['id'] == player1_id].to_dict(orient="records")[0],
            "player2": df[df['id'] == player2_id].to_dict(orient="records")[0],
            "comparison_date": pd.Timestamp.now().isoformat(),
            "player_type": "goalkeeper" if is_player1_gk else "field_player"
        }
    
    finally:
        db.close()


@router.get("/available-stats")
async def get_available_stats(player_type: Optional[str] = Query(None, description="Player type: 'goalkeeper' or 'field_player'")):
    """
    Returns list of available statistics for comparison.
    Different stats are returned for goalkeepers vs field players.
    """
    if player_type == "goalkeeper":
        return {
            "goalkeeper_specific": [
                {"key": "saves", "label": "Saves", "type": "count"},
                {"key": "save_percentage", "label": "Save %", "type": "percentage"},
                {"key": "clean_sheets", "label": "Clean Sheets", "type": "count"},
                {"key": "clean_sheet_percentage", "label": "Clean Sheet %", "type": "percentage"},
                {"key": "goals_against", "label": "Goals Against", "type": "count"},
                {"key": "goals_against_per90", "label": "Goals Against per 90", "type": "decimal"},
                {"key": "shots_on_target_against", "label": "Shots on Target Against", "type": "count"}
            ],
            "penalties": [
                {"key": "penalties_attempted", "label": "Penalties Attempted", "type": "count"},
                {"key": "penalties_saved", "label": "Penalties Saved", "type": "count"},
                {"key": "penalties_allowed", "label": "Penalties Allowed", "type": "count"},
                {"key": "penalties_missed", "label": "Penalties Missed", "type": "count"}
            ],
            "performance": [
                {"key": "wins", "label": "Wins", "type": "count"},
                {"key": "draws", "label": "Draws", "type": "count"},
                {"key": "losses", "label": "Losses", "type": "count"}
            ],
            "general": [
                {"key": "matches", "label": "Matches Played", "type": "count"},
                {"key": "games_starts", "label": "Games Started", "type": "count"},
                {"key": "minutes_played", "label": "Minutes Played", "type": "count"}
            ]
        }
    else:
        # Default for field players
        return {
            "offensive": [
                {"key": "goals", "label": "Goals", "type": "count"},
                {"key": "assists", "label": "Assists", "type": "count"},
                {"key": "G+A_per_90", "label": "G+A per 90", "type": "decimal"},
                {"key": "xG", "label": "Expected Goals (xG)", "type": "decimal"},
                {"key": "xA", "label": "Expected Assists (xA)", "type": "decimal"}
            ],
            "defensive": [
                {"key": "yellow_cards", "label": "Yellow Cards", "type": "count"},
                {"key": "red_cards", "label": "Red Cards", "type": "count"}
            ],
            "general": [
                {"key": "matches", "label": "Matches Played", "type": "count"},
                {"key": "games_starts", "label": "Games Started", "type": "count"}
            ]
        }
