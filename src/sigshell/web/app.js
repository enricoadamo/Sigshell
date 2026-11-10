// Sigshell page. Every number shown here comes from a Sigshell tool, which runs sigscores in R.
// This script only collects choices, calls /api/tool/<name>, and displays the results.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// h("tag", {attributes}, ...children). Text is always set as text, never parsed as HTML.
function h(tag, attrs, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e && typeof v !== "string") e[k] = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    e.append(c instanceof Node ? c : String(c));
  }
  return e;
}

const state = {
  status: null,
  methods: null,
  files: [],
  inputs: { matrix: null, signature: null }, // {value: what the tool gets, label, note}
  check: null,
  dropMissing: false,
  chosen: new Set(),
  scores: null, // last compute_scores response
  sig: null, // last test_significance response
  sessionPath: null,
};

const GROUPS = [
  { id: "level", title: "Level", hint: "simple statistics of the signature genes' values" },
  { id: "spread", title: "Spread", hint: "how much the signature genes' values differ, not how high they are" },
  { id: "gsva", title: "GSVA-based", hint: "computed by the GSVA package, using the whole matrix" },
];
const NULL_LABELS = { random_genes: "Random gene sets", permutation: "Shuffled gene names", bootstrap: "Bootstrap" };

// ---------------------------------------------------------------- server calls

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Sigshell": "1" },
    body: JSON.stringify(body),
  };
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("The Sigshell server is not answering. Is it still running in the terminal?");
  }
  let payload = null;
  try { payload = await response.json(); } catch { /* not JSON */ }
  if (!response.ok || (payload && payload.error)) {
    throw new Error((payload && payload.error) || `The server answered with status ${response.status}.`);
  }
  return payload;
}

const tool = (name, args = {}) => api(`/api/tool/${name}`, args);

// Disable a button and show elapsed time while fn runs.
async function running(button, fn) {
  const label = button.textContent;
  const started = Date.now();
  button.disabled = true;
  button.classList.add("busy");
  const tick = () => {
    const s = Math.round((Date.now() - started) / 1000);
    button.textContent = s >= 2 ? `Running… ${s} s` : "Running…";
  };
  tick();
  const timer = setInterval(tick, 1000);
  try {
    return await fn();
  } finally {
    clearInterval(timer);
    button.textContent = label;
    button.classList.remove("busy");
    button.disabled = false;
  }
}

// ---------------------------------------------------------------- small views

function fmt(v) {
  if (v === null || v === undefined) return "NA";
  if (typeof v !== "number") return String(v);
  if (Number.isInteger(v)) return String(v);
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e6)) return v.toExponential(3);
  return String(Number(v.toPrecision(5)));
}

function alertBox(kind, title, ...body) {
  return h("div", { class: `alert ${kind}`, role: kind === "error" ? "alert" : null },
    title ? h("strong", { text: title }) : null, ...body);
}

function errorBox(err) {
  return alertBox("error", "Not run", h("p", { class: "pre", text: err.message || String(err) }));
}

function problemItem(p) {
  return h("li", {}, h("span", { class: "code-chip", text: p.code }), p.message);
}

function notesBox(notes) {
  if (!notes || !notes.length) return null;
  return alertBox("warn", "Notes", h("ul", {}, notes.map((n) => h("li", { text: n }))));
}

function downloads(files) {
  if (!files || !files.length) return null;
  return h("div", { class: "downloads" }, h("span", { class: "hint", text: "Files:" }),
    files.map((f) => h("a", { href: f.url, download: f.name, text: f.name })));
}

function provenance(line, step) {
  return line ? h("p", { class: "provenance", text: `Provenance: ${line}. Step ${step}.` }) : null;
}

// columns: header labels; rows: arrays of values; extra(k): optional node for a last column.
function dataTable(columns, rows, extra) {
  const head = h("tr", {}, columns.map((c) => h("th", { scope: "col", text: c })), extra ? h("th", { scope: "col" }) : null);
  const body = rows.map((r, k) => h("tr", {},
    r.map((v, j) => h("td", {
      class: v === null || v === undefined ? "na" : null,
      title: typeof v === "number" ? String(v) : null,
      text: j === 0 ? String(v) : fmt(v),
    })),
    extra ? h("td", { class: "act" }, extra(k)) : null));
  return h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("thead", {}, head), h("tbody", {}, body)));
}

