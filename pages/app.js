const REPO = "refracta/itr2-ko";
const MARKER = "ITR2_KO_TRANSLATION_PROPOSAL_V1";
const REPO_PAGES_ROOT = (() => {
  const marker = "/itr2-ko/";
  const index = window.location.pathname.indexOf(marker);
  return index >= 0 ? `${window.location.origin}${window.location.pathname.slice(0, index + marker.length)}` : "";
})();
const DATA_URLS = [
  "data/unique_sources_with_ko.json",
  REPO_PAGES_ROOT ? `${REPO_PAGES_ROOT}data/unique_sources_with_ko.json` : "",
  `https://raw.githubusercontent.com/${REPO}/main/translations/unique_sources_with_ko.json`,
].filter(Boolean);
const META_URLS = [
  "data/site-meta.json",
  REPO_PAGES_ROOT ? `${REPO_PAGES_ROOT}data/site-meta.json` : "",
].filter(Boolean);
const MAX_RENDERED = 180;

const state = {
  rows: [],
  byId: new Map(),
  originalKo: new Map(),
  changes: new Map(),
  selectedId: null,
  meta: {},
};

const el = {
  buildMeta: document.getElementById("buildMeta"),
  submitIssue: document.getElementById("submitIssue"),
  exportProposal: document.getElementById("exportProposal"),
  clearChanges: document.getElementById("clearChanges"),
  searchInput: document.getElementById("searchInput"),
  statusFilter: document.getElementById("statusFilter"),
  prevResult: document.getElementById("prevResult"),
  nextResult: document.getElementById("nextResult"),
  stats: document.getElementById("stats"),
  resultMeta: document.getElementById("resultMeta"),
  sourceList: document.getElementById("sourceList"),
  editor: document.getElementById("editor"),
  editorTemplate: document.getElementById("editorTemplate"),
};

function placeholders(text) {
  const matches = String(text || "").match(/\{[^{}]+\}|<[^<>/]+>|<\/[^<>]+>|\[[A-Za-z0-9_]+\]|#[A-Za-z0-9_]+/g);
  return new Set(matches || []);
}

function missingPlaceholders(source, ko) {
  const sourcePlaceholders = placeholders(source);
  const koPlaceholders = placeholders(ko);
  return [...sourcePlaceholders].filter((value) => !koPlaceholders.has(value));
}

function trimLine(text, limit = 120) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  return normalized.length > limit ? `${normalized.slice(0, limit - 1)}...` : normalized;
}

async function fetchFirst(urls) {
  const failures = [];
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (response.ok) {
        return response.json();
      }
      failures.push(`${url}: ${response.status}`);
    } catch (error) {
      failures.push(`${url}: ${error.message}`);
    }
  }
  throw new Error(failures.length ? failures.join(" / ") : "fetch failed");
}

function storageKey() {
  return `itr2-ko-proposal:${state.meta.commit || "local"}`;
}

function loadDraft() {
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return;
    const draft = JSON.parse(raw);
    if (!Array.isArray(draft.changes)) return;
    for (const change of draft.changes) {
      const row = state.byId.get(change.source_id);
      if (!row || typeof change.ko !== "string") continue;
      if (change.ko !== state.originalKo.get(change.source_id)) {
        state.changes.set(change.source_id, change.ko);
      }
    }
  } catch {
    localStorage.removeItem(storageKey());
  }
}

function saveDraft() {
  const changes = proposalChanges();
  if (!changes.length) {
    localStorage.removeItem(storageKey());
    return;
  }
  localStorage.setItem(storageKey(), JSON.stringify({ changes }));
}

function currentKo(row) {
  return state.changes.has(row.source_id) ? state.changes.get(row.source_id) : row.ko || "";
}

function proposalChanges() {
  return [...state.changes.entries()].map(([source_id, ko]) => {
    const row = state.byId.get(source_id);
    return {
      source_id,
      source: row.source,
      ko,
    };
  });
}

function proposalPayload() {
  return {
    version: 1,
    base_commit: state.meta.commit || null,
    changes: proposalChanges(),
  };
}

function proposalBody() {
  return [
    "### ITR2_KO_TRANSLATION_PROPOSAL_V1",
    "",
    "```json",
    JSON.stringify(proposalPayload(), null, 2),
    "```",
  ].join("\n");
}

