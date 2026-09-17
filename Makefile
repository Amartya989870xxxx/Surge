SHELL := /bin/bash
.PHONY: help install backend-install frontend-install backend frontend test clean

help:
	@echo "Surge - available commands:"
	@echo "  make install   Install backend + frontend dependencies"
	@echo "  make backend   Start the backend API (installs deps on first run)"
	@echo "  make frontend  Start the frontend dev server (installs deps on first run)"
	@echo "  make test      Run the backend test suite"
	@echo "  make clean     Remove local venv/node_modules/build artifacts"

install: backend-install frontend-install
	@echo "Done. Run 'make backend' and 'make frontend' in two separate terminals."

backend-install:
	@if [ ! -x backend/.venv/bin/python ]; then \
		echo "Setting up backend virtual environment..." && \
		cd backend && \
		( command -v uv >/dev/null 2>&1 && uv venv .venv || python3 -m venv .venv ) && \
		.venv/bin/pip install -q --upgrade pip && \
		.venv/bin/pip install -q -e ".[dev]"; \
	fi

backend: backend-install
	@PORT=8000; \
	if [ -f .env ] && grep -q SURGE_PUBLIC_BASE_URL .env; then \
		FOUND=$$(grep SURGE_PUBLIC_BASE_URL .env | grep -oE '[0-9]+$$'); \
		[ -n "$$FOUND" ] && PORT=$$FOUND; \
	fi; \
	echo "Starting backend on http://localhost:$$PORT (Ctrl+C to stop)"; \
	cd backend && \
	set -a && \
	[ -f ../.env ] && source ../.env; \
	set +a; \
	exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port $$PORT

frontend-install:
	@if [ ! -d frontend/node_modules ]; then \
		echo "Installing frontend dependencies..." && \
		cd frontend && npm install; \
	fi

frontend: frontend-install
	@echo "Starting frontend dev server (Ctrl+C to stop)"
	@cd frontend && exec npm run dev

test: backend-install
	@cd backend && .venv/bin/python -m pytest -q

clean:
	@rm -rf backend/.venv backend/surge.egg-info backend/.pytest_cache frontend/node_modules frontend/dist
	@echo "Cleaned. Run 'make install' to set up again."