function figure(url, caption, files) {
  const png = (files || []).find((f) => f.name.endsWith(".png"));
  return h("figure", {},
    h("img", { src: `${url}?v=${Date.now()}`, alt: caption }),
    h("figcaption", {}, caption, " ", png ? h("a", { href: png.url, download: png.name, text: "Download PNG" }) : null));
}

// ---------------------------------------------------------------- status

function renderStatus() {
  const s = state.status;
  const box = $("#status");
  box.className = `status ${s.ok ? "ok" : "err"}`;
  box.textContent = s.ok
    ? `Ready. ${s.provenance}.`
    : `Sigshell can't run sigscores yet, so it can check files but not compute scores.\n${s.error}`;
  $("#data-dir").textContent = s.data_dir;
  $("#link-callmap").hidden = !s.callmap;
  $("#link-paper").hidden = !s.paper;
  $("#citation").textContent = `If you publish results, cite sigscores: ${s.citation.split(" Licensed")[0]}`;
}

// ---------------------------------------------------------------- step 1: data

async function refreshFiles() {
  const r = await api("/api/files");
  state.files = r.files;
  $("#data-dir").textContent = r.data_dir;
  fillSelect("matrix");
  fillSelect("signature");
}

function fillSelect(role) {
  const sel = $(`.picker[data-role="${role}"] select`);
  const files = [...state.files].sort((a, b) => (a.kind === role ? 0 : 1) - (b.kind === role ? 0 : 1) || a.name.localeCompare(b.name));
  const describe = (f) => (f.kind === "matrix" ? `table with ${f.sample_columns} sample columns` : "list");
  sel.replaceChildren(
    h("option", { value: "", text: files.length ? "Or pick a file in the data folder…" : "The data folder is empty" }),
    ...files.map((f) => h("option", { value: f.name, text: `${f.name} · ${describe(f)} · ${f.kb} KB` })));
  const current = state.inputs[role];
  sel.value = current && files.some((f) => f.name === current.value) ? current.value : "";
  sel.disabled = !files.length;
}

function renderChosen(role) {
  const box = $(`.picker[data-role="${role}"] .chosen`);
  const i = state.inputs[role];
  box.replaceChildren(...(i ? ["Using ", h("strong", { text: i.label }), i.note ? h("span", { class: "hint", text: ` (${i.note})` }) : null] : []));
}

function choose(role, input) {
  state.inputs[role] = input;
  renderChosen(role);
  fillSelect(role);
  resetResults();
  runCheck();
}

async function uploadFile(role, file) {
  const msg = $("#data-msg");
  const chosen = $(`.picker[data-role="${role}"] .chosen`);
  msg.replaceChildren();
  chosen.textContent = `Copying ${file.name}…`;
  const form = new FormData();
  form.append("file", file);
  try {
    let r;
    try {
      r = await fetch("/api/upload", { method: "POST", headers: { "X-Sigshell": "1" }, body: form });
    } catch {
      throw new Error("The Sigshell server is not answering. Is it still running in the terminal?");
    }
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.error) throw new Error(j.error || `The upload failed (status ${r.status}).`);
    await refreshFiles();
    choose(role, {
      value: j.name,
      label: j.name,
      note: j.renamed ? `saved under this name because a different ${file.name} is already in the data folder` : null,
    });
  } catch (err) {
    renderChosen(role);
    msg.replaceChildren(errorBox(err));
  }
}

function bindPicker(role) {
  const box = $(`.picker[data-role="${role}"]`);
  const input = $("input[type=file]", box);
  const drop = $(".drop", box);
  const sel = $("select", box);
  input.addEventListener("change", () => {
    if (input.files[0]) uploadFile(role, input.files[0]);
    input.value = "";
  });
  for (const t of ["dragenter", "dragover"]) drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); });
  for (const t of ["dragleave", "drop"]) drop.addEventListener(t, () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) uploadFile(role, f);
  });
  sel.addEventListener("change", () => { if (sel.value) choose(role, { value: sel.value, label: sel.value }); });
}

async function useExample(e) {
  const msg = $("#data-msg");
  msg.replaceChildren();
  try {
    const r = await running(e.currentTarget, () => api("/api/example", {}));
    await refreshFiles();
    state.inputs.signature = { value: r.signature, label: r.signature, note: "20 genes drawn in the vignette" };
    renderChosen("signature");
    fillSelect("signature");
    choose("matrix", { value: r.matrix, label: r.matrix, note: "the vignette's simulated 100 genes × 10 samples, made by R with seed 5381" });
  } catch (err) {
    msg.replaceChildren(errorBox(err));
  }
}

