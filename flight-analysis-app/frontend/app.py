from __future__ import annotations

import calendar
import os
from datetime import time

import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
CHART_COLORS = {
    "ink": "#182b32",
    "teal": "#147d78",
    "coral": "#dd684f",
    "gold": "#d7a940",
    "muted": "#718080",
    "grid": "#e4e9e5",
    "paper": "#f5f7f3",
}

st.set_page_config(page_title="Flight Operations", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');
    :root {
        --ink: #182b32;
        --teal: #147d78;
        --coral: #dd684f;
        --gold: #d7a940;
        --paper: #f5f7f3;
        --line: #e0e7e1;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    .stApp { background: var(--paper); }
    [data-testid="stSidebar"] { background: #eaf0eb; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] h1 { font-family: 'DM Serif Display', Georgia, serif; font-size: 1.65rem; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
    h1, h2, h3 { color: var(--ink) !important; }
    h1 { font-family: 'DM Serif Display', Georgia, serif; font-size: 2.55rem; font-weight: 400; }
    .eyebrow { color: var(--teal); font-size: .72rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .25rem; }
    .section-note { color: #637272; margin-top: -.6rem; margin-bottom: 1.2rem; }
    [data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-top: 3px solid var(--teal); padding: 1rem 1.15rem; border-radius: 5px; min-height: 112px; }
    [data-testid="stMetricLabel"] { color: #5a6c6b; font-size: .8rem; }
    [data-testid="stMetricValue"] { color: var(--ink); font-weight: 700; }
    [data-testid="stAlert"] p { color: var(--ink) !important; }
    [data-testid="stForm"] { background: #fff; border: 1px solid var(--line); border-radius: 5px; padding: 1.25rem; }
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button { background: var(--teal); color: #fff; border: 0; border-radius: 4px; font-weight: 600; }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover { background: #0e625e; color: #fff; border: 0; }
    @media (max-width: 700px) {
      h1 { font-size: 2rem; }
      .block-container { padding-left: 1rem; padding-right: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=120, show_spinner=False)
def get_health() -> dict:
    response = requests.get(f"{API_BASE_URL}/health", timeout=10)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120, show_spinner=False)
def get_analytics(origin: str | None) -> dict:
    params = {"origin": origin} if origin else None
    response = requests.get(f"{API_BASE_URL}/analytics", params=params, timeout=240)
    response.raise_for_status()
    return response.json()


def show_api_error(error: requests.RequestException) -> None:
    response = getattr(error, "response", None)
    detail = ""
    if response is not None:
        try:
            detail = response.json().get("detail", "")
        except (ValueError, AttributeError):
            detail = response.text
    st.error(detail or f"The analytics API is not reachable at {API_BASE_URL}.")
    st.code("uvicorn backend.app.main:app --reload --port 8000", language="powershell")


def chart_layout(figure: go.Figure, height: int = 330) -> go.Figure:
    figure.update_layout(
        height=height,
        margin={"l": 12, "r": 12, "t": 20, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Sans, sans-serif", "color": CHART_COLORS["ink"]},
        xaxis={"gridcolor": CHART_COLORS["grid"], "zerolinecolor": CHART_COLORS["grid"]},
        yaxis={"gridcolor": CHART_COLORS["grid"], "zerolinecolor": CHART_COLORS["grid"]},
        showlegend=False,
    )
    return figure


def render_overview() -> None:
    st.markdown('<p class="eyebrow">Network overview</p>', unsafe_allow_html=True)
    st.title("Departure performance")
    st.markdown(
        '<p class="section-note">A weather-aware view of scheduled departures and delay patterns.</p>',
        unsafe_allow_html=True,
    )

    try:
        health = get_health()
        if not health.get("data_available"):
            st.error("Flight data is missing. Set FLIGHT_DATA_PATH to the merged flight and weather CSV.")
            return
        if not health.get("model_available"):
            st.warning("Prediction model unavailable. Analytics are ready; train a model to enable predictions.")
        initial = get_analytics(None)
    except requests.RequestException as error:
        show_api_error(error)
        return

    origins = ["All origins", *initial.get("origins", [])]
    selected_origin = st.sidebar.selectbox("Departure airport", origins)
    origin_filter = None if selected_origin == "All origins" else selected_origin
    try:
        summary = initial if origin_filter is None else get_analytics(origin_filter)
    except requests.RequestException as error:
        show_api_error(error)
        return

    metric_columns = st.columns(4)
    metrics = [
        ("Flights", f"{summary['total_flights']:,}"),
        ("Delayed 15+ min", f"{summary['delayed_flights']:,}"),
        ("Delay rate", f"{summary['delay_rate']:.1f}%"),
        ("Avg. positive delay", f"{summary['average_delay_minutes']:.1f} min"),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, value)

    st.markdown("### Delay patterns")
    monthly = summary.get("monthly", [])
    if monthly:
        month_labels = [calendar.month_abbr[row["month"]] for row in monthly]
        left, right = st.columns((1.35, 1))
        with left:
            figure = go.Figure(
                go.Scatter(
                    x=month_labels,
                    y=[row["delay_rate"] for row in monthly],
                    mode="lines+markers",
                    line={"color": CHART_COLORS["teal"], "width": 3},
                    marker={"size": 7, "color": CHART_COLORS["teal"]},
                    fill="tozeroy",
                    fillcolor="rgba(20,125,120,0.09)",
                    hovertemplate="%{x}<br>Delay rate: %{y:.1f}%<extra></extra>",
                )
            )
            figure.update_yaxes(title="Flights delayed 15+ min (%)", rangemode="tozero")
            st.plotly_chart(chart_layout(figure), width="stretch", config={"displayModeBar": False})
        with right:
            figure = px.bar(
                x=month_labels,
                y=[row["average_delay_minutes"] for row in monthly],
                labels={"x": "Month", "y": "Minutes"},
                color_discrete_sequence=[CHART_COLORS["coral"]],
            )
            figure.update_yaxes(title="Positive delay (minutes)", rangemode="tozero")
            st.plotly_chart(chart_layout(figure), width="stretch", config={"displayModeBar": False})

    origin_rows = summary.get("top_origins", [])
    route_rows = summary.get("top_routes", [])
    if origin_rows or route_rows:
        st.markdown("### Busiest departure points and routes")
        left, right = st.columns(2)
        if origin_rows:
            origin_figure = px.bar(
                x=[row["flights"] for row in origin_rows],
                y=[row["origin"] for row in origin_rows],
                orientation="h",
                labels={"x": "Flights", "y": "Airport"},
                color_discrete_sequence=[CHART_COLORS["gold"]],
            )
            origin_figure.update_yaxes(autorange="reversed")
            left.plotly_chart(
                chart_layout(origin_figure), width="stretch", config={"displayModeBar": False}
            )
        if route_rows:
            route_figure = px.bar(
                x=[row["flights"] for row in route_rows],
                y=[row["route"] for row in route_rows],
                orientation="h",
                labels={"x": "Flights", "y": "Route"},
                color_discrete_sequence=[CHART_COLORS["teal"]],
            )
            route_figure.update_yaxes(autorange="reversed")
            right.plotly_chart(
                chart_layout(route_figure), width="stretch", config={"displayModeBar": False}
            )


def render_prediction() -> None:
    st.markdown('<p class="eyebrow">Flight planning</p>', unsafe_allow_html=True)
    st.title("Delay probability")
    st.markdown(
        '<p class="section-note">Estimate the chance of a departure delay of 15 minutes or more.</p>',
        unsafe_allow_html=True,
    )
    try:
        health = get_health()
    except requests.RequestException as error:
        show_api_error(error)
        return

    if not health.get("model_available"):
        st.warning("No trained model is available. Run the backend training command, then refresh this page.")
        st.code("python -m backend.train_model", language="powershell")
        return

    with st.form("flight_prediction"):
        schedule_column, weather_column = st.columns(2)
        with schedule_column:
            st.markdown("#### Schedule")
            month = st.selectbox("Departure month", range(1, 13), format_func=lambda value: calendar.month_name[value])
            day_of_week = st.selectbox(
                "Day of week", range(1, 8), format_func=lambda value: calendar.day_name[value - 1]
            )
            departure_time = st.time_input("Scheduled departure time (HH:MM)", value=time(9, 0), step=300)
        with weather_column:
            st.markdown("#### Weather conditions")
            visibility = st.number_input("Visibility (miles)", min_value=0.0, value=10.0, step=0.5)
            temperature = st.number_input("Dry-bulb temperature (°F)", min_value=-100.0, max_value=150.0, value=55.0, step=1.0)
            humidity = st.number_input("Relative humidity (%)", min_value=0.0, max_value=100.0, value=60.0, step=1.0)
            wind_speed = st.number_input("Wind speed (knots)", min_value=0.0, value=8.0, step=1.0)
            precipitation = st.number_input("Precipitation (inches)", min_value=0.0, value=0.0, step=0.01)
        submitted = st.form_submit_button("Estimate delay probability")

    if submitted:
        payload = {
            "month": month,
            "day_of_week": day_of_week,
            "crs_dep_time": departure_time.hour * 100 + departure_time.minute,
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
            response.raise_for_status()
            prediction = response.json()
        except requests.RequestException as error:
            show_api_error(error)
            return

        probability = prediction["delay_probability"]
        st.markdown("### Estimate")
        result_column, probability_column = st.columns((1, 2))
        result_column.metric("Delay probability", f"{probability:.1%}")
        result_column.write(prediction["prediction"])
        probability_column.progress(probability, text="Probability of a 15+ minute departure delay")
        st.caption("This estimate is based on the trained model and supplied schedule and weather conditions.")


def main() -> None:
    st.sidebar.markdown("<p class='eyebrow'>Flight operations</p>", unsafe_allow_html=True)
    st.sidebar.title("Performance desk")
    page = st.sidebar.radio("Workspace", ["Overview", "Predict a flight"], label_visibility="collapsed")
    st.sidebar.markdown("---")
    st.sidebar.caption("Flight and weather analysis")

    if page == "Overview":
        render_overview()
    else:
        render_prediction()


if __name__ == "__main__":
    main()
