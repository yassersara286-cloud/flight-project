from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.settings import ANALYTICS_COLUMNS


REQUIRED_COLUMNS = {"Month", "DepDel15", "DepDelayMinutes"}


def load_flight_data(data_path: Path) -> pd.DataFrame:
    if not data_path.is_file():
        raise FileNotFoundError(f"Flight data file was not found: {data_path}")

    frame = pd.read_csv(
        data_path,
        usecols=lambda column: column in ANALYTICS_COLUMNS,
        low_memory=False,
    )
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Flight data is missing required columns: {', '.join(sorted(missing))}")

    frame["Month"] = pd.to_numeric(frame["Month"], errors="coerce")
    frame["DepDel15"] = pd.to_numeric(frame["DepDel15"], errors="coerce").fillna(0)
    frame["DepDelayMinutes"] = pd.to_numeric(frame["DepDelayMinutes"], errors="coerce")
    return frame


def build_analytics(frame: pd.DataFrame, origin: str | None = None) -> dict:
    filtered = frame
    if origin and "Origin" in frame.columns:
        filtered = frame.loc[frame["Origin"].astype(str).str.upper() == origin.upper()]

    if filtered.empty:
        return {
            "total_flights": 0,
            "delayed_flights": 0,
            "delay_rate": 0.0,
            "average_delay_minutes": 0.0,
            "origins": [],
            "monthly": [],
            "top_origins": [],
            "top_routes": [],
        }

    delayed = filtered["DepDel15"].eq(1)
    positive_delays = filtered.loc[filtered["DepDelayMinutes"] > 0, "DepDelayMinutes"]
    monthly_rows = []
    for month, group in filtered.dropna(subset=["Month"]).groupby("Month", sort=True):
        month_delayed = group["DepDel15"].eq(1)
        month_positive_delays = group.loc[
            group["DepDelayMinutes"] > 0, "DepDelayMinutes"
        ]
        monthly_rows.append(
            {
                "month": int(month),
                "flights": int(len(group)),
                "delay_rate": round(float(month_delayed.mean() * 100), 2),
                "average_delay_minutes": round(
                    float(month_positive_delays.mean()) if not month_positive_delays.empty else 0.0,
                    2,
                ),
            }
        )

    top_origins = []
    origins = []
    if "Origin" in frame.columns:
        origins = sorted(frame["Origin"].dropna().astype(str).str.upper().unique().tolist())
        top_origins = [
            {"origin": str(code), "flights": int(count)}
            for code, count in filtered["Origin"].value_counts().head(10).items()
        ]

    top_routes = []
    if {"Origin", "Dest"}.issubset(filtered.columns):
        routes = (
            filtered.groupby(["Origin", "Dest"], observed=True)
            .size()
            .sort_values(ascending=False)
            .head(10)
        )
        top_routes = [
            {"route": f"{origin_code} - {destination_code}", "flights": int(count)}
            for (origin_code, destination_code), count in routes.items()
        ]

    return {
        "total_flights": int(len(filtered)),
        "delayed_flights": int(delayed.sum()),
        "delay_rate": round(float(delayed.mean() * 100), 2),
        "average_delay_minutes": round(
            float(positive_delays.mean()) if not positive_delays.empty else 0.0,
            2,
        ),
        "origins": origins,
        "monthly": monthly_rows,
        "top_origins": top_origins,
        "top_routes": top_routes,
    }
