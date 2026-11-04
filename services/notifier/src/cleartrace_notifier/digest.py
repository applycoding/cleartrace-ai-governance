from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from cleartrace_notifier.models import NotificationRecord
from cleartrace_notifier.user_strings import DIGEST_EMPTY, DIGEST_SUBJECT


@dataclass(slots=True)
class DigestSection:
    title_en: str
    title_fr: str
    items_en: list[str]
    items_fr: list[str]


@dataclass(slots=True)
class DigestDocument:
    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    language: Literal["en", "fr"]
    subject: str
    body_html: str
    body_text: str


def build_digest(
    tenant_id: UUID,
    notifications: list[NotificationRecord],
    *,
    language: Literal["en", "fr"] = "en",
    period_hours: int = 24,
) -> DigestDocument:
    now = datetime.now(UTC)
    period_start = now.replace(microsecond=0)
    items_en = [n.alert.title_en for n in notifications]
    items_fr = [n.alert.title_fr for n in notifications]
    if language == "fr":
        subject = DIGEST_SUBJECT.fr.format(count=len(notifications))
        lines = [f"- {title}" for title in items_fr]
        body_text = "\n".join(lines) if lines else DIGEST_EMPTY.fr
    else:
        subject = DIGEST_SUBJECT.en.format(count=len(notifications))
        lines = [f"- {title}" for title in items_en]
        body_text = "\n".join(lines) if lines else DIGEST_EMPTY.en
    body_html = "<br/>".join(lines) if lines else ""
    return DigestDocument(
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=now,
        language=language,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
    )
