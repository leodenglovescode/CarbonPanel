SHELL := /bin/bash
.PHONY: dev backend frontend setup install lint lint-backend lint-frontend

UVICORN := backend/.venv/bin/uvicorn
PIP     := backend/.venv/bin/pip
PYTHON  := backend/.venv/bin/python
ALEMBIC := backend/.venv/bin/alembic

# Run both services in parallel
dev:
	@trap 'kill 0' INT; \
	(cd backend && ../$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload) & \
	(cd frontend && npm run dev) & \
	wait

# Backend only
backend:
	cd backend && ../$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend only
frontend:
	cd frontend && npm run dev

# First-time setup
setup:
	@echo "--- Setting up backend ---"
	python3 -m venv backend/.venv
	$(PIP) install -q -e "backend/.[dev]"
	cd backend && ../$(ALEMBIC) upgrade head
	cd backend && ../$(PYTHON) -m app.scripts.seed_admin
	@echo "--- Setting up frontend ---"
	cd frontend && npm install
	@echo ""
	@echo "Setup complete. Run 'make dev' to start."

install: setup

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ../$(PYTHON) -m ruff check app

lint-frontend:
	cd frontend && npm run lint
