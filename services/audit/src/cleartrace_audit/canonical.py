from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    """Serialize with RFC 8785 (JCS) ordering via sort_keys and minimal separators."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
