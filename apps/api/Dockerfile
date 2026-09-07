FROM python:3.13-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration first for cached layer builds
COPY pyproject.toml /app/

# Install python dependencies including postgres driver
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[postgres]"

# Copy application source code
COPY app /app/app

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Create storage directory for local fallback storage provider
RUN mkdir -p /app/storage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
