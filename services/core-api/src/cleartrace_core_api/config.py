from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLEARTRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace"
    keycloak_issuer: str = "http://127.0.0.1:8081/realms/cleartrace"
    keycloak_audience: str = "cleartrace-api"
    keycloak_jwks_url: str = "http://127.0.0.1:8081/realms/cleartrace/protocol/openid-connect/certs"
    cedar_policy_path: str = "policies/cedar/authz.cedar"
    cors_origins: list[str] = ["http://localhost:3000"]
    dev_skip_auth: bool = False
