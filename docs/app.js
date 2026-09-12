// app.js -- Dictionary of Lahu static search site. Runs entirely client-side:
// loads lahu-dictionary.sqlite3 (built by src/build_search_db.py) into an
// in-memory SQLite database via the official sqlite3-wasm build (vendored
// by hand in lib/sqlite3-wasm/, see that folder's README.md), then does all
// searching, paging, and rendering here.
//
// If you ever see a "disallowed MIME type" console error loading the .mjs
// or .wasm file here, it's almost certainly file permissions on the server
// (Apache returning a 403/text-html error page for a mode-600 file), not a
// path-naming issue -- see deploy-to-ec2.sh's remote chmod pass and
// that folder's README.md for the story.
//
// Modeled loosely on ~/GitHub/stedt-static's web/src/search.js (same
// "download the whole DB once, deserialize in-memory" approach, same
// gzip-transparency reasoning -- see the comment on fetchDbBytes below) but
// much simpler: no FTS5, no fielded query mini-language, no infinite scroll.
// Layout (search bar / breadcrumbs / pagination) is modeled on
// ~/GitHub/infrared's Bootstrap components, reimplemented as plain JS here
// since that project renders them server-side with Jinja2.

import sqlite3InitModule from './lib/sqlite3-wasm/sqlite3-bundler-friendly.mjs';

const DB_URL = 'lahu-dictionary.sqlite3';
const WASM_URL = 'lib/sqlite3-wasm/sqlite3.wasm';
const PAGE_SIZE = 25;

// Field dropdown -> the normalized column it searches (see
// src/build_search_db.py's ARTICLE_COLS/SUBENTRY_COLS -- both tables carry
// the same search_* column names, so one FIELDS map covers both).
const FIELDS = {
  all:        { label: 'All fields',      col: 'search_all' },
  headword:   { label: 'Headword',        col: 'search_headword' },
  definition: { label: 'Definition',      col: 'search_definition' },
  pos:        { label: 'Part of speech',  col: 'search_pos' },
  notes:      { label: 'Notes',           col: 'search_notes' },
  loan:       { label: 'Loan source',     col: 'search_loan_source' },
};

// ---------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const form = $('search-form');
const fieldSelect = $('field-select');
const valueInput = $('search-value');
const resetBtn = $('reset-btn');
const viewParagraphBtn = $('view-paragraph-btn');
const viewTableBtn = $('view-table-btn');
const breadcrumbsEl = $('breadcrumbs');
const statusEl = $('status');
const paginationEl = $('pagination');
const prevBtn = $('prev-page-btn');
const nextBtn = $('next-page-btn');
const pageInfoEl = $('page-info');
const resultsEl = $('results');

// ---------------------------------------------------------------------
// App state (also reflected in the URL query string -- see state.js-ish
// helpers at the bottom -- so results are bookmarkable/back-button-able)
// ---------------------------------------------------------------------
const state = {
  breadcrumbs: [],   // [{field, value}]
  page: 1,
  view: 'paragraph', // 'paragraph' | 'table'
};

let db = null;

// ---------------------------------------------------------------------
// Normalization: NFC + casefold, matching src/build_search_db.py's norm().
// Deliberately NOT stripping diacritics -- Lahu tone marks are contrastive.
// ---------------------------------------------------------------------
function normalize(s) {
  return (s || '').normalize('NFC').toLowerCase();
}

