from __future__ import annotations

import base64


def encode_cursor(offset: int) -> str:
    raw = str(offset).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> int:
    raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
    return int(raw.decode("utf-8"))
