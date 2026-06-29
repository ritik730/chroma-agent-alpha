# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: UI Optimization & Pipeline Robustness
- **Status**: Stable & Verified
- **Active Task**:
  1. Increased file upload limit in `pipeline_server.py` to `300 MB`, enabling large instrument raw files (e.g. `131221ajcsa23_1.cdf`) to upload and list in the UI.
  2. Optimized model fallback configurations (`models_to_try`) to prioritize fast, high-availability flash models (`gemini-2.5-flash-lite`, `gemini-3-flash-agent`, `gemini-3.5-flash-low`) and shortened individual timeouts to `20s`, preventing pipeline hangs during rate limits.
  3. Fixed a UI glitch in `dashboard.html` by clearing the peaks table body and showing a loading indicator during run changes.
  4. Successfully ran AI enrichment for `test_lavender_mix` (106 peaks) through the local proxy, resolving peak 1256 from `unidentified` to `Eucalyptol`.

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
- **Antigravity Claude Proxy**:
  - URL: `http://localhost:8080`

---

## Budget Governance (₹500 / month limit)
- **OpenRouter Credit Limit**: Set to `$3.097 / monthly` (approx. ₹258/month), ensuring a strict buffer under the ₹500/month maximum limit.
- **Model Efficiency Tiers**:
  - **Tier 1 (Scout)**: `google/gemini-2.5-flash-lite` (highly cost-effective at $0.10/M input tokens)
  - **Tier 2 (Analyst)**: `google/gemma-4-31b-it:free` (100% free endpoint)
  - **Tier 3 (Architect)**: `deepseek/deepseek-v4-flash` (cost-optimized paid endpoint)
- **Proxy Fallback Tiers**:
  - Direct local proxy (`claude-opus-4-6-thinking` and `gemini-3-flash-agent`) is utilized for free/low-cost fallback processing, avoiding external usage.
