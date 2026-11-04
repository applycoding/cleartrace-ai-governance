# Third-party code vendored in this repository

Dependencies installed from PyPI and npm are locked in `uv.lock` and `web/package-lock.json` and checked by the licence gate (`tools/licence_gate.py`) against `docs/LICENSE_POLICY.md`; every shipped dependency is listed in `THIRD_PARTY_LICENSES.md`. The files below are copied into the repository instead, so they are listed here and in `NOTICE`. Test datasets and fixtures are registered separately in `tests/fixtures/LICENSES.md`.

| Component | Version | Path | Licence | Copyright | Source |
| --- | --- | --- | --- | --- | --- |
| swagger-ui-dist | 5.17.14 | `services/core-api/static/swagger-ui/` | Apache-2.0 (`LICENSE`, `NOTICE` in that folder) | 2020-2021 SmartBear Software Inc. | https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-5.17.14.tgz |

Vendored files are unmodified copies from the npm package:

| File | SHA-256 |
| --- | --- |
| `swagger-ui-bundle.js` | `c2e4a9ef08144839ff47c14202063ecfe4e59e70a4e7154a26bd50d880c88ba1` |
| `swagger-ui.css` | `40170f0ee859d17f92131ba707329a88a070e4f66874d11365e9a77d232f6117` |
| `favicon-32x32.png` | `3ed612f41e050ca5e7000cad6f1cbe7e7da39f65fca99c02e99e6591056e5837` |
| `LICENSE` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| `NOTICE` | `0d20d1adef18aee3f40dd258172155521ce702ac445cb5f7b7d60ed32dad2fb2` |
