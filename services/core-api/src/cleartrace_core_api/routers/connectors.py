from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_connectors.manifest import ConnectorManifest
from cleartrace_connectors.runtime import ConnectorRuntime
from fastapi import APIRouter, Request
from pydantic import BaseModel
from uuid6 import uuid7

router = APIRouter(prefix="/connectors", tags=["connectors"])

_MANIFESTS = Path(__file__).resolve().parents[5] / "services" / "connectors" / "manifests"
_installed: dict[str, dict[str, str]] = {}


class ConnectorSummary(BaseModel):
    id: UUID
    name: str
    version: str


class ConnectorInstall(BaseModel):
    manifest_name: str


class ConnectorRunBody(BaseModel):
    system_id: UUID
    fixture_name: str = "default"


@router.get("")
async def list_connectors() -> dict[str, list[ConnectorSummary]]:
    items = [
        ConnectorSummary(id=UUID(cid), name=meta["name"], version=meta["version"])
        for cid, meta in _installed.items()
    ]
    return {"items": items}


@router.post("", status_code=201)
async def install_connector(request: Request, body: ConnectorInstall) -> dict[str, str]:
    auth = request.state.auth
    settings = request.app.state.settings
    manifest_path = _MANIFESTS / body.manifest_name
    if not manifest_path.exists():
        manifest_path = _MANIFESTS / f"{body.manifest_name}.yaml"
    runtime = ConnectorRuntime(
        settings.database_url.replace("+psycopg", ""),
        auth.tenant_id,
    )
    manifest = runtime.load_manifest(manifest_path)
    connector_id = uuid7()
    _installed[str(connector_id)] = {"name": manifest.name, "version": manifest.version}
    return {"id": str(connector_id), "name": manifest.name}


@router.post("/{connector_id}:run")
async def run_connector(
    connector_id: UUID,
    request: Request,
    body: ConnectorRunBody,
) -> dict[str, Any]:
    auth = request.state.auth
    settings = request.app.state.settings
    meta = _installed.get(str(connector_id))
    if meta is None:
        return {"status": "not_found"}
    manifest_path = _MANIFESTS / f"{meta['name']}.yaml"
    runtime = ConnectorRuntime(
        settings.database_url.replace("+psycopg", ""),
        auth.tenant_id,
    )
    manifest = ConnectorManifest.load_path(manifest_path)
    updates = runtime.run_manifest_for_system(
        manifest,
        system_id=body.system_id,
        fixture_name=body.fixture_name,
    )
    return {"connector_id": str(connector_id), "fields_updated": len(updates)}