function escapeLike(s) {
  return s.replace(/[\\%_]/g, (c) => '\\' + c);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

// ---------------------------------------------------------------------
// Highlighting: every word from every active breadcrumb, wrapped in
// <mark> wherever it turns up in a rendered result -- regardless of
// which field that breadcrumb was scoped to. Simpler than tracking
// per-field scope through rendering, and still answers "why did this
// article match" for an All-fields (or any) search. Rebuilt once per
// runSearch(), not per row.
// ---------------------------------------------------------------------
let highlightRegex = null;

function buildHighlightRegex() {
  const terms = new Set();
  for (const bc of state.breadcrumbs) {
    for (const t of bc.value.split(/\s+/)) if (t) terms.add(t);
  }
  if (!terms.size) return null;
  const escaped = [...terms]
    .sort((a, b) => b.length - a.length) // longest first, so overlapping terms prefer the longer match
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').normalize('NFC'));
  if (!escaped.length) return null;
  return new RegExp('(' + escaped.join('|') + ')', 'giu');
}

// Escapes text AND wraps every regex match in <mark>, in one pass, so a
// match's HTML-escaping and its highlight span always line up correctly.
function hl(text) {
  const s = text == null ? '' : String(text);
  if (!s || !highlightRegex) return esc(s);
  highlightRegex.lastIndex = 0;
  let out = '';
  let last = 0;
  let m;
  while ((m = highlightRegex.exec(s))) {
    if (m[0].length === 0) { highlightRegex.lastIndex++; continue; }
    out += esc(s.slice(last, m.index));
    out += '<mark class="dict-hl">' + esc(m[0]) + '</mark>';
    last = m.index + m[0].length;
  }
  out += esc(s.slice(last));
  return out;
}

// ---------------------------------------------------------------------
// DB loading
// ---------------------------------------------------------------------
async function fetchDbMeta() {
  try {
    const res = await fetch('db-meta.json');
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null; // best-effort only -- just means no progress percentage
  }
}

async function fetchDbBytes(url) {
  const meta = await fetchDbMeta();
  const res = await fetch(url);
  if (!res.ok) throw new Error('database fetch failed: HTTP ' + res.status);
  // GitHub Pages always gzips a file this size, so Content-Length is the
  // compressed wire size, not what a streamed reader counts (decompressed) --
  // db-meta.json (written by src/build_search_db.py) carries the true size.
  const total = (meta && meta.bytes) || 0;
  if (!res.body) return new Uint8Array(await res.arrayBuffer());
  const reader = res.body.getReader();
  const parts = [];
  let loaded = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value);
    loaded += value.length;
    const mb = (n) => (n / 1048576).toFixed(1);
    statusEl.textContent = total
      ? `Loading search index… ${mb(loaded)} / ${mb(total)} MB`
      : `Loading search index… ${mb(loaded)} MB`;
  }
  const buf = new Uint8Array(loaded);
  let o = 0;
  for (const p of parts) { buf.set(p, o); o += p.length; }
  return buf;
}

async function loadDb() {
  const sqlite3 = await sqlite3InitModule({ locateFile: () => WASM_URL });
  const bytes = await fetchDbBytes(DB_URL);
  const p = sqlite3.wasm.allocFromTypedArray(bytes);
  const database = new sqlite3.oo1.DB();
  database.checkRc(sqlite3.capi.sqlite3_deserialize(
    database.pointer, 'main', p, bytes.length, bytes.length,
    sqlite3.capi.SQLITE_DESERIALIZE_FREEONCLOSE | sqlite3.capi.SQLITE_DESERIALIZE_RESIZEABLE,
  ));
  return database;
}

function run(sql, params) {
  const rows = [];
  db.exec({ sql, bind: params, rowMode: 'object', resultRows: rows });
  return rows;
}

// ---------------------------------------------------------------------
// Search: each breadcrumb resolves to a Set of matching article ids
// (an id matches if the article's OWN field matches, or any of its
// subentries' field does -- a result is always the whole article, per
// the "results are individual dictionary articles" requirement).
// Breadcrumbs AND together (set intersection). No breadcrumbs = browse
// the whole dictionary in collation order (the id column already IS
// that order -- see build_search_db.py).
// ---------------------------------------------------------------------
function idsForBreadcrumb(bc) {
  const col = FIELDS[bc.field].col;
  const tokens = normalize(bc.value).split(/\s+/).filter(Boolean);
  if (!tokens.length) return new Set();
  const where = tokens.map(() => `${col} LIKE ? ESCAPE '\\'`).join(' AND ');
  const params = tokens.map((t) => '%' + escapeLike(t) + '%');

  const set = new Set();
  for (const r of run(`SELECT id FROM articles WHERE ${where}`, params)) set.add(r.id);
  for (const r of run(`SELECT DISTINCT article_id AS id FROM subentries WHERE ${where}`, params)) set.add(r.id);
  return set;
}

function matchedIds() {
  if (!state.breadcrumbs.length) {
    return run('SELECT id FROM articles ORDER BY id').map((r) => r.id);
  }
  let result = null;
  for (const bc of state.breadcrumbs) {
    const s = idsForBreadcrumb(bc);
    result = result === null ? s : new Set([...result].filter((x) => s.has(x)));
    if (!result.size) break;
  }
  return [...result].sort((a, b) => a - b);
}

