# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: Technical Implementation & Pipeline Verification
- **Status**: Stable & Verified Bug-Free
- **Active Task**: Created an interactive Windows installer (`install.cmd` and `install.ps1`) to automate Python venv creation, `.env` generation, and n8n global checks. Configured folder junction linkage (`mklink /J`) between `raw_data` and raw instrument outputs. Placed `Start_All_Chroma_Services.cmd` and `Stop_All_Chroma_Services.cmd` shortcuts on the Desktop. Documented Python 3.10-3.12 compatibility constraints due to `numba`/`matchms` package builds failing on Python 3.13+. Imported Macro-to-Micro agent exchange context logs into the repository at `agent_exchange/`. Committed and pushed all upgrades to GitHub.
- **Future Modeler Integration**: Created dormant physical GC-MS chromatogram modeler blueprint in [gc_modeler.py](file:///C:/chroma-agent-alpha/scripts/gc_modeler.py) for future validation.



---

## Workspace Configuration
- **API Environment**:
  - `ANTIGRAVITY_BASE_URL`: `http://localhost:8080` (Claude local proxy)
  - `ANTIGRAVITY_MODEL`: `claude-opus-4-6-thinking` (Primary proxy model configured)
- **FastAPI Backend Server**:
  - URL: `http://localhost:8001`
  - Mode: Active (unbuffered logging `-u` enabled, process UID verified)
- **LiteLLM Config**:
  - URL: `http://localhost:4000`
  - Configuration: `C:\chroma-agent-alpha\litellm_config.yaml`
- **n8n Instance**:
  - URL: `http://localhost:5678`

---

## Budget Governance (₹500 / month limit)
- **OpenRouter Credit Limit**: Set to `$3.097 / monthly` (approx. ₹258/month), ensuring a strict buffer under the ₹500/month maximum limit.
- **Model Efficiency Tiers**:
  - **Tier 1 (Scout)**: `google/gemini-2.5-flash-lite` (highly cost-effective at $0.10/M input tokens)
  - **Tier 2 (Analyst)**: `google/gemma-4-31b-it:free` (100% free endpoint)
  - **Tier 3 (Architect)**: `deepseek/deepseek-v4-flash` (cost-optimized paid endpoint)
- **Proxy Fallback Tiers**:
  - Direct local proxy (`claude-opus-4-6-thinking` and `gemini-3-flash-agent`) is utilized for free/low-cost fallback processing, avoiding external usage.
