SHELL := /bin/bash
.PHONY: dev backend frontend setup install lint lint-backend lint-frontend

UVICORN := backend/.venv/bin/uvicorn
PIP     := backend/.venv/bin/pip
PYTHON  := backend/.venv/bin/python
ALEMBIC := backend/.venv/bin/alembic
RUFF    := backend/.venv/bin/ruff
BACKEND_PORT := 8000

# Run both services in parallel
dev:
	@if ss -ltn '( sport = :$(BACKEND_PORT) )' | grep -q ':$(BACKEND_PORT)'; then \
		echo "Port $(BACKEND_PORT) is already in use. Stop the existing backend process before running 'make dev'."; \
		exit 1; \
	fi
	@trap 'kill 0' EXIT INT TERM; \
	(cd backend && ../$(UVICORN) app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload) & \
	backend_pid=$$!; \
	(cd frontend && npm run dev) & \
	frontend_pid=$$!; \
	wait -n $$backend_pid $$frontend_pid; \
	status=$$?; \
	kill $$backend_pid $$frontend_pid 2>/dev/null || true; \
	wait $$backend_pid $$frontend_pid 2>/dev/null || true; \
	exit $$status

# Backend only
backend:
	@if ss -ltn '( sport = :$(BACKEND_PORT) )' | grep -q ':$(BACKEND_PORT)'; then \
		echo "Port $(BACKEND_PORT) is already in use. Stop the existing backend process before running 'make backend'."; \
		exit 1; \
	fi
	cd backend && ../$(UVICORN) app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

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
	cd backend && ../$(RUFF) check app

lint-frontend:
	cd frontend && npm run lint
