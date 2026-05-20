#!/usr/bin/env bash
set -euo pipefail

# ─── ZenSEO AI — Production Deploy ────────────────────────────
# Run this on your Ubuntu 24.04 server to pull & start the stack.
#
# Prerequisites:
#   curl -fsSL https://get.docker.com | bash
#   sudo usermod -aG docker $USER
#   (log out and back in)
#
# Usage:
#   GITHUB_USER=devrahmanbd \
#   GITHUB_TOKEN=ghp_xxx \
#   SECRET_KEY=$(openssl rand -hex 32) \
#   bash deploy.sh

REPO="seoengine"
GITHUB_USER="${GITHUB_USER:?Set GITHUB_USER}"
GITHUB_TOKEN="${GITHUB_TOKEN:?Set GITHUB_TOKEN}"
SECRET_KEY="${SECRET_KEY:?Set SECRET_KEY}"
TAG="${TAG:-latest}"

echo "==> Logging into ghcr.io..."
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin

echo "==> Pulling images..."
docker pull "ghcr.io/$GITHUB_USER/$REPO-backend:$TAG"
docker pull "ghcr.io/$GITHUB_USER/$REPO-frontend:$TAG"
docker pull "ghcr.io/$GITHUB_USER/$REPO-ml-service:$TAG"

echo "==> Creating data directory..."
mkdir -p data

echo "==> Starting stack..."
docker compose -f - up -d <<STACK
services:
  postgres:
    image: postgres:16-alpine
    container_name: zenseo-postgres
    environment:
      POSTGRES_DB: zenseo
      POSTGRES_USER: rahman
      POSTGRES_PASSWORD: zenseo123
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rahman -d zenseo"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: zenseo-redis
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redisdata:/data
    restart: unless-stopped

  backend:
    image: ghcr.io/$GITHUB_USER/$REPO-backend:$TAG
    container_name: zenseo-backend
    environment:
      DATABASE_URL: postgresql://rahman:zenseo123@postgres:5432/zenseo
      REDIS_URL: redis://redis:6379
      SECRET_KEY: $SECRET_KEY
      ENVIRONMENT: production
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; exit(0) if urllib.request.urlopen(\"http://localhost:8000/health\").status == 200 else exit(1)'"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped

  ml-service:
    image: ghcr.io/$GITHUB_USER/$REPO-ml-service:$TAG
    container_name: zenseo-ml
    environment:
      DATABASE_URL: postgresql://rahman:zenseo123@postgres:5432/zenseo
      ML_API_KEY: $ML_API_KEY
      LOG_LEVEL: INFO
    ports:
      - "127.0.0.1:8001:8000"
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 4G
    restart: unless-stopped

  frontend:
    image: ghcr.io/$GITHUB_USER/$REPO-frontend:$TAG
    container_name: zenseo-frontend
    environment:
      VITE_API_URL: http://backend:8000
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      backend:
        condition: service_started
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
STACK

echo ""
echo "==> Done! Services:"
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo ""
echo "==> Admin login: admin@zenseo.ai / admin123"
echo ""
echo "==> To set up a reverse proxy (Nginx/Caddy), point it to :3000 for frontend"
echo "    or :8000 for the API."
