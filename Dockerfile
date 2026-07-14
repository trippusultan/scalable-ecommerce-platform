# syntax=docker/dockerfile:1
# Multi-stage image for ALL services. Pass SERVICE=<dir name> at build time,
# e.g.  docker build -f Dockerfile --build-arg SERVICE=user_service -t ecom-user .
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# copy app code
COPY common /app/common
COPY ${SERVICE} /app/${SERVICE}

EXPOSE 8000
# SERVICE_NAME is injected by docker-compose; uvicorn module = <service>/main:app
CMD ["sh", "-c", "uvicorn ${SERVICE}.main:app --host 0.0.0.0 --port 8000"]