function fetchArticlesAndSubs(ids) {
  if (!ids.length) return [];
  const placeholders = ids.map(() => '?').join(',');
  const articleRows = run(`SELECT * FROM articles WHERE id IN (${placeholders})`, ids);
  const byId = new Map(articleRows.map((r) => [r.id, r]));
  const subRows = run(
    `SELECT * FROM subentries WHERE article_id IN (${placeholders}) ORDER BY id`, ids,
  );
  const subsByArticle = new Map();
  for (const s of subRows) {
    if (!subsByArticle.has(s.article_id)) subsByArticle.set(s.article_id, []);
    subsByArticle.get(s.article_id).push(s);
  }
  return ids.map((id) => ({ article: byId.get(id), subs: subsByArticle.get(id) || [] }))
    .filter((r) => r.article);
}

// ---------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------
function loanBadge(marker) {
  if (!marker) return '';
  return `<span class="badge text-bg-warning loan-badge ms-1">${esc(marker)}</span>`;
}

function renderExamplesParagraph(examplesJson, subClass) {
  let examples = [];
  try { examples = JSON.parse(examplesJson || '[]'); } catch (e) { examples = []; }
  return examples.map(([lhu, eng]) =>
    `<div class="${subClass}"><span class="dict-example-lhu">${hl(lhu)}</span>${hl(eng)}</div>`,
  ).join('');
}

