from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
DATA_PATH = Path(
    os.getenv("FLIGHT_DATA_PATH", WORKSPACE_ROOT / "merged_flight_weather_data.csv")
).expanduser()
MODEL_PATH = Path(
    os.getenv("MODEL_PATH", PROJECT_ROOT / "backend" / "models" / "flight_delay_model.pkl")
).expanduser()

ANALYTICS_COLUMNS = {
    "Month",
    "FlightDate",
    "Origin",
    "Dest",
    "DepDelayMinutes",
    "DepDel15",
}

MODEL_BASE_FEATURES = ["Month", "DayOfWeek", "CRSDepTime", "DEP_HOUR"]
MODEL_EXCLUDED_COLUMNS = {
    "FlightDate",
    "Origin",
    "Dest",
    "Operating_Airline",
    "Airline",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "Is_Delayed",
}
