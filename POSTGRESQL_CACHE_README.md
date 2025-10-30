# 🐘 PostgreSQL Cache Integration

Complete PostgreSQL caching system for the facial processing service with intelligent cache management, performance tracking, and Rich logging.

## 🚀 Overview

The PostgreSQL cache system provides:
- **Intelligent Result Caching**: Automatic caching based on input hash
- **Performance Tracking**: Detailed metrics and statistics
- **TTL Management**: Configurable cache expiration
- **Rich Monitoring**: Beautiful logging and real-time stats
- **Error Caching**: Avoid reprocessing failed inputs
- **Docker Integration**: Fully containerized setup

## 📊 Features

### 🔄 Smart Caching
- **Input Hash-Based**: Cache key generated from image, landmarks, and parameters
- **Automatic Storage**: Results stored after successful processing
- **Cache Hit Detection**: Fast lookup before processing
- **Error Caching**: Failed processing results cached to avoid retry

### 📈 Performance Metrics
- **Hit Ratio Tracking**: Monitor cache effectiveness
- **Processing Time Stats**: Average, min, max processing times
- **Storage Analytics**: Cache size and entry count
- **Component Metrics**: Detailed timing for each processing step

### 🧹 Cache Management
- **TTL Support**: Configurable expiration (default 24 hours)
- **Automatic Cleanup**: Remove expired entries
- **Statistics Tracking**: Daily performance summaries
- **Recent Tasks View**: Monitor latest processing activity

## 🛠️ Setup

### 1. Dependencies
Already included in `pyproject.toml`:
```toml
"sqlalchemy>=2.0.0",
"asyncpg>=0.29.0", 
"psycopg2-binary>=2.9.0",
"alembic>=1.13.0",
```

### 2. Environment Configuration
Update `.env` file:
```bash
# PostgreSQL Configuration
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/facial_processing
DEBUG_SQL=false
CACHE_TTL_HOURS=24
```

### 3. Docker Services
PostgreSQL is now included in `docker-compose.yml`:
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: facial_processing
    POSTGRES_USER: postgres  
    POSTGRES_PASSWORD: postgres
```

## 🚀 Quick Start

### Start with Cache
```bash
# Build and start all services (including PostgreSQL)
make build
make up

# Check cache statistics
make cache-stats

# View recent tasks
curl http://localhost:8000/api/v1/cache/recent
```

### Monitor Cache Performance
```bash
# Real-time cache stats
curl http://localhost:8000/api/v1/cache/stats

# Database shell access
make db-shell

# Clean expired entries
make cache-clean
```

## 📊 Database Schema

### TaskResult Table
Main cache storage with comprehensive tracking:
```sql
- id: UUID primary key
- task_id: Unique task identifier
- input_hash: SHA256 hash of inputs (cache key)
- status: SUCCESS/FAILURE/PENDING
- result_data: Complete JSON result
- svg_data: Base64 encoded SVG
- processing_time_ms: Processing duration
- cache_hits: Number of times served from cache
- ttl_expires_at: Cache expiration timestamp
```

### ProcessingMetrics Table
Detailed performance metrics:
```sql
- metric_name: Type of metric (decode_time, processing_time, etc.)
- metric_value: Numeric value
- component: Which component generated the metric
- recorded_at: Timestamp
```

## 🔄 Cache Workflow

### 1. Task Submission
```
Request → Check Cache → Cache Hit? → Return Cached Result
                     ↓ Cache Miss
                   Process → Store Result → Return New Result
