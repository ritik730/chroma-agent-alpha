# CHROMA-AGENT-ALPHA // SESSION CONTEXT v5
# Auto-read by Claude Code at session start. Do not delete.
# Updated: 2026-05-19 | Source: CHROMA-AGENT-ALPHA-CONTEXT.md v3.0

## IDENTITY
User: Devendra Kataria | MSc Chemistry 82% | 2027 PhD Target
Narrative: "I don't run the machines. I build the brains that analyze their telemetry."
Machine: Dell Latitude 5300 | i5-8th Gen | 16GB RAM | No GPU | Windows 11
No local LLM models. Zero local compute. All inference is cloud via OpenRouter.

## PIPELINE
.cdf/.mzML/.D → netCDF4/xarray → ALS baseline → scipy.find_peaks → np.trapz → GNN deconv → JSON → n8n → FAIR store
*Future Upgrade (Dormant Blueprint): Stage -1 Modeler (SMILES → GNN-QSPR → Poiseuille/Clausius-Clapeyron Solver) in [gc_modeler.py](file:///C:/chroma-agent-alpha/scripts/gc_modeler.py)*

## CODING RULES (enforced every script)
1. All functions: docstring with chemical context
2. Integration: always validated with np.trapz()
3. Baseline (ALS) always runs BEFORE peak detection
4. Commit format: feat(ingestion): parse .cdf retention_time array
5. Output JSON: {sample_id, retention_time, peak_area_mAU, baseline_corrected: bool}

## THREE-TIER ROUTER (LiteLLM proxy on port 4000)

| Tier | Model | Purpose | Cost |
|------|-------|---------|------|
| T1 | google/gemini-2.5-flash-lite | classify, label, json_reformat, dedup | ~₹0.010/call |
| T2 | google/gemma-4-31b-it:free | summarize, enrich, compact_memory, research_synthesis | ₹0 |
| T3 | deepseek/deepseek-v4-flash | all coding, pipeline, GNN, scientific analysis | ~₹0.011/call |

Budget ceiling: ≤₹500/month | Projected actual: ~₹52/month OpenRouter

### Mid-session model switch
```
/model claude-t1    # T1: Gemini Flash Lite (scout/classify)
/model claude-t2    # T2: Gemma 4 31B free (analysis)
/model claude-t3    # T3: DeepSeek V4 Flash paid (coding/science)
```

### ROUTING RULES
- Default session model: claude-t2 (free, plenty of context)
- T1 for short mechanical tasks only (classify, label, reformat)
- T3 for all code writing, debugging, GNN, pipeline decisions
- Antigravity (Claude via proxy :8080): MANUAL ONLY for manuscript/PhD — NEVER auto-routed

## ANTIGRAVITY (SEPARATE — DO NOT CONFUSE WITH T1/T2/T3)
- Claude Sonnet/Opus via proxy at localhost:8080
- Used exclusively for: manuscript prose, PhD letters, identity_audit
- Weekly token budget enforced via memory/antigravity-budget.json
- Commands: claude-opus / claude-sonnet (separate PowerShell aliases)

## RAM BUDGET (no Ollama — zero local LLM)
| Process | RAM |
|---------|-----|
| Antigravity (VS Code + Gemini Pro) | ~2-3GB |
| Claude Code + LiteLLM (:4000) | ~500MB |
| Windows + background | ~3-4GB |
| **Available for pipeline/data** | **~8-10GB** |

## DUAL-AGENT ARCHITECTURE
| Layer | Tool | Model | Role |
|-------|------|-------|------|
| Macro coordinator | Antigravity | Gemini Pro (free) | Structure, indexing, docs |
| Execution engine | Claude Code | T1/T2/T3 via LiteLLM | File edits, bash, code |

## LEXICON
RT=Retention Time | mAU=milli-Absorbance Units | ALS=Asymmetric Least Squares
FAIR=Findable Accessible Interoperable Reusable | AIA/NetCDF=.cdf format
Trapz=A ≈ Σ(y_{i-1}+y_i)/2 × (x_i-x_{i-1})

## LAUNCH
cd C:\chroma-agent-alpha
litellm-start          # starts LiteLLM proxy on :4000
claude-t2              # launch Claude Code on T2 (default)

## PhD TARGETS 2027
Pirok Group (UvA NL, CAO) | Noel Group (UvA NL, CAO) |
CADET/von Lieres (Jülich DE, E13) | FZJ HDS-LEE (AI in Earth Sci, 2026D-0451) |
Radboud SDL (NL, CAO) | SimTech (Stuttgart DE, E13) | TU Delft AI4Science (NL, CAO)
