"""Database models and operations."""
from app.database.models import TaskResult, ProcessingMetrics, CacheStats
from app.database.connection import (
    engine, 
    SessionLocal, 
    Base, 
    init_database,
    get_db,
    create_tables,
    test_database_connection
)
from app.database.setup import init_database as legacy_init_database
from app.database.utilities import get_database_stats, test_database_connection as test_db_conn
from app.database.utils import generate_cache_key

__all__ = [
    # Models
    "TaskResult",
    "ProcessingMetrics",
    "CacheStats",
    
    # Connection
    "engine",
    "SessionLocal",
    "Base",
    "init_database",
    "get_db",
    "create_tables",
    "test_database_connection",
    
    # Setup & Utilities  
    "legacy_init_database",
    "get_database_stats",
    "test_db_conn",
    "generate_cache_key",
]
