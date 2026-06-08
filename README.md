# CHROMA-AGENT-ALPHA

> An agentic, vendor-independent ETL pipeline for raw chromatography data (GC-MS).

**Target:** SLAS Technology manuscript + 2027 PhD applications (Germany, Netherlands)  
**Budget:** ≤ ₹500/month | **Actual:** ~₹52/month

---

## What This Is

A dual-agent AI system that autonomously processes `.cdf`, `.mzML`, and `.D` files from GC-MS instruments into FAIR-compliant peak tables with compound identification.

```
.cdf/.mzML/.D  →  ALS Baseline  →  Peak Detection  →  GNN Deconv  →  JSON  →  FAIR Store
```

## Architecture

### Dual-Agent System
- **Macro Brain:** Antigravity (Gemini Pro) — architecture, planning, manuscript writing
- **Micro Engine:** Claude Code — code execution, data pipeline, git

### Three-Tier LLM Router (via LiteLLM on :4000)

| Tier | Model | Purpose | Cost |
|---|---|---|---|
| T1 Scout | `google/gemini-2.5-flash-lite` | classify, label, reformat | ~₹0.010/call |
| T2 Analyst | `deepseek/deepseek-v4-flash:free` | summarize, enrich, analysis | ₹0 |
| T3 Architect | `deepseek/deepseek-v4-flash` | code, pipeline, GNN, science | ~₹0.011/call |
| T3-CoT | `deepseek-r1-distill-qwen-32b` | hard science (CoT) | ~₹0.030/call |
| Antigravity | Claude Sonnet/Opus via proxy | manuscript, PhD letters | weekly budget |

## Pipeline Status

| Stage | Status |
|---|---|
| CDF/mzML Ingestion | ✅ Done |
| ALS Baseline Correction | ✅ Done |
| Peak Detection (scipy) | ✅ Done |
| n8n Folder Trigger | ✅ Done |
| Spectral Matching (matchms) | ✅ Done |
| GNN Deconvolution | ✅ Done |
| FAIR Storage (zarr + lamindb) | ✅ Done |

## Quick Start

```powershell
# 1. Start LiteLLM proxy
litellm-start

# 2. Launch Claude Code on T2 (default)
claude-t2

# 3. Switch tiers mid-session
/model claude-t1   # fast classify
/model claude-t2   # free analysis
/model claude-t3   # code/science
```

## Directory Structure

```
chroma-agent-alpha/
├── .env                    ← API keys (never commit)
├── CLAUDE.md               ← Claude Code session context
├── litellm_config.yaml     ← LiteLLM proxy config (T1/T2/T3)
├── start.cmd               ← One-click launcher
├── lib/
│   ├── openrouter-client.cjs   ← T1/T2/T3 OpenRouter calls
│   ├── tiered-ask.cjs          ← Main router orchestrator
│   ├── antigravity-client.cjs  ← Claude proxy client
│   ├── token-guard.cjs         ← Weekly Antigravity budget
│   └── soft-failure.cjs        ← Error logging
├── scripts/
│   ├── parse_cdf.py            ← GC-MS ingestion + peak detection
│   └── tier-usage-report.cjs   ← Cost dashboard
├── memory/
│   ├── tier-usage.jsonl        ← All LLM calls logged
│   └── t2-daily.json           ← T2 rate limit counter
└── raw_data/                   ← Input GC-MS files
```

## PhD Targets 2027

- Pirok Group (UvA, NL) — chromatography AI
- CADET/von Lieres (Jülich, DE, E13)
- FZJ HDS-LEE — AI in Earth Science (2026D-0451)
- Radboud SDL (NL) | SimTech Stuttgart (DE) | TU Delft AI4Science (NL)

---

*Built by Devendra Kataria — MSc Chemistry, 82%*
