# ─────────────────────────────────────────────
#  EduSentinel – Developer Makefile
# ─────────────────────────────────────────────
.PHONY: help up down build logs ps \
        migrate seed test lint \
        retrain shell-backend shell-ml shell-frontend shell-db \
        prod-up prod-down prod-build prod-migrate \
        ssl-self-signed clean

COMPOSE      = docker compose
COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ── Default target ────────────────────────────
help:
	@echo ""
	@echo "  EduSentinel – available commands"
	@echo ""
	@echo "  Development:"
	@echo "    make up              Start all services (hot-reload)"
	@echo "    make down            Stop and remove containers + volumes"
	@echo "    make build           Rebuild images"
	@echo "    make logs            Tail logs from all services"
	@echo "    make ps              Show running containers"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate         Run Alembic migrations"
	@echo "    make seed            Seed database with sample data"
	@echo ""
	@echo "  Quality:"
	@echo "    make test            Run backend + ML tests"
	@echo "    make lint            Lint + type-check backend"
	@echo ""
	@echo "  ML:"
	@echo "    make retrain         Retrain the risk prediction model"
	@echo ""
	@echo "  Shells:"
	@echo "    make shell-backend   Open bash in backend container"
	@echo "    make shell-ml        Open bash in ml_service container"
	@echo "    make shell-frontend  Open sh in frontend container"
	@echo "    make shell-db        Open psql in postgres container"
	@echo ""
	@echo "  Production:"
	@echo "    make prod-up         Start stack in production mode"
	@echo "    make prod-down       Stop production stack"
	@echo "    make prod-build      Build production images (no cache)"
	@echo "    make prod-migrate    Run migrations against prod DB"
	@echo ""
	@echo "  TLS:"
	@echo "    make ssl-self-signed Generate self-signed cert for local HTTPS"
	@echo ""

# ── Development ───────────────────────────────

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down -v

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# ── Database ──────────────────────────────────

migrate:
	$(COMPOSE) exec backend alembic upgrade head

seed:
	$(COMPOSE) exec backend python -m app.utils.seeder

# ── Quality ───────────────────────────────────

test:
	$(COMPOSE) exec backend  pytest tests/ -v --tb=short
	$(COMPOSE) exec ml_service pytest tests/ -v --tb=short

lint:
	$(COMPOSE) exec backend ruff check app/
	$(COMPOSE) exec backend mypy app/

# ── ML ────────────────────────────────────────

retrain:
	$(COMPOSE) exec ml_service python -m app.pipeline.trainer

# ── Shells ────────────────────────────────────

shell-backend:
	$(COMPOSE) exec backend bash

shell-ml:
	$(COMPOSE) exec ml_service bash

shell-frontend:
	$(COMPOSE) exec frontend sh

shell-db:
	$(COMPOSE) exec postgres psql -U $${DB_USER:-edu_user} -d $${DB_NAME:-edusentinel}

# ── Production ────────────────────────────────

prod-up:
	$(COMPOSE_PROD) up -d

prod-down:
	$(COMPOSE_PROD) down

prod-build:
	$(COMPOSE_PROD) build --no-cache

prod-migrate:
	$(COMPOSE_PROD) exec backend alembic upgrade head

# ── TLS helpers ───────────────────────────────

ssl-self-signed:
	@mkdir -p infra/nginx/ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	  -keyout infra/nginx/ssl/edusentinel.key \
	  -out    infra/nginx/ssl/edusentinel.crt \
	  -subj   "/C=IN/ST=State/L=City/O=EduSentinel/CN=localhost"
	@echo "Self-signed cert written to infra/nginx/ssl/"

# ── Cleanup ───────────────────────────────────

clean:
	$(COMPOSE) down -v --rmi local --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
