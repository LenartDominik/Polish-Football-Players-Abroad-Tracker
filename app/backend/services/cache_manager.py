"""
Enhanced Cache Manager for RapidAPI

Provides multi-layer caching to reduce API calls and improve performance.

Cache TTL (Time To Live) settings:
- Lineups: 12 hours (match data doesn't change frequently)
- Team Squads: 6 hours (squad changes infrequently)
- Match Details: 1 hour (for non-live matches)
- Match Live: 5 minutes (for live/ongoing matches)
- Player Details: 12 hours
- Players List: 1 hour (for /api/players/ endpoint)
- League Teams: 24 hours

Usage:
    cache = CacheManager(db)
    data = await cache.get_or_fetch("lineup", "event_12345", fetch_function)
    # Or for non-async endpoints:
    data = cache.get_sync("lineup", "event_12345")
"""
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.backend.models.cache_store import CacheStore

logger = logging.getLogger(__name__)


# Cache TTL settings (in hours)
# For live matches, use fraction: 0.08 = 5 minutes, 0.25 = 15 minutes
CACHE_TTL = {
    "lineup": 12,  # Reduced from 24h - more frequent updates for match data
    "squad": 6,
    "match": 1,
    "match_live": 0.08,  # 5 minutes for live matches
    "player": 12,
    "players_list": 1,  # 1 hour for players list endpoint
    "league_teams": 24,
}