```

### 2. Cache Key Generation
```python
cache_key = SHA256({
    'image_hash': MD5(image_data),
    'landmarks_hash': MD5(landmarks),  
    'segmentation_hash': MD5(segmentation_map),
    'show_landmarks': boolean,
    'region_opacity': float
})
```

### 3. Automatic Cleanup
- Expired entries removed based on TTL
- Failed tasks older than 7 days deleted
- Unused cache entries (0 hits) cleaned after 30 days

## 📈 API Endpoints

### Cache Statistics
```http
GET /api/v1/cache/stats?days=7
```
Response:
```json
{
  "total_requests": 150,
  "cache_hits": 95,
  "cache_hit_ratio": 63.33,
  "avg_processing_time_ms": 1250.5,
  "cache_efficiency": "good"
}
```

### Recent Tasks
```http
GET /api/v1/cache/recent?limit=10
```

### Cache Cleanup
```http
POST /api/v1/cache/cleanup
```

## 🎯 Performance Benefits

### Before Cache (Cold Processing)
```
Request → Image Decode → Landmark Processing → 
Region Extraction → SVG Generation → Response
⏱️ ~2-5 seconds per request
```

### With Cache (Warm Hits)
```
Request → Cache Lookup → Response
⏱️ ~50-100ms per request (20-50x faster!)
```

### Expected Performance Gains
- **First Request**: Normal processing time (~2-5s)
- **Cache Hit**: ~50-100ms response (98% faster)
- **Similar Requests**: Instant responses from cache
- **Memory Efficiency**: PostgreSQL handles large result storage

## 🔍 Monitoring & Debugging

### Rich Logging Output
```
🔍 Checking PostgreSQL cache for existing result...
⚡ Cache HIT! Returning cached result for task abc12345
💾 Result cached successfully for task xyz98765
🧹 Cleaned up 15 expired cache entries
```

### Database Queries
```sql
-- View cache performance
SELECT * FROM cache_performance;

-- Check recent activity  
SELECT task_id, status, cache_hits, processing_time_ms 
FROM task_results 
ORDER BY submitted_at DESC LIMIT 10;

-- Find most cached results
SELECT input_hash, cache_hits, regions_detected
FROM task_results 
WHERE cache_hits > 0 
ORDER BY cache_hits DESC;
```

### Performance Views
```sql
-- Daily cache statistics
CREATE VIEW cache_performance AS
SELECT 
    DATE(submitted_at) as date,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN cache_hits > 0 THEN 1 END) as cache_hits,
    ROUND((cache_hits * 100.0 / total_requests), 2) as hit_ratio_percent
FROM task_results 
GROUP BY DATE(submitted_at);
```

## 🛠️ Configuration Options

### Environment Variables
```bash
# Cache behavior
CACHE_TTL_HOURS=24              # Default cache expiration
DATABASE_URL=postgresql://...    # PostgreSQL connection
DEBUG_SQL=false                 # Log SQL queries

# Performance tuning
SQLALCHEMY_POOL_SIZE=10         # Connection pool size
SQLALCHEMY_MAX_OVERFLOW=20      # Max additional connections
```

### Cache Service Settings
```python
# In cache_service.py
cache_service = CacheService(
    default_ttl_hours=24,      # Cache expiration
    max_cache_size_mb=1000,    # Optional size limit
    cleanup_interval=3600      # Cleanup frequency
)
```

## 📊 Grafana Integration

Cache metrics are exposed for Grafana dashboards:

### Key Metrics
```promql
# Cache hit ratio
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])

# Average processing time
avg(processing_time_ms) by (status)

# Cache size growth
increase(cached_entries_total[1h])
```

### Dashboard Panels
- Cache hit ratio over time
- Processing time comparison (cached vs new)
- Storage usage and growth
- Error rate by type

## 🔧 Troubleshooting

### Common Issues

#### Cache Not Working
```bash
# Check database connection
make db-shell
\dt  # List tables

# Verify environment
docker-compose exec api env | grep DATABASE_URL
```

#### Poor Cache Performance
```bash
# Check cache statistics
make cache-stats

# View recent activity
curl http://localhost:8000/api/v1/cache/recent

# Clean expired entries
make cache-clean
```

#### Database Issues
```bash
# Restart PostgreSQL
docker-compose restart postgres

# View logs
docker-compose logs postgres

# Recreate database
make clean && make up
```

## 🚀 Production Optimization

### PostgreSQL Tuning
```sql
-- Optimize for cache workload
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### Connection Pooling
```python
# In database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Increase for high load
    max_overflow=40,        # Handle bursts
    pool_pre_ping=True,     # Verify connections
    pool_recycle=3600       # Refresh connections
)
```

### Scaling Considerations
- **Read Replicas**: For high read loads
- **Connection Pooling**: PgBouncer for many connections
- **Partitioning**: Split large tables by date
- **Indexing**: Add custom indexes for query patterns

This PostgreSQL cache integration provides a robust, scalable caching solution with comprehensive monitoring and management capabilities! 🚀