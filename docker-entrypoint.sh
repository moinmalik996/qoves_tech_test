#!/bin/bash
# Docker-specific startup script with Rich logging and Prometheus integration

set -e

echo "🐳 Starting Facial Processing Service in Docker"
echo "=============================================="

# Function to wait for Redis
wait_for_redis() {
    echo "⏳ Waiting for Redis to be ready..."
    while ! redis-cli -h redis -p 6379 ping > /dev/null 2>&1; do
        sleep 1
    done
    echo "✅ Redis is ready!"
}

# Function to check if we're the API service or worker
if [ "$1" = "api" ]; then
    echo "🚀 Starting API service with Prometheus metrics..."
    wait_for_redis
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
elif [ "$1" = "worker" ]; then
    echo "👷 Starting Celery worker with Rich logging..."
    wait_for_redis
    exec celery -A celery_config worker --loglevel=info --concurrency=2
elif [ "$1" = "monitor" ]; then
    echo "📊 Starting monitoring dashboard..."
    wait_for_redis
    sleep 10  # Wait for API to be ready
    exec python monitor_demo.py
else
    echo "❓ Unknown service type: $1"
    echo "Available options: api, worker, monitor"
    exit 1
fi