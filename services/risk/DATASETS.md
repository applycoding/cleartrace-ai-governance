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

Attribution: Dua, D. and Graff, C. (2019). UCI Machine Learning Repository. Irvine, CA: University of California, School of Information and Computer Science.
