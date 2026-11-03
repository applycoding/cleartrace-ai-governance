from __future__ import annotations

from dataclasses import dataclass

from cleartrace_evidence.constants import MAX_UPLOAD_BYTES


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    media_type: str
    reason_en: str
    reason_fr: str


def scan_upload(payload: bytes, declared_media_type: str) -> ScanResult:
    if len(payload) > MAX_UPLOAD_BYTES:
        return ScanResult(
            ok=False,
            media_type=declared_media_type,
            reason_en="File exceeds the 50 MB size limit.",
            reason_fr="Le fichier dépasse la limite de 50 Mo.",
        )
    if not declared_media_type or "/" not in declared_media_type:
        return ScanResult(
            ok=False,
            media_type=declared_media_type,
            reason_en="Invalid media type.",
            reason_fr="Type de média invalide.",
        )
    if _malware_hook(payload):
        return ScanResult(
            ok=False,
            media_type=declared_media_type,
            reason_en="Malware scan rejected this file.",
            reason_fr="Analyse antimalware : fichier refusé.",
        )
    return ScanResult(ok=True, media_type=declared_media_type, reason_en="", reason_fr="")


def _malware_hook(payload: bytes) -> bool:
    """Hook for external scanners; test payloads may include CLEARTRACE_EICAR_TEST."""
    marker = b"CLEARTRACE_EICAR_TEST"
    return marker in payload