// ---------------------------------------------------------------- step 2: check

let checkSeq = 0;

async function runCheck() {
  const { matrix, signature } = state.inputs;
  if (!matrix) return;
  const out = $("#check-out");
  $("#s-check").hidden = false;
  out.replaceChildren(h("p", { class: "hint", text: "Checking the files…" }));
  const seq = ++checkSeq;
  try {
    const r = await tool("check_inputs", { matrix_file: matrix.value, signature_file: signature ? signature.value : null });
    if (seq !== checkSeq) return;
    state.check = r.data;
    renderCheck();
  } catch (err) {
    if (seq !== checkSeq) return;
    state.check = null;
    out.replaceChildren(errorBox(err));
    updateSections();
  }
}

function blockingErrors() {
  const c = state.check;
  if (!c) return [];
  return c.errors.filter((e) => !(e.code === "missing_genes" && state.dropMissing && c.signature_found.length));
}

function renderCheck() {
  const c = state.check;
  const signature = state.inputs.signature;
  const parts = [];
  const line = h("div", { class: "summary-line" });
  if (c.genes !== null) line.append(h("span", {}, "Matrix: ", h("b", { text: c.genes }), " genes × ", h("b", { text: c.samples.length }), " samples"));
  if (signature && (c.signature_found.length || c.signature_missing.length)) {
    line.append(h("span", {}, "Signature: ", h("b", { text: c.signature_found.length + c.signature_missing.length }), " genes, ",
      h("b", { text: c.signature_found.length }), " found in the matrix", c.signature_has_weights ? ", with weights" : ""));
  }
  parts.push(line);

  if (c.errors.length) parts.push(alertBox("error", "To fix before computing", h("ul", {}, c.errors.map(problemItem))));
  const onlyMissing = c.errors.length > 0 && c.errors.every((e) => e.code === "missing_genes") && c.signature_found.length > 0;
  if (onlyMissing) {
    parts.push(h("label", { class: "check fix" },
      h("input", {
        type: "checkbox",
        checked: state.dropMissing,
        onchange: (e) => { state.dropMissing = e.target.checked; resetResults(); renderCheck(); },
      }),
      h("span", { text: `Score only the ${c.signature_found.length} genes found in the matrix, and leave out the ${c.signature_missing.length} missing ones. This choice is written into the R script.` })));
  }
  if (c.warnings.length) parts.push(alertBox("warn", "Warnings", h("ul", {}, c.warnings.map(problemItem))));
  if (c.constant_genes.length || c.genes_with_na.length) parts.push(prepareBox(c));

  if (!signature) parts.push(alertBox("warn", null, h("p", { text: "Now choose a gene signature." })));
  else if (!blockingErrors().length) {
    parts.push(alertBox("ok", c.warnings.length || c.errors.length ? "Ready to compute" : "No problems found",
      h("p", { text: c.warnings.length ? "Read the warnings above: they say which scores are affected." : "Choose scores below." })));
  }
  $("#check-out").replaceChildren(...parts);
  updateSections();
}

function prepareBox(c) {
  const box = h("div", { class: "fix" });
  const constant = h("input", { type: "checkbox", checked: c.constant_genes.length > 0, disabled: !c.constant_genes.length });
  const na = h("input", { type: "checkbox", checked: c.genes_with_na.length > 0, disabled: !c.genes_with_na.length });
  const button = h("button", { class: "ghost small", type: "button", text: "Make the copy" });
  button.addEventListener("click", async () => {
    try {
      const original = state.inputs.matrix.label;
      const r = await running(button, () => tool("prepare_matrix", {
        matrix_file: state.inputs.matrix.value,
        remove_constant_genes: constant.checked,
        remove_genes_with_missing_values: na.checked,
      }));
      const n = r.data.removed.length;
      sessionStarted(r.session);
      choose("matrix", {
        value: r.data.file,
        label: r.data.file.split(/[\\/]/).pop(),
        note: `a copy of ${original} without ${n} gene${n === 1 ? "" : "s"}, kept in the session folder`,
      });
    } catch (err) {
      box.append(errorBox(err));
    }
  });
  box.append(
    h("strong", { text: "Make a copy of the matrix without these genes" }),
    h("p", { class: "hint", text: "While these genes are in the matrix, the GSVA-based scores are refused, and so is quantile normalisation if values are missing. The other scores work on the file as it is. Your original file is not changed." }),
    h("label", { class: "check" }, constant, `Remove the ${c.constant_genes.length} genes with the same value in every sample`),
    h("label", { class: "check" }, na, `Remove the ${c.genes_with_na.length} genes with missing values`),
    h("div", {}, button));
  return box;
}

