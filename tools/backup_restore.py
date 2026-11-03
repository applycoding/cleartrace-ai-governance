#!/usr/bin/env python3
"""Postgres dump/restore helpers for T-05 backup evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import psycopg

DATA_POLICY_TABLES = (
    "tenant_data_policy",
    "retention_rule",
    "legal_hold",
    "encrypted_payload",
    "record_data_key",
    "deletion_request",
    "deletion_certificate",
    "data_policy_backup_snapshot",
)


def ensure_postgres_cluster(
    data_dir: Path,
    port: int,
    *,
    superuser: str = "cleartrace_super",
) -> None:
    """Start a dedicated Postgres cluster for restore tests (not a separate physical node)."""
    pg_bin = os.environ.get("PG_BIN", "/usr/lib/postgresql/16/bin")
    initdb = Path(pg_bin) / "initdb"
    pg_ctl = Path(pg_bin) / "pg_ctl"
    if not data_dir.joinpath("PG_VERSION").exists():
        subprocess.run(
            [
                str(initdb),
                "-D",
                str(data_dir),
                "-U",
                superuser,
                "--auth-local=trust",
                "--auth-host=trust",
            ],
            check=True,
            capture_output=True,
        )
        conf = data_dir / "postgresql.conf"
        conf.write_text(
            conf.read_text(encoding="utf-8")
            + f"\nlisten_addresses = '127.0.0.1'\nport = {port}\n"
            + f"unix_socket_directories = '{data_dir}'\n",
            encoding="utf-8",
        )
        hba = data_dir / "pg_hba.conf"
        hba.write_text(
            hba.read_text(encoding="utf-8") + "host all all 127.0.0.1/32 trust\n",
            encoding="utf-8",
        )
    pg_isready = Path(pg_bin) / "pg_isready"
    if pg_isready.exists():
        ready = subprocess.run(
            [str(pg_isready), "-h", "127.0.0.1", "-p", str(port)],
            capture_output=True,
        )
        if ready.returncode == 0:
            return
    subprocess.run(
        [str(pg_ctl), "-D", str(data_dir), "-l", str(data_dir / "postgres.log"), "start"],
        check=True,
        capture_output=True,
    )
    time.sleep(1)


def export_encrypted_object_store(dsn: str, dest: Path) -> dict[str, str]:
    """Write ciphertext objects to dest/{payload_id} and return id -> sha256 map."""
    dest.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, ciphertext FROM encrypted_payload ORDER BY id")
        for payload_id, ciphertext in cur.fetchall():
            blob = bytes(ciphertext)
            digest = hashlib.sha256(blob).hexdigest()
            path = dest / f"{payload_id}.bin"
            path.write_bytes(blob)
            manifest[str(payload_id)] = digest
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return manifest


def load_object_manifest(object_dir: Path) -> dict[str, str]:
    return json.loads((object_dir / "manifest.json").read_text(encoding="utf-8"))


def verify_object_store(object_dir: Path, expected: dict[str, str]) -> tuple[int, int]:
    actual = load_object_manifest(object_dir)
    if set(actual.keys()) != set(expected.keys()):
        return 0, len(expected)
    matched = sum(1 for key, digest in expected.items() if actual.get(key) == digest)
    return matched, len(expected)


def table_row_checksums(dsn: str, tables: tuple[str, ...] = DATA_POLICY_TABLES) -> dict[str, str]:
    """Per-table checksum over row hashes (stable ordering by primary key)."""
    checksums: dict[str, str] = {}
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for table in tables:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema = 'public' AND table_name = %s
                )
                """,
                (table,),
            )
            if not cur.fetchone()[0]:
                checksums[table] = "missing"
                continue
            cur.execute(
                f"""
                SELECT md5(coalesce(string_agg(row_hash, '' ORDER BY row_hash), ''))
                FROM (
                  SELECT md5(t::text) AS row_hash
                  FROM {table} AS t
                ) s
                """
            )
            row = cur.fetchone()
            checksums[table] = row[0] if row and row[0] else "empty"
    return checksums


def _pg_tool(name: str) -> str:
    """Return a Postgres client tool, preferring PG_BIN so the client matches the server."""
    pg_bin = os.environ.get("PG_BIN")
    if pg_bin and (Path(pg_bin) / name).exists():
        return str(Path(pg_bin) / name)
    return name


def pg_dump_roles(super_dsn: str, roles_path: Path) -> None:
    """Dump cluster roles (global objects that pg_dump leaves out)."""
    roles_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_pg_tool("pg_dumpall"), "--roles-only", "--no-role-passwords", "-f", str(roles_path),
         f"--dbname={super_dsn}"],
        check=True,
        capture_output=True,
    )


def restore_roles(super_dsn: str, roles_path: Path) -> list[str]:
    """Create the dumped roles that are missing on the restore cluster.

    Each dumped ``CREATE ROLE`` is applied only when the role does not exist,
    and its ``ALTER ROLE`` attributes are applied with it. Returns the roles created.
    """
    created: list[str] = []
    statements = [
        line.strip()
        for line in roles_path.read_text(encoding="utf-8").splitlines()
        if line.startswith(("CREATE ROLE ", "ALTER ROLE "))
    ]
    with psycopg.connect(super_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT rolname FROM pg_roles")
        existing = {row[0] for row in cur.fetchall()}
        for statement in statements:
            role = statement.split()[2].rstrip(";").strip('"')
            if role in existing and role not in created:
                continue
            cur.execute(statement)
            if statement.startswith("CREATE ROLE "):
                created.append(role)
    return created


def pg_dump_database(super_dsn: str, dump_path: Path) -> None:
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            _pg_tool("pg_dump"),
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "-f",
            str(dump_path),
            super_dsn,
        ],
        check=True,
        capture_output=True,
    )


def drop_and_create_database(super_dsn: str, db_name: str) -> None:
    admin = super_dsn.rsplit("/", maxsplit=1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (db_name,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.execute(f'CREATE DATABASE "{db_name}"')


def pg_restore_database(super_dsn: str, db_name: str, dump_path: Path) -> None:
    target = super_dsn.rsplit("/", maxsplit=1)[0] + f"/{db_name}"
    subprocess.run(
        [_pg_tool("pg_restore"), "--no-owner", "--no-acl", f"--dbname={target}", str(dump_path)],
        check=True,
        capture_output=True,
    )


def compare_table_checksums(left: dict[str, str], right: dict[str, str]) -> tuple[int, int]:
    keys = set(left.keys()) | set(right.keys())
    matched = sum(
        1 for key in keys if left.get(key) == right.get(key) and left.get(key) != "missing"
    )
    return matched, len(keys)
