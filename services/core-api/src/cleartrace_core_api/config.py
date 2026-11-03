from __future__ import annotations

from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLEARTRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace"
    keycloak_issuer: str = "http://127.0.0.1:8081/realms/cleartrace"
    keycloak_audience: str = "cleartrace-api"
    keycloak_jwks_url: str = "http://127.0.0.1:8081/realms/cleartrace/protocol/openid-connect/certs"
    cedar_policy_path: str = "policies/cedar/authz.cedar"
    cors_origins: list[str] = ["http://localhost:3000"]
    api_host: str = "127.0.0.1"
    api_port: int = 8080
    dev_skip_auth: bool = False
    dev_auth_token: str = Field(
        default="",
        description=(
            "Bearer token accepted when dev_skip_auth is true; "
            "set via CLEARTRACE_DEV_AUTH_TOKEN"
        ),
    )
    dev_tenant_id: UUID = UUID("11111111-1111-7111-8111-111111111101")
    evidence_storage_root: str = ".data/evidence"
    audit_worm_root: str = ".data/worm-audit"
    audit_signer_key_path: str = ".data/audit-checkpoint-signer.key"
    tenant_rate_limit_per_window: int = Field(
        default=120,
        description="Max authenticated API requests per tenant per window (0 disables)",
    )
    tenant_rate_limit_window_seconds: int = Field(
        default=60,
        description="Sliding window length for per-tenant rate limits",
    )
