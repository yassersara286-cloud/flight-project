const apiBase = window.location.origin;
const numberFormat = new Intl.NumberFormat("en-US");
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const state = { health: null, summary: null };

const byId = (id) => document.getElementById(id);
const escapeText = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));

async function apiRequest(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function setSystemStatus(health) {
  state.health = health;
  const dot = byId("status-dot");
  dot.classList.toggle("ready", health.status === "ok" && health.data_available);
  dot.classList.toggle("unavailable", !health.data_available);
  byId("system-status").textContent = health.data_available ? "Data connected" : "Data unavailable";
  byId("model-dot").classList.toggle("ready", health.model_available);
  byId("model-dot").classList.toggle("unavailable", !health.model_available);
  byId("model-status").textContent = health.model_available ? "Model ready" : "Model unavailable";
}

function showError(id, message) {
  const element = byId(id);
  element.textContent = message;
  element.classList.remove("hidden");
}

function clearError(id) {
  const element = byId(id);
  element.textContent = "";
  element.classList.add("hidden");
}

function renderMetrics(summary) {
  byId("metric-flights").textContent = numberFormat.format(summary.total_flights);
  byId("metric-delayed").textContent = numberFormat.format(summary.delayed_flights);
  byId("metric-rate").textContent = `${Number(summary.delay_rate).toFixed(1)}%`;
  byId("metric-average").textContent = `${Number(summary.average_delay_minutes).toFixed(1)} min`;
}

function renderTrendChart(elementId, rows, key, colorClass = "") {
  const container = byId(elementId);
  if (!rows.length) {
    container.innerHTML = '<p class="empty-bars">No monthly data is available for this selection.</p>';
    return;
  }

  const width = 620;
  const height = 220;
  const plot = { left: 43, right: 14, top: 12, bottom: 31 };
  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const maxValue = Math.max(1, ...rows.map((row) => Number(row[key]) || 0));
  const ceiling = Math.ceil(maxValue / 5) * 5 || 5;
  const points = rows.map((row, index) => {
    const x = rows.length === 1 ? plot.left + plotWidth / 2 : plot.left + (index / (rows.length - 1)) * plotWidth;
    const y = plot.top + plotHeight - (Number(row[key]) / ceiling) * plotHeight;
    return { x, y, label: monthNames[Number(row.month) - 1] || String(row.month), value: Number(row[key]) || 0 };
  });
  const line = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const area = `${line} L${points[points.length - 1].x},${plot.top + plotHeight} L${points[0].x},${plot.top + plotHeight} Z`;
  const grid = [0, 0.25, 0.5, 0.75, 1].map((fraction) => {
    const y = plot.top + plotHeight * fraction;
    const label = (ceiling * (1 - fraction)).toFixed(0);
    return `<line class="chart-grid-line" x1="${plot.left}" y1="${y}" x2="${width - plot.right}" y2="${y}"/><text class="chart-axis-label" x="${plot.left - 9}" y="${y + 3}" text-anchor="end">${label}</text>`;
  }).join("");
  const labels = points.map((point) => `<text class="chart-axis-label" x="${point.x}" y="${height - 7}" text-anchor="middle">${escapeText(point.label)}</text>`).join("");
  const dots = points.map((point) => `<circle class="chart-point ${colorClass ? "orange-point" : ""}" cx="${point.x}" cy="${point.y}" r="4"><title>${escapeText(point.label)}: ${point.value.toFixed(1)}</title></circle>`).join("");
  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${grid}<path class="chart-area ${colorClass ? "orange-area" : ""}" d="${area}"/><path class="chart-line ${colorClass ? "orange-line" : ""}" d="${line}"/>${dots}${labels}</svg>`;
}

function renderBars(elementId, rows, labelKey) {
  const container = byId(elementId);
  if (!rows.length) {
    container.innerHTML = '<p class="empty-bars">No flight volume data is available.</p>';
    return;
  }
  const maxCount = Math.max(1, ...rows.map((row) => Number(row.flights)));
  container.innerHTML = rows.map((row) => {
    const width = Math.max(2, (Number(row.flights) / maxCount) * 100);
    return `<div class="bar-row"><span class="bar-name" title="${escapeText(row[labelKey])}">${escapeText(row[labelKey])}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div><span class="bar-count">${numberFormat.format(row.flights)}</span></div>`;
  }).join("");
}

function renderAnalytics(summary) {
  state.summary = summary;
  renderMetrics(summary);
  renderTrendChart("delay-chart", summary.monthly || [], "delay_rate");
  renderTrendChart("average-chart", summary.monthly || [], "average_delay_minutes", "orange");
  renderBars("origin-bars", summary.top_origins || [], "origin");
  renderBars("route-bars", summary.top_routes || [], "route");
  const filter = byId("origin-filter");
  const selected = filter.value;
  const options = ['<option value="">All airports</option>', ...(summary.origins || []).map((origin) => `<option value="${escapeText(origin)}">${escapeText(origin)}</option>`)];
  filter.innerHTML = options.join("");
  filter.value = selected;
}

async function loadAnalytics(origin = "") {
  clearError("overview-error");
  byId("overview-loading").classList.remove("hidden");
  byId("overview-content").classList.add("hidden");
  try {
    const query = origin ? `?origin=${encodeURIComponent(origin)}` : "";
    const summary = await apiRequest(`/analytics${query}`);
    renderAnalytics(summary);
    byId("overview-content").classList.remove("hidden");
  } catch (error) {
    showError("overview-error", error.message);
  } finally {
    byId("overview-loading").classList.add("hidden");
  }
}

function initializeSelects() {
  byId("month-input").innerHTML = monthNames.map((name, index) => `<option value="${index + 1}">${new Date(2000, index, 1).toLocaleString("en-US", { month: "long" })}</option>`).join("");
  byId("weekday-input").innerHTML = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day, index) => `<option value="${index + 1}">${day}</option>`).join("");
}

function navigate(viewName) {
  const prediction = viewName === "prediction";
  document.querySelectorAll(".nav-link").forEach((button) => {
    const active = button.dataset.view === viewName;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  byId("overview-view").hidden = prediction;
  byId("overview-view").classList.toggle("active", !prediction);
  byId("prediction-view").hidden = !prediction;
  byId("prediction-view").classList.toggle("active", prediction);
  byId("breadcrumb-current").textContent = prediction ? "PREDICTION" : "OVERVIEW";
  document.title = prediction ? "Delay Prediction | Flight Operations" : "Flight Operations | Departure Intelligence";
}

async function submitPrediction(event) {
  event.preventDefault();
  clearError("prediction-error");
  const button = byId("predict-button");
  button.disabled = true;
  button.textContent = "Calculating";
  const data = new FormData(event.currentTarget);
  const [hour, minute] = String(data.get("departure_time")).split(":").map(Number);
  const payload = {
    month: Number(data.get("month")),
    day_of_week: Number(data.get("day_of_week")),
    crs_dep_time: hour * 100 + minute,
    weather_features: {
      HOURLYVISIBILITY: Number(data.get("visibility")),
      HOURLYDRYBULBTEMPF: Number(data.get("temperature")),
      HOURLYRelativeHumidity: Number(data.get("humidity")),
      HOURLYWindSpeed: Number(data.get("wind_speed")),
      HOURLYPrecip: Number(data.get("precipitation")),
    },
  };

  try {
    const prediction = await apiRequest("/predict", { method: "POST", body: JSON.stringify(payload) });
    const probability = Number(prediction.delay_probability);
    byId("result-empty").classList.add("hidden");
    byId("result-populated").classList.remove("hidden");
    byId("result-probability").textContent = `${(probability * 100).toFixed(1)}%`;
    byId("result-classification").textContent = prediction.prediction;
    const fill = byId("probability-fill");
    fill.style.width = `${Math.min(100, Math.max(0, probability * 100))}%`;
    fill.classList.toggle("high", probability >= prediction.threshold);
  } catch (error) {
    showError("prediction-error", error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Calculate probability";
  }
}

async function initialize() {
  byId("today-label").textContent = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date());
  initializeSelects();
  document.querySelectorAll(".nav-link").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
  byId("origin-filter").addEventListener("change", (event) => loadAnalytics(event.target.value));
  byId("prediction-form").addEventListener("submit", submitPrediction);

  try {
    const health = await apiRequest("/health");
    setSystemStatus(health);
    await loadAnalytics();
  } catch (error) {
    byId("system-status").textContent = "API unavailable";
    byId("status-dot").classList.add("unavailable");
    showError("overview-error", error.message);
    byId("overview-loading").classList.add("hidden");
  }
}

initialize();
