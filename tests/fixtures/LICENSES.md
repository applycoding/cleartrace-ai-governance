# Fixtures licence register (step 4)

Public datasets used in tests with source URL, licence, and attribution.

| File | Source | Licence | Attribution | SHA-256 |
| --- | --- | --- | --- | --- |
| `synthetic/marked-synthetic-patients.json` | generated | Apache-2.0 (generated synthetic data) | ClearTrace synthetic Synthea-style patient records for tests | `62c9e1904b0d1102507b25c929279cb20f650aece12cf9ed60e60748c0d6488a` |
| `gc-ai-register/gc-ai-register-mvp-registre-de-lia-du-gc-pmv-04-26.csv` | https://open.canada.ca/data/dataset/gc-ai-register-mvp-registre-de-lia-du-gc-pmv | Open Government Licence – Canada | Government of Canada GC AI Register | run `tools/freeze_fixtures.py` |
| `aia/survey-enfr.json` | https://github.com/canada-ca/aia-eia-js | MIT | canada-ca/aia-eia-js (pin commit in manifest.json) | run `tools/freeze_fixtures.py` |
| `aia/departments.json` | https://github.com/canada-ca/aia-eia-js | MIT | canada-ca/aia-eia-js | run `tools/freeze_fixtures.py` |

Run `uv run python tools/freeze_fixtures.py` before G0 to download remaining public fixtures, refresh `checksums.sha256`, and complete this table.
