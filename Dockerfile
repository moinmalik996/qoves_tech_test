FROM python:3.12-slim

# Environment variables for Rich logging and Prometheus
ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color
ENV COLORTERM=truecolor
ENV FORCE_COLOR=1
ENV ENABLE_METRICS=true
ENV LOG_LEVEL=INFO

WORKDIR /app

# Install system dependencies for Rich terminal support
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY pyproject.toml ./
RUN pip install uv && uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Create logs directory and set permissions
RUN mkdir -p logs && chmod 755 logs

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]