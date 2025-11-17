# Quick Reference: New Project Structure

## 📁 Where to Find Things

| What You Need | Where to Look | File |
|---------------|---------------|------|
| API Request/Response Models | `app/models/` | `schemas.py` |
| Database Models (SQLAlchemy) | `app/database/` | `models.py` |
| Database Connection & Sessions | `app/database/` | `connection.py` |
| Cache Key Generation | `app/database/` | `utils.py` |
| Configuration & Constants | `app/core/` | `config.py` |
| Celery App Setup | `app/core/` | `celery_app.py` |
| Image Processing Utils | `app/utils/` | `image_processing.py` |
| SVG Generation Utils | `app/utils/` | `svg_generation.py` |
| Celery Tasks | `app/tasks/` | `facial_processing.py` |
| API Endpoints | `app/api/` | `routes.py` |
| Main App Entry Point | Root | `main.py` |

## 🎯 Common Tasks

### Adding a New API Endpoint

1. Open `app/api/routes.py`
2. Add your route handler:
```python
@router.get("/api/v1/your-endpoint")
async def your_endpoint():
    # Your logic here
    return {"status": "success"}
```

### Adding a New Pydantic Model

1. Open `app/models/schemas.py`
2. Add your model:
```python
class YourModel(BaseModel):
    field1: str
    field2: int = Field(..., ge=0)
```

### Adding a New Celery Task

1. Create a new file in `app/tasks/` or add to `facial_processing.py`
2. Import celery_app: `from app.core.celery_app import celery_app`
3. Define your task:
```python
@celery_app.task(name='app.tasks.your_task')
def your_task(param1, param2):
    # Your logic
    return result
```
4. Update `celery_config.py` to include your task module

### Adding a New Utility Function

1. Determine category (image, SVG, or new)
2. Add to existing file in `app/utils/` or create new file
3. Import where needed:
```python
from app.utils.image_processing import your_function
```

### Adding Configuration

1. Open `app/core/config.py`
2. Add your constant:
```python
YOUR_CONFIG = os.getenv('YOUR_VAR', 'default_value')
```

### Adding a Database Model

1. Open `app/database/models.py`
2. Add your model:
```python
class YourModel(Base):
    __tablename__ = 'your_table'
    id = Column(String, primary_key=True)
    # Add your columns
```

## 🔍 Import Patterns

### From API Routes
```python
from app.models.schemas import FacialRequest, TaskStatusResponse
from app.tasks.facial_processing import process_facial_regions_task
from app.core.config import MEDIAPIPE_FACE_REGIONS
```

### From Tasks
```python
from app.core.celery_app import celery_app
from app.core.config import DEFAULT_REGION_COLORS
from app.utils.svg_generation import generate_svg_mask_overlay
from app.database.models import TaskResult
```

### From Utilities
```python
from app.utils.image_processing import decode_base64_image
from app.utils.svg_generation import landmarks_to_svg_path
```

## 🚀 Running Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Restart after code changes
docker-compose restart api
docker-compose restart worker

# Stop all services
docker-compose down

# Rebuild containers
docker-compose build
docker-compose up -d

# Run tests
python3 test_docker_api.py

# Check structure
python3 test_structure.py  # Requires dependencies
```

## 🔧 Development Workflow

1. **Make Changes**: Edit files in `app/` directory
2. **Test Locally**: Run import tests (optional)
3. **Rebuild**: `docker-compose build` (if dependencies changed)
4. **Restart**: `docker-compose restart api worker`
5. **Test**: Use `test_docker_api.py` or curl
6. **Monitor**: Check logs with `docker-compose logs -f`

## 📊 Monitoring Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/v1/database/health

# Cache stats (last 7 days)
curl http://localhost:8000/api/v1/cache/stats?days=7

# Recent tasks
curl http://localhost:8000/api/v1/cache/recent?limit=10

# Prometheus metrics
curl http://localhost:8000/metrics

# API documentation
open http://localhost:8000/docs
```

## 🐛 Debugging Tips

### Check Worker is Processing Tasks
```bash
docker-compose logs worker | grep "process_facial_regions_task"
# Should show task registration
```

### Check Database Connection
```bash
docker-compose exec postgres psql -U qoves -d facial_processing -c "SELECT 1;"
```

### Check Redis
```bash
docker-compose exec redis redis-cli PING
```

### View Task Status in Redis
```bash
docker-compose exec redis redis-cli
> KEYS celery*
> GET celery-task-meta-<task_id>
```

### Check Imports in Container
```bash
docker-compose exec api python3 -c "from app.models.schemas import FacialRequest; print('OK')"
```

## 📝 MediaPipe Face Regions

5 regions defined in `app/core/config.py`:

| Region | ID | Color | Landmarks |
|--------|----|----|-----------|
| Forehead | 1 | Red | Upper face |
| Nose | 2 | Green | Nasal area |
| Left Under Eye | 3 | Blue | Left infraorbital |
| Right Under Eye | 4 | Yellow | Right infraorbital |
| Mouth | 5 | Purple | Oral region |

Access via:
```python
from app.core.config import MEDIAPIPE_FACE_REGIONS, DEFAULT_REGION_COLORS
```

## 🎨 Code Style

### File Organization
- One model/class per concern
- Group related functions together
- Import order: stdlib → third-party → local
- Use type hints

### Naming Conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_CASE`

### Documentation
- Docstrings for all functions
- Type hints for parameters
- Examples in docstrings when useful

## 📚 Key Files to Remember

| File | Purpose | Modify When |
|------|---------|-------------|
| `main.py` | App entry point | Rarely |
| `app/api/routes.py` | API endpoints | Adding routes |
| `app/models/schemas.py` | API models | Adding validation |
| `app/tasks/facial_processing.py` | Celery tasks | Changing task logic |
| `app/core/config.py` | Configuration | Adding settings |
| `celery_config.py` | Celery setup | Adding task modules |
| `docker-compose.yml` | Services | Adding services |
| `Dockerfile` | Container setup | Changing dependencies |

## 🎯 Module Responsibilities

- **`app/models/`**: Data validation (Pydantic)
- **`app/database/`**: Data persistence (SQLAlchemy)
- **`app/tasks/`**: Background processing (Celery)
- **`app/api/`**: HTTP endpoints (FastAPI)
- **`app/core/`**: Configuration & setup
- **`app/utils/`**: Reusable functions

## ✨ Benefits of New Structure

✅ **Easy to find** code by functionality
✅ **Easy to test** isolated modules
✅ **Easy to extend** with new features
✅ **Easy to maintain** single-responsibility modules
✅ **Easy to understand** self-documenting organization

## 📖 Documentation Files

- `README.md` - Project overview
- `PROJECT_STRUCTURE.md` - Detailed structure docs
- `RESTRUCTURING_SUMMARY.md` - What changed
- `TESTING_RESTRUCTURED.md` - How to test
- `QUICK_REFERENCE.md` - This file!

---

**Need more help?** Check the detailed documentation files above! 🚀
