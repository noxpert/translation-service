FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Data directory will be mounted from host; ensure it exists
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

EXPOSE 8081

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8081}
