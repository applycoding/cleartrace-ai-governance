"""Public dataset loaders and synthetic defect generators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DatasetWindow:
    reference: pd.DataFrame
    current: pd.DataFrame
    dataset_version: str
    schema: dict[str, object]


def _synthetic_adult_like(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "age": rng.integers(18, 80, size=rows),
            "workclass": rng.choice(
                ["Private", "Self-emp", "Gov"], size=rows, p=[0.7, 0.2, 0.1]
            ),
            "education-num": rng.integers(1, 16, size=rows),
            "hours-per-week": rng.integers(20, 60, size=rows),
            "income": rng.choice(["<=50K", ">50K"], size=rows, p=[0.75, 0.25]),
        }
    )


def _synthetic_german_credit_like(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "checking_status": rng.choice(["A11", "A12", "A13", "A14"], size=rows),
            "duration": rng.integers(4, 48, size=rows),
            "credit_amount": rng.integers(250, 15000, size=rows),
            "personal_status": rng.choice(["A91", "A92", "A93", "A94"], size=rows),
            "age": rng.integers(19, 75, size=rows),
            "class": rng.choice([0, 1], size=rows, p=[0.7, 0.3]),
        }
    )


def load_reference_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return UCI-shaped synthetic frames (licence notes in DATASETS.md)."""
    return _synthetic_adult_like(800, 11), _synthetic_german_credit_like(800, 22)


ADULT_SCHEMA: dict[str, object] = {
    "age": "numeric",
    "workclass": "category",
    "workclass_allowed": ["Private", "Self-emp", "Gov"],
    "education-num": "numeric",
    "hours-per-week": "numeric",
    "income": "category",
    "income_allowed": ["<=50K", ">50K"],
}

GERMAN_SCHEMA: dict[str, object] = {
    "checking_status": "category",
    "checking_status_allowed": ["A11", "A12", "A13", "A14"],
    "duration": "numeric",
    "credit_amount": "numeric",
    "personal_status": "category",
    "personal_status_allowed": ["A91", "A92", "A93", "A94"],
    "age": "numeric",
    "class": "numeric",
}


def _schema_for_frame(frame: pd.DataFrame, base: dict[str, object]) -> dict[str, object]:
    schema: dict[str, object] = dict(base)
    for column in frame.columns:
        if schema.get(column) == "category":
            values = frame[column].dropna().unique().tolist()
            schema[f"{column}_allowed"] = values
    return schema


def sample_clean_window(source: str, seed: int, rows: int = 200) -> DatasetWindow:
    adult_ref, german_ref = load_reference_frames()
    if source == "adult":
        ref = adult_ref.sample(min(rows, len(adult_ref)), random_state=seed).reset_index(drop=True)
        cur = ref.copy()
        schema = _schema_for_frame(ref, ADULT_SCHEMA)
        return DatasetWindow(ref, cur, "uci-adult@v2-synthetic", schema)
    ref = german_ref.sample(min(rows, len(german_ref)), random_state=seed).reset_index(drop=True)
    cur = ref.copy()
    schema = _schema_for_frame(ref, GERMAN_SCHEMA)
    return DatasetWindow(ref, cur, "german-credit@v1-synthetic", schema)


def sample_defective_window(
    defect_type: str, source: str, seed: int, rows: int = 200
) -> DatasetWindow:
    window = sample_clean_window(source, seed, rows)
    ref = window.reference.copy()
    cur = window.current.copy()
    schema = window.schema
    rng = np.random.default_rng(seed)
    cat_col = next(
        (col for col in cur.columns if schema.get(col) == "category"),
        cur.columns[0],
    )
    if defect_type == "completeness":
        cur[cat_col] = cur[cat_col].astype(object)
        cur[cat_col] = np.nan
    elif defect_type == "schema":
        cur[cat_col] = cur[cat_col].astype(object)
        cur.iloc[: max(1, len(cur) // 10), cur.columns.get_loc(cat_col)] = "INVALID_ENUM"
    elif defect_type == "psi":
        numeric_col = next(col for col in cur.columns if pd.api.types.is_numeric_dtype(cur[col]))
        cur[numeric_col] = cur[numeric_col].astype(float) * 8 + rng.normal(0, 5, size=len(cur))
    elif defect_type == "ks":
        numeric_col = next(col for col in cur.columns if pd.api.types.is_numeric_dtype(cur[col]))
        mean_val = float(cur[numeric_col].mean())
        cur[numeric_col] = rng.normal(loc=mean_val + 25, scale=3, size=len(cur))
    return DatasetWindow(ref, cur, window.dataset_version, schema)
