'use strict';
const fs = require('fs');
const path = require('path');

// Load .env
const ENV_PATH = path.join(__dirname, '..', '.env');
if (fs.existsSync(ENV_PATH)) {
  for (const line of fs.readFileSync(ENV_PATH, 'utf8').split('\n')) {
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [k, ...v] = line.split('=');
    if (k.trim() && !process.env[k.trim()]) process.env[k.trim()] = v.join('=').trim();
  }
}

const BASE = process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1';
const T2_DAILY_LOG = path.join(__dirname, '..', 'memory', 't2-daily.json');

function getKey() {
  const k = process.env.OPENROUTER_API_KEY;
  if (!k) throw new Error('OPENROUTER_API_KEY not set in .env');
  return k;
}

// Read T2 daily call count
function getT2DailyCount() {
  try {
    if (!fs.existsSync(T2_DAILY_LOG)) return { date: '', count: 0 };
    return JSON.parse(fs.readFileSync(T2_DAILY_LOG, 'utf8'));
  } catch (_) { return { date: '', count: 0 }; }
}

// Increment T2 daily counter
function incrementT2Count() {
  const today = new Date().toISOString().slice(0, 10);
  const data = getT2DailyCount();
  const count = (data.date === today ? data.count : 0) + 1;
  try { fs.writeFileSync(T2_DAILY_LOG, JSON.stringify({ date: today, count })); } catch (_) {}
  return count;
}

// Select T2 model based on daily limit
function pickT2Model() {
  const daily = getT2DailyCount();
  const today = new Date().toISOString().slice(0, 10);
  const count = daily.date === today ? daily.count : 0;
  const limit = parseInt(process.env.TIER2_DAILY_LIMIT || '180', 10);
  if (count >= limit) {
    console.warn(`[router] T2 daily limit hit (${count}/${limit}), using fallback`);
    return process.env.TIER2_FALLBACK || 'meta-llama/llama-3.3-70b-instruct:free';
  }
  return process.env.TIER2_MODEL || 'deepseek/deepseek-v4-flash:free';
}

async function callOpenRouter(model, system, prompt, opts = {}) {
  const started = Date.now();
  const body = {
    model,
    messages: [
      ...(system ? [{ role: 'system', content: system }] : []),
      { role: 'user', content: prompt }
    ],
    max_tokens: opts.max_tokens ?? 1024,
    temperature: opts.temperature ?? 0.7,
  };

  const res = await fetch(`${BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getKey()}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://chroma-agent-alpha',
      'X-Title': 'CHROMA-AGENT-ALPHA',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(opts.timeout ?? 120000),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`openrouter ${res.status} [${model}]: ${errText.slice(0, 300)}`);
  }

  const j = await res.json();
  const choice = j.choices?.[0];
  return {
    text: (choice?.message?.content || '').trim(),
    model: j.model || model,
    usage: j.usage,
    finish_reason: choice?.finish_reason,
    reasoning: choice?.message?.reasoning || null,
    latency_ms: Date.now() - started,
  };
}

// T1: Scout — Gemini Flash Lite (fastest, ~0.4-0.7s)
async function callT1(system, prompt, opts = {}) {
  const model = process.env.TIER1_MODEL || 'google/gemini-2.5-flash-lite';
  try {
    return await callOpenRouter(model, system, prompt, opts);
  } catch (e) {
    const fallback = process.env.TIER1_FALLBACK || 'meta-llama/llama-3.1-8b-instruct';
    console.warn(`[router] T1 failed (${model}), trying fallback ${fallback}: ${e.message}`);
    return callOpenRouter(fallback, system, prompt, opts);
  }
}

// T2: Analyst (with daily counter)
async function callT2(system, prompt, opts = {}) {
  const model = pickT2Model();
  const result = await callOpenRouter(model, system, prompt, opts);
  incrementT2Count();
  return result;
}

// T3: Architect — V4-Flash fast (no thinking timeout), R1-distill for CoT tasks
async function callT3(system, prompt, opts = {}) {
  // Use CoT model only for hard science tasks
  const cotTasks = new Set(['gnn_architecture', 'peak_deconvolution', 'statistical_validation']);
  const useCot = opts.purpose && cotTasks.has(opts.purpose);

  const model = useCot
    ? (process.env.TIER3_COT_MODEL || 'deepseek/deepseek-r1-distill-qwen-32b')
    : (process.env.TIER3_MODEL || 'deepseek/deepseek-v4-flash');

  const timeout = useCot
    ? parseInt(process.env.TIER3_COT_TIMEOUT || '60000', 10)
    : (opts.timeout ?? 120000);

  try {
    return await callOpenRouter(model, system, prompt, { ...opts, max_tokens: opts.max_tokens ?? 2048, timeout });
  } catch (e) {
    const fallback = process.env.TIER3_FALLBACK || 'google/gemini-2.5-flash-lite';
    console.warn(`[router] T3 failed (${model}), trying fallback ${fallback}: ${e.message}`);
    return callOpenRouter(fallback, system, prompt, opts);
  }
}

async function probeHealth() {
  const started = Date.now();
  try {
    const r = await callT1(null, 'ping', { max_tokens: 5, timeout: 10000 });
    return { ok: !!r.text, ts: Date.now(), latency_ms: Date.now() - started };
  } catch (e) {
    return { ok: false, ts: Date.now(), reason: e.message, latency_ms: Date.now() - started };
  }
}

module.exports = { callT1, callT2, callT3, probeHealth, pickT2Model, getT2DailyCount };
