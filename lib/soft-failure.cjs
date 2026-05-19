'use strict';
const fs = require('fs');
const path = require('path');
const LOG_PATH = path.join(__dirname, '..', 'memory', 'soft-failures.jsonl');

function logSoftFailure(source, error, context = {}) {
  const entry = {
    ts: new Date().toISOString(),
    source,
    error: error?.message || String(error),
    context,
  };
  try { fs.appendFileSync(LOG_PATH, JSON.stringify(entry) + '\n'); } catch (_) {}
  return entry;
}

module.exports = { logSoftFailure };
