from __future__ import annotations

from enum import StrEnum
from typing import Any


class LineageRelation(StrEnum):
    GENERATED_BY = "prov:wasGeneratedBy"
    ATTRIBUTED_TO = "prov:wasAttributedTo"
    DERIVED_FROM = "prov:wasDerivedFrom"


def prov_links(
    *,
    generated_by: str | None = None,
    attributed_to: str | None = None,
    derived_from: str | None = None,
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    if generated_by:
        links.append({"relation": LineageRelation.GENERATED_BY, "target_uri": generated_by})
    if attributed_to:
        links.append({"relation": LineageRelation.ATTRIBUTED_TO, "target_uri": attributed_to})
    if derived_from:
        links.append({"relation": LineageRelation.DERIVED_FROM, "target_uri": derived_from})
    return links


def lineage_to_rows(links: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for link in links:
        relation = str(link.get("relation", ""))
        target = str(link.get("target_uri", ""))
        if relation and target:
            rows.append((relation, target))
    return rows
