# GSD Persistent State Map — CHROMA-AGENT-ALPHA

## Current Project Phase
- **Phase**: Manuscript Submission & PhD Candidacy Outreach
- **Status**: Active Drafting / Application Preparation
- **Active Task**: Fully executed **Track B (Academic Placement)** tasks. Migrated the revised Academic CV (`cv_draft.md` and LaTeX `cv.tex`) from scratch to the Desktop portfolio (`PhD Roadmap\05_Application_Templates\`). Drafted a tailored, high-impact **Statement of Purpose (SOP)** (`sop_draft.md`) using the candidate's core positioning narrative (*"I don't run the machines. I build the brains that analyze their telemetry."*). Compiled both markdown drafts to styled Word documents (`cv_draft.docx` and `sop_draft.docx`) containing native equation objects. Synchronized and pushed updated portfolio files to the repository main branch.



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
