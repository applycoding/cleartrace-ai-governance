from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    number: int
    slug: str
    name_en: str
    name_fr: str
    primary_slot: str


GOVERNANCE_CATEGORIES: tuple[CategoryDefinition, ...] = (
    CategoryDefinition(
        1, "metadata", "AI system metadata", "Métadonnées du système d'IA", "summary"
    ),
    CategoryDefinition(2, "ownership", "Ownership", "Propriété", "business_owner"),
    CategoryDefinition(3, "intent", "Intent", "Intention", "intended_use"),
    CategoryDefinition(
        4, "deployment", "Deployment status", "État de déploiement", "register_status"
    ),
    CategoryDefinition(5, "funding", "Funding state", "État du financement", "funding_status"),
    CategoryDefinition(
        6, "clients", "Client information", "Renseignements sur les clients", "primary_users"
    ),
    CategoryDefinition(7, "objectives", "System objectives", "Objectifs du système", "objective"),
    CategoryDefinition(8, "risk", "Risk assessments", "Évaluations des risques", "risk_summary"),
    CategoryDefinition(
        9,
        "aia",
        "Algorithmic Impact Assessment",
        "Évaluation d'impact algorithmique",
        "impact_level",
    ),
    CategoryDefinition(
        10, "findings", "Compliance findings", "Constats de conformité", "finding_state"
    ),
    CategoryDefinition(11, "evidence", "Audit evidence", "Preuves d'audit", "evidence_count"),
    CategoryDefinition(
        12, "monitoring", "Monitoring results", "Résultats de surveillance", "metric_snapshot"
    ),
    CategoryDefinition(13, "approvals", "Approvals", "Approbations", "approval_status"),
    CategoryDefinition(
        14, "decisions", "Decision records", "Registres de décision", "last_decision"
    ),
    CategoryDefinition(
        15, "controls", "Control requirements", "Exigences de contrôle", "framework_assignment"
    ),
)


def category_by_number(number: int) -> CategoryDefinition:
    for cat in GOVERNANCE_CATEGORIES:
        if cat.number == number:
            return cat
    msg = f"Unknown category number {number}"
    raise ValueError(msg)
