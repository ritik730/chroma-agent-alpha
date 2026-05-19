'use strict';
const fs = require('fs');
const path = require('path');

const ENV_PATH = path.join(__dirname, '..', '.env');
if (fs.existsSync(ENV_PATH)) {
  for (const line of fs.readFileSync(ENV_PATH, 'utf8').split('\n')) {
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [k, ...v] = line.split('=');
    if (k.trim() && !process.env[k.trim()]) process.env[k.trim()] = v.join('=').trim();
  }
}

const BUDGET_FILE = path.join(
  __dirname, '..',
  process.env.ANTIGRAVITY_BUDGET_FILE || 'memory/antigravity-budget.json'
);
const WEEKLY_BUDGET = parseInt(process.env.ANTIGRAVITY_WEEKLY_BUDGET_TOKENS || '100000', 10);
const RESERVE_PCT = parseFloat(process.env.ANTIGRAVITY_RESERVE_PCT || '0.10');
const RESERVE_TOKENS = Math.floor(WEEKLY_BUDGET * RESERVE_PCT);

function getMondayISO() {
  const d = new Date();
  const day = d.getUTCDay();
  const diff = (day === 0 ? -6 : 1 - day);
  d.setUTCDate(d.getUTCDate() + diff);
  return d.toISOString().slice(0, 10);
}

function readBudget() {
  const weekStart = getMondayISO();
  try {
    if (!fs.existsSync(BUDGET_FILE)) return fresh(weekStart);
    const data = JSON.parse(fs.readFileSync(BUDGET_FILE, 'utf8'));
    if (data.week_start !== weekStart) {
      console.log(`[token-guard] New week (${weekStart}), resetting budget.`);
      return fresh(weekStart);
    }
    return data;
  } catch (_) { return fresh(weekStart); }
}

function fresh(weekStart) {
  return {
    week_start: weekStart,
    budget_total: WEEKLY_BUDGET,
    tokens_used: 0,
    tokens_remaining: WEEKLY_BUDGET,
    calls: 0,
    call_log: [],
  };
}

function saveBudget(data) {
  try {
    const dir = path.dirname(BUDGET_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(BUDGET_FILE, JSON.stringify(data, null, 2));
  } catch (e) { console.error('[token-guard] Failed to save budget:', e.message); }
}

function checkBudget() {
  const data = readBudget();
  const hardStop = data.tokens_remaining <= RESERVE_TOKENS;
  const warning = data.tokens_remaining < WEEKLY_BUDGET * 0.25;
  return {
    allowed: !hardStop,
    tokens_remaining: data.tokens_remaining,
    tokens_used: data.tokens_used,
    reserve_tokens: RESERVE_TOKENS,
    hard_stop: hardStop,
    warning,
    calls_this_week: data.calls,
    pct_remaining: Math.round(data.tokens_remaining / WEEKLY_BUDGET * 100),
  };
}

function recordUsage(promptTokens, completionTokens, purpose, cacheKey = null) {
  const data = readBudget();
  const total = (promptTokens || 0) + (completionTokens || 0);
  data.tokens_used += total;
  data.tokens_remaining = Math.max(0, data.tokens_remaining - total);
  data.calls += 1;
  data.call_log.push({
    ts: new Date().toISOString(),
    purpose,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total,
    cache_key: cacheKey,
    remaining_after: data.tokens_remaining,
  });
  if (data.call_log.length > 100) data.call_log = data.call_log.slice(-100);
  saveBudget(data);
  return data;
}

function getStatus() {
  const data = readBudget();
  const pct = Math.round(data.tokens_remaining / WEEKLY_BUDGET * 100);
  return {
    week_start: data.week_start,
    budget_total: WEEKLY_BUDGET,
    tokens_used: data.tokens_used,
    tokens_remaining: data.tokens_remaining,
    pct_remaining: pct,
    calls: data.calls,
    reserve_tokens: RESERVE_TOKENS,
    status: data.tokens_remaining <= RESERVE_TOKENS ? 'BLOCKED'
      : data.tokens_remaining < WEEKLY_BUDGET * 0.25 ? 'WARNING'
      : 'OK',
  };
}

module.exports = { checkBudget, recordUsage, getStatus, getMondayISO };
