from __future__ import annotations

import os
import re
from datetime import datetime

import gradio as gr
import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


CSS = """
:root { --ink: #172536; --muted: #667587; --line: #e0e6ed; --blue: #315fe8; --orange: #ed7644; }
body { background: #f4f6f8; }
.gradio-container { max-width: 1040px !important; margin: 0 auto !important; }
#gradio-title h1 { color: var(--ink); font-family: Manrope, sans-serif; font-size: 2rem; }
#gradio-subtitle { color: var(--muted); }
.gradio-container .block { border-color: var(--line) !important; border-radius: 8px !important; }
.gradio-container button.primary { background: var(--blue) !important; border-color: var(--blue) !important; }
.gradio-container button.primary:hover { background: #244cc5 !important; }
footer { display: none !important; }
@media (max-width: 640px) { #gradio-title h1 { font-size: 1.55rem; } }
"""


def predict_delay(
    month: str,
    day_of_week: str,
    departure_time: str,
    visibility: float,
    temperature: float,
    humidity: float,
    wind_speed: float,
    precipitation: float,
) -> tuple[float, str]:
    if not TIME_PATTERN.fullmatch(departure_time or ""):
        raise gr.Error("Enter the scheduled departure time in 24-hour HH:MM format, for example 09:30.")

    parsed_time = datetime.strptime(departure_time, "%H:%M").time()
    payload = {
        "month": MONTHS.index(month) + 1,
        "day_of_week": WEEKDAYS.index(day_of_week) + 1,
        "crs_dep_time": parsed_time.hour * 100 + parsed_time.minute,
        "weather_features": {
            "HOURLYVISIBILITY": visibility,
            "HOURLYDRYBULBTEMPF": temperature,
            "HOURLYRelativeHumidity": humidity,
            "HOURLYWindSpeed": wind_speed,
            "HOURLYPrecip": precipitation,
        },
    }

    try:
        response = requests.post(f"{API_BASE_URL}/predict", json=payload, timeout=30)
    except requests.RequestException as error:
        raise gr.Error(f"Could not reach the FastAPI service at {API_BASE_URL}: {error}") from error

    try:
        result = response.json()
    except ValueError as error:
        raise gr.Error(f"FastAPI returned an invalid response (HTTP {response.status_code}).") from error

    if not response.ok:
        raise gr.Error(result.get("detail", f"Prediction request failed (HTTP {response.status_code})."))

    probability = float(result["delay_probability"])
    return probability * 100, result["prediction"]


with gr.Blocks(
    title="Quick Delay Prediction | Flight Operations",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate", radius_size="sm"),
    css=CSS,
) as demo:
    gr.Markdown("# Quick delay prediction", elem_id="gradio-title")
    gr.Markdown(
        f"Interactive estimate powered by the Flight Operations FastAPI model at `{API_BASE_URL}`.",
        elem_id="gradio-subtitle",
    )

    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("### Flight schedule")
            with gr.Row():
                month = gr.Dropdown(MONTHS, value="January", label="Departure month")
                day_of_week = gr.Dropdown(WEEKDAYS, value="Monday", label="Day of week")
            departure_time = gr.Textbox(
                value="09:00",
                label="Scheduled departure time (HH:MM)",
                placeholder="HH:MM",
                max_lines=1,
                info="Use 24-hour time.",
            )

            gr.Markdown("### Weather conditions")
            with gr.Row():
                visibility = gr.Number(value=10, minimum=0, label="Visibility (miles)")
                temperature = gr.Number(value=55, minimum=-100, maximum=150, label="Temperature (°F)")
            with gr.Row():
                humidity = gr.Number(value=60, minimum=0, maximum=100, label="Relative humidity (%)")
                wind_speed = gr.Number(value=8, minimum=0, label="Wind speed (knots)")
            precipitation = gr.Number(value=0, minimum=0, label="Precipitation (inches)")
            submit = gr.Button("Estimate delay probability", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### Model estimate")
            probability = gr.Number(value=None, label="Delay probability (%)", precision=1, interactive=False)
            classification = gr.Textbox(label="Prediction", interactive=False, lines=2)
            gr.Markdown("The estimate represents the likelihood of a departure delay of 15 minutes or more.")

    submit.click(
        fn=predict_delay,
        inputs=[month, day_of_week, departure_time, visibility, temperature, humidity, wind_speed, precipitation],
        outputs=[probability, classification],
    )


def main() -> None:
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=True,
    )


if __name__ == "__main__":
    main()