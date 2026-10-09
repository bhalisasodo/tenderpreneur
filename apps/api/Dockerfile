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

# Copy application source code and database migration configuration
COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Create storage directory and run the API as a non-root user
RUN mkdir -p /app/storage && \
    addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app app && \
    chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
