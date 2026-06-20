# CHROMA-AGENT-ALPHA — Master Context
> Single source of truth. Both agents read this. Neither modifies it alone.
> Version: June 2026 (updated 2026-06-20 — routing v5) | Operator: [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria/)

---

## 1. Project Identity

| Field | Value |
| :--- | :--- |
| **Project** | CHROMA-AGENT-ALPHA |
| **Goal** | Vendor-independent AI-driven ETL for raw chromatography data |
| **Operator** | [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria/) / MSc Chemistry 82% / India |
| **PhD Target** | 2027 EU cohort — TV-L E13 (Germany) or CAO (Netherlands) |
| **Budget** | ₹500/month hard cap |
| **Paper Target** | SLAS Technology — submit before Oct 2026 |
| **Working Title** | *Agentic Orchestration for Automated Chromatography: A Tiered AI Framework for Lab 4.0 Telemetry* |

---

## 2. Pipeline Architecture

```
RAW DATA (.cdf / .mzML / .D / .RAW)
        ↓
[n8n] — folder-watch trigger
        ↓
[T1] parse_cdf.py → structured JSON (netCDF4, xarray)
        ↓
[T2] baseline_als.py → ALS baseline correction (scipy / statsmodels)
        ↓
[T3] peak_detect.py → Peak detection → np.trapezoid area quantification
        ↓
[T4] gnn_deconv.py → GNN deconvolution (torch-geometric) ← DONE
        ↓
[T5] spectral_match.py → matchms spectral matching → compound ID
        ↓
[T6] data_store.py → Polars ETL + FAIR output (zarr + lamindb lineage) → SLAS manuscript
```

---

## 3. Pipeline Completion Status

| Layer | Status | Owner Agent |
| :--- | :--- | :--- |
| **.cdf / .mzML Ingestion** | **✓ DONE** | Claude Code |
| **Agilent & Varian Parsers** | **✓ DONE** | Claude Code |
| **ALS Baseline Correction** | **✓ DONE** | Claude Code |
| **Peak Detection + trapezoid** | **✓ DONE** | Claude Code |
| **n8n folder-watch trigger** | **✓ DONE** | Antigravity planned / CC executed |
| **matchms spectral matching** | **✓ DONE** | Claude Code |
| **GNN deconvolution (torch-geometric)** | **✓ DONE** | Claude Code |
| **zarr + lamindb FAIR layer** | **✓ DONE** | Claude Code |
| **SLAS manuscript draft** | **✓ POLISHED** | Antigravity |
| **PhD application materials** | **✓ PARTIAL** | Antigravity |

---

## 4. Dual-Agent System

Two agents. Strict separation. Zero overlap.

| Agent | Identity | Loop | Proxy |
| :--- | :--- | :--- | :--- |
| **Antigravity** (Gemini + Claude proxy) | Macro Brain | Loop 1 — Environment Validation | 8080 (14 Google OAuth accounts) |
| **Claude Code** (CCR-routed CLI) | Micro Engine | Loop 2 — Logic & Execution Audit | 8080 (Claude brains) / 3456 (T1/T2/T3 via CCR) |

**Handoff protocol:** Antigravity plans → Claude Code executes → Claude Code audits → Antigravity compiles output.

---

## 5. Brain Routing Table

### Claude Code's Brains (via CCR :3456)

| Tier | Model | Route | Cost | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **T1** | google/gemini-2.5-flash-lite | OpenRouter via Port 4000 | ~₹0.010/call | classify, label, json_reformat, dedup |
| **T2** | google/gemma-4-31b-it:free | OpenRouter via Port 4000 | ₹0 | summarize, enrich, compact_memory, research |
| **T3** | deepseek/deepseek-v4-flash | OpenRouter PAID via Port 4000 | ~₹0.011/call | standard coding, pipeline, GNN, scientific analysis |

**Full routing context:** See `AGENT_EXCHANGE/CHROMA_ROUTING_SETUP_V5.md`

### Antigravity's Token Pool

| Source | Route | Use |
| :--- | :--- | :--- |
| **Gemini accounts** | Direct (free) | Planning, Ghost Runtime, doc compilation |
| **Claude proxy** (14 accounts) | :8080 | Manuscript, literature, professor outreach |

**Routing rule:** cheapest competent brain first. Never route Opus/T3 if Sonnet/T2 sufficient.

---

## 6. Antigravity Token Pool

| Source | Quota | Use |
| :--- | :--- | :--- |
| **Gemini accounts** | Large free window | Macro planning, Ghost Runtime, doc compilation |
| **14-account Claude proxy** (:8080) | Free Claude tokens | Manuscript drafts, literature review, professor outreach |

**Rule:** Exhaust free pools before touching paid T2/T3 budget. Claude Code's T1/T2/T3 route through LiteLLM (:4000) -> OpenRouter, NOT through local compute. System runs zero local compute to prevent RAM swap freezes.

---

## 7. Double-Loop Validation

```
Loop 1 (Antigravity / Ghost Runtime)
  → Spawn ephemeral Linux container
  → Build + run script against .cdf / .mzML
  → Flag: compilation errors, library deprecations, import failures
  → Output: PASS / FAIL + error log → hand to Claude Code

Loop 2 (Claude Code / 6-Brain CLI)
  → Ingest Loop 1 output
  → Audit: ALS math, trapezoid logic, GNN output coherence
  → Verify: FAIR compliance, naming conventions
  → Output: PASS / FAIL + delta report → log to CLAUDE.md
```

