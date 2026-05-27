const state = {
  leads: [],
  selectedLeadId: null,
};

const API_TIMEOUT_MS = 10000;

const $ = (selector) => document.querySelector(selector);

function text(value, fallback = "") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function pct(value) {
  if (value === null || value === undefined) return "";
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "";
}

function el(tagName, attributes = {}, ...children) {
  const node = document.createElement(tagName);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "className") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key === "textContent") node.textContent = text(value);
    else node.setAttribute(key, String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function empty(message) {
  return el("div", { className: "empty", textContent: message });
}

function showError(target, message) {
  $(target).replaceChildren(el("div", { className: "error", textContent: message }));
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), options.timeout ?? API_TIMEOUT_MS);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail ? JSON.stringify(payload.detail) : response.statusText);
    }
    return response;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("API request timed out");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function loadHealth() {
  try {
    const response = await api("/api/health");
    const payload = await response.json();
    $("#health").textContent = payload.status || "unknown";
  } catch {
    $("#health").textContent = "API unavailable";
  }
}

async function loadBatches() {
  try {
    const response = await api("/api/batches");
    const payload = await response.json();
    const rows = (payload.items || []).map((batch) => {
      const counts = Object.entries(batch.status_counts || {})
        .map(([key, value]) => `${key}:${value}`)
        .join(" ");
      return el(
        "div",
        { className: "batch-row" },
        el("strong", { textContent: text(batch.source, batch.id) }),
        el("span", { textContent: `${batch.lead_count || 0} leads` }),
        el("code", { textContent: counts }),
      );
    });
    $("#batches").replaceChildren(...(rows.length ? rows : [empty("No batches")]));
  } catch (error) {
    showError("#batches", error.message);
  }
}

async function loadLeads() {
  try {
    const action = $("#action-filter").value;
    const query = action ? `?action=${encodeURIComponent(action)}` : "";
    const response = await api(`/api/leads${query}`);
    const payload = await response.json();
    state.leads = payload.items || [];
    const rows = state.leads.map((lead) => {
      const decision = lead.decision || {};
      const row = el(
        "tr",
        { dataset: { leadId: lead.id } },
        el("td", { textContent: text(lead.domain) }),
        el("td", { textContent: text(lead.company) }),
        el("td", { textContent: text(lead.t0_score) }),
        el("td", { textContent: Object.keys(lead.t1_signals || {}).length }),
        el("td", { textContent: text(decision.action) }),
        el("td", { textContent: pct(decision.confidence) }),
      );
      if (lead.id === state.selectedLeadId) row.classList.add("active");
      return row;
    });
    $("#leads").replaceChildren(...rows);
  } catch (error) {
    state.leads = [];
    $("#leads").replaceChildren(el("tr", {}, el("td", { colspan: "6", className: "error", textContent: error.message })));
  }
}

async function loadDecisions() {
  try {
    const response = await api("/api/decisions");
    const payload = await response.json();
    const rows = (payload.items || []).map((item) => {
      const decision = item.decision || {};
      return el(
        "div",
        { className: "decision-row" },
        el("strong", { textContent: text(item.domain, item.lead_id) }),
        el("span", { textContent: text(decision.action) }),
        el("span", { textContent: text(decision.campaign) }),
      );
    });
    $("#decisions").replaceChildren(...(rows.length ? rows : [empty("No decisions")]));
  } catch (error) {
    showError("#decisions", error.message);
  }
}

async function loadRulesets() {
  try {
    const response = await api("/api/rulesets");
    const payload = await response.json();
    const buttons = (payload.items || []).map((item) =>
      el("button", { type: "button", dataset: { ruleset: item.name }, textContent: item.name }),
    );
    $("#rulesets").replaceChildren(...(buttons.length ? buttons : [empty("No rulesets")]));
  } catch (error) {
    showError("#rulesets", error.message);
  }
}

