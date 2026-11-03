# ADR-0002: Python 3.12 workspace with uv

## Status

Accepted (2026-11-03)

## Context

The platform is Python 3.12 with multiple services and shared contracts (BLUEPRINT section 15). We need reproducible installs for developers and CI.

## Decision

Use a single **uv** workspace at the repository root (`pyproject.toml`) with member packages:

- `packages/cleartrace-contracts` — shared Pydantic models and service protocols
- `services/core-api` — FastAPI governance API
- `db` — Alembic migrations and database helpers

Lockfile: `uv.lock`. Install with `uv sync --all-packages --group dev`.

## Consequences

CI and `make lint` invoke `uv run` for consistent environments. pip-tools was not chosen to reduce duplicate tooling alongside uv.
