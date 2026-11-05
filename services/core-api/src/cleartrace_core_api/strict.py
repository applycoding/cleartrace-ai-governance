"""Shared request-body base: reject undeclared fields in OpenAPI and at runtime."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Request bodies forbid extra properties so Schemathesis cannot inject free junk."""

    model_config = ConfigDict(extra="forbid")
