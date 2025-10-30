# Facial Region SVG Service

FastAPI service that processes facial landmarks and segmentation maps to generate SVG masks using background tasks.

## Quick Start with Docker

```bash
# Start all services
docker-compose up --build

# Access the API
curl http://localhost:8000/health
```

## API Usage

### Submit Task
```bash
POST /api/v1/frontal/crop/submit
```

### Check Status
```bash
GET /api/v1/frontal/crop/status/{task_id}
```

### Endpoints
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## Local Development

```bash
# Install dependencies
pip install -r pyproject.toml

# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Start worker (terminal 1)
celery -A celery_config worker --loglevel=info

# Start API (terminal 2)  
python main.py
```

## Test

```bash
python test_async_api.py
```