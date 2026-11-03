# ClearTrace risk service

Metric registry, per-system baselines, evaluators (Evidently, Fairlearn, scikit-learn, SciPy, Presidio), **cel-python 0.5.0** tier-1 metrics (§6.1 limits, dedupe with `services/engine` when Package A merges), tier-2 plug-ins via **spawn + AST checks + time limit** (not a separate container at TRL 5), binding versus advisory breaches, and output monitoring.

Frozen UCI datasets: `fixtures/manifest.json`. Licence notes: [DATASETS.md](./DATASETS.md). TRL 5 notes: [../../tests/trl5/RISK_TRL5_REPORT.md](../../tests/trl5/RISK_TRL5_REPORT.md).
