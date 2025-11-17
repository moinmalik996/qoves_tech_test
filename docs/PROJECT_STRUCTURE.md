# Project Structure Documentation

## Overview
The project has been restructured into a clean, modular architecture with logical separation of concerns.

## New Directory Structure

```
qoves_tech_test/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── models/                   # Pydantic models for validation
│   │   ├── __init__.py
│   │   └── schemas.py           # Request/Response models
│   │
│   ├── database/                # Database functionality
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── connection.py        # DB session management
│   │   └── utils.py             # Cache key generation
│   │
│   ├── tasks/                   # Celery task processing
│   │   ├── __init__.py
│   │   └── facial_processing.py # Facial region processing task
│   │
│   ├── api/                     # API routes
│   │   ├── __init__.py
│   │   └── routes.py            # FastAPI endpoint handlers
│   │
│   ├── core/                    # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py            # Application configuration
│   │   └── celery_app.py        # Celery application setup
│   │
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── image_processing.py  # Image utilities
│       └── svg_generation.py    # SVG generation utilities
│
├── main.py                      # FastAPI application entry point
├── celery_config.py             # Celery configuration
├── run_worker.py                # Celery worker startup script
├── cache_service.py             # Cache service wrapper
├── database.py                  # Legacy database setup
├── database_setup.py            # Database utilities
├── metrics.py                   # Prometheus metrics
├── rich_logging.py              # Rich console logging
├── tasks.py                     # Legacy tasks (can be removed)
│
├── docker-compose.yml           # Docker services configuration
├── Dockerfile                   # Container image definition
├── docker-entrypoint.sh         # Container startup script
├── pyproject.toml               # Python dependencies
├── Makefile                     # Build commands
└── README.md                    # Project documentation
```

## Module Descriptions

### app/models/schemas.py
**Purpose**: Centralized Pydantic models for API request/response validation

**Classes**:
- `Landmark`: Individual facial landmark (x, y coordinates)
- `FacialRequest`: API request with image, landmarks, dimensions
- `TaskSubmissionResponse`: Response when submitting async task
- `TaskStatusResponse`: Response when polling task status
- `CacheStatsResponse`: Cache performance statistics
- `RecentTaskResponse`: Recent task information

### app/database/
**Purpose**: Database operations and models

**Files**:
- `models.py`: SQLAlchemy ORM models (TaskResult, ProcessingMetrics, CacheStats)
- `connection.py`: Database session management and initialization
- `utils.py`: Utility functions (cache key generation)

### app/tasks/facial_processing.py
**Purpose**: Celery task for processing facial regions

**Key Function**:
- `process_facial_regions_task()`: Async task that processes MediaPipe landmarks and generates SVG masks

**Features**:
- Validates 478 MediaPipe landmarks
- Generates SVG mask overlay with 5 facial regions
- Caches results in PostgreSQL
- Includes retry logic and error handling

### app/api/routes.py
**Purpose**: FastAPI route handlers

**Endpoints**:
- `POST /api/v1/frontal/crop/submit_async`: Submit facial processing task
- `GET /api/v1/frontal/crop/status/{task_id}`: Poll task status
- `GET /api/v1/cache/stats`: Get cache statistics
- `GET /api/v1/cache/recent`: Get recent tasks
- `POST /api/v1/cache/cleanup`: Clean up expired cache
- `GET /health`: Health check
- `GET /api/v1/database/health`: Database health check

### app/core/
**Purpose**: Core application configuration

**Files**:
- `config.py`: Centralized configuration constants (MediaPipe regions, colors, DB URLs)
- `celery_app.py`: Celery application setup

### app/utils/
**Purpose**: Reusable utility functions

**Files**:
- `image_processing.py`: Image decoding/encoding, region contour extraction
- `svg_generation.py`: SVG path generation, mask overlay creation

## MediaPipe Facial Regions

The application uses MediaPipe Face Mesh with 478 landmarks organized into 5 regions:

1. **Forehead** (region 1): Upper face area
2. **Nose** (region 2): Nasal area
3. **Left Under Eye** (region 3): Left infraorbital area
4. **Right Under Eye** (region 4): Right infraorbital area
5. **Mouth** (region 5): Oral area

Each region is rendered with a distinct color and 65% opacity in the generated SVG.

## Migration Guide

### Old vs New Imports

**Before**:
```python
from tasks import process_facial_regions_task
from database import init_database
```

**After**:
```python
from app.tasks.facial_processing import process_facial_regions_task
from database import init_database  # Legacy - will be migrated
```

### Celery Configuration

**Updated in celery_config.py**:
```python
include=['app.tasks.facial_processing']

task_routes={
    'app.tasks.facial_processing.process_facial_regions_task': {'queue': 'facial_processing'}
}
```

## Benefits of New Structure

1. **Modularity**: Clear separation of concerns (models, database, tasks, API)
2. **Maintainability**: Easier to locate and modify specific functionality
3. **Scalability**: Simple to add new modules or features
4. **Testing**: Isolated components are easier to test
5. **Code Reusability**: Utility functions can be imported across modules
6. **Documentation**: Self-documenting structure with clear purpose for each module

## Next Steps

1. ✅ Create app/ folder structure
2. ✅ Extract Pydantic models to app/models/schemas.py
3. ✅ Extract database models to app/database/
4. ✅ Extract core configuration to app/core/
5. ✅ Extract utility functions to app/utils/
6. ✅ Extract task processing to app/tasks/
7. ✅ Extract API routes to app/api/
8. ✅ Update main.py to use new structure
9. ✅ Update celery_config.py imports
10. 🔄 Test the restructured application
11. 🔄 Migrate remaining legacy modules (cache_service, database_setup)
12. 🔄 Remove old files (tasks.py, main_old.py)

## Running the Application

```bash
# Start services with Docker
docker-compose up -d

# Or run locally
python main.py  # API server
python run_worker.py  # Celery worker
```

## Testing

```bash
# Run tests
python test_docker_api.py

# Check API documentation
curl http://localhost:8000/docs
```