// ---------------------------------------------------------------- step 3: scores

function renderScoreChoices() {
  $("#score-groups").replaceChildren(...GROUPS.map((g) => {
    const items = state.methods.scores.filter((s) => s.group === g.id);
    if (!items.length) return null;
    return h("div", { class: "group", "data-group": g.id },
      h("h3", {}, g.title, h("span", { class: "hint", text: g.hint })),
      g.id === "gsva" ? h("p", { class: "hint why", hidden: true }) : null,
      h("div", { class: "choices" }, items.map(choiceItem)));
  }));
  $$("[data-pick]").forEach((b) => b.addEventListener("click", () => {
    const pick = b.dataset.pick;
    const block = gsvaBlock();
    state.chosen = new Set(pick === "none" ? [] : state.methods.scores
      .filter((s) => (pick === "all" || s.group === pick) && !(s.group === "gsva" && block))
      .map((s) => s.id));
    updateScoreChoices();
  }));
}

function choiceItem(s) {
  return h("label", { class: "choice", "data-score": s.id },
    h("input", {
      type: "checkbox",
      value: s.id,
      onchange: (e) => { if (e.target.checked) state.chosen.add(s.id); else state.chosen.delete(s.id); updateScoreChoices(); },
    }),
    h("span", {}, h("span", { class: "name", text: s.name }), h("span", { class: "id", text: s.id }), h("span", { class: "desc", text: s.description })));
}

function renderTransforms() {
  const sel = $("#opt-transform");
  sel.replaceChildren(h("option", { value: "none", text: "No transformation" }),
    ...state.methods.transformers.map((t) => h("option", { value: t.id, text: `${t.name} (${t.id})` })));
  const help = () => {
    const t = state.methods.transformers.find((x) => x.id === sel.value);
    $("#opt-transform-help").textContent = t ? t.description : "Scores are computed on the values as they are in the file.";
  };
  sel.addEventListener("change", () => { help(); resetResults(); });
  help();
}

function gsvaBlock() {
  const c = state.check;
  if (!c) return null;
  if (c.constant_genes.length || c.genes_with_na.length) {
    return "Not available for this matrix: it has genes with the same value in every sample, or with missing values. Make a copy without them in step 2.";
  }
  if (c.samples && c.samples.length < 2) return "Not available with a single sample.";
  return null;
}

function orderedChosen() {
  return state.methods.scores.map((s) => s.id).filter((id) => state.chosen.has(id));
}

function updateScoreChoices() {
  if (!state.methods) return;
  const block = gsvaBlock();
  for (const label of $$(".choice")) {
    const id = label.dataset.score;
    const input = $("input", label);
    const off = state.methods.scores.find((x) => x.id === id).group === "gsva" && !!block;
    if (off) state.chosen.delete(id);
    input.disabled = off;
    input.checked = state.chosen.has(id);
    label.classList.toggle("disabled", off);
  }
  const why = $(".group[data-group=gsva] .why");
  if (why) { why.hidden = !block; why.textContent = block || ""; }

  const ready = !!(state.status && state.status.ok);
  const ids = orderedChosen();
  $("#run-scores").disabled = !ids.length || !ready;
  $("#scores-hint").textContent = !ready ? "R is not ready: see the message at the top."
    : ids.length ? `${ids.length} score${ids.length === 1 ? "" : "s"} chosen.` : "Choose at least one score.";
  $("#opt-trim-row").hidden = !state.chosen.has("trimmedMean");

  $("#run-sig").disabled = !ids.length || !ready;
  const slow = ids.some((id) => state.methods.scores.find((s) => s.id === id).group === "gsva");
  $("#sig-hint").textContent = !ids.length ? "Choose scores in step 3." : `Tests ${ids.join(", ")}.${slow ? " GSVA-based scores with many random sets can take several minutes." : ""}`;
}

function analysisArgs() {
  return {
    matrix_file: state.inputs.matrix.value,
    signature_file: state.inputs.signature.value,
    scores: orderedChosen(),
    transform: $("#opt-transform").value,
    trim: state.chosen.has("trimmedMean") ? Number($("#opt-trim").value) || 0 : 0,
    na_rm: $("#opt-narm").checked,
    drop_missing_genes: state.dropMissing,
  };
}