function signalList(signals = {}) {
  const entries = Object.entries(signals || {});
  if (!entries.length) return empty("No signals");
  const list = el("dl");
  for (const [key, value] of entries) {
    list.append(
      el("dt", { textContent: key }),
      el("dd", { textContent: typeof value === "object" ? JSON.stringify(value) : text(value) }),
    );
  }
  return list;
}

function option(value, label) {
  return el("option", { value, textContent: label });
}

function overrideForm(leadId) {
  return el(
    "form",
    { id: "override-form", className: "override-form", dataset: { leadId } },
    el(
      "select",
      { name: "action" },
      option("manual_review", "Manual review"),
      option("skip", "Skip"),
      option("retry", "Retry"),
      option("t2_required", "T2 required"),
      option("t2_optional", "T2 optional"),
      option("send", "Send"),
    ),
    el(
      "select",
      { name: "campaign" },
      option("", "No campaign"),
      option("REDESIGN_OUTDATED", "REDESIGN_OUTDATED"),
      option("REDESIGN_ADS_WASTE", "REDESIGN_ADS_WASTE"),
      option("REDESIGN_CONVERSION", "REDESIGN_CONVERSION"),
      option("REDESIGN_TRUST", "REDESIGN_TRUST"),
      option("WORDPRESS_REWORK", "WORDPRESS_REWORK"),
      option("MOBILE_REBUILD", "MOBILE_REBUILD"),
      option("TECH_REBUILD", "TECH_REBUILD"),
    ),
    el("input", { name: "reason", required: true, placeholder: "Reason" }),
    el("button", { type: "submit", textContent: "Override" }),
  );
}

async function loadLeadDetail(leadId) {
  state.selectedLeadId = leadId;
  await loadLeads();
  try {
    const response = await api(`/api/leads/${encodeURIComponent(leadId)}`);
    const payload = await response.json();
    const scans = payload.scans || {};
    const decision = payload.decision || {};
    const trace = el("pre", { textContent: JSON.stringify(payload.trace || {}, null, 2) });
    $("#lead-detail").replaceChildren(
      el(
        "div",
        { className: "detail-title" },
        el("strong", { textContent: text(payload.lead.normalized_domain) }),
        el("span", { textContent: text(decision.action) }),
      ),
      el("h3", { textContent: "T0" }),
      signalList(scans.t0?.signals),
      el("h3", { textContent: "T0.5" }),
      signalList(scans.t0_5?.signals),
      el("h3", { textContent: "T1" }),
      signalList(scans.t1?.signals),
      el("h3", { textContent: "Decision trace" }),
      trace,
      el("h3", { textContent: "QA override" }),
      overrideForm(leadId),
    );
  } catch (error) {
    showError("#lead-detail", error.message);
  }
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
  try {
    await api(`/api/leads/${encodeURIComponent(event.target.dataset.leadId)}/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadLeadDetail(event.target.dataset.leadId);
    await loadDecisions();
  } catch (error) {
    showError("#lead-detail", error.message);
  }
});
$("#rulesets").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-ruleset]");
  if (!button) return;
  try {
    const response = await api(`/api/rulesets/${encodeURIComponent(button.dataset.ruleset)}`);
    const payload = await response.json();
    $("#lead-detail").replaceChildren(
      el("div", { className: "detail-title" }, el("strong", { textContent: payload.name })),
      el("pre", { textContent: payload.content }),
    );
  } catch (error) {
    showError("#lead-detail", error.message);
  }
});
$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = $("#csv-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    await api("/api/batches", { method: "POST", body: form, timeout: 30000 });
    $("#csv-file").value = "";
    await refresh();
  } catch (error) {
    $("#health").textContent = error.message;
  }
});
$("#export").addEventListener("click", async () => {
  try {
    const response = await api("/api/export", { method: "POST" });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "leadpipe-export.csv";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    $("#health").textContent = error.message;
  }
});

refresh().catch((error) => {
  $("#health").textContent = error.message;
});
