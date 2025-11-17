"""Database connection and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base
from app.database.utilities import create_database_views_and_functions

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://postgres:postgres@postgres:5432/facial_processing'
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=os.getenv('DEBUG_SQL', 'false').lower() == 'true'
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session (generator for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session (non-generator version)."""
    return SessionLocal()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)


def test_database_connection() -> bool:
    """Test database connection."""
    try:
        db = get_db_session()
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT 1")).scalar()
            return result == 1
        finally:
            db.close()
    except Exception:
        return False


def init_database():
    """Initialize database with tables and initial data."""
    try:
        # Create tables
        create_tables()
        print("✅ Database tables created successfully")
        
        # Test connection
        if test_database_connection():
            print("✅ Database connection test successful")
        else:
            raise Exception("Database connection test failed")
        
        # Create views and functions after tables exist
        try:
            create_database_views_and_functions()
            print("✅ Database views and functions created successfully")
        except Exception as e:
            print(f"⚠️ Warning: Could not create views/functions: {e}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
