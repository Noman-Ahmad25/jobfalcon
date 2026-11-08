# ==============================================================================
# JobFalcon Backend Dockerfile
# Production-ready Python 3.12 container running FastAPI via Uvicorn
# ==============================================================================

FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build dependencies and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /bin/

# Copy dependency definition
COPY pyproject.toml .

# Install dependencies into virtualenv using pyproject.toml
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install -r pyproject.toml

# ==============================================================================
# Runner Stage
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime utilities (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Copy backend application code
COPY app ./app

# Create directory for persistent SQLite database files
RUN mkdir -p /app/data

# Expose backend API port
EXPOSE 8000

# Health check probe against API health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/healthz || exit 1

# Launch production ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
