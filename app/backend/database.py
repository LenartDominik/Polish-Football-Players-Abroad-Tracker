from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Ensure we use a synchronous DBAPI driver for SQLAlchemy's sync engine.
# If the DATABASE_URL contains an async driver like '+aiosqlite', replace
# it with the synchronous SQLite driver portion so create_engine uses the
# standard DBAPI and doesn't attempt async IO (which triggers greenlet errors).
database_url = settings.database_url
if not database_url:
    raise ValueError(
        "? DATABASE_URL not configured!\n"
        "Please set DATABASE_URL in your .env file.\n"
        "Example: DATABASE_URL=postgresql://user:pass@host:port/db\n"
        "See SUPABASE_GUIDE.md for setup instructions."
    )
if "+aiosqlite" in database_url:
    database_url = database_url.replace("+aiosqlite", "")

# Detect database type
is_sqlite = database_url.startswith("sqlite")
is_postgresql = database_url.startswith("postgresql") or database_url.startswith("postgres")

# Create engine with appropriate settings
if is_sqlite:
    # SQLite-specific settings
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}  # tylko dla SQLite
    )
elif is_postgresql:
    # PostgreSQL-specific settings
    # Check if using Supabase Transaction Pooler (port 6543 - needs prepared statements disabled)
    connect_args = {
        "client_encoding": "utf8",  # Required for Supabase pooler
    }
    if "6543" in database_url or ("supabase.com" in database_url and "pooler" in database_url):
        # Disable prepared statements for Supabase Transaction Pooling (psycopg2)
        # This is required because Transaction Pooler doesn't support PREPARE statements
        connect_args.update({
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        })
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,  # Test connection before using
        pool_recycle=300,  # Recycle connections every 30 minutes
        pool_size=5,        # Connection pool size
        max_overflow=10,     # Allow up to 10 connections above pool_size
        pool_timeout=30,     # Wait max 30s for a connection from the pool
        echo=False,          # Set to True for SQL debugging
        connect_args=connect_args,
        # Disable statement caching for Transaction Pooler compatibility
        execution_options={"statement_cache_size": 0} if "6543" in database_url else {}
    )
else:
    # Default (other databases)
    engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


