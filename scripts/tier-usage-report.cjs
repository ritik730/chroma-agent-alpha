'use strict';
const fs = require('fs');
const path = require('path');
const { getStatus } = require('../lib/token-guard.cjs');

const LOG = path.join(__dirname, '..', 'memory', 'tier-usage.jsonl');
if (!fs.existsSync(LOG)) { console.log('No tier-usage log yet.'); process.exit(0); }

const entries = fs.readFileSync(LOG, 'utf8').split('\n').filter(Boolean)
  .map(l => { try { return JSON.parse(l); } catch (_) { return null; } }).filter(Boolean);
const N = parseInt(process.argv[2] || '100', 10);
const w = entries.slice(-N);
const by = { t1: 0, t2: 0, t3: 0, antigravity: 0 };
const models = {};
let totalLatency = 0, cached = 0;
for (const e of w) {
  if (by[e.class] !== undefined) by[e.class]++;
  models[e.model] = (models[e.model] || 0) + 1;
  totalLatency += e.latency_ms || 0;
  if (e.cached) cached++;
}
const total = w.length || 1;
console.log(`\n=== CHROMA-AGENT-ALPHA Router Report (last ${total} calls) ===\n`);
console.log(`  T1 Scout       ${(by.t1/total*100).toFixed(1)}%  (target 40%)`);
console.log(`  T2 Analyst     ${(by.t2/total*100).toFixed(1)}%  (target 35%)`);
console.log(`  T3 Architect   ${(by.t3/total*100).toFixed(1)}%  (target 25%)`);
console.log(`  Antigravity    ${(by.antigravity/total*100).toFixed(1)}%  (manual only)`);
console.log(`\n  Avg latency:   ${(totalLatency/total).toFixed(0)}ms`);
console.log(`  Cache hits:    ${cached} (${(cached/total*100).toFixed(1)}%)`);
console.log(`\nBy model:`);
for (const [m, c] of Object.entries(models).sort((a,b) => b[1]-a[1]))
  console.log(`  ${m.padEnd(45)} ${c}`);

console.log('\n=== Antigravity Weekly Budget ===\n');
const s = getStatus();
console.log(`  Week start:    ${s.week_start}`);
console.log(`  Used:          ${s.tokens_used.toLocaleString()} tokens`);
console.log(`  Remaining:     ${s.tokens_remaining.toLocaleString()} (${s.pct_remaining}%)`);
console.log(`  Calls:         ${s.calls}`);
console.log(`  Status:        ${s.status}`);
