# app/backend/models/goalkeeper_stats.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base
from .competition_stats import CompetitionType


class GoalkeeperStats(Base):
    """
    Statystyki bramkarskie w podziale na rozgrywki
    """
    __tablename__ = "goalkeeper_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    season = Column(String, nullable=False)
    competition_type = Column(String, nullable=False)
    competition_name = Column(String, nullable=False)
    
    # Podstawowe statystyki bramkarskie
    games = Column(Integer, default=0)
    games_starts = Column(Integer, default=0)
    minutes = Column(Integer, default=0)
    
    goals_against = Column(Integer, default=0)
    goals_against_per90 = Column(Float, default=0.0)
    shots_on_target_against = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    save_percentage = Column(Float, default=0.0)
    
    clean_sheets = Column(Integer, default=0)
    clean_sheet_percentage = Column(Float, default=0.0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    
    penalties_attempted = Column(Integer, default=0)
    penalties_allowed = Column(Integer, default=0)
    penalties_saved = Column(Integer, default=0)
    penalties_missed = Column(Integer, default=0)
    
    post_shot_xg = Column(Float, default=0.0)

    # Data source: 'rapidapi'
    data_source = Column(String, nullable=False, default='rapidapi', index=True)
    
    # Relacje
    player = relationship("Player", back_populates="goalkeeper_stats")
    
    # Unikalne ograniczenie na sezon, typ rozgrywek itd.
    __table_args__ = (
        UniqueConstraint('player_id', 'season', 'competition_type', 'competition_name',
                         name='uq_gk_player_season_competition'),
    )
    
    def __repr__(self):
        return f"<GoalkeeperStats player_id={self.player_id} season={self.season} competition={self.competition_name}>"


