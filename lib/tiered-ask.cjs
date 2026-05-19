'use strict';
const fs = require('fs');
const path = require('path');
const { callT1, callT2, callT3 } = require('./openrouter-client.cjs');
const { callAntigravity } = require('./antigravity-client.cjs');
const { logSoftFailure } = require('./soft-failure.cjs');

const ENV_PATH = path.join(__dirname, '..', '.env');
if (fs.existsSync(ENV_PATH)) {
  for (const line of fs.readFileSync(ENV_PATH, 'utf8').split('\n')) {
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [k, ...v] = line.split('=');
    if (k.trim() && !process.env[k.trim()]) process.env[k.trim()] = v.join('=').trim();
  }
}

const USAGE_LOG = path.join(__dirname, '..', 'memory', 'tier-usage.jsonl');
const WINDOW = parseInt(process.env.QUOTA_WINDOW_SIZE || '50', 10);

// ── Task classification ────────────────────────────────────────────

// Antigravity: manual only, never auto-routed
const ANTIGRAVITY_PURPOSES = new Set([
  'manuscript', 'phd_letter', 'author_voice', 'identity_audit',
  'high_stakes_review', 'architectural_decision_irreversible', 'antigravity',
]);

// T1: mechanical, fast, cheap
const T1_PURPOSES = new Set([
  'classify', 'label', 'json_reformat', 'template_slot_fill',
  'dedup', 'hash_match', 'greeting', 'echo',
]);

// T2: analysis, summarization (free)
const T2_PURPOSES = new Set([
  'summarize', 'summary', 'enrich', 'compact_memory',
  'research_synthesis', 'long_context_analysis', 'codebase_analysis',
  'reflexion_first_pass', 'kg_titling',
]);

// T3: hard science (always T3 regardless of quota)
const T3_HARD_FLOOR = new Set([
  'gnn_architecture', 'peak_deconvolution', 'shap_analysis', 'sdl_design',
  'statistical_validation', 'pipeline_decision', 'pytorch_debug', 'scientific_reasoning',
]);

function classifyTask({ purpose, prompt, flags = [] }) {
  if (!purpose && !prompt) return 't1';
  if (purpose && ANTIGRAVITY_PURPOSES.has(purpose)) return 'antigravity';
  if (flags.includes('antigravity')) return 'antigravity';
  if (purpose && T3_HARD_FLOOR.has(purpose)) return 't3';
  if (purpose && T1_PURPOSES.has(purpose)) return 't1';
  if (purpose && T2_PURPOSES.has(purpose)) return 't2';
  if (typeof prompt === 'string' && prompt.length < 40 &&
      /^(hi|hello|hey|thanks|ok|yes|no|sure)\b/i.test(prompt.trim())) return 't1';
  return 't3'; // Default: T3 for unknown tasks
}

// ── Quota balancing ───────────────────────────────────────────────

function readWindow() {
  if (!fs.existsSync(USAGE_LOG)) return [];
  return fs.readFileSync(USAGE_LOG, 'utf8')
    .split('\n').filter(Boolean).slice(-WINDOW)
    .map(l => { try { return JSON.parse(l); } catch (_) { return null; } })
    .filter(Boolean);
}

function applyQuota(cls) {
  if (cls === 'antigravity') return cls;
  if (T3_HARD_FLOOR.has(cls)) return 't3';

  const w = readWindow();
  if (w.length < 10) return cls;

  const targets = {
    t1: parseFloat(process.env.QUOTA_T1 || '0.40'),
    t2: parseFloat(process.env.QUOTA_T2 || '0.35'),
    t3: parseFloat(process.env.QUOTA_T3 || '0.25'),
  };
  const tolerance = parseFloat(process.env.QUOTA_TOLERANCE || '0.10');
  const counts = { t1: 0, t2: 0, t3: 0 };
  for (const e of w) if (counts[e.class] !== undefined) counts[e.class]++;
  const total = w.length;

  const overBy = (c) => (counts[c] / total) - targets[c];
  if (overBy(cls) > tolerance) {
    const alt = ['t1', 't2', 't3']
      .filter(c => c !== cls && c !== 'antigravity')
      .sort((a, b) => overBy(a) - overBy(b))[0];
    if (alt) return alt;
  }
  return cls;
}

// ── Usage logging ─────────────────────────────────────────────────

function logCall(entry) {
  try {
    const dir = path.dirname(USAGE_LOG);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(USAGE_LOG, JSON.stringify(entry) + '\n');
  } catch (_) {}
}

// ── Dispatch ─────────────────────────────────────────────────────

async function dispatch(cls, system, prompt, opts) {
  if (cls === 'antigravity') {
    return { ...(await callAntigravity(system, prompt, opts)), tier: 4, class: 'antigravity' };
  }
  if (cls === 't1') {
    try {
      return { ...(await callT1(system, prompt, opts)), tier: 1, class: 't1' };
    } catch (e) {
      logSoftFailure('tier1', e, { prompt: prompt?.slice(0, 100) });
      return dispatch('t2', system, prompt, opts);
    }
  }
  if (cls === 't2') {
    try {
      return { ...(await callT2(system, prompt, opts)), tier: 2, class: 't2' };
    } catch (e) {
      logSoftFailure('tier2', e, { prompt: prompt?.slice(0, 100) });
      return dispatch('t3', system, prompt, opts);
    }
  }
  // T3
  try {
    return { ...(await callT3(system, prompt, opts)), tier: 3, class: 't3' };
  } catch (e) {
    logSoftFailure('tier3', e, { prompt: prompt?.slice(0, 100) });
    throw e;
  }
}

// ── Main API ──────────────────────────────────────────────────────

async function ask({ purpose, prompt, system, flags = [], ...opts }) {
  const classified = classifyTask({ purpose, prompt, flags });
  const final = applyQuota(classified);
  const started = Date.now();
  const result = await dispatch(final, system, prompt, { purpose, ...opts });
  logCall({
    ts: new Date().toISOString(),
    purpose: purpose || null,
    class: final,
    tier: result.tier,
    model: result.model,
    latency_ms: Date.now() - started,
    usage: result.usage || null,
  });
  return result;
}

async function ping() {
  const { probeHealth } = require('./openrouter-client.cjs');
  const { probeHealth: probeAG } = require('./antigravity-client.cjs');
  const [t1, ag] = await Promise.all([probeHealth(), probeAG()]);
  return {
    tier1: { ...t1, model: process.env.TIER1_MODEL || 'google/gemini-2.5-flash-lite' },
    tier2: { ok: t1.ok, model: process.env.TIER2_MODEL || 'deepseek/deepseek-v4-flash:free', note: 'same key as T1' },
    tier3: { ok: t1.ok, model: process.env.TIER3_MODEL || 'deepseek/deepseek-v4-flash', note: 'same key as T1' },
    antigravity: { ...ag },
  };
}

module.exports = { ask, ping, classifyTask, T1_PURPOSES, T2_PURPOSES, T3_HARD_FLOOR, ANTIGRAVITY_PURPOSES };

if (require.main === module) {
  const [,, mode, ...rest] = process.argv;
  if (mode === 'ping') ping().then(r => { console.log(JSON.stringify(r, null, 2)); process.exit(0); });
  else if (mode === 'ask') ask({ prompt: rest.join(' ') })
    .then(r => console.log(JSON.stringify({ tier: r.tier, model: r.model, text: r.text }, null, 2)));
  else console.log('Usage: node lib/tiered-ask.cjs <ping|ask> "prompt"');
}