async function computeScores(e) {
  try {
    const r = await running(e.currentTarget, () => tool("compute_scores", analysisArgs()));
    state.scores = r;
    state.sig = null;
    $("#sig-out").replaceChildren();
    renderScores();
    sessionStarted(r.session);
  } catch (err) {
    $("#scores-out").replaceChildren(errorBox(err));
  }
  updateScoreChoices();
  updateSections();
}

function renderScores() {
  const r = state.scores;
  const d = r.data;
  const ids = Object.keys(d.scores);
  const rows = d.samples.map((s, k) => [s, ...ids.map((id) => d.scores[id][k])]);
  const plotArea = h("div");
  const corrWhy = ids.length < 2 ? "Needs at least two scores." : d.samples.length < 3 ? "Needs at least three samples." : null;
  const plotButton = (kind, label, why) => h("button", {
    class: "ghost small", type: "button", disabled: !!why, title: why, text: label,
    onclick: (e) => drawPlot(e.currentTarget, kind, label, plotArea),
  });
  $("#scores-out").replaceChildren(h("div", { class: "result" },
    h("div", { class: "result-head" },
      h("h3", { text: `Scores for ${d.samples.length} samples` }),
      h("span", { class: "hint", text: `signature of ${d.n_genes_scored} genes · result ${d.result_id}` })),
    dataTable(["sample", ...ids], rows),
    downloads(r.files),
    notesBox(d.notes),
    h("div", { class: "plots" }, h("span", { class: "hint", text: "Plot:" }),
      plotButton("heatmap", "Heatmap"),
      plotButton("correlation", "Correlation between scores", corrWhy),
      plotButton("boxplot", "Boxplot"),
      plotButton("scatter", "Per sample")),
    plotArea,
    provenance(d.provenance_line, r.step)));
}

async function drawPlot(button, kind, label, area) {
  try {
    const r = await running(button, () => tool("plot_scores", { result_id: state.scores.data.result_id, kind }));
    area.replaceChildren(figure(r.url, `${label}, drawn by sigscores::${r.data.function}.`, r.files));
  } catch (err) {
    area.replaceChildren(errorBox(err));
  }
}

// ---------------------------------------------------------------- step 4: significance

function renderNulls() {
  $("#sig-nulls").replaceChildren(...state.methods.null_models.map((m, i) => h("label", { class: "check null" },
    h("input", { type: "radio", name: "sig-null", value: m.id, checked: i === 0 }),
    h("span", {}, h("span", { class: "name", text: NULL_LABELS[m.id] || m.id }), h("span", { class: "desc", text: m.description })))));
  $("#sig-not-offered").textContent = state.methods.not_offered.join(" ");
}

function numberField(id, label, integer) {
  const raw = $(id).value.trim();
  const v = integer ? Number.parseInt(raw, 10) : Number(raw);
  if (raw === "" || !Number.isFinite(v)) throw new Error(`${label} must be a number.`);
  return v;
}

async function testSignificance(e) {
  const out = $("#sig-out");
  let args;
  try {
    args = {
      ...analysisArgs(),
      null: $("input[name=sig-null]:checked").value,
      n_repeat: numberField("#sig-n", "The number of random scores", true),
      seed: numberField("#sig-seed", "The seed", true),
      alternative: $("#sig-alt").value,
      conf_level: numberField("#sig-conf", "The confidence level", false),
    };
  } catch (err) {
    out.replaceChildren(errorBox(err));
    return;
  }
  try {
    const r = await running(e.currentTarget, () => tool("test_significance", args));
    state.sig = r;
    renderSig();
    sessionStarted(r.session);
  } catch (err) {
    out.replaceChildren(errorBox(err));
  }
  updateScoreChoices();
}

