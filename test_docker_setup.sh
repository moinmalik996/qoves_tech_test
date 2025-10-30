#!/bin/bash
# Test PostgreSQL Docker setup

echo "🧪 Testing PostgreSQL Docker Setup"
echo "=================================="

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down -v --remove-orphans 2>/dev/null || true

# Start just PostgreSQL first
echo "🐘 Starting PostgreSQL container..."
if docker-compose up -d postgres; then
    echo "✅ PostgreSQL container started"
else
    echo "❌ Failed to start PostgreSQL container"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Check PostgreSQL health
echo "🔍 Checking PostgreSQL health..."
if docker-compose exec postgres pg_isready -U postgres -d facial_processing; then
    echo "✅ PostgreSQL is healthy"
else
    echo "❌ PostgreSQL health check failed"
    docker-compose logs postgres
    exit 1
fi

# Test connection
echo "🔌 Testing PostgreSQL connection..."
if docker-compose exec postgres psql -U postgres -d facial_processing -c "SELECT 1;"; then
    echo "✅ PostgreSQL connection successful"
else
    echo "❌ PostgreSQL connection failed"
    docker-compose logs postgres
    exit 1
fi

# Build the application image
echo "🔨 Building application image..."
if docker-compose build api; then
    echo "✅ Application image built successfully"
else
    echo "❌ Failed to build application image"
    exit 1
fi

# Start Redis
echo "📦 Starting Redis..."
if docker-compose up -d redis; then
    echo "✅ Redis started"
else
    echo "❌ Failed to start Redis"
    exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo "Ready to start the full application with: make up"