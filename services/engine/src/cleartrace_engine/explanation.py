from __future__ import annotations

from cleartrace_contracts.models import OutcomeState

from cleartrace_engine.certainty import certainty_band
from cleartrace_engine.types import EvaluationInput


def _state_label(state: str, lang: str) -> str:
    mapping_en = {
        OutcomeState.MET: "Met",
        OutcomeState.PARTIALLY_MET: "Partially met",
        OutcomeState.NOT_MET: "Not met",
        OutcomeState.NOT_APPLICABLE: "Not applicable",
        OutcomeState.UNABLE_TO_DETERMINE: "Unable to determine",
    }
    mapping_fr = {
        OutcomeState.MET: "Conforme",
        OutcomeState.PARTIALLY_MET: "Partiellement conforme",
        OutcomeState.NOT_MET: "Non conforme",
        OutcomeState.NOT_APPLICABLE: "Non applicable",
        OutcomeState.UNABLE_TO_DETERMINE: "Impossible à déterminer",
    }
    if lang == "fr":
        return mapping_fr.get(OutcomeState(state), state)
    return mapping_en.get(OutcomeState(state), state)


def build_explanation(
    payload: EvaluationInput, outcome_state: str, reason_code: str, score: float
) -> tuple[str, str]:
    band_en, band_fr = certainty_band(score)
    ctrl = payload.control
    evidence_count = len(payload.evidence)
    en = (
        f"**Requirement:** {ctrl.requirement_en} "
        f"**Control:** {ctrl.control_id} v{ctrl.control_version}. "
        f"**Result:** {_state_label(outcome_state, 'en')}. "
        f"**Why:** Reason code {reason_code}. "
        f"Objectives evaluated: {len(payload.objective_results)}. "
        f"**Evidence used:** search over {evidence_count} artefact(s). "
        f"**Certainty index:** {score:.2f} ({band_en}; deterministic rules). "
        f"**What to do:** {ctrl.remediation_en} "
        f"Source: {ctrl.source_url} "
        f"Engine bundle digest: {payload.engine_bundle_digest}."
    )
    fr = (
        f"**Exigence :** {ctrl.requirement_fr} "
        f"**Contrôle :** {ctrl.control_id} v{ctrl.control_version}. "
        f"**Résultat :** {_state_label(outcome_state, 'fr')}. "
        f"**Pourquoi :** Code de motif {reason_code}. "
        f"Objectifs évalués : {len(payload.objective_results)}. "
        f"**Preuves utilisées :** recherche sur {evidence_count} artefact(s). "
        f"**Indice de certitude :** {score:.2f} ({band_fr}; règles déterministes). "
        f"**Mesure à prendre :** {ctrl.remediation_fr} "
        f"Source : {ctrl.source_url} "
        f"Empreinte du lot moteur : {payload.engine_bundle_digest}."
    )
    return en, fr
