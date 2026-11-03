from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from cleartrace_core_api.interop.exporter import InteropExportService

router = APIRouter(tags=["interop"])
_exporter = InteropExportService()

# In-memory dossiers until register/assessment packages wire persistent stores.
_dossiers: dict[str, dict[str, object]] = {}


def seed_demo_dossiers() -> None:
    if _dossiers:
        return
    for key, en, fr in (
        ("demo-alpha", "Alpha assistant", "Assistant Alpha"),
        ("demo-beta", "Beta classifier", "Classificateur Beta"),
    ):
        dossier = _exporter.dossier_from_seed(system_key=key, name_en=en, name_fr=fr)
        _dossiers[key] = dossier


@router.get("/capabilities")
async def get_capabilities() -> JSONResponse:
    return JSONResponse(_exporter.capabilities())


@router.get("/export/oscal/{export_type}")
async def export_oscal(export_type: str, request: Request) -> Response:
    seed_demo_dossiers()
    system_key = request.query_params.get("system_key", "demo-alpha")
    dossier = _dossiers.get(system_key)
    if dossier is None:
        return Response(status_code=404, content=b"system dossier not found")
    try:
        payload = _exporter.export_oscal(export_type, dossier)
    except ValueError as exc:
        return Response(status_code=422, content=str(exc).encode())
    return Response(
        content=payload,
        media_type="application/json",
        headers={"X-ClearTrace-Lossy-Export-Note": "true"},
    )


@router.get("/export/cyclonedx/{system_id}")
async def export_cyclonedx(system_id: UUID, request: Request) -> Response:
    seed_demo_dossiers()
    _ = system_id
    system_key = request.query_params.get("system_key", "demo-alpha")
    dossier = _dossiers.get(system_key)
    if dossier is None:
        return Response(status_code=404, content=b"system dossier not found")
    system = dossier["system"]
    if not isinstance(system, dict):
        return Response(status_code=500, content=b"system dossier is malformed")
    payload = _exporter.export_cyclonedx(system)
    return Response(content=payload, media_type="application/json")
