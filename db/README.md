# ClearTrace database

Alembic migrations, row-level security, bitemporal tables, SECURITY DEFINER procedures, audit and outbox tables.

```bash
cd db
uv run alembic -c alembic.ini upgrade head
```

Use `cleartrace_db.session.tenant_transaction` to set `app.tenant_id` with `SET LOCAL` for PgBouncer transaction pooling.
