# ADR-0001: Three engines (OPA, CEL, Cedar)

## Status

Accepted (2026-11-03)

## Context

ClearTrace must evaluate compliance (OPA/Rego), bounded user expressions (CEL), and authorization (Cedar) as described in BLUEPRINT section 6.1.

## Decision

- **OPA/Rego** for control evaluation and five-state outcomes.
- **CEL** for applicability predicates and tier-1 custom metrics with documented limits.
- **Cedar** for all API authorization decisions.

JsonLogic and other rule languages are not used.

## Consequences

Each engine is versioned and tested independently. Cedar runs in the core API via the `cedarpy` binding (Apache-2.0).
