# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: Technical Implementation & Pipeline Verification
- **Status**: Stable & Verified Bug-Free
- **Active Task**: Fixed critical Agilent `.ch` v817 parser bug (times converted from ms to minutes, intensities parsed as flat LE doubles from offset 6144). Added v817 unit test case in `test_software_track.py`. Verified ingestion, deconvolution, spectral matching, and Zarr storage/quantification via `test_real_data_pipeline.py`. Started all services (LiteLLM, n8n, Pipeline Server) in the background.
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
