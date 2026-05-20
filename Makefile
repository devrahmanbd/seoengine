.PHONY: up down deploy test smoke seed migrate db-shell

# ─── One-command deploy ───────────────────────────────────────
# Builds everything and starts all services.
# Set SECRET_KEY env var for production (auto-generated if not set).
deploy:
	docker compose up -d --build

# Start existing services (no rebuild)
up:
	docker compose up -d

# Stop everything
down:
	docker compose down

# Rebuild single service (e.g., make rebuild backend)
rebuild:
	docker compose up -d --build $(filter-out $@,$(MAKECMDGOALS))

# View logs
logs:
	docker compose logs -f

# ─── Tests ─────────────────────────────────────────────────────
test:
	cd backend && PYTHONPATH=. venv/bin/python3 -m pytest tests/ -q --tb=short

smoke:
	cd backend && PYTHONPATH=. venv/bin/python3 -m pytest \
		tests/test_core/ tests/test_executor/ \
		tests/test_atropos/test_base_env.py \
		tests/test_atropos/test_scored_data_api.py \
		-q --tb=short

# ─── Database ──────────────────────────────────────────────────
seed:
	cd backend && PYTHONPATH=. venv/bin/python3 seed.py

migrate:
	cd backend && PYTHONPATH=. venv/bin/python3 -m alembic upgrade head

migrate-new:
	cd backend && PYTHONPATH=. venv/bin/python3 -m alembic revision --autogenerate -m "$(name)"

db-shell:
	docker compose exec postgres psql -U rahman -d zenseo

# ─── Local Dev (no Docker) ────────────────────────────────────
dev-backend:
	cd backend && PYTHONPATH=. SECRET_KEY=dev-key venv/bin/python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd admin && npm run dev

shell:
	cd backend && PYTHONPATH=. venv/bin/python3
