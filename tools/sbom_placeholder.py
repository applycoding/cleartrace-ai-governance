#!/usr/bin/env python3
"""Emit CycloneDX SBOM (delegates to sbom_builder)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_builder = Path(__file__).with_name("sbom_builder.py")
spec = importlib.util.spec_from_file_location("sbom_builder", _builder)
if spec is None or spec.loader is None:
    raise RuntimeError("sbom_builder.py missing")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.main()
