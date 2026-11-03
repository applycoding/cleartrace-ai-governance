from __future__ import annotations

from cleartrace_db.session import libpq_dsn


def test_sqlalchemy_driver_suffix_is_removed() -> None:
    assert libpq_dsn("postgresql+psycopg://u:p@h:6432/db") == "postgresql://u:p@h:6432/db"


def test_plain_dsn_is_unchanged() -> None:
    assert libpq_dsn("postgresql://u:p@h:6432/db") == "postgresql://u:p@h:6432/db"
    assert libpq_dsn("host=h dbname=db") == "host=h dbname=db"
