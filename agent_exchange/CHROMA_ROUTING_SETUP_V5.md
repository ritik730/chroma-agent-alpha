# CHROMA-AGENT-ALPHA — Routing & Infrastructure Deep Context v5
> For Gemini / Antigravity consumption. Read-only awareness.
> Last updated: 2026-06-08 | Operator: Devendra Kataria
> Partner context: CLAUDE_CODE_CONTEXT.md | Master: CHROMA_MASTER_CONTEXT.md

---

## 1. WHAT CHANGED (v4 → v5)

| Component | v4 (old) | v5 (current) | Why |
|-----------|----------|--------------|-----|
| Primary Router | CCR on :3456 | **LiteLLM on :4000** | LiteLLM provides robust fallback retry arrays, cooldown configurations, and rate-limit preservation. |
| Local Compute | Ollama (`phi4-mini`) | **Disabled (Zero Local Compute)** | Local execution OOM'd/swap-froze the Latitude 5300 host (16GB RAM). All inference is cloud-based. |
| T1 Model | `phi4-mini` (local) | **Gemini 2.5 Flash Lite (cloud)** | Cost-effective, very fast (~0.4-0.7s), zero host RAM utilization. |
| T2 Model | DeepSeek free | **DeepSeek V4 Flash free** | Free tier workhorse with automated Llama fallback. |
| T3 Model | `deepseek-v3.2-speciale` | **DeepSeek V4 Flash paid / R1 Distill Qwen** | paid Flash for standard coding to save budget, R1 Distill for complex GNN reasoning. |

---

## 2. CURRENT INFRASTRUCTURE MAP

```
┌─────────────────────────────────────────────────────────────┐
│                    Dell Latitude 5300                        │
│                 16GB RAM · No GPU · Windows 11               │
│                                                              │
│  ┌─────────────────────────┐       ┌──────────────────────┐  │
│  │   LiteLLM Proxy (:4000) │       │ Antigravity Proxy    │  │
│  │   Routes T1, T2, T3 to  │       │ (Port 8080)          │  │
│  │   OpenRouter endpoints  │       │ OAuth Claude Proxy   │  │
│  └────────────┬────────────┘       └──────────┬───────────┘  │
│               │                               │              │
│               ├───────── T1 / T2 / T3 ────────┤              │
│               │                               │              │
│  ┌────────────┴────────────┐                  │              │
│  │   FastAPI Server        │                  │              │
│  │   Pipeline URL: :8001   │                  │              │
│  └────────────┬────────────┘                  │              │
│               │                               │              │
│               ▼                               ▼              │
│  [n8n Folder-Watch Watcher] ──────► [FAIR Data Archiving]    │
│  Port: 5678                         Zarr Store + LaminDB     │
│                                                              │
│  RAM used: ~4-5 GB                  Available: ~11-12 GB     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. BRAIN ROUTING TABLE (v5 — CURRENT)

### Claude Code's Brains via LiteLLM (:4000)

| Tier | Model | Provider | LiteLLM Route | Use | Cost | Rate Limit |
|------|-------|----------|---------------|-----|------|------------|
| **T1** | `google/gemini-2.5-flash-lite` | OpenRouter | `claude-t1` | Classify, label, json_reformat, dedup | ~₹0.010/call | 30 RPM |
| **T1-FREE** | `meta-llama/llama-3.1-8b-instruct:free` | OpenRouter | `claude-t1-free` | Fallback scout for mechanical tasks | ₹0 | 30 RPM |
| **T2** | `deepseek/deepseek-v4-flash:free` | OpenRouter | `claude-t2` | Summarize, enrich, compact memory | ₹0 | 20 RPM |
| **T2-FREE** | `meta-llama/llama-3.3-70b-instruct:free` | OpenRouter | `claude-t2-free` | Fallback analyst to prevent rate-limits | ₹0 | 20 RPM |
| **T3** | `deepseek/deepseek-v4-flash` | OpenRouter | `claude-t3` | standard coding, pipeline, GNN | ~₹0.011/call | 30 RPM |
| **T3-COT** | `deepseek/deepseek-r1-distill-qwen-32b` | OpenRouter | `claude-t3-cot` | complex GNN reasoning & manuscripts | paid CoT | 30 RPM |

### Antigravity's Brains (unchanged)

| Source | Route | Use | Cost |
|--------|-------|-----|------|
| Gemini Pro | Direct (free) | Planning, Ghost Runtime, document compilation, indexing | ₹0 |
| Claude Proxy | localhost:8080 (14 Google OAuth) | Manuscript drafting, literature review, outreach letters | ₹0 |

### Budget Governance
- **Ceiling:** ₹500/month
- **OpenRouter Credit Guard:** Monthly credit cap set to $3.097 (approx. ₹258/month).
- **LiteLLM Max Tokens:** Tier 3 models restricted to `max_tokens: 8192` to conserve credit pool.

---

## 4. PORT MAP (v5)

| Port | Service | Owner | Status |
|------|---------|-------|--------|
| 4000 | LiteLLM Proxy | Claude Code ecosystem | PRIMARY router (OpenRouter proxy) |
| 5678 | n8n | Pipeline Automator | Active (triggers pipeline on file drop) |
| 8001 | FastAPI Server | Pipeline execution engine | Active (serves dashboard and API routes) |
| 8080 | Antigravity Proxy | Antigravity ecosystem | Active (free Claude proxy via OAuth) |

---

## 5. INFRASTRUCTURE CONFIG FILES

- `C:\chroma-agent-alpha\litellm_config.yaml` — LiteLLM router configuration (includes retry arrays and fallback lists)
- `C:\chroma-agent-alpha\.env` — API keys, base paths, and server parameters
- `C:\chroma-agent-alpha\CLAUDE.md` — Active development rules and shortcut commands
- `~/.claude/settings.json` — Tool definitions and plugin count limit (restricted to 13)

---

*Gemini reads this file for infrastructure awareness only. Do NOT modify routing configs. Escalate issues to operator (Devendra Kataria).*
