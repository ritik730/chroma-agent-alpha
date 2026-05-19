'use strict';
const fs = require('fs');
const path = require('path');
const { checkBudget, recordUsage } = require('./token-guard.cjs');

const ENV_PATH = path.join(__dirname, '..', '.env');
if (fs.existsSync(ENV_PATH)) {
  for (const line of fs.readFileSync(ENV_PATH, 'utf8').split('\n')) {
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [k, ...v] = line.split('=');
    if (k.trim() && !process.env[k.trim()]) process.env[k.trim()] = v.join('=').trim();
  }
}

// PROXY ONLY — never api.anthropic.com
const BASE = process.env.ANTIGRAVITY_BASE_URL;
const MODEL = process.env.ANTIGRAVITY_MODEL || 'claude-sonnet-4-5';

// Response cache — never repeat the same Antigravity call
const CACHE_FILE = path.join(__dirname, '..', 'memory', 'antigravity-cache.json');

function readCache() {
  try {
    if (!fs.existsSync(CACHE_FILE)) return {};
    return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
  } catch (_) { return {}; }
}

function writeCache(cache) {
  try { fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2)); } catch (_) {}
}

function makeCacheKey(purpose, prompt) {
  const str = `${purpose}::${prompt.trim().slice(0, 500)}`;
  let h = 0;
  for (let i = 0; i < str.length; i++) { h = ((h << 5) - h + str.charCodeAt(i)) | 0; }
  return `ag_${Math.abs(h).toString(16)}`;
}

async function callAntigravity(system, prompt, opts = {}) {
  if (!BASE) {
    throw new Error(
      'ANTIGRAVITY_BASE_URL not set in .env. ' +
      'Set this to your Claude proxy URL. Do NOT use api.anthropic.com.'
    );
  }

  const purpose = opts.purpose || 'unknown';

  // Check cache first
  if (!opts.skipCache) {
    const cacheKey = makeCacheKey(purpose, prompt);
    const cache = readCache();
    if (cache[cacheKey]) {
      console.log(`[antigravity] Cache hit for ${purpose} (${cacheKey})`);
      return { ...cache[cacheKey], cached: true, cache_key: cacheKey };
    }
  }

  // Check weekly token budget
  const budget = checkBudget();
  if (!budget.allowed) {
    throw new Error(
      `[antigravity] BLOCKED — weekly token budget exhausted. ` +
      `${budget.tokens_remaining} tokens remain (reserve: ${budget.reserve_tokens}). ` +
      `Resets Monday. Use T3 (DeepSeek V4-Flash) instead.`
    );
  }
  if (budget.warning) {
    console.warn(
      `[antigravity] WARNING: Only ${budget.pct_remaining}% of weekly budget remains ` +
      `(${budget.tokens_remaining} tokens). Use T3 where possible.`
    );
  }

  const started = Date.now();
  const model = opts.model || MODEL;
  const body = {
    model,
    max_tokens: opts.max_tokens ?? 4096,
    temperature: opts.temperature ?? 0.7,
    system: system || undefined,
    messages: [{ role: 'user', content: prompt }],
  };

  const res = await fetch(`${BASE}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(opts.timeout ?? 180000),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`antigravity proxy ${res.status}: ${errText.slice(0, 300)}`);
  }

  const j = await res.json();
  const text = (j.content || [])
    .filter(c => c.type === 'text')
    .map(c => c.text)
    .join('')
    .trim();

  const promptTokens = j.usage?.input_tokens || 0;
  const completionTokens = j.usage?.output_tokens || 0;

  const cacheKey = makeCacheKey(purpose, prompt);
  recordUsage(promptTokens, completionTokens, purpose, cacheKey);

  const result = {
    text,
    model: j.model || model,
    usage: { input_tokens: promptTokens, output_tokens: completionTokens },
    stop_reason: j.stop_reason,
    latency_ms: Date.now() - started,
    cached: false,
    cache_key: cacheKey,
  };

  if (!opts.skipCache) {
    const cache = readCache();
    cache[cacheKey] = { text, model: result.model, usage: result.usage, purpose, ts: new Date().toISOString() };
    const keys = Object.keys(cache);
    if (keys.length > 200) {
      keys.slice(0, keys.length - 200).forEach(k => delete cache[k]);
    }
    writeCache(cache);
  }

  return result;
}

async function probeHealth() {
  const started = Date.now();
  if (!BASE) return { ok: false, reason: 'ANTIGRAVITY_BASE_URL not configured', latency_ms: 0 };
  const budget = checkBudget();
  if (!budget.allowed) return { ok: false, reason: 'budget exhausted', budget, latency_ms: 0 };
  return { ok: true, ts: Date.now(), budget_pct_remaining: budget.pct_remaining, latency_ms: Date.now() - started };
}

module.exports = { callAntigravity, probeHealth };
