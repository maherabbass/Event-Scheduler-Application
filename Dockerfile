# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install Python deps first (better layer caching)
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir .

# Copy migration files — needed at runtime for alembic
COPY migrations/ ./migrations/
COPY alembic.ini .

# Cloud Run injects PORT; default to 8080
EXPOSE 8080

# Use shell form so ${PORT:-8080} is expanded at container startup
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
