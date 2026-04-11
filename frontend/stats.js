const LAST_RESPONSE_KEY = "latestCohortResponse";

let currentResponse = JSON.parse(localStorage.getItem(LAST_RESPONSE_KEY) || "null");

const cohortIdEl = document.getElementById("stats-cohort-id");
const cohortSizeEl = document.getElementById("stats-cohort-size");
const warningsCountEl = document.getElementById("stats-warnings-count");
const filtersCountEl = document.getElementById("stats-filters-count");
const warningsContent = document.getElementById("warnings-content");

const autoBookedCountEl = document.getElementById("auto-booked-count");
const pendingCountEl = document.getElementById("pending-count");
const routineCountEl = document.getElementById("routine-count");

const filtersTableBody = document.getElementById("filters-table-body");
const patientsTableBody = document.getElementById("patients-table-body");
const followupTableBody = document.getElementById("followup-table-body");

function setText(el, value) {
  if (el) el.textContent = value;
}

function setHTML(el, value) {
  if (el) el.innerHTML = value;
}

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

function renderWarnings(warnings = [], unknownTerms = []) {
  const count = (warnings?.length || 0) + (unknownTerms?.length || 0);
  setText(warningsCountEl, String(count));

  if (!warningsContent) return;

  if ((!warnings || warnings.length === 0) && (!unknownTerms || unknownTerms.length === 0)) {
    setHTML(warningsContent, `<p class="muted">Sin warnings</p>`);
    return;
  }

  let html = "<ul>";

  warnings.forEach((warning) => {
    html += `<li>${warning}</li>`;
  });

  if (unknownTerms.length > 0) {
    html += `<li>Términos no reconocidos: ${unknownTerms.join(", ")}</li>`;
  }

  html += "</ul>";
  setHTML(warningsContent, html);
}

