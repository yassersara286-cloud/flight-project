# Flight Delay Analytics

A deployable FastAPI application with a responsive HTML, CSS, and JavaScript frontend for exploring flight and weather data and predicting departure delays.

## Project layout

- `backend/`: API, analytics, model training, and tests.
- `frontend/`: static web dashboard served directly by FastAPI, plus an optional Gradio prediction client.

The source CSV and original model file remain in the parent workspace. The application reads the merged dataset from `FLIGHT_DATA_PATH`; it does not copy the 180 MB CSV into this project. The original `flight_delay_model.pkl` is empty (0 bytes). A valid model trained from the merged data is stored at `backend/models/flight_delay_model.pkl`.

## Local setup

1. Create a virtual environment and install the API requirements:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   ```

2. From the project directory, start the application:

   ```powershell
   uvicorn backend.app.main:app --reload --port 8000
   ```

The dashboard is available at `http://localhost:8000`; API documentation is at `http://localhost:8000/docs`.

## Optional Gradio predictor

The Gradio interface is a separate client of the existing FastAPI prediction endpoint. It does not load a second model or change the main HTML/CSS dashboard.

Install its optional dependencies and start it in another terminal while FastAPI is running:

```powershell
pip install -r frontend\gradio-requirements.txt
python frontend\gradio_app.py
```

Open `http://localhost:7860`. The client uses `API_BASE_URL` (default `http://127.0.0.1:8000`) and sends predictions to `POST /predict`. In Docker Compose, the optional Gradio service is available on port 7860 and connects to the API service over the Compose network.

By default, local settings point to `merged_flight_weather_data.csv` in the parent workspace. Set `FLIGHT_DATA_PATH` and `MODEL_PATH` to override them.

## Train a model

The source `flight_delay_model.pkl` is a zero-byte placeholder and cannot be loaded. Train a valid estimator from the merged data:

```powershell
python -m backend.train_model
```

The trainer samples up to 200,000 rows by default to keep memory and runtime manageable. Set `TRAIN_SAMPLE_SIZE` to change the limit, or `0` to use all rows. The resulting model is written to `backend/models/flight_delay_model.pkl`. Set `MODEL_PATH` if you need another location.

## Docker

From this directory, run:

```powershell
docker compose up --build
```

The compose configuration mounts the parent CSV read-only, persists trained models in `backend/models`, and serves the dashboard and API on port 8000. It also starts the optional Gradio predictor on port 7860. Copy `.env.example` to `.env` to override the container paths. If changing the data file itself, update the host path in the API service volume mapping as well.

For cloud deployment, deploy the FastAPI container and configure `FLIGHT_DATA_PATH` and `MODEL_PATH` to mounted or object-storage-backed files. The dashboard is served from the same origin as the API. Keep model and data files outside the container image.

## API

- `GET /health`: application and model availability.
- `GET /analytics`: dataset KPIs and chart-ready aggregations.
- `POST /predict`: estimate the probability that a flight departure is at least 15 minutes late.

Prediction input fields are `month`, `day_of_week`, `crs_dep_time`, and an optional mapping of numeric weather features. The model's persisted feature names and order are used for inference.

## Tests

```powershell
python -m unittest discover -s backend\tests -v
```
