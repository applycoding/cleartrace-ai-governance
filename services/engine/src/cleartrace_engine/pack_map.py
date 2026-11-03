"""Map pack directory slugs to OPA package names."""

from __future__ import annotations

PACK_SLUG_TO_OPA: dict[str, str] = {
    "dadm": "dadm",
    "aia": "aia",
    "psd": "psd",
    "dsd": "dsd",
    "ai-strategy": "ai_strategy",
    "guiding-principles": "guiding_principles",
    "nist-ai-rmf": "nist_ai_rmf",
    "iso42001-ids": "iso42001_ids",
    "golden": "golden",
}


def opa_package_for_slug(pack_slug: str) -> str:
    if pack_slug not in PACK_SLUG_TO_OPA:
        raise KeyError(f"Unknown pack slug for OPA: {pack_slug}")
    return PACK_SLUG_TO_OPA[pack_slug]
