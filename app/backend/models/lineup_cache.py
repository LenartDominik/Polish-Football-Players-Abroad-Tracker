"""
Cache for lineup data to avoid repeated API calls.

Stores: player appearances in matches with minutes played.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class LineupCache(Base):
    """
    Cache table for player match appearances from lineups.

    Reduces API calls by storing lineup data.
    """
    __tablename__ = "lineup_cache"

    id = Column(Integer, primary_key=True, index=True)
    player_api_id = Column(Integer, nullable=False, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    minutes = Column(Integer, default=0)
    updated_at = Column(DateTime, nullable=False)

    # Data source: 'rapidapi'
    data_source = Column(String, nullable=False, default='rapidapi', index=True)

    # Constraint: one record per player per match
    __table_args__ = (
        UniqueConstraint('player_api_id', 'event_id',
                         name='uq_player_event_lineup'),
    )

    def __repr__(self):
        return f"<LineupCache player={self.player_api_id} event={self.event_id} min={self.minutes}>"
