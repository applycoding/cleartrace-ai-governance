from __future__ import annotations

import base64
import binascii

MAX_OFFSET = 1_000_000


class InvalidCursorError(ValueError):
    """Pagination cursor is not one this API issued."""


def encode_cursor(offset: int) -> str:
    raw = str(offset).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        offset = int(raw.decode("ascii"))
    except (UnicodeError, binascii.Error, ValueError) as exc:
        raise InvalidCursorError("invalid pagination cursor") from exc
    if not 0 <= offset <= MAX_OFFSET:
        raise InvalidCursorError("invalid pagination cursor")
    return offset
