# ClearTrace core API

FastAPI governance API: OIDC login, Cedar authorization, tenant context, RFC 9457 errors, pagination, ETag/If-Match, and idempotency keys.

Run locally:

```bash
uv sync --all-packages --group dev
make up
uv run cleartrace-api
```

Environment variables use the `CLEARTRACE_` prefix (see `services/core-api/src/cleartrace_core_api/config.py`).
