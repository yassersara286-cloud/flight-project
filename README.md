# Flight Delay Analytics

A deployable FastAPI and Streamlit application for exploring flight and weather data and predicting departure delays.

## Project layout

- `backend/`: API, analytics, model training, and tests.
- `frontend/`: Streamlit dashboard.

The source CSV and original model file remain in the parent workspace. The application reads the merged dataset from `FLIGHT_DATA_PATH`; it does not copy the 180 MB CSV into this project. The original `flight_delay_model.pkl` is empty (0 bytes). A valid model trained from the merged data is stored at `backend/models/flight_delay_model.pkl`.

## Local setup

1. Create a virtual environment and install backend and frontend requirements:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt -r frontend\requirements.txt
   ```

2. From the project directory, start the API:

   ```powershell
   uvicorn backend.app.main:app --reload --port 8000
   ```

3. In a second terminal, start the dashboard:

   ```powershell
   streamlit run frontend\app.py
   ```

The dashboard is available at `http://localhost:8501`; API documentation is at `http://localhost:8000/docs`.

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

The compose configuration mounts the parent CSV read-only and persists trained models in `backend/models`. The API listens on port 8000 and the dashboard on port 8501. Copy `.env.example` to `.env` to override the container paths. If changing the data file itself, update the host path in the API service volume mapping as well.

For cloud deployment, deploy the API and Streamlit app as separate services, configure `FLIGHT_DATA_PATH` and `MODEL_PATH` to mounted or object-storage-backed files, and expose ports 8000 and 8501 respectively. Keep model and data files outside the container image.

## API

- `GET /health`: application and model availability.
- `GET /analytics`: dataset KPIs and chart-ready aggregations.
- `POST /predict`: estimate the probability that a flight departure is at least 15 minutes late.

Prediction input fields are `month`, `day_of_week`, `crs_dep_time`, and an optional mapping of numeric weather features. The model's persisted feature names and order are used for inference.

## Tests

```powershell
python -m unittest discover -s backend\tests -v
```
