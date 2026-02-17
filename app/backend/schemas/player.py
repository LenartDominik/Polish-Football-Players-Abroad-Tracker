# Schemas for Player API - Updated 2026-02-17
from pydantic import BaseModel
from datetime import date
from typing import Optional, Union


class PlayerBase(BaseModel):
    name: str
    team: str
    league: str
    nationality: str = "Poland"
    position: Optional[str] = None


class PlayerCreate(PlayerBase):
    rapidapi_player_id: Optional[int] = None
    rapidapi_team_id: Optional[int] = None


class PlayerResponse(PlayerBase):
    id: int
    rapidapi_player_id: Optional[int] = None
    rapidapi_team_id: Optional[int] = None
    last_updated: Optional[date] = None
    level: int = 2
    data_source: str = "rapidapi"
    
    class Config:
        from_attributes = True

