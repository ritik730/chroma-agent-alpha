# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: Ingestion & Deconvolution Robustness
- **Status**: Stable
- **Active Task**: Successfully copy-ingested and executed the full 4-stage pipeline on the Agilent `PE-2.D` and `PE-5.D` datasets from `AllPolymers_GCMS_RawData`. Fixed a `pyteomics` unitfloat attribute error in `parse_cdf.py` and implemented adaptive peak capping to recover minor peaks in high-dynamic-range runs. Validated results against MassHunter/NIST20 reference reports, achieving an 84-93% peak detection overlap.

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
  - **Tier 2 (Analyst)**: `deepseek/deepseek-v4-flash:free` and `meta-llama/llama-3.3-70b-instruct:free` (100% free endpoints)
  - **Tier 3 (Architect)**: `deepseek/deepseek-v4-flash` (cost-optimized paid endpoint)
- **Proxy Fallback Tiers**:
  - Direct local proxy (`claude-opus-4-6-thinking` and `gemini-3-flash-agent`) is utilized for free/low-cost fallback processing, avoiding external usage.
