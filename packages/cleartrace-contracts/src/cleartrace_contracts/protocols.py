from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from cleartrace_contracts.models import OutcomeState


@runtime_checkable
class AssessmentEngine(Protocol):
    """OPA/CEL assessment engine (services/engine)."""

    async def run_assessment(self, system_id: UUID, framework_version_id: UUID) -> UUID:
        """Start an assessment run; returns run id."""
        ...

    async def get_finding_outcome(self, finding_id: UUID) -> OutcomeState: ...


@runtime_checkable
class AIAEngine(Protocol):
    """Official AIA parity scorer (services/aia)."""

    async def score_answers(self, answers: dict[str, object]) -> dict[str, object]: ...

    async def export_record(self, record_id: UUID) -> dict[str, object]: ...


@runtime_checkable
class PolicyWatcher(Protocol):
    """Policy snapshot and impact analysis (services/policy-watch)."""

    async def compute_impact_set(self, policy_diff_id: UUID) -> UUID: ...


@runtime_checkable
class EvidenceStore(Protocol):
    """Evidence artefacts and lineage (services/evidence)."""

    async def store_artefact(
        self,
        tenant_id: UUID,
        payload: bytes,
        metadata: dict[str, object],
    ) -> UUID: ...


@runtime_checkable
class RiskEngine(Protocol):
    """Metrics, baselines, observations (services/risk)."""

    async def ingest_observations(
        self, tenant_id: UUID, batch: list[dict[str, object]]
    ) -> None: ...


@runtime_checkable
class AuditLedger(Protocol):
    """Hash-chained audit ledger (services/audit)."""

    async def append_event(self, tenant_id: UUID, event: dict[str, object]) -> UUID: ...


@runtime_checkable
class ConnectorRunner(Protocol):
    """Connector plug-in runner (services/connectors)."""

    async def run_connector(self, connector_id: UUID) -> UUID: ...


@runtime_checkable
class Notifier(Protocol):
    """Alerts and webhooks (services/notifier)."""

    async def dispatch_alert(self, tenant_id: UUID, alert: dict[str, object]) -> None: ...


@runtime_checkable
class ReportBuilder(Protocol):
    """EN/FR reports (services/reports)."""

    async def build_report(self, tenant_id: UUID, spec: dict[str, object]) -> UUID: ...


@runtime_checkable
class DataPolicyService(Protocol):
    """Retention, legal hold, deletion (services/core-api data-policy module later)."""

    async def request_deletion(self, tenant_id: UUID, request: dict[str, object]) -> UUID: ...


@runtime_checkable
class InteropExporter(Protocol):
    """OSCAL/CycloneDX export (services/core-api interop module later)."""

    async def export_oscal(self, tenant_id: UUID, export_type: str) -> bytes: ...
