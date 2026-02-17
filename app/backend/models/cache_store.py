"""
Cache Store Model for Enhanced Caching

Stores API responses with TTL for different cache types.
Reduces API calls and improves performance.
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base


class CacheStore(Base):
    """
    Generic cache store for API responses

    Cache types:
    - lineup: Player match lineups (24h TTL)
    - squad: Team squad data (6h TTL)
    - match: Match details (1h TTL)
    - player: Player details (12h TTL)
    """
    __tablename__ = "cache_store"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(500), nullable=False, unique=True, index=True)
    cache_type = Column(String(50), nullable=False, index=True)  # lineup, squad, match, player
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    hits = Column(Integer, default=0)

    def __repr__(self):
        return f"<CacheStore type={self.cache_type} key={self.cache_key} expires={self.expires_at}>"
