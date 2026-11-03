# Package D TRL 5 test report notes (risk engine)

## Tier-2 plug-in sandbox (T-17)

Blueprint section 9.1 describes a **separate container** for tier-2 plug-ins at full deployment. At TRL 5 we use **process isolation only**:

- `multiprocessing` **spawn** worker (no shared interpreter state)
- **AST validation** before execution (no imports; blocked `open` / `exec` / `eval`)
- **Wall-clock time limit** (2 s worker join; SIGALRM inside worker)

This is **not** a separate container. Hostile plug-in tests assert that network, file, and infinite-loop attempts do not escape that sandbox.

## Tier-1 CEL (T-17)

Uses the shared evaluator `cleartrace_engine.cel_evaluator` (cel-python 0.5.0) with the blueprint section 6.1 limits; the risk engine has no CEL evaluator of its own.

## T-16 measured results

Recorded from `uv run pytest tests/trl5/test_t16_data_quality_windows.py -v` after loading frozen UCI files (see `services/risk/fixtures/manifest.json`).

| Dataset | Defect type | Defective flagged | Clean false positives |
|---|---|---|---|
| UCI Adult | completeness | 50/50 | 0/50 |
| UCI Adult | schema | 50/50 | 0/50 |
| UCI Adult | psi | 50/50 | 0/50 |
| UCI Adult | ks | 50/50 | 0/50 |
| German Credit | completeness | 50/50 | 0/50 |
| German Credit | schema | 50/50 | 0/50 |
| German Credit | psi | 50/50 | 0/50 |
| German Credit | ks | 50/50 | 0/50 |

Pass criteria (blueprint section 18): ≥48/50 defective per type; ≤2/50 clean false alarms; traceable issue metadata on every flag.
