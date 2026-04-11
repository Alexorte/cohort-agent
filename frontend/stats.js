const LAST_RESPONSE_KEY = "latestCohortResponse";

const response = JSON.parse(localStorage.getItem(LAST_RESPONSE_KEY) || "null");

const autoBookedCountEl = document.getElementById("auto-booked-count");
const pendingCountEl = document.getElementById("pending-count");
const routineCountEl = document.getElementById("routine-count");

const filtersTableBody = document.getElementById("filters-table-body");
const patientsTableBody = document.getElementById("patients-table-body");
const followupTableBody = document.getElementById("followup-table-body");

function formatFilterValue(key, value) {
  if (key === "age" && value?.operator && value?.value !== undefined) {
    return `${value.operator} ${value.value}`;
  }

  if (key === "age_range" && value?.min !== undefined && value?.max !== undefined) {
    return `${value.min} - ${value.max}`;
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "boolean") {
    return value ? "Sí" : "No";
  }

  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }

  return String(value);
}

function prettifyFilterKey(key) {
  const map = {
    age: "Edad",
    age_range: "Rango de edad",
    include_conditions: "Condiciones incluidas",
    exclude_conditions: "Condiciones excluidas",
    include_allergies: "Alergias incluidas",
    exclude_allergies: "Alergias excluidas",
    include_medications: "Medicaciones incluidas",
    exclude_medications: "Medicaciones excluidas",
    has_allergies: "Tiene alergias",
    has_conditions: "Tiene condiciones",
    has_medications: "Tiene medicaciones",
    table_filters: "Filtros por tabla",
  };
  return map[key] || key;
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

function renderFiltersTable(filters = {}) {
  filtersTableBody.innerHTML = "";

  const entries = Object.entries(filters);

  if (entries.length === 0) {
    filtersTableBody.innerHTML = `
      <tr>
        <td colspan="2" class="empty-cell">Sin filtros</td>
      </tr>
    `;
    return;
  }

  entries.forEach(([key, value]) => {
    const tr = document.createElement("tr");

    const tdKey = document.createElement("td");
    tdKey.textContent = prettifyFilterKey(key);

    const tdValue = document.createElement("td");

    if (key === "table_filters" && Array.isArray(value)) {
      tdValue.innerHTML = value
        .map(
          (item) =>
            `<span class="badge">${item.table}.${item.column} ${item.operator} ${item.value}</span>`
        )
        .join(" ");
    } else {
      tdValue.textContent = formatFilterValue(key, value);
    }

    tr.appendChild(tdKey);
    tr.appendChild(tdValue);
    filtersTableBody.appendChild(tr);
  });
}

function renderPatientsTable(patientSummary = [], followupPlan = [], patientIds = []) {
  patientsTableBody.innerHTML = "";

  if (followupPlan && followupPlan.length > 0) {
    followupPlan.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.PacienteID}</td>
        <td>${row.Edad}</td>
        <td>${row.Genero}</td>
        <td>${row.Provincia}</td>
        <td><span class="priority-chip priority-${(row.priority_level || "").toLowerCase()}">${row.priority_level}</span></td>
      `;
      patientsTableBody.appendChild(tr);
    });
    return;
  }

  if (patientSummary && patientSummary.length > 0) {
    patientSummary.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.PacienteID}</td>
        <td>${row.Edad}</td>
        <td>${row.Genero}</td>
        <td>${row.Provincia}</td>
        <td>—</td>
      `;
      patientsTableBody.appendChild(tr);
    });
    return;
  }

  if (!patientIds || patientIds.length === 0) {
    patientsTableBody.innerHTML = `
      <tr>
        <td colspan="5" class="empty-cell">Sin pacientes</td>
      </tr>
    `;
    return;
  }

  patientIds.forEach((id) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${id}</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
    `;
    patientsTableBody.appendChild(tr);
  });
}

function renderBookingSummary(plan = []) {
  const autoBooked = plan.filter((row) => row.appointment_status === "auto_booked").length;
  const pending = plan.filter((row) => row.appointment_status === "awaiting_user_confirmation").length;
  const routine = plan.filter((row) => row.appointment_status === "routine_followup").length;

  autoBookedCountEl.textContent = String(autoBooked);
  pendingCountEl.textContent = String(pending);
  routineCountEl.textContent = String(routine);
}

function renderAgendaCell(row) {
  if (row.appointment_status === "auto_booked") {
    return `
      <div class="agenda-block">
        <span class="status-badge status-auto">Auto-reservada</span>
        <div class="agenda-card">
          <div class="agenda-main">${formatDate(row.booked_date)} · ${row.booked_time || "—"}</div>
          <div class="agenda-sub">${row.booked_clinic_name || row.booked_clinic || "Clínica"}</div>
          <div class="agenda-sub">${row.booked_city || row.Provincia || ""}</div>
          <div class="agenda-sub">${row.booked_provider_name || row.booked_provider || "Profesional"}</div>
        </div>
      </div>
    `;
  }

  if (row.appointment_status === "awaiting_user_confirmation") {
    const slots = row.suggested_slots || [];

    return `
      <div class="agenda-block">
        <span class="status-badge status-pending">Pendiente de confirmación</span>
        <details class="agenda-dropdown">
          <summary class="agenda-dropdown-summary">
            Ver ${slots.length} propuesta${slots.length === 1 ? "" : "s"}
          </summary>
          <div class="slot-stack">
            ${slots.map((slot) => `
              <div class="slot-card">
                <div class="slot-main">${formatDate(slot.date)} · ${slot.start_time}-${slot.end_time}</div>
                <div class="slot-sub">${slot.clinic_name || slot.clinic_id || "Clínica"}</div>
                <div class="slot-sub">${slot.city || row.Provincia || ""}</div>
                <div class="slot-sub">${slot.provider_name || slot.provider_id || slot.role || "Profesional"}</div>
              </div>
            `).join("")}
          </div>
        </details>
      </div>
    `;
  }

  if (row.appointment_status === "routine_followup") {
    return `
      <div class="agenda-block">
        <span class="status-badge status-routine">Rutinario</span>
        <div class="agenda-note">No se agenda automáticamente. Seguimiento estándar.</div>
      </div>
    `;
  }

  if (row.appointment_status === "needs_manual_review") {
    return `
      <div class="agenda-block">
        <span class="status-badge status-review">Revisión manual</span>
        <div class="agenda-note">No se encontró hueco automático en la ventana prevista.</div>
      </div>
    `;
  }

  return `<span class="muted">Sin información de agenda</span>`;
}

function renderFollowupPlan(plan = []) {
  followupTableBody.innerHTML = "";

  if (!plan || plan.length === 0) {
    followupTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-cell">
          Todavía no se ha generado un plan de seguimiento
        </td>
      </tr>
    `;
    return;
  }

  plan.forEach((row) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${row.PacienteID}</td>
      <td>${row.Edad}</td>
      <td>${row.Provincia}</td>
      <td><span class="priority-chip priority-${(row.priority_level || "").toLowerCase()}">${row.priority_level}</span></td>
      <td>${row.priority_reason}</td>
      <td>${renderAgendaCell(row)}</td>
      <td>${row.suggested_action}</td>
    `;

    followupTableBody.appendChild(tr);
  });
}

if (response) {
  const plan = response.data?.followup_plan ?? [];

  renderFiltersTable(response.filters_applied ?? {});
  renderPatientsTable(response.data?.patient_summary ?? [], plan, response.data?.patient_ids ?? []);
  renderBookingSummary(plan);
  renderFollowupPlan(plan);
} else {
  filtersTableBody.innerHTML = `
    <tr>
      <td colspan="2" class="empty-cell">No hay datos cargados todavía</td>
    </tr>
  `;

  patientsTableBody.innerHTML = `
    <tr>
      <td colspan="5" class="empty-cell">No hay datos cargados todavía</td>
    </tr>
  `;

  followupTableBody.innerHTML = `
    <tr>
      <td colspan="7" class="empty-cell">No hay datos cargados todavía</td>
    </tr>
  `;
}