# Testing the Restructured Application

## Quick Start

### 1. Start Services with Docker

```bash
# Start all services (API, worker, PostgreSQL, Redis)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api      # API server logs
docker-compose logs -f worker   # Celery worker logs
docker-compose logs -f postgres # Database logs
docker-compose logs -f redis    # Redis logs
```

### 2. Verify Services are Running

```bash
# Check API health
curl http://localhost:8000/health

# Check database health
curl http://localhost:8000/api/v1/database/health

# View API documentation
open http://localhost:8000/docs  # or visit in browser
```

## Testing the New Structure

### Test 1: Verify Imports (Without Dependencies)

The structure itself is correct. The import test will fail without dependencies installed:

```bash
python3 test_structure.py
```

Expected: Module not found errors (normal - dependencies are in Docker)

### Test 2: Test API with Docker

Use the provided test script:

```bash
# Basic API test
python3 test_docker_api.py

# Or manually test
curl -X POST http://localhost:8000/api/v1/frontal/crop/submit_async \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Test 3: Verify Module Organization

Check that all files exist:

```bash
# List app structure
tree app/

# Or manually
ls -R app/

# Expected output:
# app/
# ├── __init__.py
# ├── api/
# │   ├── __init__.py
# │   └── routes.py
# ├── core/
# │   ├── __init__.py
# │   ├── celery_app.py
# │   └── config.py
# ├── database/
# │   ├── __init__.py
# │   ├── connection.py
# │   ├── models.py
# │   └── utils.py
# ├── models/
# │   ├── __init__.py
# │   └── schemas.py
# ├── tasks/
# │   ├── __init__.py
# │   └── facial_processing.py
# └── utils/
#     ├── __init__.py
#     ├── image_processing.py
#     └── svg_generation.py
```

### Test 4: Check Celery Worker

```bash
# View worker logs
docker-compose logs -f worker

# Should see:
# - Worker startup
# - Queue registration (facial_processing)
# - Task registration (app.tasks.facial_processing.process_facial_regions_task)
```

### Test 5: Database Connection

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U qoves -d facial_processing

# Run queries
\dt                           # List tables
SELECT COUNT(*) FROM task_results;
SELECT * FROM task_results LIMIT 5;
\q                           # Exit
```

### Test 6: Cache Statistics

```bash
# Get cache stats
curl http://localhost:8000/api/v1/cache/stats?days=7

# Get recent tasks
curl http://localhost:8000/api/v1/cache/recent?limit=10
```

## Detailed API Testing

### Submit a Task

Create a test payload file `test_payload.json`:

```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "landmarks": [
    {"x": 100.5, "y": 200.3},
    ...478 landmarks total...
  ],
  "dimensions": [640, 480]
}
```

Submit the task:

```bash
curl -X POST http://localhost:8000/api/v1/frontal/crop/submit_async \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

Response:
```json
{
  "task_id": "abc123...",
  "status": "PENDING",
  "message": "Task submitted successfully...",
  "submitted_at": "2024-01-15T10:30:00",
  "estimated_completion_time": 30
}
```

### Poll Task Status

```bash
TASK_ID="abc123..."  # Use actual task ID from above

curl http://localhost:8000/api/v1/frontal/crop/status/$TASK_ID
```

Response (when completed):
```json
{
  "task_id": "abc123...",
  "status": "SUCCESS",
  "result": {
    "svg_base64": "PHN2ZyB3aWR0aD0iNjQwIi...",
    "region_data": {
      "forehead": [[100, 200], [101, 202], ...],
      "nose": [[150, 250], ...],
      ...
    }
  },
  "completed_at": "2024-01-15T10:30:25",
  "processing_time_ms": 2543.2
}
```

## Monitoring and Metrics

### Prometheus Metrics

```bash
# View metrics
curl http://localhost:8000/metrics

