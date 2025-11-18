#!/usr/bin/env bash
# Quick test runner script

set -e

echo "🧪 Running Facial Region SVG Service Tests"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest is not installed"
    echo "Install with: pip install pytest pytest-cov httpx"
    exit 1
fi

# Run tests with different options based on arguments
case "${1:-all}" in
    fast)
        echo "⚡ Running fast tests only..."
        pytest -m "not slow" -v
        ;;
    coverage)
        echo "📊 Running tests with coverage..."
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo "✅ Coverage report generated in htmlcov/index.html"
        ;;
    submit)
        echo "🎯 Running submit endpoint tests..."
        pytest tests/test_submit_endpoint.py -v
        ;;
    watch)
        echo "👀 Running tests in watch mode..."
        pytest-watch
        ;;
    debug)
        echo "🐛 Running tests with debugging..."
        pytest -v --tb=long --pdb
        ;;
    *)
        echo "🚀 Running all tests..."
        pytest -v
        ;;
esac

echo ""
echo "✅ Tests completed!"