function articleParagraphHtml(article, subs) {
  let html = '<div class="dict-article">';
  html += '<div>';
  html += `<span class="dict-headword">${hl(article.headword)}</span>`;
  if (article.pos) html += `<span class="dict-pos">${hl(article.pos)}</span>`;
  if (article.loan_marker) html += `<span class="dict-usg">[${esc(article.loan_marker)}]</span>`;
  if (article.usg_label) html += `<span class="dict-usg">[${hl(article.usg_label)}]</span>`;
  if (article.definition) html += `<span class="dict-def">${hl(article.definition)}</span>`;
  html += '</div>';
  if (article.notes) html += `<div class="dict-note">/ ${hl(article.notes)} /</div>`;
  html += renderExamplesParagraph(article.examples_json, 'dict-example');

  for (const sub of subs) {
    html += '<div class="dict-subentry"><div>';
    html += `<span class="dict-subheadword">${hl(sub.headword)}</span>`;
    if (sub.pos) html += `<span class="dict-pos">${hl(sub.pos)}</span>`;
    if (sub.loan_marker) html += `<span class="dict-usg">[${esc(sub.loan_marker)}]</span>`;
    if (sub.usg_label) html += `<span class="dict-usg">[${hl(sub.usg_label)}]</span>`;
    if (sub.definition) html += `<span class="dict-def">${hl(sub.definition)}</span>`;
    html += '</div>';
    if (sub.notes) html += `<div class="dict-subnote">/ ${hl(sub.notes)} /</div>`;
    html += renderExamplesParagraph(sub.examples_json, 'dict-subexample');
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function renderParagraphView(rows) {
  resultsEl.innerHTML = rows.map((r) => articleParagraphHtml(r.article, r.subs)).join('');
}

function tableRow(item, isSub) {
  const cls = isSub ? 'sub-row' : 'article-row';
  const hw = isSub ? `<span class="ms-2">↳ ${hl(item.headword)}</span>` : hl(item.headword);
  return `<tr class="${cls}">
    <td>${hw}</td>
    <td>${hl(item.pos)}</td>
    <td>${loanBadge(item.loan_marker)}${item.loan_source ? ' <span class="text-muted small">' + hl(item.loan_source) + '</span>' : ''}</td>
    <td>${hl(item.definition)}</td>
    <td class="text-muted">${hl(item.notes)}</td>
  </tr>`;
}

function renderTableView(rows) {
  let html = '<table class="table table-sm align-top"><thead><tr>'
    + '<th>Headword</th><th>Part of speech</th><th>Loan</th><th>Definition</th><th>Notes</th>'
    + '</tr></thead><tbody>';
  for (const r of rows) {
    html += tableRow(r.article, false);
    for (const sub of r.subs) html += tableRow(sub, true);
  }
  html += '</tbody></table>';
  resultsEl.innerHTML = html;
}

function renderResults(rows) {
  if (!rows.length) {
    resultsEl.innerHTML = '<p class="text-muted">No matching entries.</p>';
    return;
  }
  if (state.view === 'table') renderTableView(rows);
  else renderParagraphView(rows);
}

// ---------------------------------------------------------------------
// Breadcrumbs
// ---------------------------------------------------------------------
function renderBreadcrumbs() {
  breadcrumbsEl.innerHTML = state.breadcrumbs.map((bc, i) => `
    <span class="badge text-bg-secondary breadcrumb-chip">
      ${esc(FIELDS[bc.field].label)}: ${esc(bc.value)}
      <button type="button" class="btn-close btn-close-white" data-index="${i}" aria-label="Remove"></button>
    </span>
  `).join('');
  breadcrumbsEl.querySelectorAll('button[data-index]').forEach((btn) => {
    btn.addEventListener('click', () => {
      state.breadcrumbs.splice(Number(btn.dataset.index), 1);
      state.page = 1;
      pushState();
      runSearch();
    });
  });
}

// ---------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------
let currentIds = [];

function renderPagination(total) {
  if (total <= PAGE_SIZE) {
    paginationEl.classList.add('d-none');
    return;
  }
  paginationEl.classList.remove('d-none');
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  state.page = Math.min(Math.max(1, state.page), totalPages);
  const start = (state.page - 1) * PAGE_SIZE + 1;
  const end = Math.min(total, state.page * PAGE_SIZE);
  pageInfoEl.textContent = `${start}–${end} of ${total} (page ${state.page} of ${totalPages})`;
  prevBtn.disabled = state.page <= 1;
  nextBtn.disabled = state.page >= totalPages;
}

// ---------------------------------------------------------------------
// Main search/render cycle
// ---------------------------------------------------------------------
function runSearch() {
  renderBreadcrumbs();
  highlightRegex = buildHighlightRegex();
  currentIds = matchedIds();
  const total = currentIds.length;
  statusEl.textContent = state.breadcrumbs.length
    ? `${total} matching ${total === 1 ? 'entry' : 'entries'}`
    : `Browsing all ${total} entries`;
  renderPagination(total);
  const offset = (state.page - 1) * PAGE_SIZE;
  const pageIds = currentIds.slice(offset, offset + PAGE_SIZE);
  const rows = fetchArticlesAndSubs(pageIds);
  renderResults(rows);
}

// ---------------------------------------------------------------------
// URL state (bookmarkable / back-button friendly)
// ---------------------------------------------------------------------
function serializeState() {
  const params = new URLSearchParams();
  for (const bc of state.breadcrumbs) params.append('f', `${bc.field}:${bc.value}`);
  if (state.page !== 1) params.set('page', String(state.page));
  if (state.view !== 'paragraph') params.set('view', state.view);
  return params;
}

function pushState() {
  const params = serializeState();
  const qs = params.toString();
  history.pushState(state, '', qs ? '?' + qs : location.pathname);
}

function loadStateFromUrl() {
  const params = new URLSearchParams(location.search);
  state.breadcrumbs = params.getAll('f').map((v) => {
    const i = v.indexOf(':');
    const field = i === -1 ? 'all' : v.slice(0, i);
    const value = i === -1 ? v : v.slice(i + 1);
    return FIELDS[field] ? { field, value } : { field: 'all', value: v };
  });
  state.page = Number(params.get('page')) || 1;
  state.view = params.get('view') === 'table' ? 'table' : 'paragraph';
}

function applyViewButtons() {
  viewParagraphBtn.classList.toggle('active', state.view === 'paragraph');
  viewParagraphBtn.setAttribute('aria-pressed', String(state.view === 'paragraph'));
  viewTableBtn.classList.toggle('active', state.view === 'table');
  viewTableBtn.setAttribute('aria-pressed', String(state.view === 'table'));
}

// ---------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------
form.addEventListener('submit', (e) => {
  e.preventDefault();
  const value = valueInput.value.trim();
  if (!value) return;
  state.breadcrumbs.push({ field: fieldSelect.value, value });
  valueInput.value = '';
  state.page = 1;
  pushState();
  runSearch();
});

resetBtn.addEventListener('click', () => {
  state.breadcrumbs = [];
  state.page = 1;
  valueInput.value = '';
  fieldSelect.value = 'all';
  pushState();
  runSearch();
});

viewParagraphBtn.addEventListener('click', () => {
  state.view = 'paragraph';
  applyViewButtons();
  pushState();
  runSearch();
});
viewTableBtn.addEventListener('click', () => {
  state.view = 'table';
  applyViewButtons();
  pushState();
  runSearch();
});

prevBtn.addEventListener('click', () => {
  if (state.page > 1) { state.page -= 1; pushState(); runSearch(); }
});
nextBtn.addEventListener('click', () => {
  state.page += 1; pushState(); runSearch();
});

window.addEventListener('popstate', () => {
  loadStateFromUrl();
  applyViewButtons();
  runSearch();
});

// ---------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------
(async function boot() {
  loadStateFromUrl();
  applyViewButtons();
  try {
    db = await loadDb();
  } catch (err) {
    statusEl.textContent = 'Could not load the search database: ' + err.message;
    return;
  }
  runSearch();
})();
