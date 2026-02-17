# app/backend/models/player.py
import logging
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from ..database import Base

logger = logging.getLogger(__name__)


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    team = Column(String)
    league = Column(String)
    nationality = Column(String)
    position = Column(String, nullable=True)
    last_updated = Column(Date)

    # RapidAPI IDs for new API-based sync
    rapidapi_player_id = Column(Integer, nullable=True, index=True)
    rapidapi_team_id = Column(Integer, nullable=True, index=True)

    # Competition level: 1 = Top leagues (2x/week sync), 2 = Lower leagues (1x/week sync)
    # Top leagues: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Süper Lig
    level = Column(Integer, default=2, nullable=False)

    # Data source: 'rapidapi'
    data_source = Column(String, nullable=False, default='rapidapi', index=True)

    # Relacje - istniejące
    season_stats = relationship(
        "PlayerSeasonStats", 
        back_populates="player", 
        cascade="all, delete-orphan"
    )
    
    matches = relationship(
        "PlayerMatch", 
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    # Relacje - NOWE dla statystyk z podziałem na rozgrywki
    competition_stats = relationship(
        "CompetitionStats", 
        back_populates="player", 
        cascade="all, delete-orphan"
    )
    
    goalkeeper_stats = relationship(
        "GoalkeeperStats", 
        back_populates="player", 
        cascade="all, delete-orphan"
    )
    
    # Property pomocnicza
    @property
    def is_goalkeeper(self):
        """Sprawdza czy gracz jest bramkarzem"""
        if not self.position:
            return False
        return 'GK' in self.position.upper() or 'GOALKEEPER' in self.position.upper()
    
    def __repr__(self):
        return f"<Player {self.name} ({self.position}) - {self.team}>"