Both loops must PASS before any production commit.

---

## 8. PhD Target Matrix

| Institution | Contract | Yr1 Gross | Grade Fit | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **UvA — Noel Group** | CAO | €3,059 | ✓ | P1 |
| **UvA — CAST Group** | CAO | €3,059 | ✓ | P1 |
| **TU Delft** | CAO | €2,770+ | ✓ | P1 |
| **Liverpool MIF CDT** | Stipend + waiver | ~£18k | ✓ (80%+) | P1 |
| **FZ Jülich — CADET** | TV-L E13 | ~€4,760 | ✓ | P1 |
| **SimTech Stuttgart** | TV-L E13 | €4,760 | ⚠ risk | P2 |
| **ETH AI Center** | Rate 5 | CHF 73k/yr | ⚠ competitive | P3 |
| **MSCA Doctoral Network** | Fellowship | variable | ✓ | P1 |

**Key gap:** 82% MSc meets NL/UK floors. German DAAD wants 85%+. Compensate via SLAS paper + CHROMA GitHub.

---

## 9. Critical Deadlines

```
Jun 2026             ──► SLAS Technology manuscript submitted
Jul - Aug 2026       ──► Screen rolling vacancies & initiate PI outreach (Start of 2027 Intake)
Sept 15, 2026        ──► EPFL EDCH Portal Submission Deadline
Oct 21, 2026         ──► DAAD Doctoral Fellowship Deadline (Germany)
Oct - Dec 2026       ──► Liverpool CDT, UvA, TU Delft applications open
Nov 2026             ──► MSCA Doctoral Network application deadline
Early 2027           ──► Start of 2027 PhD Intake program start
Fall 2027            ──► Fall of 2027 PhD Intake program start
```

---

## 10. Shared Lexicon (use exact terms)

**Chromatography:** Retention Time · mAU · Abundance · TIC · XIC · m/z · co-elution · Peak Deconvolution · ALS · SNIP · FAIR Data
**ML/AI:** GNN · GCN · GAT · message passing · SHAP · UMAP · scaffold split · ECFP
**System:** T1/T2/T3 · Ghost Runtime · Loop 1 · Loop 2 · Macro Brain · Micro Engine
**PhD:** TV-L E13 · CAO · MSCA · IMRAD · SLAS Technology · DFG · promovendi

---

## 11. Naming Conventions (both agents enforce)

```
Scripts:     scripts/parse_cdf.py | scripts/baseline_als.py | scripts/peak_detect.py | scripts/gnn_deconv.py
Outputs:     peak_summary_YYYYMMDD.xlsx | chroma_report_YYYYMMDD.json
Git commits: [T1] fix: ... | [T2] feat: ... | [LOOP1] val: ... | [LOOP2] audit: ...
Logs:        CLAUDE.md (execution log) | STATE.md (state map)
```

---

## 12. File Map (Exchange Folder & Project)

```
C:\chroma-agent-alpha\                    # Project root (git repo)
├── CLAUDE.md                             # Claude Code session context (v5)
├── STATE.md                              # GSD Persistent State Map (Achievements & Services)
├── litellm_config.yaml                   # LiteLLM router config
├── start_all_services.cmd                # Launcher for FastAPI, LiteLLM, n8n
├── venv\                                 # Python virtual environment
└── scripts\                              # Project source files
    ├── parse_cdf.py                      # T1: Ingestion & Custom Binary Parsers (Agilent/Varian)
    ├── baseline_als.py                   # T2: ALS baseline correction
    ├── peak_detect.py                    # T3: Peak detection + trapezoid integration
    ├── gnn_deconv.py                     # T4: GNN peak deconvolution node classifier
    ├── spectral_match.py                 # T5: matchms matching
    ├── sst_metrics.py                    # System Suitability Testing metrics
    ├── data_store.py                     # Zarr/LaminDB FAIR storage layer
    ├── pipeline_server.py                # FastAPI backend server
    ├── test_software_track.py            # Unit tests for binary parsers
    └── test_real_data_pipeline.py        # Integration test for full pipeline

C:\Users\yaduv\Desktop\AGENT_EXCHANGE\    # Dual-agent shared folder
├── CHROMA_MASTER_CONTEXT.md              # THIS FILE
├── ANTIGRAVITY.md                        # Antigravity session log
├── ANTIGRAVITY_CONTEXT.md                # Antigravity identity rules
├── CLAUDE_CODE_CONTEXT.md                # Claude Code identity rules
├── CLAUDE_EXCHANGE_INSTRUCTIONS.md       # Claude Code exchange folder guidelines
├── GEMINI_DEEP_MEMORY.md                 # Master Project Memory
├── CHROMA_ROUTING_SETUP_V5.md            # Routing table deep details
├── Antigravity_to_Claude\                # Tasks/specs from you → CC
├── Claude_to_Antigravity\                # Results/reports from CC → you
└── Operator_Inputs\                      # Manual overrides from Devendra Kataria
```

---

*Both agents read this file at session start. Neither agent acts on tasks outside their defined role. Conflicts resolved by escalating to operator (Devendra Kataria).*
*Operator: Devendra Kataria | Budget: Rs 500/month | PhD deadline: 2027 intakes (both Start of 2027 and Fall of 2027)*
