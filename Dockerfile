# syntax=docker/dockerfile:1
# Single image for ALL services. The service to run is chosen at RUNTIME via the
# SERVICE env var (e.g. SERVICE=user_service), so the same image + one env var
# powers every service — works with Render/Railway (no build-args needed).
#
# Local/compose can still build per-service with --build-arg SERVICE=... but the
# runtime SERVICE env always wins.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# copy the whole app (all services + shared common)
COPY . /app

EXPOSE 8000
# Two modes:
#  - Single-container (default): run ALL services + gateway via the entrypoint.
#    The gateway listens on $PORT. Best for one-service free-tier hosts (Render).
#  - Per-service: set SERVICE=<pkg> (e.g. user_service) to run just that service.
#    Used by render.yaml (one Render service per component) and docker-compose.
CMD ["sh", "-c", "if [ -n \"$SERVICE\" ]; then exec uvicorn ${SERVICE}.main:app --host 0.0.0.0 --port ${PORT:-8000}; else exec python container_entrypoint.py; fi"]
