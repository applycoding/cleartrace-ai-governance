from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WormObjectStore:
    """Local WORM stand-in: write-once files with object-lock metadata sidecar."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def put_worm(self, key: str, payload: bytes, metadata: dict[str, Any]) -> str:
        dest = self._root / key
        if dest.exists():
            raise FileExistsError(f"WORM object already exists: {key}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        meta_path = dest.with_suffix(dest.suffix + ".lock.json")
        meta_path.write_text(json.dumps({"object_lock": "COMPLIANCE", **metadata}, sort_keys=True))
        return f"worm://{dest.resolve()}"

    def read(self, worm_uri: str) -> bytes:
        if worm_uri.startswith("worm://"):
            path = Path(worm_uri.removeprefix("worm://"))
        else:
            path = Path(worm_uri)
        return path.read_bytes()