class CacheManager:
    """Enhanced cache manager for API responses"""

    def __init__(self, db: Session):
        """
        Initialize cache manager

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def get(self, cache_type: str, cache_key: str) -> Optional[Dict]:
        """
        Get cached data if valid (not expired)

        Args:
            cache_type: Type of cache (lineup, squad, match, player, etc.)
            cache_key: Unique key for the cached item

        Returns:
            Cached data dict, or None if not found/expired
        """
        now = datetime.now()

        cached = self.db.query(CacheStore).filter(
            and_(
                CacheStore.cache_key == cache_key,
                CacheStore.cache_type == cache_type,
                CacheStore.expires_at > now
            )
        ).first()

        if cached:
            # Update hit counter
            cached.hits += 1
            self.db.commit()

            self.stats["hits"] += 1
            logger.debug(f"✅ Cache HIT: {cache_type}:{cache_key}")

            return cached.data

        self.stats["misses"] += 1
        logger.debug(f"❌ Cache MISS: {cache_type}:{cache_key}")

        return None

    async def set(
        self,
        cache_type: str,
        cache_key: str,
        data: Any,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Store data in cache

        Args:
            cache_type: Type of cache
            cache_key: Unique key for the cached item
            data: Data to cache (will be JSON serialized)
            ttl_hours: Custom TTL in hours (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        # Use default TTL for cache type if not specified
        if ttl_hours is None:
            ttl_hours = CACHE_TTL.get(cache_type, 1)

        now = datetime.now()
        expires_at = now + timedelta(hours=ttl_hours)

        # Check if entry already exists
        existing = self.db.query(CacheStore).filter(
            CacheStore.cache_key == cache_key
        ).first()

        if existing:
            # Update existing entry
            existing.data = data
            existing.expires_at = expires_at
            existing.created_at = now
            logger.debug(f"🔄 Cache UPDATED: {cache_type}:{cache_key} (TTL: {ttl_hours}h)")
        else:
            # Create new entry
            new_cache = CacheStore(
                cache_key=cache_key,
                cache_type=cache_type,
                data=data,
                created_at=now,
                expires_at=expires_at
            )
            self.db.add(new_cache)
            logger.debug(f"➕ Cache CREATED: {cache_type}:{cache_key} (TTL: {ttl_hours}h)")

        try:
            self.db.commit()
            self.stats["sets"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            self.db.rollback()
            return False

    async def get_or_fetch(
        self,
        cache_type: str,
        cache_key: str,
        fetch_func: Callable,
        ttl_hours: Optional[int] = None,
        *args,
        **kwargs
    ) -> Optional[Dict]:
        """
        Get from cache, or fetch and cache if miss

        Args:
            cache_type: Type of cache
            cache_key: Unique key for the cached item
            fetch_func: Async function to call if cache miss
            ttl_hours: Custom TTL in hours
            *args, **kwargs: Arguments to pass to fetch_func

        Returns:
            Data from cache or fetch function
        """
        # Try cache first
        cached_data = await self.get(cache_type, cache_key)

        if cached_data is not None:
            return cached_data

        # Cache miss - fetch data
        logger.info(f"📡 Fetching fresh data for {cache_type}:{cache_key}")

        try:
            fresh_data = await fetch_func(*args, **kwargs)

            if fresh_data is not None:
                # Store in cache
                await self.set(cache_type, cache_key, fresh_data, ttl_hours)

            return fresh_data

        except Exception as e:
            logger.error(f"Failed to fetch data for {cache_type}:{cache_key}: {e}")
            return None

    # ========================================================================
    # SYNC METHODS (for non-async endpoints)
    # ========================================================================

    def get_sync(self, cache_type: str, cache_key: str) -> Optional[Dict]:
        """
        Get cached data if valid (not expired) - Synchronous version.

        Args:
            cache_type: Type of cache (lineup, squad, match, player, etc.)
            cache_key: Unique key for the cached item

        Returns:
            Cached data dict, or None if not found/expired
        """
        now = datetime.now()

        cached = self.db.query(CacheStore).filter(
            and_(
                CacheStore.cache_key == cache_key,
                CacheStore.cache_type == cache_type,
                CacheStore.expires_at > now
            )
        ).first()

        if cached:
            # Update hit counter
            cached.hits += 1
            self.db.commit()

            self.stats["hits"] += 1
            logger.debug(f"✅ Cache HIT (sync): {cache_type}:{cache_key}")

            return cached.data

        self.stats["misses"] += 1
        logger.debug(f"❌ Cache MISS (sync): {cache_type}:{cache_key}")

        return None

    def set_sync(
        self,
        cache_type: str,
        cache_key: str,
        data: Any,
        ttl_hours: Optional[float] = None
    ) -> bool:
        """
        Store data in cache - Synchronous version.

        Args:
            cache_type: Type of cache
            cache_key: Unique key for the cached item
            data: Data to cache (will be JSON serialized)
            ttl_hours: Custom TTL in hours (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        # Use default TTL for cache type if not specified
        if ttl_hours is None:
            ttl_hours = CACHE_TTL.get(cache_type, 1)

        now = datetime.now()
        expires_at = now + timedelta(hours=ttl_hours)

        # Check if entry already exists
        existing = self.db.query(CacheStore).filter(
            CacheStore.cache_key == cache_key
        ).first()

        if existing:
            # Update existing entry
            existing.data = data
            existing.expires_at = expires_at
            existing.created_at = now
            logger.debug(f"🔄 Cache UPDATED (sync): {cache_type}:{cache_key} (TTL: {ttl_hours}h)")
        else:
            # Create new entry
            new_cache = CacheStore(
                cache_key=cache_key,
                cache_type=cache_type,
                data=data,
                created_at=now,
                expires_at=expires_at
            )
            self.db.add(new_cache)
            logger.debug(f"➕ Cache CREATED (sync): {cache_type}:{cache_key} (TTL: {ttl_hours}h)")

        try:
            self.db.commit()
            self.stats["sets"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            self.db.rollback()
            return False

    def get_or_fetch_sync(
        self,
        cache_type: str,
        cache_key: str,
        fetch_func: Callable,
        ttl_hours: Optional[float] = None,
        *args,
        **kwargs
    ) -> Optional[Dict]:
        """
        Get from cache, or fetch and cache if miss - Synchronous version.

        Args:
            cache_type: Type of cache
            cache_key: Unique key for the cached item
            fetch_func: Function to call if cache miss (can be sync or async)
            ttl_hours: Custom TTL in hours
            *args, **kwargs: Arguments to pass to fetch_func

        Returns:
            Data from cache or fetch function
        """
        # Try cache first
        cached_data = self.get_sync(cache_type, cache_key)

        if cached_data is not None:
            return cached_data

        # Cache miss - fetch data
        logger.info(f"📡 Fetching fresh data for {cache_type}:{cache_key}")

        try:
            fresh_data = fetch_func(*args, **kwargs)

            if fresh_data is not None:
                # Store in cache
                self.set_sync(cache_type, cache_key, fresh_data, ttl_hours)

            return fresh_data

        except Exception as e:
            logger.error(f"Failed to fetch data for {cache_type}:{cache_key}: {e}")
            return None

    def invalidate(self, cache_type: str, cache_key: str = None) -> int:
        """
        Invalidate cache entries

        Args:
            cache_type: Type of cache to invalidate
            cache_key: Specific key to invalidate (invalidates all of type if None)

        Returns:
            Number of entries invalidated
        """
        query = self.db.query(CacheStore).filter(
            CacheStore.cache_type == cache_type
        )

        if cache_key:
            query = query.filter(CacheStore.cache_key == cache_key)

        count = query.count()

        if count > 0:
            query.delete()
            self.db.commit()
            self.stats["deletes"] += count
            logger.info(f"🗑️  Invalidated {count} cache entries: {cache_type}:{cache_key or '*'}")

        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries

        Returns:
            Number of entries removed
        """
        now = datetime.now()

        expired = self.db.query(CacheStore).filter(
            CacheStore.expires_at <= now
        ).all()

        count = len(expired)

        if count > 0:
            for entry in expired:
                self.db.delete(entry)
            self.db.commit()
            self.stats["deletes"] += count
            logger.info(f"🧹 Cleaned up {count} expired cache entries")

        return count

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        # Get current cache size
        cache_size = self.db.query(CacheStore).count()

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "hit_rate": round(hit_rate, 2),
            "cache_size": cache_size,
        }

    def get_size_by_type(self) -> Dict[str, int]:
        """Get cache entry count by type"""
        result = {}

        for cache_type in CACHE_TTL.keys():
            count = self.db.query(CacheStore).filter(
                CacheStore.cache_type == cache_type
            ).count()
            result[cache_type] = count

        return result


def generate_cache_key(cache_type: str, **kwargs) -> str:
    """
    Generate a consistent cache key from parameters

    Args:
        cache_type: Type of cache
        **kwargs: Parameters to include in key

    Returns:
        Cache key string

    Examples:
        generate_cache_key("lineup", event_id=12345) -> "lineup:event_id=12345"
        generate_cache_key("squad", team_id=100, season="2025-2026") -> "squad:season=2025-2026:team_id=100"
    """
    parts = [cache_type]

    # Sort kwargs for consistent keys
    for key, value in sorted(kwargs.items()):
        if value is not None:
            parts.append(f"{key}={value}")

    return ":".join(parts)


async def cached_lineup_fetch(
    cache_manager: CacheManager,
    rapidapi_client,
    event_id: int
) -> Optional[Dict]:
    """
    Helper to fetch lineup with caching

    Args:
        cache_manager: CacheManager instance
        rapidapi_client: RapidAPIClient instance
        event_id: Match event ID

    Returns:
        Lineup data
    """
    cache_key = generate_cache_key("lineup", event_id=event_id)

    return await cache_manager.get_or_fetch(
        "lineup",
        cache_key,
        rapidapi_client.get_lineup_all,
        event_id=event_id
    )


async def cached_squad_fetch(
    cache_manager: CacheManager,
    rapidapi_client,
    team_id: int
) -> Optional[List]:
    """
    Helper to fetch team squad with caching

    Args:
        cache_manager: CacheManager instance
        rapidapi_client: RapidAPIClient instance
        team_id: Team ID

    Returns:
        Squad data list
    """
    cache_key = generate_cache_key("squad", team_id=team_id)

    return await cache_manager.get_or_fetch(
        "squad",
        cache_key,
        rapidapi_client.get_team_squad,
        team_id=team_id
    )
