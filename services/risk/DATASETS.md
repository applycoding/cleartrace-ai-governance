# Public dataset licence notes for Package D tests (blueprint section 20).

| Dataset | Source | Licence | Use in ClearTrace |
|---|---|---|---|
| UCI Adult (Census Income) | UCI ML Repository / OpenML `adult` | CC BY 4.0 | Data quality and drift windows in T-16 |
| Statlog German Credit | UCI ML Repository / OpenML `credit-g` | CC BY 4.0 | Data quality and drift windows in T-16 |

Tests download these sets at runtime via scikit-learn `fetch_openml` when network is available; seeded defect generators use the same column layout offline when fetch is skipped.

Attribution: Dua, D. and Graff, C. (2019). UCI Machine Learning Repository. Irvine, CA: University of California, School of Information and Computer Science.