function renderSig() {
  const r = state.sig;
  const d = r.data;
  const s = d.significance;
  const n = s.sample.length;
  const cols = ["sample", "score", "observed", "random mean", "random SD", "ASL", "interval low", "interval high"];
  const rows = [...Array(n).keys()].map((k) => [s.sample[k], s.score[k], s.observed[k], s.null_mean[k], s.null_sd[k], s.asl[k],
    s.ci_percentile_lower[k], s.ci_percentile_upper[k]]);
  const plotArea = h("div");
  const table = dataTable(cols, rows, (k) => h("button", {
    class: "ghost small", type: "button", text: "Histogram",
    onclick: (e) => drawNull(e.currentTarget, s.sample[k], s.score[k], plotArea),
  }));
  $("#sig-out").replaceChildren(h("div", { class: "result" },
    h("div", { class: "result-head" },
      h("h3", { text: `Significance for ${new Set(s.sample).size} samples × ${new Set(s.score).size} scores` }),
      h("span", { class: "hint", text: `${NULL_LABELS[d.null] || d.null} · ${d.n_repeat} random scores per sample · seed ${d.seed} · ${d.alternative} · result ${d.result_id}` })),
    h("p", { class: "hint", text: "ASL is the achieved significance level. The interval columns are the percentile interval of the random scores. The notes below say exactly what both mean here." }),
    table,
    downloads(r.files),
    notesBox(d.notes),
    plotArea,
    provenance(d.provenance_line, r.step)));
}

async function drawNull(button, sample, score, area) {
  $$("#sig-out tr.selected").forEach((tr) => tr.classList.remove("selected"));
  button.closest("tr").classList.add("selected");
  try {
    const r = await running(button, () => tool("plot_null_distribution", { result_id: state.sig.data.result_id, sample, score }));
    area.replaceChildren(figure(r.url, `Random ${score} scores for ${sample}. The dashed line is the observed score. Drawn by sigscores::histogramRndSigScores.`, r.files));
    area.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    area.replaceChildren(errorBox(err));
  }
}

// ---------------------------------------------------------------- step 5: reproduce

function sessionStarted(path) {
  if (!path) return;
  state.sessionPath = path;
  $("#s-script").hidden = false;
  $("#session-path").replaceChildren("Session folder: ", h("code", { text: path }));
  if (!$("#script-out").hidden) showScript();
}

async function showScript() {
  const pre = $("#script-out");
  try {
    const r = await tool("get_r_script");
    pre.textContent = r.script || r.text;
  } catch (err) {
    pre.textContent = err.message;
  }
  pre.hidden = false;
  $("#show-script").textContent = "Hide the R script";
}

function toggleScript() {
  const pre = $("#script-out");
  if (pre.hidden) { showScript(); return; }
  pre.hidden = true;
  $("#show-script").textContent = "Show the R script";
}

async function newSession() {
  if (!window.confirm("Start a new session? The current session folder stays on disk. New results go into a new folder.")) return;
  try {
    await api("/api/new-session", {});
  } catch (err) {
    window.alert(err.message);
    return;
  }
  state.sessionPath = null;
  $("#s-script").hidden = true;
  $("#script-out").hidden = true;
  $("#show-script").textContent = "Show the R script";
  resetResults();
  runCheck();
}

// ---------------------------------------------------------------- layout

function resetResults() {
  state.scores = null;
  state.sig = null;
  $("#scores-out").replaceChildren();
  $("#sig-out").replaceChildren();
  updateSections();
}

function updateSections() {
  const ready = !!(state.check && state.inputs.signature && !blockingErrors().length);
  $("#s-scores").hidden = !ready || !state.methods;
  $("#s-sig").hidden = !ready || !state.methods || !state.scores;
  updateScoreChoices();
}

async function init() {
  bindPicker("matrix");
  bindPicker("signature");
  $("#example").addEventListener("click", useExample);
  $("#run-scores").addEventListener("click", computeScores);
  $("#run-sig").addEventListener("click", testSignificance);
  $("#show-script").addEventListener("click", toggleScript);
  $("#new-session").addEventListener("click", newSession);
  $("#opt-narm").addEventListener("change", resetResults);
  $("#opt-trim").addEventListener("change", resetResults);

  try { await refreshFiles(); } catch (err) { $("#data-msg").replaceChildren(errorBox(err)); }
  try {
    state.status = await api("/api/status");
    renderStatus();
  } catch (err) {
    $("#status").className = "status err";
    $("#status").textContent = err.message;
  }
  if (state.status && state.status.ok) {
    try {
      state.methods = await api("/api/methods");
      renderScoreChoices();
      renderTransforms();
      renderNulls();
    } catch (err) {
      $("#status").className = "status err";
      $("#status").textContent = err.message;
    }
  }
  if (state.status && state.status.session) sessionStarted(state.status.session);
  updateSections();
}

document.addEventListener("DOMContentLoaded", init);
