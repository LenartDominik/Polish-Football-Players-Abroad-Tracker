from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class PlayerMatch(Base):
    """Statystyki gracza z pojedynczego meczu"""
    __tablename__ = "player_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    
    # Informacje o meczu
    match_date = Column(Date, nullable=False, index=True)
    competition = Column(String)  # np. "La Liga", "Champions League"
    round = Column(String)  # np. "Matchweek 12", "Group Stage MD 4"
    venue = Column(String)  # "Home" lub "Away"
    opponent = Column(String)  # Przeciwnik
    result = Column(String)  # "W 3-1", "L 0-2", "D 1-1"
    
    # Statystyki podstawowe
    minutes_played = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    
    # Statystyki zaawansowane
    xg = Column(Float)
    xa = Column(Float)
    passes_completed = Column(Integer, default=0)
    passes_attempted = Column(Integer, default=0)
    pass_completion_pct = Column(Float)
    key_passes = Column(Integer, default=0)
    
    # Obrona
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    blocks = Column(Integer, default=0)
    
    # Posiadanie
    touches = Column(Integer, default=0)
    dribbles_completed = Column(Integer, default=0)
    carries = Column(Integer, default=0)
    
    # Różne
    fouls_committed = Column(Integer, default=0)
    fouls_drawn = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)

    # Data source: 'rapidapi'
    data_source = Column(String, nullable=False, default='rapidapi', index=True)
    
    # Relacja
    player = relationship("Player", back_populates="matches")
    
    # Unique constraint - prevent duplicate matches
    __table_args__ = (
        UniqueConstraint(
            'player_id', 
            'match_date', 
            'competition', 
            'opponent',
            name='uq_player_match'
        ),
    )
