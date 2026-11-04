"""User-facing notification strings (EN/FR) for alerts and digests."""

from __future__ import annotations

from dataclasses import dataclass

from cleartrace_notifier.models import AlertType


@dataclass(frozen=True)
class BilingualString:
    en: str
    fr: str


ALERT_TEMPLATES: dict[AlertType, tuple[BilingualString, BilingualString]] = {
    AlertType.NON_CONFORMITY: (
        BilingualString(
            "Control outcome is not met",
            "Le résultat de contrôle est non conforme",
        ),
        BilingualString(
            "A mandatory control objective failed for this system. Review the finding and attach evidence.",
            "Un objectif de contrôle obligatoire a échoué pour ce système. Examinez la constatation et joignez une preuve.",
        ),
    ),
    AlertType.REASSESSMENT_REQUIRED: (
        BilingualString(
            "Reassessment required",
            "Réévaluation requise",
        ),
        BilingualString(
            "Framework or policy change requires a new assessment for affected systems.",
            "Un changement de cadre ou de politique exige une nouvelle évaluation pour les systèmes touchés.",
        ),
    ),
    AlertType.EVIDENCE_EXPIRING: (
        BilingualString(
            "Evidence expiring soon",
            "Preuve expirant bientôt",
        ),
        BilingualString(
            "Linked evidence will expire before the next review cycle.",
            "La preuve liée expirera avant le prochain cycle d'examen.",
        ),
    ),
    AlertType.APPROVAL_EXPIRING: (
        BilingualString(
            "Approval expiring",
            "Approbation expirant",
        ),
        BilingualString(
            "Human approval for this finding expires soon.",
            "L'approbation humaine pour cette constatation expire bientôt.",
        ),
    ),
    AlertType.BINDING_BREACH: (
        BilingualString(
            "Binding risk threshold breached",
            "Seuil de risque contraignant dépassé",
        ),
        BilingualString(
            "A binding telemetry threshold linked to a control objective was exceeded.",
            "Un seuil de télémétrie contraignant lié à un objectif de contrôle a été dépassé.",
        ),
    ),
    AlertType.QUARANTINE_ITEM: (
        BilingualString(
            "Evidence quarantined",
            "Preuve en quarantaine",
        ),
        BilingualString(
            "An evidence artefact was quarantined pending review.",
            "Un artefact de preuve a été mis en quarantaine en attente d'examen.",
        ),
    ),
    AlertType.JIT_GRANT_USED: (
        BilingualString(
            "Just-in-time grant used",
            "Octroi ponctuel utilisé",
        ),
        BilingualString(
            "A just-in-time access grant was exercised and logged.",
            "Un octroi d'accès ponctuel a été utilisé et consigné.",
        ),
    ),
}

DIGEST_EMPTY = BilingualString(
    "No alerts in the period.",
    "Aucune alerte sur la période.",
)

DIGEST_SUBJECT = BilingualString(
    "ClearTrace digest — {count} alerts",
    "Sommaire ClearTrace — {count} alertes",
)


def notification_template_rows() -> list[tuple[str, str, str, str, str]]:
    """Return rows of template_id, title_en, title_fr, body_en, body_fr."""
    rows: list[tuple[str, str, str, str, str]] = []
    for alert_type, (title, body) in ALERT_TEMPLATES.items():
        rows.append(
            (
                f"notification:{alert_type.value}",
                title.en,
                title.fr,
                body.en,
                body.fr,
            )
        )
    rows.append(
        (
            "notification:digest_subject",
            DIGEST_SUBJECT.en.replace("{count}", "N"),
            DIGEST_SUBJECT.fr.replace("{count}", "N"),
            "",
            "",
        )
    )
    rows.append(
        (
            "notification:digest_empty",
            DIGEST_EMPTY.en,
            DIGEST_EMPTY.fr,
            "",
            "",
        )
    )
    return rows
