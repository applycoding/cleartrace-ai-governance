.PHONY: up down test lint migrate sbom secrets-scan trivy

ROOT := $(CURDIR)
export PATH := $(HOME)/.local/bin:$(HOME)/miniforge3/bin:$(PATH)
export LD_LIBRARY_PATH := $(HOME)/miniforge3/lib:$(LD_LIBRARY_PATH)

up:
	bash scripts/stack_up.sh

down:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose -f deploy/compose/docker-compose.yml down; \
	fi
	-pkill -f "pgbouncer $(ROOT)/.data/pgbouncer.ini" || true

migrate:
	cd db && uv run alembic -c alembic.ini upgrade head

test: up
	uv run pytest -q tests services --ignore=tests/integration --cov=services/core-api/src --cov=packages/cleartrace-contracts/src --cov=db/src --cov-report=term-missing
	uv run pytest -q tests/integration services

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy packages/cleartrace-contracts/src services/core-api/src services/notifier/src services/reports/src db/src

sbom:
	@if command -v syft >/dev/null 2>&1; then \
		syft dir:$(ROOT) -o cyclonedx-json > sbom.json; \
	else \
		uv run python tools/sbom_placeholder.py; \
	fi

secrets-scan:
	@if command -v gitleaks >/dev/null 2>&1; then gitleaks detect --no-git -v; else uv run python tools/secrets_scan.py; fi

trivy:
	@if command -v trivy >/dev/null 2>&1; then trivy fs --severity HIGH,CRITICAL $(ROOT); else uv run python tools/trivy_placeholder.py; fi
