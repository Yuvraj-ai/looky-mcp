# syntax=docker/dockerfile:1

# ---- Backend image (Architecture §23: single uvicorn worker by design) ----
FROM python:3.12-slim

WORKDIR /app

# system deps for Pillow + asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 gcc libpq-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./

RUN pip install --no-cache-dir uv \
    && uv pip install --system -e .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# single worker: in-memory rate/concurrency limiter state matches Decision #9
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