function renderFiltersTable(filters = {}) {
  if (!filtersTableBody) return;

  filtersTableBody.innerHTML = "";

  const entries = Object.entries(filters);
  setText(filtersCountEl, String(entries.length));

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

function renderPatientsTable(followupPlan = [], patientSummary = [], patientIds = []) {
  if (!patientsTableBody) return;

  patientsTableBody.innerHTML = "";

  if (followupPlan && followupPlan.length > 0) {
    followupPlan.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.PacienteID}</td>
        <td>${row.Edad ?? "—"}</td>
        <td>${row.Genero ?? "—"}</td>
        <td>${row.Provincia ?? "—"}</td>
        <td><span class="priority-chip priority-${(row.priority_level || "").toLowerCase()}">${row.priority_level || "—"}</span></td>
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
        <td>${row.Edad ?? "—"}</td>
        <td>${row.Genero ?? "—"}</td>
        <td>${row.Provincia ?? "—"}</td>
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

  setText(autoBookedCountEl, String(autoBooked));
  setText(pendingCountEl, String(pending));
  setText(routineCountEl, String(routine));
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

          <div class="agenda-actions">
            <button
              class="slot-action-btn cancel-booking-btn"
              data-patient-id="${row.PacienteID}"
              data-slot-id="${row.booked_slot_id}"
            >
              Cancelar reserva
            </button>

            <button
              class="slot-action-btn reschedule-booking-btn"
              data-patient-id="${row.PacienteID}"
              data-slot-id="${row.booked_slot_id}"
              data-province="${row.Provincia}"
            >
              Modificar cita
            </button>
          </div>
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

                <div class="agenda-actions">
                  <button
                    class="slot-action-btn confirm-slot-btn"
                    data-patient-id="${row.PacienteID}"
                    data-slot-id="${slot.slot_id}"
                  >
                    Reservar esta cita
                  </button>
                </div>
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

  if (row.appointment_status === "cancelled_by_user") {
    return `
      <div class="agenda-block">
        <span class="status-badge status-review">Cancelada</span>
        <div class="agenda-note">La reserva automática ha sido cancelada por el usuario.</div>
      </div>
    `;
  }

  if (row.appointment_status === "confirmed_by_user") {
    return `
      <div class="agenda-block">
        <span class="status-badge status-auto">Reservada por confirmación</span>
        <div class="agenda-card">
          <div class="agenda-main">${formatDate(row.booked_date)} · ${row.booked_time || "—"}</div>
          <div class="agenda-sub">${row.booked_clinic_name || row.booked_clinic || "Clínica"}</div>
          <div class="agenda-sub">${row.booked_city || row.Provincia || ""}</div>
          <div class="agenda-sub">${row.booked_provider_name || row.booked_provider || "Profesional"}</div>
        </div>
      </div>
    `;
  }

  return `<span class="muted">Sin información de agenda</span>`;
}

function renderFollowupPlan(plan = []) {
  if (!followupTableBody) return;

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
      <td>${row.Edad ?? "—"}</td>
      <td>${row.Provincia ?? "—"}</td>
      <td><span class="priority-chip priority-${(row.priority_level || "").toLowerCase()}">${row.priority_level || "—"}</span></td>
      <td>${row.priority_reason || "—"}</td>
      <td>${renderAgendaCell(row)}</td>
      <td>${row.suggested_action || "—"}</td>
    `;

    followupTableBody.appendChild(tr);
  });
}

function saveCurrentResponse() {
  localStorage.setItem(LAST_RESPONSE_KEY, JSON.stringify(currentResponse));
}

function findFollowupRow(patientId) {
  const plan = currentResponse?.data?.followup_plan || [];
  return plan.find((row) => row.PacienteID === patientId);
}

function rerenderStatsPage() {
  if (!currentResponse) return;

  const plan = currentResponse.data?.followup_plan ?? [];

  setText(cohortIdEl, currentResponse.cohort_id ?? "—");
  setText(cohortSizeEl, currentResponse.cohort_size ?? "—");

  renderFiltersTable(currentResponse.filters_applied ?? {});
  renderPatientsTable(
    plan,
    currentResponse.data?.patient_summary ?? [],
    currentResponse.data?.patient_ids ?? []
  );
  renderBookingSummary(plan);
  renderFollowupPlan(plan);
  renderWarnings(currentResponse.warnings ?? [], currentResponse.unknown_terms ?? []);
}

async function cancelBooking(patientId, slotId, button) {
  button.disabled = true;
  button.textContent = "Cancelando...";

  try {
    await fetch("http://127.0.0.1:8000/actions/cancel-booking", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        slot_id: slotId,
      }),
    });

    const row = findFollowupRow(patientId);
    if (!row) return;

    row.appointment_status = "cancelled_by_user";
    row.booked_slot_id = null;
    row.booked_date = null;
    row.booked_time = null;
    row.booked_clinic = null;
    row.booked_clinic_name = null;
    row.booked_city = null;
    row.booked_address = null;
    row.booked_provider = null;
    row.booked_provider_name = null;
    row.booked_provider_role = null;

    saveCurrentResponse();
    rerenderStatsPage();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = "Cancelar reserva";
  }
}

async function rescheduleBooking(patientId, currentSlotId, province, button) {
  button.disabled = true;
  button.textContent = "Buscando...";

  try {
    const response = await fetch("http://127.0.0.1:8000/actions/reschedule-booking", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        current_slot_id: currentSlotId,
        province: province,
      }),
    });

    const result = await response.json();
    const row = findFollowupRow(patientId);
    if (!row) return;

    if (result.new_slot_id) {
      row.appointment_status = "auto_booked";
      row.booked_slot_id = result.new_slot_id;
      row.booked_date = result.booked_date;
      row.booked_time = result.booked_time;
      row.booked_clinic = result.booked_clinic;
      row.booked_clinic_name = result.booked_clinic_name;
      row.booked_city = result.booked_city;
      row.booked_address = result.booked_address;
      row.booked_provider = result.booked_provider;
      row.booked_provider_name = result.booked_provider_name;
      row.booked_provider_role = result.booked_provider_role;
    } else {
      row.appointment_status = "needs_manual_review";
    }

    saveCurrentResponse();
    rerenderStatsPage();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = "Modificar cita";
  }
}

document.addEventListener("click", async (event) => {
  const cancelBtn = event.target.closest(".cancel-booking-btn");
  if (cancelBtn) {
    const patientId = Number(cancelBtn.dataset.patientId);
    const slotId = cancelBtn.dataset.slotId;
    await cancelBooking(patientId, slotId, cancelBtn);
    return;
  }

  const rescheduleBtn = event.target.closest(".reschedule-booking-btn");
  if (rescheduleBtn) {
    const patientId = Number(rescheduleBtn.dataset.patientId);
    const slotId = rescheduleBtn.dataset.slotId;
    const province = rescheduleBtn.dataset.province;
    await rescheduleBooking(patientId, slotId, province, rescheduleBtn);
  }

  const confirmBtn = event.target.closest(".confirm-slot-btn");
  if (confirmBtn) {
    const patientId = Number(confirmBtn.dataset.patientId);
    const slotId = confirmBtn.dataset.slotId;
    await confirmSuggestedSlot(patientId, slotId, confirmBtn);
    return;
  }
});

async function confirmSuggestedSlot(patientId, slotId, button) {
  button.disabled = true;
  button.textContent = "Reservando...";

  try {
    const response = await fetch("http://127.0.0.1:8000/actions/confirm-suggested-slot", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        slot_id: slotId,
      }),
    });

    const result = await response.json();
    const row = findFollowupRow(patientId);
    if (!row) return;

    if (result.status === "confirmed" && result.slot_id) {
      row.appointment_status = "confirmed_by_user";
      row.booked_slot_id = result.slot_id;
      row.booked_date = result.booked_date;
      row.booked_time = result.booked_time;
      row.booked_clinic = result.booked_clinic;
      row.booked_clinic_name = result.booked_clinic_name;
      row.booked_city = result.booked_city;
      row.booked_address = result.booked_address;
      row.booked_provider = result.booked_provider;
      row.booked_provider_name = result.booked_provider_name;
      row.booked_provider_role = result.booked_provider_role;
      row.suggested_slots = [];
      row.suggested_action = "Cita confirmada por el usuario";
    } else {
      row.appointment_status = "needs_manual_review";
    }

    saveCurrentResponse();
    rerenderStatsPage();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = "Reservar esta cita";
  }
}

if (currentResponse) {
  rerenderStatsPage();
} else {
  if (warningsContent) {
    warningsContent.innerHTML = `<p class="muted">No hay datos cargados todavía. Vuelve al dashboard y realiza una consulta.</p>`;
  }
}