"""Clear the cache_store table to force fresh data"""
import sys
sys.path.insert(0, 'E:/Polish Footballers Abroad Tracker/polish-players-tracker')

from app.backend.database import SessionLocal
from app.backend.models.cache_store import CacheStore

db = SessionLocal()
try:
    # Delete all cached data
    deleted = db.query(CacheStore).delete()
    db.commit()
    print(f"OK: Cleared {deleted} cache entries from cache_store table")
except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
finally:
    db.close()
