# Approved exception: OS packages inside shipped container images

ClearTrace application dependencies (Python and npm) are gated by
[`docs/LICENSE_POLICY.md`](../LICENSE_POLICY.md). This file is the approved
exception named by the blueprint for **operating-system packages** that come
from third-party base images and from the Debian slim base of the ClearTrace
`core-api` image.

## Scope

| Image | Role | Base |
| --- | --- | --- |
| `ghcr.io/applycoding/cleartrace-core-api:0.1.0` | ClearTrace API | `python:3.12-slim-bookworm` (Debian) |
| `pgvector/pgvector:pg16` | Postgres 16 + pgvector | Debian |
| `edoburu/pgbouncer:v1.24.1-p1` | PgBouncer | Alpine/Debian as published |
| `chrislusf/seaweedfs:3.80` | object store | upstream |
| `nats:2.10` | NATS JetStream | upstream |
| `quay.io/keycloak/keycloak:26.0` | identity | upstream |
| Offline-bundle companions (`postgres:16`, `nats:2.10`) | air-gap mirrors | upstream |

## Why an exception

Debian and Alpine distribution images include GPL-2.0, GPL-3.0, LGPL-2.1 and
LGPL-3.0 packages (for example `gcc-*-base`, `bash`, `coreutils`, `glibc`,
`openssl` dual-licence components). ClearTrace ships those packages
**unmodified**, as distributed by the upstream image maintainers. Source for
Debian packages is available from the Debian project; Alpine packages from the
Alpine Linux aports tree; other images from their documented upstream source
locations.

ClearTrace does not modify these OS packages, does not combine them into a
derivative work that would require ClearTrace itself to be GPL, and does not
use them as application libraries beyond running the stock container.

## What remains gated

- Every ClearTrace first-party manifest keeps
  `LicenseRef-ClearTrace-Evaluation-Only`.
- Every Python and npm dependency of ClearTrace remains under the rules in
  `docs/LICENSE_POLICY.md` (no GPL/AGPL/SSPL/BUSL; LGPL/MPL only when listed
  unmodified in `THIRD_PARTY_LICENSES.md`).
- CI builds a Syft SBOM for each shipped image
  (`scripts/ci_image_sbom.sh`) and records OS-package licence findings in the
  `image-sbom` artifact. Findings covered by this exception are not treated as
  licence-gate failures.

## Review

This exception was added for TRL 5 test T-28 so that OS-level copyleft in base
images is explicit rather than silent. Revisit if ClearTrace starts modifying
OS packages or linking ClearTrace code against GPL libraries in a way that
would create a combined work.
