# EduSentinel – Docker Setup Guide

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Nginx :80/:443                │
│              (reverse proxy / TLS)              │
└───────────┬──────────────────┬──────────────────┘
            │                  │
     /api/* │           / (UI) │
            ▼                  ▼
   ┌────────────────┐  ┌────────────────┐
   │  Backend :8000 │  │ Frontend :3000 │
   │   (FastAPI)    │  │   (Next.js)    │
   └───────┬────────┘  └────────────────┘
           │
    ┌──────┼──────────────────┐
    │      │                  │
    ▼      ▼                  ▼
┌──────┐ ┌───────┐  ┌─────────────────┐
│  PG  │ │ Redis │  │  ML Svc :8001   │
│ :5432│ │ :6379 │  │   (FastAPI)     │
└──────┘ └───────┘  └─────────────────┘
                    Celery Worker / Beat
                    (share backend image)
```

## Prerequisites

- Docker Desktop ≥ 24 (or Docker Engine + Compose v2)
- `openssl` in PATH (for TLS helpers)
- 4 GB RAM recommended (ML service loads scikit-learn + XGBoost)

---

## Local Development

### 1. Clone and configure

```bash
git clone <repo-url> && cd EduSentinel
cp .env.example .env
# Edit .env – minimum required changes:
#   APP_SECRET_KEY  → any random string (dev is fine)
#   JWT_SECRET_KEY  → any random string (dev is fine)
```

### 2. Start the stack

```bash
# Build images and start all services with hot-reload
make up
# or: docker compose up --build
```

Services started:

| Service | URL |
|---------|-----|
| Frontend (Next.js) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| ML Service | http://localhost:8001 |
| ML docs | http://localhost:8001/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Nginx proxy | http://localhost:80 |

### 3. Run database migrations

```bash
# In a second terminal, once the backend container is healthy:
make migrate
# or: docker compose exec backend alembic upgrade head
```

### 4. Seed sample data

```bash
make seed
```

### 5. Common dev commands

```bash
make logs            # tail all logs
make ps              # show container status
make shell-backend   # bash into backend
make shell-db        # psql prompt
make test            # run all tests
make lint            # ruff + mypy
make retrain         # retrain ML model
make down            # stop and delete volumes
```

---

## Environment Variables Reference

All variables live in `.env` (copy from `.env.example`).

### Required in all environments

| Variable | Example | Purpose |
|----------|---------|---------|
| `DB_NAME` | `edusentinel` | PostgreSQL database name |
| `DB_USER` | `edu_user` | PostgreSQL user |
| `DB_PASSWORD` | `strongpassword` | PostgreSQL password |
| `JWT_SECRET_KEY` | `<32+ char random>` | Signs JWT tokens |
| `APP_SECRET_KEY` | `<32+ char random>` | General app secret |

### Required in production

| Variable | Example | Purpose |
|----------|---------|---------|
| `REDIS_PASSWORD` | `<random>` | Redis AUTH password |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com/api/v1` | API URL seen by browser |

### Optional / service-specific

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_ENV` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `true` | Enables Swagger UI and verbose logs |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Token lifetime |
| `ML_MODEL_STORE_PATH` | `/app/artifacts` | Where model files are saved |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | — | Email alerts |
| `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | — | Object storage for model artifacts |

Generate strong secrets:

```bash
openssl rand -hex 32   # for JWT_SECRET_KEY / APP_SECRET_KEY
openssl rand -hex 16   # for REDIS_PASSWORD
```

---

## Production Deployment

### 1. Generate TLS certificates

**Option A – Let's Encrypt (recommended)**

```bash
# Install certbot on the host, then:
certbot certonly --standalone -d yourdomain.com

# Copy certs into the repo:
mkdir -p infra/nginx/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem infra/nginx/ssl/edusentinel.crt
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   infra/nginx/ssl/edusentinel.key
```

**Option B – Self-signed (local HTTPS testing only)**

```bash
make ssl-self-signed
```

### 2. Create a production `.env`

```bash
cp .env.example .env.prod
# Then set:
APP_ENV=production
DEBUG=false
DB_PASSWORD=<strong-password>
JWT_SECRET_KEY=<openssl rand -hex 32>
APP_SECRET_KEY=<openssl rand -hex 32>
REDIS_PASSWORD=<openssl rand -hex 16>
NEXT_PUBLIC_API_URL=https://yourdomain.com/api/v1
```

> Keep `.env.prod` outside version control.

### 3. Build production images

```bash
# Builds with target: runner (minimal, no dev tools or source mounts)
make prod-build
# or:
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
```

### 4. Start the production stack

```bash
# Use your production .env
cp .env.prod .env
make prod-up
# or:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Run migrations on first deploy

```bash
make prod-migrate
# or:
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec backend alembic upgrade head
```

### 6. Verify all services are healthy

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
# All services should show "healthy" or "running"

curl -s https://yourdomain.com/api/v1/health
# → {"status":"ok"}
```

---

## Image Summary

| Service | Base image | Multi-stage | Final size (approx) |
|---------|-----------|-------------|---------------------|
| Frontend | `node:20-alpine` | deps → builder → runner | ~150 MB |
| Backend | `python:3.12-slim` | builder → runner | ~250 MB |
| ML Service | `python:3.12-slim` | builder → runner | ~600 MB (sklearn+XGBoost) |
| PostgreSQL | `postgres:16-alpine` | — | ~250 MB |
| Redis | `redis:7-alpine` | — | ~35 MB |
| Nginx | `nginx:1.27-alpine` | — | ~20 MB |

---

## Volume Reference

| Volume | Mounted to | Contains |
|--------|-----------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | All database rows |
| `redis_data` | `/data` | Redis AOF persistence |
| `ml_artifacts` | `/app/artifacts` | Trained model files (`.joblib`, metadata JSON) |

> **Warning:** `make down` deletes all volumes. Use `docker compose down` (no `-v`) to
> stop containers without deleting data.

---

## Useful One-liners

```bash
# View logs for a single service
docker compose logs -f backend

# Restart a single service without rebuilding
docker compose restart backend

# Force-rebuild a single service
docker compose up -d --build backend

# Open psql prompt
make shell-db

# Check ML model registry
docker compose exec ml_service python -c "from app.registry.model_registry import ModelRegistry; print(ModelRegistry().list())"

# Backup the database
docker compose exec postgres pg_dump -U edu_user edusentinel > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20250101.sql | docker compose exec -T postgres psql -U edu_user edusentinel
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `backend` exits immediately | Check `DATABASE_URL` in `.env`; run `make logs` |
| Migrations fail on first run | Run `make migrate` after `make up` (DB needs to be healthy first) |
| Frontend shows "Network Error" | Verify `NEXT_PUBLIC_API_URL` points to the backend |
| ML model not found on startup | Run `make retrain` to train an initial model |
| Port 80/443 already in use | Stop local web server: `sudo systemctl stop nginx` |
| Nginx 502 Bad Gateway | Backend/frontend not healthy yet; wait 30s and refresh |
| `permission denied` on artifacts volume | ML container runs as non-root; the `Dockerfile` `chown`s the dir — rebuild with `make build` |
