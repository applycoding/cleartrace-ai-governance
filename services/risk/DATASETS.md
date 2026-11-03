# Risk engine test datasets (blueprint section 20)

Frozen copies of the **real** UCI repository files used in T-16. Do not substitute synthetic data labelled as UCI.

| ID | File | Source | Licence |
|---|---|---|---|
| `uci-adult` | `fixtures/uci/adult.data` | [UCI Adult (Census Income)](https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data) | CC BY 4.0 |
| `statlog-german-credit` | `fixtures/uci/german.data` | [Statlog German Credit](https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data) | CC BY 4.0 |

SHA-256 digests are recorded in `fixtures/manifest.json`. Verify before tests:

```bash
uv run python services/risk/tools/verify_fixtures.py
```

Attribution: Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. https://doi.org/10.24432/C5XW20. Hofmann, H. (1994). Statlog (German Credit Data). UCI Machine Learning Repository. https://doi.org/10.24432/C5NC77. Both are distributed under CC BY 4.0 and are committed unmodified; they are also listed in `tests/fixtures/LICENSES.md` and `tests/fixtures/manifest.json`.
