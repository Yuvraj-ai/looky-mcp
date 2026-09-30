# syntax=docker/dockerfile:1

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Backend + Serve Frontend
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 gcc libpq-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/alembic.ini ./

RUN pip install --no-cache-dir uv \
    && uv pip install --system -e .

# Copy built frontend assets
COPY --from=frontend-builder /build/dist /app/static

ENV PYTHONUNBUFFERED=1
ENV STATIC_DIR=/app/static

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
