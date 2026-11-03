from __future__ import annotations

from uuid import UUID

from uuid6 import uuid7

from cleartrace_policy_watch.normalizer import snapshot_sha256


class PostgresPolicyRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def ensure_source(
        self, slug: str, *, name_en: str, name_fr: str, url_en: str, url_fr: str
    ) -> UUID:
        source_id = uuid7()
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("SET ROLE cleartrace_app")
            cur.execute(
                """
                INSERT INTO policy_source (id, slug, name_en, name_fr, canonical_url_en, canonical_url_fr)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET name_en = EXCLUDED.name_en
                RETURNING id
                """,
                (source_id, slug, name_en, name_fr, url_en, url_fr),
            )
            row = cur.fetchone()
            assert row is not None
            return UUID(str(row[0]))

    def save_snapshot(
        self,
        source_id: UUID,
        locale: str,
        html: str,
        *,
        active: bool = False,
    ) -> UUID:
        snap_id = uuid7()
        digest = snapshot_sha256(html)
        import psycopg

        with psycopg.connect(self._dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("SET ROLE cleartrace_app")
            if active:
                cur.execute(
                    "UPDATE policy_snapshot SET is_active = false WHERE policy_source_id = %s AND locale = %s",
                    (source_id, locale),
                )
            cur.execute(
                """
                INSERT INTO policy_snapshot (
                  id, policy_source_id, locale, raw_content, content_sha256, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (snap_id, source_id, locale, html, digest, active),
            )
        return snap_id
