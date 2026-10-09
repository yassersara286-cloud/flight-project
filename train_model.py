from __future__ import annotations

import math
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from backend.app.settings import MODEL_BASE_FEATURES, MODEL_EXCLUDED_COLUMNS, MODEL_PATH


RANDOM_STATE = 42
CHUNK_SIZE = 100_000


def _training_columns(data_path: Path) -> tuple[list[str], str]:
    preview = pd.read_csv(data_path, nrows=1_000, low_memory=False)
    target_column = "DepDel15" if "DepDel15" in preview.columns else "DepDelayMinutes"
    if target_column not in preview.columns:
        raise ValueError("The dataset needs either DepDel15 or DepDelayMinutes as its target.")

    missing = set(MODEL_BASE_FEATURES).difference(preview.columns)
    if missing:
        raise ValueError(f"The dataset is missing model features: {', '.join(sorted(missing))}")

    numeric_columns = [
        column
        for column in preview.select_dtypes(include=[np.number]).columns
        if column not in MODEL_EXCLUDED_COLUMNS
    ]
    feature_columns = list(MODEL_BASE_FEATURES)
    feature_columns.extend(column for column in numeric_columns if column not in feature_columns)
    return feature_columns, target_column


def _sample_training_rows(
    data_path: Path,
    feature_columns: list[str],
    target_column: str,
    sample_limit: int,
) -> pd.DataFrame:
    selected_columns = list(dict.fromkeys([*feature_columns, target_column]))
    samples = []
    per_chunk_sample = max(1, math.ceil(sample_limit / 20)) if sample_limit else 0

    for chunk in pd.read_csv(
        data_path,
        usecols=selected_columns,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        if sample_limit and len(chunk) > per_chunk_sample:
            chunk = chunk.sample(n=per_chunk_sample, random_state=RANDOM_STATE)
        samples.append(chunk)

    if not samples:
        raise ValueError("The dataset contains no flight rows.")

    frame = pd.concat(samples, ignore_index=True)
    if sample_limit and len(frame) > sample_limit:
        frame = frame.sample(n=sample_limit, random_state=RANDOM_STATE)
    return frame


def train_model(
    data_path: Path,
    model_path: Path,
    sample_limit: int = 200_000,
) -> dict[str, float | int | str]:
    if not data_path.is_file():
        raise FileNotFoundError(f"Flight data file was not found: {data_path}")
    if sample_limit < 0:
        raise ValueError("sample_limit must be zero (all rows) or a positive integer.")

    feature_columns, target_column = _training_columns(data_path)
    frame = _sample_training_rows(data_path, feature_columns, target_column, sample_limit)
    if target_column == "DepDel15":
        target = pd.to_numeric(frame[target_column], errors="coerce")
    else:
        target = (pd.to_numeric(frame[target_column], errors="coerce") >= 15).astype(float)

    features = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    valid_rows = target.notna()
    features = features.loc[valid_rows]
    target = target.loc[valid_rows].astype(int)
    feature_means = features.mean().fillna(0.0)
    features = features.fillna(feature_means).astype(np.float32)

    if target.nunique() < 2 or target.value_counts().min() < 2:
        raise ValueError("The sampled data needs at least two examples of each target class.")

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=target,
    )
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=16,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_means": feature_means.to_dict(),
            "feature_columns": feature_columns,
        },
        model_path,
    )
    return {
        "training_rows": int(len(X_train)),
        "validation_rows": int(len(X_test)),
        "validation_accuracy": round(float(model.score(X_test, y_test)), 4),
        "features": len(feature_columns),
        "model_path": str(model_path),
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    data_path = Path(
        os.getenv("FLIGHT_DATA_PATH", project_root.parent / "merged_flight_weather_data.csv")
    ).expanduser()
    model_path = Path(os.getenv("MODEL_PATH", MODEL_PATH)).expanduser()
    sample_limit = int(os.getenv("TRAIN_SAMPLE_SIZE", "200000"))
    result = train_model(data_path, model_path, sample_limit)
    print("Model training complete")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