function updateStats() {
  const total = state.rows.length;
  const translatable = state.rows.filter((row) => row.translatable).length;
  const changed = state.changes.size;
  el.stats.textContent = `문자열 ${total.toLocaleString()}개 / 번역 대상 ${translatable.toLocaleString()}개 / 변경 ${changed.toLocaleString()}개`;
  el.submitIssue.disabled = changed === 0;
  el.exportProposal.disabled = changed === 0;
  el.clearChanges.disabled = changed === 0;
}

function filteredRows() {
  const query = el.searchInput.value.trim().toLocaleLowerCase();
  const filter = el.statusFilter.value;
  return state.rows.filter((row) => {
    const ko = currentKo(row);
    if (filter === "changed" && !state.changes.has(row.source_id)) return false;
    if (filter === "untranslated" && ko !== row.source) return false;
    if (filter === "withReference" && !((row.reference_ru || []).length || (row.reference_ja || []).length)) return false;
    if (!query) return true;
    const haystack = [
      row.source,
      ko,
      ...(row.reference_ru || []),
      ...(row.reference_ja || []),
      row.source_id,
    ].join("\n").toLocaleLowerCase();
    return haystack.includes(query);
  });
}

function renderList() {
  const rows = filteredRows();
  const selectedIndex = rows.findIndex((row) => row.source_id === state.selectedId);
  const maxStart = Math.max(0, rows.length - MAX_RENDERED);
  const start = selectedIndex >= MAX_RENDERED ? Math.min(maxStart, selectedIndex - Math.floor(MAX_RENDERED / 2)) : 0;
  const renderedRows = rows.slice(start, start + MAX_RENDERED);
  const rangeText = rows.length > MAX_RENDERED
    ? ` / 표시 ${start + 1}-${start + renderedRows.length}`
    : "";
  const selectedText = selectedIndex >= 0 ? ` / 선택 ${selectedIndex + 1}` : "";
  el.resultMeta.textContent = `검색 결과 ${rows.length.toLocaleString()}개${rangeText}${selectedText}`;
  el.prevResult.disabled = rows.length === 0;
  el.nextResult.disabled = rows.length === 0;
  el.sourceList.innerHTML = "";
  for (const row of renderedRows) {
    const button = document.createElement("button");
    button.className = "item";
    if (state.changes.has(row.source_id)) button.classList.add("changed");
    if (state.selectedId === row.source_id) button.classList.add("active");
    button.type = "button";
    button.dataset.sourceId = row.source_id;
    button.innerHTML = `
      <span class="itemTitle">${escapeHtml(trimLine(currentKo(row) || row.source, 100))}</span>
      <span class="itemSub">${escapeHtml(trimLine(row.source, 110))}</span>
    `;
    button.addEventListener("click", () => selectRow(row.source_id));
    el.sourceList.appendChild(button);
  }
  el.sourceList.querySelector(".item.active")?.scrollIntoView({ block: "nearest" });
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function pill(text, kind = "") {
  const span = document.createElement("span");
  span.className = `pill ${kind}`.trim();
  span.textContent = text;
  return span;
}

function renderChecks(row, value, target) {
  target.innerHTML = "";
  const missing = missingPlaceholders(row.source, value);
  target.appendChild(pill(state.changes.has(row.source_id) ? "변경됨" : "원본 유지", state.changes.has(row.source_id) ? "changed" : ""));
  target.appendChild(pill(`${String(value).length.toLocaleString()}자`));
  if (missing.length) {
    target.appendChild(pill(`placeholder 누락: ${missing.join(", ")}`, "bad"));
  } else {
    target.appendChild(pill("placeholder 정상", "ok"));
  }
}

function selectRow(sourceId) {
  const row = state.byId.get(sourceId);
  if (!row) return;
  state.selectedId = sourceId;

  const fragment = el.editorTemplate.content.cloneNode(true);
  const sourceIdNode = fragment.querySelector('[data-field="sourceId"]');
  const titleNode = fragment.querySelector('[data-field="title"]');
  const sourceNode = fragment.querySelector('[data-field="source"]');
  const textarea = fragment.querySelector('[data-field="ko"]');
  const checks = fragment.querySelector('[data-field="checks"]');
  const referenceRu = fragment.querySelector('[data-field="referenceRu"]');
  const referenceJa = fragment.querySelector('[data-field="referenceJa"]');
  const recordInfo = fragment.querySelector('[data-field="recordInfo"]');
  const revert = fragment.querySelector('[data-action="revert"]');

  sourceIdNode.textContent = row.source_id;
  titleNode.textContent = trimLine(row.source, 80) || "(빈 문자열)";
  sourceNode.textContent = row.source;
  textarea.value = currentKo(row);
  referenceRu.textContent = (row.reference_ru || []).join("\n\n");
  referenceJa.textContent = (row.reference_ja || []).join("\n\n");
  recordInfo.textContent = `record ${row.record_count}개 / ${row.containers.join(", ")}`;
  renderChecks(row, textarea.value, checks);

  textarea.addEventListener("input", () => {
    const original = state.originalKo.get(row.source_id) || "";
    if (textarea.value === original) {
      state.changes.delete(row.source_id);
    } else {
      state.changes.set(row.source_id, textarea.value);
    }
    saveDraft();
    renderChecks(row, textarea.value, checks);
    updateStats();
    renderList();
  });

  revert.addEventListener("click", () => {
    state.changes.delete(row.source_id);
    textarea.value = state.originalKo.get(row.source_id) || "";
    saveDraft();
    renderChecks(row, textarea.value, checks);
    updateStats();
    renderList();
  });

  el.editor.innerHTML = "";
  el.editor.appendChild(fragment);
  renderList();
}

function moveSelection(delta) {
  const rows = filteredRows();
  if (!rows.length) return;
  let index = rows.findIndex((row) => row.source_id === state.selectedId);
  if (index === -1) {
    index = delta > 0 ? -1 : 0;
  }
  const nextIndex = (index + delta + rows.length) % rows.length;
  selectRow(rows[nextIndex].source_id);
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(proposalPayload(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `itr2-ko-proposal-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

async function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  return false;
}

async function openIssue() {
  const body = proposalBody();
  const title = `[translation-proposal] ${state.changes.size} changes`;
  const params = new URLSearchParams({
    title,
    body,
    labels: "translation-proposal",
  });
  const url = `https://github.com/${REPO}/issues/new?${params.toString()}`;
  if (url.length <= 7600) {
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }

  await copyText(body);
  const shortUrl = `https://github.com/${REPO}/issues/new?${new URLSearchParams({ title, labels: "translation-proposal" }).toString()}`;
  window.open(shortUrl, "_blank", "noopener,noreferrer");
  alert("변경 내용이 길어서 Issue 본문을 클립보드에 복사했습니다. 열린 Issue 본문에 붙여 넣은 뒤 제출하세요.");
}

async function init() {
  try {
    try {
      state.meta = await fetchFirst(META_URLS);
    } catch {
      state.meta = { commit: null, generated_at: null };
    }
    state.rows = await fetchFirst(DATA_URLS);
    state.rows = state.rows.filter((row) => row && row.source_id).sort((a, b) => {
      const ac = a.containers.join(",");
      const bc = b.containers.join(",");
      if (ac !== bc) return ac.localeCompare(bc);
      return a.source.localeCompare(b.source);
    });
    for (const row of state.rows) {
      state.byId.set(row.source_id, row);
      state.originalKo.set(row.source_id, row.ko || "");
    }
    loadDraft();
    el.buildMeta.textContent = state.meta.commit
      ? `기준 커밋 ${state.meta.commit.slice(0, 12)}`
      : "로컬 데이터";
    updateStats();
    renderList();
  } catch (error) {
    el.buildMeta.textContent = `데이터 로드 실패: ${error.message}`;
  }
}

el.searchInput.addEventListener("input", renderList);
el.statusFilter.addEventListener("change", renderList);
el.prevResult.addEventListener("click", () => moveSelection(-1));
el.nextResult.addEventListener("click", () => moveSelection(1));
el.exportProposal.addEventListener("click", downloadJson);
el.submitIssue.addEventListener("click", openIssue);
el.clearChanges.addEventListener("click", () => {
  state.changes.clear();
  saveDraft();
  updateStats();
  renderList();
  if (state.selectedId) selectRow(state.selectedId);
});

init();
