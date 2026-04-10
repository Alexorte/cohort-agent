const API_URL = "http://127.0.0.1:8000/chat";

const CHAT_HISTORY_KEY = "cohortChatHistory";
const LAST_RESPONSE_KEY = "latestCohortResponse";
const SESSION_ID_KEY = "cohortSessionId";

const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const followupBtn = document.getElementById("followup-btn");
const resetBtn = document.getElementById("reset-btn");

const cohortIdEl = document.getElementById("cohort-id");
const cohortSizeEl = document.getElementById("cohort-size");
const warningsCountEl = document.getElementById("warnings-count");
const filtersCountEl = document.getElementById("filters-count");

let sessionId = getOrCreateSessionId();

function generateSessionId() {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `session_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
}

function getOrCreateSessionId() {
  const existing = localStorage.getItem(SESSION_ID_KEY);
  if (existing) return existing;

  const created = generateSessionId();
  localStorage.setItem(SESSION_ID_KEY, created);
  return created;
}

function getChatHistory() {
  try {
    return JSON.parse(localStorage.getItem(CHAT_HISTORY_KEY) || "[]");
  } catch (error) {
    console.error("No se pudo leer el historial del chat", error);
    return [];
  }
}

function saveChatHistory(history) {
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(history));
}

function addMessage(text, type = "bot", persist = true) {
  const div = document.createElement("div");
  div.className = `message ${type}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  if (persist) {
    const history = getChatHistory();
    history.push({ text, type });
    saveChatHistory(history);
  }
}

function renderChatHistory() {
  const history = getChatHistory();
  chatMessages.innerHTML = "";

  history.forEach((item) => {
    addMessage(item.text, item.type, false);
  });
}

function countWarnings(response) {
  return (response.warnings?.length || 0) + (response.unknown_terms?.length || 0);
}

function renderSummary(response) {
  if (response.cohort_id !== null && response.cohort_id !== undefined) {
    cohortIdEl.textContent = response.cohort_id;
  }

  if (response.cohort_size !== null && response.cohort_size !== undefined) {
    cohortSizeEl.textContent = response.cohort_size;
  }

  warningsCountEl.textContent = String(countWarnings(response));
  filtersCountEl.textContent = String(
    response.filters_applied ? Object.keys(response.filters_applied).length : 0
  );
}

function resetDashboard() {
  cohortIdEl.textContent = "—";
  cohortSizeEl.textContent = "—";
  warningsCountEl.textContent = "0";
  filtersCountEl.textContent = "0";

  try {
    Plotly.purge("sex-chart");
    Plotly.purge("conditions-chart");
    Plotly.purge("medications-chart");
  } catch (error) {
    console.warn("No se pudieron limpiar algunas gráficas", error);
  }
}

function persistLatestResponse(data) {
  localStorage.setItem(LAST_RESPONSE_KEY, JSON.stringify(data));
}

function restoreLatestResponse() {
  try {
    const raw = localStorage.getItem(LAST_RESPONSE_KEY);
    if (!raw) return;

    const data = JSON.parse(raw);
    renderSummary(data);
    renderCharts(data.data?.charts);
  } catch (error) {
    console.error("No se pudo restaurar la última respuesta", error);
  }
}

function renderSexChart(chart) {
  if (!chart) return;

  Plotly.newPlot(
    "sex-chart",
    [
      {
        labels: chart.labels,
        values: chart.values,
        type: "pie",
        hole: 0.55,
        marker: { colors: chart.colors },
        textinfo: "label+percent",
      },
    ],
    {
      margin: { t: 10, b: 10, l: 10, r: 10 },
      showlegend: true,
    },
    { responsive: true }
  );
}

function renderBarChart(containerId, chart) {
  if (!chart) return;

  Plotly.newPlot(
    containerId,
    [
      {
        x: chart.x,
        y: chart.y,
        type: "bar",
        marker: { color: chart.colors },
      },
    ],
    {
      margin: { t: 10, b: 70, l: 45, r: 10 },
      xaxis: { tickangle: -20 },
      yaxis: { title: "Frecuencia" },
    },
    { responsive: true }
  );
}

function renderCharts(charts) {
  if (!charts) return;

  if (charts.sex_distribution) {
    renderSexChart(charts.sex_distribution);
  }

  if (charts.top_conditions) {
    renderBarChart("conditions-chart", charts.top_conditions);
  }

  if (charts.top_medications) {
    renderBarChart("medications-chart", charts.top_medications);
  }
}

async function sendMessage(message, userVisibleMessage = null) {
  const visibleMessage = userVisibleMessage || message;
  addMessage(visibleMessage, "user");

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });

    const data = await response.json();

    addMessage(data.message || "Respuesta recibida.", "bot");
    renderSummary(data);
    renderCharts(data.data?.charts);
    persistLatestResponse(data);

    return data;
  } catch (error) {
    addMessage("Error al conectar con el backend.", "bot");
    console.error(error);
    return null;
  }
}

function resetConversation() {
  localStorage.removeItem(CHAT_HISTORY_KEY);
  localStorage.removeItem(LAST_RESPONSE_KEY);

  sessionId = generateSessionId();
  localStorage.setItem(SESSION_ID_KEY, sessionId);

  chatMessages.innerHTML = "";
  resetDashboard();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = chatInput.value.trim();
  if (!message) return;

  chatInput.value = "";
  await sendMessage(message);
});

followupBtn.addEventListener("click", async () => {
  followupBtn.disabled = true;
  const originalText = followupBtn.textContent;
  followupBtn.textContent = "Generando...";

  await sendMessage("Prepara seguimiento clinico", "Preparar seguimiento clínico");

  followupBtn.disabled = false;
  followupBtn.textContent = originalText;
});

resetBtn.addEventListener("click", () => {
  resetConversation();
});

window.addEventListener("load", () => {
  renderChatHistory();
  restoreLatestResponse();
});