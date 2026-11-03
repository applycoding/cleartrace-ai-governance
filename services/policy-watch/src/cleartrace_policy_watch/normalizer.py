from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_clause_text(text: str) -> str:
    """Collapse formatting differences for formatting-only detection."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u00a0", " ")
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip().lower()


def clause_tree_from_html(html: str, *, normalize: bool = True) -> dict[str, str]:
    """Extract clause ids and text from simplified policy HTML fixtures."""
    clauses: dict[str, str] = {}
    for match in re.finditer(
        r'data-clause-id="([^"]+)"[^>]*>(.*?)</(?:p|div|section)>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        clause_id = match.group(1).strip()
        inner_html = match.group(2)
        if normalize:
            raw = re.sub(r"<[^>]+>", " ", inner_html)
            clauses[clause_id] = normalize_clause_text(raw)
        else:
            clauses[clause_id] = inner_html.strip()
    return clauses


def snapshot_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
