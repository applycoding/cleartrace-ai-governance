from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_connectors.manifest import ConnectorManifest
from cleartrace_connectors.runtime import ConnectorRuntime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from uuid6 import uuid7

router = APIRouter(prefix="/connectors", tags=["connectors"])

_MANIFESTS = Path(__file__).resolve().parents[5] / "services" / "connectors" / "manifests"
_installed: dict[str, dict[str, str]] = {}


class ConnectorSummary(BaseModel):
    id: UUID
    name: str
    version: str


class ConnectorInstall(BaseModel):
    # A shipped manifest name such as ``mlflow`` or ``mlflow.yaml``; never a path.
    manifest_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}(\.yaml)?$")


class ConnectorRunBody(BaseModel):
    system_id: UUID
    fixture_name: str = Field(default="default", pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")


@router.get("")
async def list_connectors(request: Request) -> dict[str, list[ConnectorSummary]]:
    tenant = str(request.state.auth.tenant_id)
    items = [
        ConnectorSummary(id=UUID(cid), name=meta["name"], version=meta["version"])
        for cid, meta in _installed.items()
        if meta.get("tenant_id") == tenant
    ]
    return {"items": items}


@router.post("", status_code=201)
async def install_connector(request: Request, body: ConnectorInstall) -> dict[str, str]:
    auth = request.state.auth
    settings = request.app.state.settings
    stem = body.manifest_name.removesuffix(".yaml")
    manifest_path = (_MANIFESTS / f"{stem}.yaml").resolve()
    if not manifest_path.is_relative_to(_MANIFESTS.resolve()) or not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="Connector manifest not found")
    runtime = ConnectorRuntime(
        settings.database_url.replace("+psycopg", ""),
        auth.tenant_id,
    )
    manifest = runtime.load_manifest(manifest_path)
    connector_id = uuid7()
    _installed[str(connector_id)] = {
        "tenant_id": str(auth.tenant_id),
        "name": manifest.name,
        "version": manifest.version,
    }
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
    # Installed connectors belong to the installing tenant.
    if meta is None or meta.get("tenant_id") != str(auth.tenant_id):
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
