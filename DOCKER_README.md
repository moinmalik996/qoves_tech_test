# 🐳 Docker Setup for Facial Processing Service

Complete Docker setup with Prometheus metrics and Rich logging integration.

## 🚀 Quick Start

### Basic Setup (API + Worker + Redis)
```bash
# Build and start services
make build
make up

# View logs with Rich formatting
make logs

# Check status
make status
```

### With Monitoring (+ Prometheus + Grafana)
```bash
# Start everything including monitoring
make monitoring

# Access services
open http://localhost:8000      # API Documentation
open http://localhost:9090      # Prometheus
open http://localhost:3000      # Grafana (admin/admin123)
```

## 📊 Available Services

| Service | Port | Description |
|---------|------|-------------|
| **API** | 8000 | FastAPI with Rich logging |
| **Metrics** | 8000/metrics | Prometheus metrics endpoint |
| **Prometheus** | 9090 | Metrics collection (optional) |
| **Grafana** | 3000 | Metrics visualization (optional) |
| **Redis** | 6379 | Task queue backend |

## 🛠️ Commands

### Essential Commands
```bash
make up         # Start core services
make down       # Stop all services  
make logs       # View Rich formatted logs
make test       # Run integration tests
make health     # Check service health
```

### Development
```bash
make dev        # Development mode with hot reload
make shell      # Shell access to API container
make worker     # View worker logs
make monitor    # Live monitoring dashboard
```

### Monitoring
```bash
make monitoring # Start with full monitoring stack
make metrics    # View current metrics
```

### Maintenance  
```bash
make clean      # Remove containers/volumes
make rebuild    # Clean rebuild
```

## 🌈 Rich Logging in Docker

The service provides beautiful colored logging even in Docker containers:

```
🚀 Service Started
   Facial Region SVG Service v1.0.0
   Running on http://0.0.0.0:8000
   Started at 2025-10-29 10:30:45

   GET /health 200 15.2ms 
📋 Task Started abc12345 facial_processing
🖼️ Image decoded: (512, 512, 3) 
✅ Task Success abc12345 facial_processing 2.34s
```

## 📈 Prometheus Metrics

Access metrics at: `http://localhost:8000/metrics`

Key metrics available:
- `api_requests_total` - API request counts
- `task_processing_duration_seconds` - Task timing
- `landmarks_processed_total` - Landmarks processed
- `regions_generated_total` - Regions generated

## 🔍 Health Checks

All services include health checks:
- API: `curl http://localhost:8000/health`
- Redis: Built-in Redis ping
- Worker: Celery inspect ping

## 📊 Grafana Dashboards

When using `make monitoring`, Grafana comes pre-configured with:
- Prometheus data source
- Default dashboards directory
- Admin access (admin/admin123)

## 🔧 Environment Variables

Key variables (configured in `.env`):

```bash
# Metrics & Logging
ENABLE_METRICS=true
LOG_LEVEL=INFO

# Rich Terminal Support
TERM=xterm-256color
COLORTERM=truecolor
FORCE_COLOR=1

# Redis Connection
REDIS_URL=redis://redis:6379/0
```

## 🐛 Troubleshooting

### No colored output in logs
```bash
# Ensure these are set in docker-compose.yml
environment:
  - TERM=xterm-256color
  - COLORTERM=truecolor
  - FORCE_COLOR=1
```

### Metrics not appearing
```bash
# Check if metrics are enabled
curl http://localhost:8000/metrics

# Verify environment variable
docker-compose exec api env | grep ENABLE_METRICS
```

### Services not starting
```bash
# Check logs for specific service
docker-compose logs api
docker-compose logs worker
docker-compose logs redis

# Check health status
make status
```

## 🔄 Development Workflow

1. **Start services**: `make up`
2. **View logs**: `make logs` (in another terminal)
3. **Make changes**: Code changes auto-reload in dev mode
4. **Test**: `make test`
5. **Monitor**: `make monitor` (live dashboard)
6. **Stop**: `make down`

## 📦 Production Deployment

For production, modify `docker-compose.yml`:

```yaml
# Remove --reload from API command
command: uvicorn main:app --host 0.0.0.0 --port 8000

# Add resource limits
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

## 🚀 Scaling

Scale services as needed:
```bash
# Scale workers
docker-compose up -d --scale worker=3

# Scale with monitoring
docker-compose --profile monitoring up -d --scale worker=2
```

This Docker setup provides a complete development and production environment with beautiful logging and comprehensive monitoring!