"""UCI Adult and Statlog German Credit windows for data-quality tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

_FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
_MANIFEST_PATH = _FIXTURES_ROOT / "manifest.json"

ADULT_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country",
    "income",
]

GERMAN_COLUMNS = [
    "checking_status",
    "duration",
    "credit_history",
    "purpose",
    "credit_amount",
    "savings_status",
    "employment",
    "installment_rate",
    "personal_status",
    "other_debtors",
    "residence_since",
    "property",
    "age",
    "other_installment_plans",
    "housing",
    "existing_credits",
    "job",
    "num_dependents",
    "telephone",
    "foreign_worker",
    "class",
]


@dataclass(frozen=True)
class DatasetWindow:
    reference: pd.DataFrame
    current: pd.DataFrame
    dataset_version: str
    schema: dict[str, object]


def _verify_manifest() -> None:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    import hashlib

    for entry in manifest["fixtures"]:
        path = _FIXTURES_ROOT / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            msg = f"fixture checksum mismatch for {entry['path']}"
            raise RuntimeError(msg)


@lru_cache(maxsize=1)
def _load_adult_frame() -> pd.DataFrame:
    _verify_manifest()
    path = _FIXTURES_ROOT / "uci" / "adult.data"
    frame = pd.read_csv(
        path,
        header=None,
        names=ADULT_COLUMNS,
        skipinitialspace=True,
        na_values="?",
        comment=None,
    )
    return frame.dropna(how="all").reset_index(drop=True)


@lru_cache(maxsize=1)
def _load_german_frame() -> pd.DataFrame:
    _verify_manifest()
    path = _FIXTURES_ROOT / "uci" / "german.data"
    return pd.read_csv(path, sep=r"\s+", header=None, names=GERMAN_COLUMNS)


ADULT_SCHEMA: dict[str, object] = {
    "age": "numeric",
    "workclass": "category",
    "education-num": "numeric",
    "hours-per-week": "numeric",
    "income": "category",
}

GERMAN_SCHEMA: dict[str, object] = {
    "checking_status": "category",
    "duration": "numeric",
    "credit_amount": "numeric",
    "personal_status": "category",
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


def load_reference_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    return _load_adult_frame(), _load_german_frame()


def sample_clean_window(source: str, seed: int, rows: int = 200) -> DatasetWindow:
    adult_ref, german_ref = load_reference_frames()
    if source == "adult":
        ref = adult_ref.sample(min(rows, len(adult_ref)), random_state=seed).reset_index(drop=True)
        cur = ref.copy()
        schema = _schema_for_frame(ref, ADULT_SCHEMA)
        return DatasetWindow(ref, cur, "uci-adult@archive-ics-uci", schema)
    ref = german_ref.sample(min(rows, len(german_ref)), random_state=seed).reset_index(drop=True)
    cur = ref.copy()
    schema = _schema_for_frame(ref, GERMAN_SCHEMA)
    return DatasetWindow(ref, cur, "statlog-german-credit@archive-ics-uci", schema)


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
