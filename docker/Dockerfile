# =============================================================================
# Multi-stage Dockerfile for Security-First RAG System
# =============================================================================
# Stage 1: Builder — install Python dependencies
# Stage 2: Runtime — slim image with non-root user
#
# SECURITY:
#   - Non-root user (appuser, UID 1000)
#   - No dev tools in final image
#   - Health check built in
#   - Only required files copied
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies for native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# SECURITY: Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY security/ ./security/
COPY rag/ ./rag/

# Create directories for data persistence
RUN mkdir -p /app/chroma_data /app/uploads && \
    chown -R appuser:appuser /app

# SECURITY: Switch to non-root user
USER appuser

# Environment defaults
ENV APP_ENV=production \
    APP_LOG_LEVEL=INFO \
    CHROMA_PERSIST_DIR=/app/chroma_data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port (default for local, overridden by Render)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')" || exit 1

# Run with uvicorn (Render sets PORT automatically)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"
