# ==============================================================================
# Production Dockerfile: FastAPI Backend & Outbox Execution Worker
# Team CrackerX · Ask-Your-Payments FinOps Platform
# ==============================================================================

FROM python:3.11-slim AS base

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system build dependencies and security utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy APIMatic Python SDK and install into environment
COPY paypal_erp_sdk /app/paypal_erp_sdk
RUN pip install --no-cache-dir ./paypal_erp_sdk/sdk/python

# Copy application source code
COPY config.py database.py models.py main.py execution_worker.py ingestion_worker.py ai_router.py ai_schema_validators.py ./
COPY *.json ./

# Security: Run as dedicated non-root application user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -m appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose FastAPI HTTP server port
EXPOSE 8000

# Health check to ensure API readiness
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command: Launch FastAPI production server with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