# Key metrics:
# - task_counter (started, success, failed)
# - task_latency_seconds
# - http_request_duration_seconds
# - cache_hit_counter
```

### View in Grafana (if monitoring stack is running)

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000  # admin/admin

# Access Prometheus
open http://localhost:9090
```

## Troubleshooting

### Issue: Imports Failing Locally

**Solution**: This is expected. The dependencies are only installed in Docker containers. To test locally:

```bash
# Install dependencies (optional)
pip install -r requirements.txt  # or use uv

# Then test
python3 test_structure.py
```

### Issue: Worker Not Processing Tasks

**Check 1**: Verify Celery configuration
```bash
docker-compose logs worker | grep "app.tasks.facial_processing"
# Should see: [tasks] . app.tasks.facial_processing.process_facial_regions_task
```

**Check 2**: Verify Redis connection
```bash
docker-compose exec redis redis-cli PING
# Should see: PONG
```

**Check 3**: Check task routes in celery_config.py
```python
task_routes={
    'app.tasks.facial_processing.process_facial_regions_task': {'queue': 'facial_processing'}
}
```

### Issue: Database Connection Error

**Check 1**: Verify PostgreSQL is running
```bash
docker-compose ps postgres
# Should show: Up
```

**Check 2**: Test connection
```bash
docker-compose exec postgres psql -U qoves -d facial_processing -c "SELECT 1;"
```

**Check 3**: Check environment variables
```bash
docker-compose exec api env | grep DATABASE_URL
```

### Issue: API Not Starting

**Check 1**: View detailed logs
```bash
docker-compose logs api
```

**Check 2**: Verify main.py syntax
```bash
docker-compose exec api python3 -m py_compile main.py
```

**Check 3**: Test imports in container
```bash
docker-compose exec api python3 test_structure.py
```

## Performance Testing

### Load Test with Apache Bench

```bash
# Install ab (if not installed)
# macOS: brew install httpd
# Linux: apt-get install apache2-utils

# Simple load test
ab -n 100 -c 10 http://localhost:8000/health

# With POST requests
ab -n 50 -c 5 -p test_payload.json \
   -T application/json \
   http://localhost:8000/api/v1/frontal/crop/submit_async
```

### Monitor Resource Usage

```bash
# Docker stats
docker stats

# Specific service stats
docker stats qoves_tech_test-api-1
docker stats qoves_tech_test-worker-1
```

## Code Quality Checks

### Lint Check

```bash
# Inside container
docker-compose exec api pylint app/

# Or locally (if pylint installed)
pylint app/
```

### Type Checking

```bash
# Inside container
docker-compose exec api mypy app/

# Or locally
mypy app/
```

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove old files (optional)
rm main_old.py tasks.py  # After verifying new structure works
```

## Success Criteria

Your restructured application is working correctly if:

1. ✅ All services start without errors (`docker-compose up -d`)
2. ✅ Health check returns "healthy" (`curl localhost:8000/health`)
3. ✅ Database health check passes
4. ✅ Worker registers tasks (check logs)
5. ✅ Can submit and poll tasks successfully
6. ✅ Cache statistics endpoint works
7. ✅ No import errors in Docker container
8. ✅ Prometheus metrics are exposed
9. ✅ API documentation loads (http://localhost:8000/docs)
10. ✅ All code follows modular structure

## Next Steps

After verifying everything works:

1. Run your actual test cases with real MediaPipe data
2. Monitor performance metrics
3. Consider migrating remaining legacy files (cache_service, database_setup, etc.)
4. Add comprehensive unit tests for new modules
5. Update CI/CD pipeline if applicable
6. Document any custom deployment procedures

## Questions or Issues?

If you encounter issues:

1. Check Docker logs first: `docker-compose logs -f`
2. Verify environment variables are set correctly
3. Ensure all required ports are available (8000, 5432, 6379)
4. Review `PROJECT_STRUCTURE.md` for module organization
5. Check `RESTRUCTURING_SUMMARY.md` for detailed changes

The restructured codebase is now much cleaner and more maintainable! 🎉
