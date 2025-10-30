# Docker Management for Facial Processing Service with PostgreSQL Cache & Prometheus

.PHONY: help build up down logs test clean monitoring cache-stats db-shell

# Default target
help:
	@echo "🐳 Facial Processing Service - Docker Commands"
	@echo "=============================================="
	@echo ""
	@echo "Basic Commands:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start all services (API + Worker + Redis + PostgreSQL)"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - Show logs from all services"
	@echo "  make test      - Run integration tests"
	@echo ""
	@echo "PostgreSQL Cache:"
	@echo "  make cache-stats - Show cache performance statistics"
	@echo "  make db-shell    - Connect to PostgreSQL database"
	@echo "  make cache-clean - Clean up expired cache entries"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitoring - Start with Prometheus + Grafana"
	@echo "  make metrics    - Show current metrics"
	@echo "  make monitor    - Start live monitoring dashboard"
	@echo ""
	@echo "Development:"
	@echo "  make dev       - Start in development mode with hot reload"
	@echo "  make shell     - Get shell access to API container"
	@echo "  make worker    - View worker logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean     - Remove containers and volumes"
	@echo "  make rebuild   - Clean rebuild of all images"

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

# Start services (API + Worker + Redis + PostgreSQL)
up:
	@echo "🚀 Starting facial processing services..."
	docker-compose up -d postgres redis api worker
	@echo "✅ Services started!"
	@echo "📊 API: http://localhost:8000"
	@echo "📊 Metrics: http://localhost:8000/metrics"
	@echo "🏥 Health: http://localhost:8000/health"
	@echo "🐘 PostgreSQL: localhost:5432"
	@echo "💾 Cache Stats: http://localhost:8000/api/v1/cache/stats"

# Start with monitoring (includes Prometheus + Grafana)
monitoring:
	@echo "📊 Starting core services..."
	docker-compose up -d
	@echo "📊 Starting monitoring stack..."
	docker-compose -f docker-compose.monitoring.yml up -d
	@echo "✅ All services started!"
	@echo "📊 API: http://localhost:8000"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin123)"
	@echo "🐘 PostgreSQL: localhost:5432"
	@echo "💾 Cache Stats: http://localhost:8000/api/v1/cache/stats"

# Development mode with hot reload
dev:
	@echo "🛠️ Starting in development mode..."
	docker-compose up postgres redis api worker

# Stop all services
down:
	@echo "🛑 Stopping services..."
	docker-compose down

# Show logs
logs:
	@echo "📋 Showing service logs..."
	docker-compose logs -f

# Show worker logs specifically
worker:
	@echo "👷 Showing worker logs..."
	docker-compose logs -f worker

# Show cache statistics
cache-stats:
	@echo "💾 Cache Performance Statistics:"
	@curl -s http://localhost:8000/api/v1/cache/stats | python -m json.tool

# Connect to PostgreSQL database
db-shell:
	@echo "🐘 Connecting to PostgreSQL database..."
	docker-compose exec postgres psql -U postgres -d facial_processing

# Clean up cache
cache-clean:
	@echo "🧹 Cleaning up expired cache entries..."
	@curl -s -X POST http://localhost:8000/api/v1/cache/cleanup | python -m json.tool

# Show metrics
metrics:
	@echo "📊 Current Prometheus metrics:"
	@curl -s http://localhost:8000/metrics | head -20
	@echo "..."
	@echo "(showing first 20 lines - visit http://localhost:8000/metrics for full output)"

# Start monitoring dashboard
monitor:
	@echo "📈 Starting live monitoring dashboard..."
	docker-compose exec api python monitor_demo.py

# Run integration tests
test:
	@echo "🧪 Running integration tests..."
	docker-compose exec api python test_integration.py

# Test PostgreSQL cache integration
test-cache:
	@echo "🐘 Testing PostgreSQL cache integration..."
	docker-compose exec api python test_postgres_cache.py

# Test Docker setup
test-docker:
	@echo "🐳 Testing Docker setup..."
	./test_docker_setup.sh

# Get shell access
shell:
	@echo "🐚 Opening shell in API container..."
	docker-compose exec api bash

# Clean everything
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker-compose -f docker-compose.monitoring.yml down -v --remove-orphans 2>/dev/null || true
	docker system prune -f

# Rebuild everything from scratch
rebuild: clean
	@echo "🔄 Rebuilding everything from scratch..."
	docker-compose build --no-cache
	@make up

# Check service status
status:
	@echo "📊 Service Status:"
	@docker-compose ps

# Quick health check
health:
	@echo "🏥 Health Check:"
	@curl -s http://localhost:8000/health | python -m json.tool

# Show recent tasks from cache
recent-tasks:
	@echo "📋 Recent Tasks (from PostgreSQL cache):"
	@curl -s http://localhost:8000/api/v1/cache/recent | python -m json.tool