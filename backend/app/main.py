from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app.analytics import build_analytics, load_flight_data
from backend.app.settings import DATA_PATH, MODEL_PATH


app = FastAPI(
    title="Flight Delay Analytics API",
    version="1.0.0",
    description="Flight and weather analytics with departure-delay probability estimates.",
)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


class PredictionRequest(BaseModel):
    month: int = Field(ge=1, le=12)
    day_of_week: int = Field(ge=1, le=7)
    crs_dep_time: int = Field(ge=0, le=2359)
    weather_features: dict[str, float] = Field(default_factory=dict)


@lru_cache(maxsize=2)
def _read_data(path: str, modified_ns: int) -> pd.DataFrame:
    return load_flight_data(Path(path))


def _get_data() -> pd.DataFrame:
    try:
        modified_ns = DATA_PATH.stat().st_mtime_ns
    except OSError as error:
        raise HTTPException(status_code=503, detail=f"Flight data is unavailable: {error}") from error
    try:
        return _read_data(str(DATA_PATH), modified_ns)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        raise HTTPException(status_code=503, detail=f"Could not read flight data: {error}") from error


@lru_cache(maxsize=2)
def _read_model(path: str, modified_ns: int, size: int) -> tuple[object | None, dict[str, float]]:
    if size == 0:
        return None, {}
    try:
        artifact = joblib.load(path)
    except Exception:
        return None, {}

    if isinstance(artifact, dict) and "model" in artifact:
        model = artifact["model"]
        means = artifact.get("feature_means", {})
    else:
        model = artifact
        means = {}
    normalized_means = {str(name): float(value) for name, value in means.items()}
    return model, normalized_means


def _get_model() -> tuple[object | None, dict[str, float]]:
    try:
        stat = MODEL_PATH.stat()
    except OSError:
        return None, {}
    return _read_model(str(MODEL_PATH), stat.st_mtime_ns, stat.st_size)


@app.get("/health")
def health() -> dict:
    model, _ = _get_model()
    return {
        "status": "ok",
        "data_available": DATA_PATH.is_file(),
        "model_available": model is not None,
    }


@app.get("/analytics")
def analytics(origin: str | None = Query(default=None, min_length=3, max_length=3)) -> dict:
    return build_analytics(_get_data(), origin)


@app.post("/predict")
def predict(request: PredictionRequest) -> dict:
    model, feature_means = _get_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="A trained flight delay model is unavailable. Run `python -m backend.train_model` first.",
        )

    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None:
        raise HTTPException(
            status_code=503,
            detail="The model has no feature schema. Train it with the project training script.",
        )

    supplied = {
        "Month": request.month,
        "DayOfWeek": request.day_of_week,
        "CRSDepTime": request.crs_dep_time,
        "DEP_HOUR": request.crs_dep_time // 100,
        **request.weather_features,
    }
    features = {}
    missing = []
    for name in feature_names:
        if name in supplied:
            features[name] = supplied[name]
        elif name in feature_means:
            features[name] = feature_means[name]
        else:
            missing.append(name)

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Provide values for model features without training defaults: {', '.join(missing)}",
        )

    prediction_frame = pd.DataFrame([features], columns=list(feature_names))
    try:
        probability = float(model.predict_proba(prediction_frame)[0][1])
    except (AttributeError, IndexError, TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=f"The loaded model cannot predict: {error}") from error

    return {
        "delay_probability": round(probability, 4),
        "prediction": "Delayed 15+ minutes" if probability >= 0.5 else "On-time or under 15 minutes late",
        "threshold": 0.5,
    }
