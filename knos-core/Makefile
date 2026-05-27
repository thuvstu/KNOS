# KnOS Core Makefile

.PHONY: up down dev-backend dev-frontend dev migrate install clean

# ─── Docker ───────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "PostgreSQL (PGroonga+pgvector+PostGIS) 起動完了"

down:
	docker compose down

# ─── Dev servers ──────────────────────────────────────────────
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "tmux or 2 terminals: make dev-backend / make dev-frontend"

# ─── DB ───────────────────────────────────────────────────────
migrate:
	cd backend && alembic upgrade head

# DB直接初期化（初回のみ）
db-init:
	docker compose exec db psql -U knos -d knos -f /docker-entrypoint-initdb.d/init.sql

# ─── Install ──────────────────────────────────────────────────
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# ─── Lint / format ────────────────────────────────────────────
lint:
	cd backend && ruff check app/
	cd frontend && npm run lint

format:
	cd backend && ruff format app/

# ─── Clean ────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	cd frontend && rm -rf .next
