"""
Database configuration and models for PostgreSQL caching.
Stores task results, processing metrics, and cache data.
"""

import os
import uuid
import json
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID

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
Base = declarative_base()

class TaskResult(Base):
    """
    Model for storing facial processing task results in PostgreSQL cache.
    """
    __tablename__ = "task_results"
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Input data hash for cache lookup
    input_hash = Column(String(64), index=True, nullable=False)
    
    # Task metadata
    status = Column(String(50), nullable=False, default='PENDING')
    task_type = Column(String(100), nullable=False, default='facial_processing')
    
    # Processing information
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Results and error data
    result_data = Column(JSON, nullable=True)  # Stores the complete result
    svg_data = Column(Text, nullable=True)  # Base64 encoded SVG
    mask_contours = Column(JSON, nullable=True)  # Facial region contours
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Input parameters for cache matching
    show_landmarks = Column(String(10), nullable=True)
    region_opacity = Column(Float, nullable=True)
    
    # Processing metrics
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    landmarks_count = Column(Integer, nullable=True)
    regions_detected = Column(Integer, nullable=True)
    
    # Cache management
    cache_hits = Column(Integer, default=0)  # How many times this result was served from cache
    last_accessed = Column(DateTime, default=datetime.utcnow)
    ttl_expires_at = Column(DateTime, nullable=True)  # Optional TTL for cache entries
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_task_results_input_hash', 'input_hash'),
        Index('idx_task_results_status', 'status'),
        Index('idx_task_results_submitted_at', 'submitted_at'),
        Index('idx_task_results_cache_lookup', 'input_hash', 'status'),
        Index('idx_task_results_ttl', 'ttl_expires_at'),
    )

class ProcessingMetrics(Base):
    """
    Model for storing detailed processing metrics and performance data.
    """
    __tablename__ = "processing_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), index=True, nullable=False)
    
    # Metric details
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)  # ms, seconds, bytes, count, etc.
    
    # Timing information
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Additional metadata
    component = Column(String(50), nullable=True)  # api, worker, image_processor, etc.
    operation = Column(String(100), nullable=True)  # decode, contour_extract, svg_generate, etc.
    additional_data = Column(JSON, nullable=True)  # Additional context data
    
    # Indexes
    __table_args__ = (
        Index('idx_processing_metrics_task_id', 'task_id'),
        Index('idx_processing_metrics_name', 'metric_name'),
        Index('idx_processing_metrics_recorded_at', 'recorded_at'),
        Index('idx_processing_metrics_component', 'component'),
    )

class CacheStats(Base):
    """
    Model for tracking cache performance statistics.
    """
    __tablename__ = "cache_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time window for statistics
    recorded_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD format
    
    # Cache performance metrics
    total_requests = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    
    # Processing metrics
    avg_processing_time_ms = Column(Float, nullable=True)
    total_processing_time_ms = Column(Float, default=0)
    
    # Storage metrics
    total_cached_results = Column(Integer, default=0)
    cache_size_bytes = Column(Integer, default=0)
    
    # Performance metrics
    fastest_processing_ms = Column(Float, nullable=True)
    slowest_processing_ms = Column(Float, nullable=True)
    
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Unique constraint on date to prevent duplicates
    __table_args__ = (
        Index('idx_cache_stats_date', 'recorded_date', unique=True),
    )

# Database utility functions
def get_db() -> Session:
    """Get database session."""
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

# Hash generation for cache keys

def generate_cache_key(image_data: str, landmarks: list, segmentation_map: str, 
                      show_landmarks: bool = False, region_opacity: float = 0.7) -> str:
    """
    Generate a consistent cache key from input parameters.
    """
    # Create a string representation of all input parameters
    cache_input = {
        'image_hash': hashlib.md5(image_data.encode()).hexdigest()[:16],
        'landmarks_hash': hashlib.md5(str(landmarks).encode()).hexdigest()[:16],
        'segmentation_hash': hashlib.md5(segmentation_map.encode()).hexdigest()[:16],
        'show_landmarks': show_landmarks,
        'region_opacity': round(region_opacity, 2)  # Round to avoid float precision issues
    }
    
    # Create SHA256 hash of the combined input
    cache_string = json.dumps(cache_input, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()

def test_database_connection():
    """Test database connection."""
    try:
        db = get_db_session()
        try:
            # Simple test query
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
            from app.database.utilities import create_database_views_and_functions
            create_database_views_and_functions()
            print("✅ Database views and functions created successfully")
        except Exception as e:
            print(f"⚠️ Warning: Could not create views/functions: {e}")
            # Don't fail initialization if views can't be created
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()