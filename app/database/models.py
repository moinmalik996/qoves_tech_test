"""Database models for PostgreSQL storage."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class TaskResult(Base):
    """Model for storing facial processing task results in PostgreSQL cache."""
    __tablename__ = "task_results"
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Input data hash for cache lookup
    input_hash = Column(String(64), index=True, nullable=False)
    perceptual_hash = Column(String(64), index=True, nullable=True)  # For similarity search
    
    # Task metadata
    status = Column(String(50), nullable=False, default='PENDING')
    task_type = Column(String(100), nullable=False, default='facial_processing')
    
    # Processing information
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Results and error data
    result_data = Column(JSON, nullable=True)
    svg_data = Column(Text, nullable=True)
    mask_contours = Column(JSON, nullable=True)
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
    cache_hits = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    ttl_expires_at = Column(DateTime, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_task_results_input_hash', 'input_hash'),
        Index('idx_task_results_perceptual_hash', 'perceptual_hash'),
        Index('idx_task_results_status', 'status'),
        Index('idx_task_results_submitted_at', 'submitted_at'),
        Index('idx_task_results_cache_lookup', 'input_hash', 'status'),
        Index('idx_task_results_perceptual_lookup', 'perceptual_hash', 'status'),
        Index('idx_task_results_ttl', 'ttl_expires_at'),
    )


class ProcessingMetrics(Base):
    """Model for storing detailed processing metrics and performance data."""
    __tablename__ = "processing_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), index=True, nullable=False)
    
    # Metric details
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)
    
    # Timing information
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Additional metadata
    component = Column(String(50), nullable=True)
    operation = Column(String(100), nullable=True)
    additional_data = Column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_processing_metrics_task_id', 'task_id'),
        Index('idx_processing_metrics_name', 'metric_name'),
        Index('idx_processing_metrics_recorded_at', 'recorded_at'),
        Index('idx_processing_metrics_component', 'component'),
    )


class CacheStats(Base):
    """Model for tracking cache performance statistics."""
    __tablename__ = "cache_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time window for statistics
    recorded_date = Column(String(10), nullable=False, index=True)
    
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
    
    # Unique constraint on date
    __table_args__ = (
        Index('idx_cache_stats_date', 'recorded_date', unique=True),
    )
