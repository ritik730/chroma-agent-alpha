# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: Manuscript Submission & PhD Candidacy Outreach
- **Status**: Active Drafting / Application Preparation
- **Active Task**: Reconstructed and refined the PhD application Academic CV (saved under `scratch/phd_cv_project/`). Based on the user's feedback, completely pivoted their positioning to an **"AI-Enabled Chemist & Workflow Orchestrator"**. The new CV accurately reflects their actual experience: it highlights their wet-lab chemistry degree and Teva GC training, focuses on **n8n workflow automation** and **AI agent direction/prompting** for code generation, and removes any claims of manual Python coding or synthesis tasks. Corrected and refined their role at Artistic Shots (**Technical & Digital Marketing Lead**) to reflect honest AI-driven digital marketing work (design, scriptwriting, SEO optimized posting), completely removing the ADGA section per user request.



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
