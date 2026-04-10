const LAST_RESPONSE_KEY = "latestCohortResponse";

const response = JSON.parse(localStorage.getItem(LAST_RESPONSE_KEY) || "null");

const cohortIdEl = document.getElementById("stats-cohort-id");
const cohortSizeEl = document.getElementById("stats-cohort-size");
const warningsCountEl = document.getElementById("stats-warnings-count");
const filtersCountEl = document.getElementById("stats-filters-count");

const filtersTableBody = document.getElementById("filters-table-body");
const patientsTableBody = document.getElementById("patients-table-body");
const followupTableBody = document.getElementById("followup-table-body");
const warningsContent = document.getElementById("warnings-content");

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

function renderFiltersTable(filters = {}) {
  filtersTableBody.innerHTML = "";

  const entries = Object.entries(filters);
  filtersCountEl.textContent = String(entries.length);

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

function renderPatientsTable(patientIds = []) {
  patientsTableBody.innerHTML = "";

  if (!patientIds || patientIds.length === 0) {
    patientsTableBody.innerHTML = `
      <tr>
        <td class="empty-cell">Sin pacientes</td>
      </tr>
    `;
    return;
  }

  patientIds.forEach((id) => {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.textContent = String(id);
    tr.appendChild(td);
    patientsTableBody.appendChild(tr);
  });
}

function renderFollowupPlan(plan = []) {
  followupTableBody.innerHTML = "";

  if (!plan || plan.length === 0) {
    followupTableBody.innerHTML = `
      <tr>
        <td colspan="11" class="empty-cell">
          Todavía no se ha generado un plan de seguimiento
        </td>
      </tr>
    `;
    return;
  }

  plan.forEach((row) => {
    const tr = document.createElement("tr");

    const priorityClass =
      row.priority_level === "Alta"
        ? "priority-high"
        : row.priority_level === "Media"
        ? "priority-medium"
        : "priority-low";

    tr.innerHTML = `
      <td>${row.PacienteID}</td>
      <td>${row.Edad}</td>
      <td>${row.Genero}</td>
      <td>${row.Provincia}</td>
      <td>${row.num_conditions}</td>
      <td>${row.num_medications}</td>
      <td>${row.num_allergies}</td>
      <td>${row.num_encounters}</td>
      <td class="${priorityClass}">${row.priority_level}</td>
      <td>${row.priority_reason}</td>
      <td>${row.suggested_action}</td>
    `;

    followupTableBody.appendChild(tr);
  });
}

function renderWarnings(warnings = [], unknownTerms = []) {
  const count = (warnings?.length || 0) + (unknownTerms?.length || 0);
  warningsCountEl.textContent = String(count);

  if ((!warnings || warnings.length === 0) && (!unknownTerms || unknownTerms.length === 0)) {
    warningsContent.innerHTML = `<p class="muted">Sin warnings</p>`;
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
  warningsContent.innerHTML = html;
}

if (response) {
  cohortIdEl.textContent = response.cohort_id ?? "—";
  cohortSizeEl.textContent = response.cohort_size ?? "—";

  renderFiltersTable(response.filters_applied ?? {});
  renderPatientsTable(response.data?.patient_ids ?? []);
  renderFollowupPlan(response.data?.followup_plan ?? []);
  renderWarnings(response.warnings ?? [], response.unknown_terms ?? []);
} else {
  warningsContent.innerHTML = `<p class="muted">No hay datos cargados todavía. Vuelve al dashboard y realiza una consulta.</p>`;
}