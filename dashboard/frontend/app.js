const state = {
  leads: [],
  selectedLeadId: null,
};

const $ = (selector) => document.querySelector(selector);

function text(value, fallback = "") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function pct(value) {
  if (value === null || value === undefined) return "";
  return `${Math.round(Number(value) * 100)}%`;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ? JSON.stringify(payload.detail) : response.statusText);
  }
  return response;
}

async function loadHealth() {
  try {
    const response = await api("/api/health");
    const payload = await response.json();
    $("#health").textContent = payload.status;
  } catch (error) {
    $("#health").textContent = "API unavailable";
  }
}

async function loadBatches() {
  const response = await api("/api/batches");
  const payload = await response.json();
  $("#batches").innerHTML = payload.items.length
    ? payload.items
        .map(
          (batch) => `
            <div class="batch-row">
              <strong>${text(batch.source, batch.id)}</strong>
              <span>${batch.lead_count} leads</span>
              <code>${Object.entries(batch.status_counts)
                .map(([key, value]) => `${key}:${value}`)
                .join(" ")}</code>
            </div>
          `,
        )
        .join("")
    : "<div class=\"empty\">No batches</div>";
}

async function loadLeads() {
  const action = $("#action-filter").value;
  const query = action ? `?action=${encodeURIComponent(action)}` : "";
  const response = await api(`/api/leads${query}`);
  const payload = await response.json();
  state.leads = payload.items;
  $("#leads").innerHTML = payload.items
    .map((lead) => {
      const decision = lead.decision || {};
      const active = lead.id === state.selectedLeadId ? " class=\"active\"" : "";
      return `
        <tr data-lead-id="${lead.id}"${active}>
          <td>${text(lead.domain)}</td>
          <td>${text(lead.company)}</td>
          <td>${text(lead.t0_score)}</td>
          <td>${Object.keys(lead.t1_signals || {}).length}</td>
          <td>${text(decision.action)}</td>
          <td>${pct(decision.confidence)}</td>
        </tr>
      `;
    })
    .join("");
}

async function loadDecisions() {
  const response = await api("/api/decisions");
  const payload = await response.json();
  $("#decisions").innerHTML = payload.items.length
    ? payload.items
        .map((item) => {
          const decision = item.decision || {};
          return `
            <div class="decision-row">
              <strong>${text(item.domain, item.lead_id)}</strong>
              <span>${text(decision.action)}</span>
              <span>${text(decision.campaign)}</span>
            </div>
          `;
        })
        .join("")
    : "<div class=\"empty\">No decisions</div>";
}

async function loadRulesets() {
  const response = await api("/api/rulesets");
  const payload = await response.json();
  $("#rulesets").innerHTML = payload.items.length
    ? payload.items.map((item) => `<button type="button" data-ruleset="${item.name}">${item.name}</button>`).join("")
    : "<div class=\"empty\">No rulesets</div>";
}

function signalList(signals = {}) {
  const entries = Object.entries(signals);
  if (!entries.length) return "<div class=\"empty\">No signals</div>";
  return `<dl>${entries
    .map(([key, value]) => `<dt>${key}</dt><dd>${text(typeof value === "object" ? JSON.stringify(value) : value)}</dd>`)
    .join("")}</dl>`;
}

async function loadLeadDetail(leadId) {
  state.selectedLeadId = leadId;
  await loadLeads();
  const response = await api(`/api/leads/${leadId}`);
  const payload = await response.json();
  const scans = payload.scans || {};
  const decision = payload.decision || {};
  $("#lead-detail").innerHTML = `
    <div class="detail-title">
      <strong>${text(payload.lead.normalized_domain)}</strong>
      <span>${text(decision.action)}</span>
    </div>
    <h3>T0</h3>
    ${signalList(scans.t0?.signals)}
    <h3>T0.5</h3>
    ${signalList(scans.t0_5?.signals)}
    <h3>T1</h3>
    ${signalList(scans.t1?.signals)}
    <h3>Decision trace</h3>
    <pre>${JSON.stringify(payload.trace || {}, null, 2)}</pre>
    <h3>QA override</h3>
    <form id="override-form" class="override-form" data-lead-id="${leadId}">
      <select name="action">
        <option value="manual_review">Manual review</option>
        <option value="skip">Skip</option>
        <option value="retry">Retry</option>
        <option value="t2_required">T2 required</option>
        <option value="t2_optional">T2 optional</option>
        <option value="send">Send</option>
      </select>
      <select name="campaign">
        <option value="">No campaign</option>
        <option value="REDESIGN_OUTDATED">REDESIGN_OUTDATED</option>
        <option value="REDESIGN_ADS_WASTE">REDESIGN_ADS_WASTE</option>
        <option value="REDESIGN_CONVERSION">REDESIGN_CONVERSION</option>
        <option value="REDESIGN_TRUST">REDESIGN_TRUST</option>
        <option value="WORDPRESS_REWORK">WORDPRESS_REWORK</option>
        <option value="MOBILE_REBUILD">MOBILE_REBUILD</option>
        <option value="TECH_REBUILD">TECH_REBUILD</option>
      </select>
      <input name="reason" required placeholder="Reason" />
      <button type="submit">Override</button>
    </form>
  `;
}

async function refresh() {
  await Promise.all([loadHealth(), loadBatches(), loadLeads(), loadDecisions(), loadRulesets()]);
}

$("#refresh").addEventListener("click", refresh);
$("#action-filter").addEventListener("change", loadLeads);
$("#leads").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-lead-id]");
  if (row) loadLeadDetail(row.dataset.leadId);
});
$("#lead-detail").addEventListener("submit", async (event) => {
  if (event.target.id !== "override-form") return;
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    action: form.get("action"),
    campaign: form.get("campaign") || null,
    reason: form.get("reason"),
  };
  await api(`/api/leads/${event.target.dataset.leadId}/override`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadLeadDetail(event.target.dataset.leadId);
  await loadDecisions();
});
$("#rulesets").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-ruleset]");
  if (!button) return;
  const response = await api(`/api/rulesets/${button.dataset.ruleset}`);
  const payload = await response.json();
  $("#lead-detail").innerHTML = `<div class="detail-title"><strong>${payload.name}</strong></div><pre>${payload.content}</pre>`;
});
$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = $("#csv-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  await api("/api/batches", { method: "POST", body: form });
  $("#csv-file").value = "";
  await refresh();
});
$("#export").addEventListener("click", async () => {
  const response = await api("/api/export", { method: "POST" });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "leadpipe-export.csv";
  link.click();
  URL.revokeObjectURL(url);
});

refresh().catch((error) => {
  $("#health").textContent = error.message;
});
