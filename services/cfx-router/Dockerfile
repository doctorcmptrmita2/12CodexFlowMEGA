# CF-X Router Dockerfile
# Python FastAPI application

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder to system location
COPY --from=builder /root/.local /usr/local

# Copy application code
COPY . .

# Create /config directory (config will use defaults if file not found)
RUN mkdir -p /config

# Create non-root user
RUN useradd -m -u 1000 cfx && \
    chown -R cfx:cfx /app

USER cfx

EXPOSE 8000

# Health check (using urllib instead of requests to avoid extra dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

