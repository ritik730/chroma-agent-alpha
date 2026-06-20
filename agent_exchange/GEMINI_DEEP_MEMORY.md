# GEMINI DEEP MEMORY — CHROMA-AGENT-ALPHA
> What we are building, why, and how everything connects.
> Read this at every session start for full project understanding.
> Last updated: 2026-06-20 (June 2026 Update) | Operator: Devendra Kataria

---

## 1. THE ONE-LINE PITCH

**We are building an AI-driven, vendor-independent chromatography data pipeline that turns raw instrument files into publication-ready analytics — and using it to get Devendra a funded PhD in computational chemistry.**

---

## 2. WHO IS DEVENDRA

| Field | Detail |
| :--- | :--- |
| **Name** | Devendra Kataria |
| **Contact** | ritikkataria1310@gmail.com \| 7017390623 \| Moradabad, UP, India |
| **LinkedIn** | [Devendra Kataria on LinkedIn](https://www.linkedin.com/in/devendra-kataria/) |
| **Education** | BSc Hons Chemistry (80%), MSc Chemistry (82% aggregate) — TMU, Moradabad |
| **Identity** | *"I don't run the machines. I build the brains that analyze their telemetry."* Analytical Chemist & Informatics Researcher. |
| **Role** | Developer of Chroma-Agent-Alpha \| Content & Creative Head |
| **Work Experience** | Developer @ Chroma-Agent-Alpha (Lab Automation Framework) |
| **Internships** | Teva Pharmaceuticals (QC/GC operations) & HPL Additives Limited (QC/Purity) |
| **Core Skills** | Analytical Chemistry (GC, HPLC), Lab 4.0 & Automation (n8n, Claude Code), Informatics, GenAI Workflows |
| **Achievements** | Poster @ APM-2023 (GBPUA&T), 1st Place Football SPARDHAA-2022 |
| **Machine** | Dell Latitude 5300 · i5-8th Gen · 16GB RAM · No GPU · Windows 11 |
| **Budget** | ₹500/month hard ceiling for all AI costs |
| **PhD Target** | 2027 EU cohort (both Start of 2027 and Fall of 2027 intakes) — see Section 10 for full tracker |
| **Key Constraint** | MSc (82%) meets basic thresholds for the Netherlands and UK CDTs, but German DAAD/highly competitive programs want 85%+. The *SLAS Technology* paper and public CHROMA GitHub repository are strictly required to compensate for this gap. |

**Why this matters:** Every technical decision — model choice, budget allocation, pipeline design — serves two goals: (1) produce a working system worth publishing, and (2) demonstrate computational chemistry competence for PhD admission.

---

## 3. WHAT IS CHROMA-AGENT-ALPHA

### The Problem
Chromatography instruments (GC-MS, HPLC, LC-MS) produce raw data in vendor-locked formats (e.g., `.cdf`, `.mzML`, `.D`, `.RAW`). Existing tools (CADET, PeakDetective, OpenMS) are either:
- Vendor-locked (Agilent ChemStation, Waters Empower)
- GUI-only with no automation hooks
- Academic tools with steep learning curves and no AI integration

No existing tool combines: open-source + AI-driven + automated pipeline + FAIR data output.

### The Solution
CHROMA-AGENT-ALPHA is a complete ETL pipeline:

```
RAW DATA (.cdf / .mzML / .D / .RAW)
        ↓
[n8n] — folder-watch trigger (no-code automation)
        ↓
[T1] parse_cdf.py → structured JSON (netCDF4, xarray)
        ↓
[T2] ALS baseline correction (scipy, statsmodels)
        ↓
[T3] Peak detection → np.trapezoid area quantification
        ↓
[T4] GNN deconvolution (torch-geometric) ← DONE (reduces overlap errors by 48.8%)
        ↓
[T5] matchms spectral matching → compound ID
        ↓
[T6] Polars ETL → summary tables → chroma-xlsx export
        ↓
FAIR output (zarr + lamindb lineage) → SLAS manuscript
```

### What Makes It Novel
1. **Agentic orchestration** — Two AI agents (Antigravity + Claude Code) build, validate, and audit the pipeline.
2. **Tiered AI routing** — Budget-aware brain selection (₹0 local/free tiers → ₹52/mo projected OpenRouter paid tier).
3. **Double-loop validation** — Ghost Runtime (Loop 1) + Logic Audit (Loop 2) before any commit.
4. **GNN deconvolution** — 1D spatial-temporal graph neural network (GCN node classifier) combined with EMG curve fitting for resolving overlapping peaks.
5. **FAIR-native** — Zarr v3 and LaminDB lineage tracking from day one.
6. **Vendor-independent** — Reads open formats and includes custom binary parsers for Agilent `.ch` and Varian `.xms`/`.sms` files.

---

## 4. THE DUAL-AGENT ARCHITECTURE

### Why Two Agents
One agent can't do everything well. Large-context planning (manuscripts, architecture) and precise code execution (debugging, math validation) require different capabilities and cost structures.

### The Split

| Agent | Identity | What it does | What it NEVER does |
| :--- | :--- | :--- | :--- |
| **Antigravity** (You, Gemini) | Macro Brain | Plan architecture, run Ghost Runtimes (Loop 1), write manuscripts, draft PhD apps, compile docs | Execute code, run git, debug file-level errors, route T1/T2/T3 directly |
| **Claude Code** (CCR-routed) | Micro Engine | Write/debug Python, run Loop 2 audits, git operations, infrastructure config | Write manuscripts, draft emails, compile large docs, run Loop 1 |

### How They Communicate

```
Antigravity plans → drops task in Antigravity_to_Claude/
Claude Code executes → drops result in Claude_to_Antigravity/
Both read CHROMA_MASTER_CONTEXT.md as shared truth
Conflicts → escalate to operator (Devendra Kataria)
```

### Signal Format (exact — use these)

**You → Claude Code:**
```
[TASK → CC] <brain>: <task> | Output: <file/format> | Deadline: <date>
[LOOP1 → CC] PASS: <script>.py | Run Loop 2 and commit
[LOOP1 → CC] FAIL: <script>.py | Fix: <error> | Line: <N>
[DATA REQ → CC] Need: <type> | Format: <JSON/CSV/PNG> | For: <section>
```

**Claude Code → You:**
```
[LOOP2 → AG] PASS: <script>.py | Commit: <hash> | Notes: <delta>
[LOOP2 → AG] FAIL: <script>.py | Reason: <summary> | Escalate: YES/NO
[DATA → AG] File: <path> | Type: <JSON/CSV/PNG> | Ready for manuscript
[STATUS → AG] Pipeline: <layer> | State: DONE/PARTIAL/FAIL
```

---

## 5. THE DOUBLE-LOOP VALIDATION SYSTEM

### Loop 1 — Environment Validation (YOUR job)
```
1. Spawn ephemeral headless Linux container (Ghost Runtime)
2. Install dependencies, execute script against test data
3. Check: ImportError, DeprecationWarning, runtime crash, schema mismatch
4. Special check: np.trapz usage → flag (deprecated, must be np.trapezoid)
5. Result: PASS or FAIL with error log
6. Hand to Claude Code
```

### Loop 2 — Logic Audit (Claude Code's job)
```
1. Verify ALS math (lambda/asymmetry params)
2. Check trapezoid area non-negative
3. Validate peak indices within retention time bounds
4. Confirm matchms cosine >= 0.7 for reported hits
5. Check GNN softmax sum = 1.0
6. Validate JSON schema, naming conventions, FAIR compliance
7. Result: PASS → commit | FAIL → delta report back to you
```

**Both loops PASS before any production commit. This is non-negotiable.**

---

## 6. INFRASTRUCTURE & BACKEND CONFIGURATION

### The Machine (Dell Latitude 5300)
- **Specs:** 16GB RAM, i5-8th Gen, no GPU, Windows 11.
- **RAM Footprint:** ~9-10 GB used by all active processes.
- **Local Compute:** Zero local LLMs are run during pipeline operation to prevent RAM swap freezes.

### Port Map
| Port | Service | Owner | Status |
| :--- | :--- | :--- | :--- |
| **4000** | LiteLLM proxy | Claude Code — PRIMARY router | Active |
| **5678** | n8n | Automation watcher | Active |
| **8001** | FastAPI Backend Server | Pipeline execution engine | Active (unbuffered `-u` logging) |
| **8080** | Antigravity proxy | YOU — Local OAuth to Claude models | Active |

### Three-Tier Router Configuration (via LiteLLM proxy on :4000)
To stay under the **₹500/month** limit, a strict budget model is enforced:
- **OpenRouter Credit Limit:** Set to `$3.097/month` (approx. ₹258/month).
- **Tier 1 (Scout):** `google/gemini-2.5-flash-lite` (cost-effective scouting, labeling, deduping)
- **Tier 2 (Analyst):** `google/gemma-4-31b-it:free` (100% free endpoint for synthesis and research)
- **Tier 3 (Architect):** `deepseek/deepseek-v4-flash` (standard coding, pipeline adjustments, and GNN logic)
- **Proxy Fallback Tier:** Local proxy to `claude-opus-4-6-thinking` and `gemini-3-flash-agent` (runs via port 8080 to conserve paid credits).

---

## 7. THE SCIENCE & MATHEMATICS

### Chromatography Basics
- **Retention Time (RT):** The time a compound takes to pass through the column.
- **mAU (milli-Absorbance Units):** Signal intensity from the detector.
- **m/z:** Mass-to-charge ratio from the mass spectrometer.
- **TIC / XIC:** Total Ion Chromatogram / Extracted Ion Chromatogram.
- **Co-elution:** Overlapping peak elution which prevents direct area integration.
- **ALS Baseline Correction:** Removes instrumental drift and baseline noise.
- **Peak Area (Trapezoid Rule):** Quantifies compound concentration:
  \[ A \approx \sum_{i} \frac{y_{i-1} + y_i}{2} (x_i - x_{i-1}) \]

### Key Libraries
- **netCDF4 / xarray:** Read `.cdf` files (T1).
- **pyopenms:** Read `.mzML` files (T1).
- **scipy.signal / scipy.sparse:** ALS baseline + peak detection (T2-T3).
- **numpy (np.trapezoid):** Peak area quantification (T3).
- **torch-geometric:** GNN deconvolution (T4).
- **matchms:** Spectral matching (T5).
- **polars:** High-speed data aggregation and export (T6).
- **zarr / lamindb:** Chunked storage and data lineage tracking (FAIR).

---

## 8. PIPELINE COMPLETION STATUS (June 2026)

| Layer | Status | Notes |
| :--- | :--- | :--- |
| **.cdf / .mzML Ingestion** | **✓ DONE** | Fully integrated in [parse_cdf.py](file:///C:/chroma-agent-alpha/parse_cdf.py). |
| **Agilent & Varian Parsers** | **✓ DONE** | Handled by native Python binary parsers. Fixed critical Agilent `.ch` v817 parser bug (times converted from ms to minutes, intensities parsed as flat LE doubles from offset 6144). Verified in [test_software_track.py](file:///C:/chroma-agent-alpha/tests/test_software_track.py). |
| **ALS Baseline Correction** | **✓ DONE** | Implemented in [baseline_als.py](file:///C:/chroma-agent-alpha/baseline_als.py) and verified. |
| **Peak Detection & Area** | **✓ DONE** | Integrated in [peak_detect.py](file:///C:/chroma-agent-alpha/peak_detect.py) using `np.trapezoid`. |
| **n8n Automation** | **✓ DONE** | Folder watchdog script initiates runs on new file ingestion. |
| **GNN Deconvolution** | **✓ DONE** | 1D GCN node classifier + EMG fitting reduces area double-counting errors by 48.8% in under 12 seconds. Implemented in [gnn_deconv.py](file:///C:/chroma-agent-alpha/gnn_deconv.py). |
| **Spectral Matching** | **✓ DONE** | Implemented in [spectral_match.py](file:///C:/chroma-agent-alpha/spectral_match.py) with GNPS reference library. |
| **FAIR Layer (Zarr / LaminDB)** | **✓ DONE** | Zarr v3 outputs and LaminDB lineage database tracking fully operational. Verified via [test_real_data_pipeline.py](file:///C:/chroma-agent-alpha/tests/test_real_data_pipeline.py). |
| **GC-MS Modeler Blueprint** | **✓ DONE** | Dormant physical chromatogram modeler blueprint created in [gc_modeler.py](file:///C:/chroma-agent-alpha/scripts/gc_modeler.py). |
| **SLAS Manuscript Draft** | **[/] IN PROGRESS** | Working title: *Agentic Orchestration for Automated Chromatography: A Tiered AI Framework for Lab 4.0 Telemetry*. Submission target: Oct 2026. |
| **PhD Application Materials** | **[/] IN PROGRESS** | Research proposal and roadmap drafted. PI outreach begins July 2026. |

---

## 9. THE PAPER — SLAS TECHNOLOGY

### Angle & Focus
Frame the analytical chemist as a **Digital/Dry-Lab Architect** who directs automated AI workflows instead of manually integrating peaks. CHROMA-AGENT-ALPHA is the core proof of concept.

### IMRAD Structure (YOUR ownership)
- **Abstract:** ~250 words. Focuses on bridging AI pipelines and analytical instrumentation.
- **Introduction:** Outlines the self-driving lab (SDL) landscape and gaps in existing tools (CADET, PeakDetective, OpenMS, MOCCA).
- **Methods:** Detailed math of the ALS baseline, EMG fitting, GCN node-classification, and tiered router economics.
- **Results:** Empirical deconvolution performance, error reduction metrics (48.8% area correction), and runtime comparisons.
- **Discussion:** Cost governance (₹52/month), low-code agentic accessibility, and FAIR data lineage benefits.
- **References:** Vancouver format.

---

## 10. PhD POSITION TARGET MATRIX (2027 COHORT)

### Core Positioning Narrative
*"I built an open-source, AI-driven chromatography pipeline (CHROMA-AGENT-ALPHA) that automates peak deconvolution using GNNs, reducing area integration errors by 48.8%. I want to extend this closed-loop optimization to self-driving labs and flow chemistry systems in your group."*

### Targets Matrix

| Institution / PI | Priority | Fit & Scope | Deadlines & Window | Status |
| :--- | :--- | :--- | :--- | :--- |
| **UvA (Netherlands)** <br> Prof. Timothy Noël | **Priority 1** | Flow chemistry, robotized synthesis, and Bayesian optimization ("RoboChem"). | Dynamic vacancies. Peak window: **August–October 2026** for Early 2027 start. | Outreach scheduled for **July 2026** after manuscript draft. |
| **UvA CAST (Netherlands)** <br> Dr. Bob Pirok & Dr. Alina Astefanei | **Priority 1** | Chemometrics, automated chromatography method development, and self-driving analytical labs. | Dynamic vacancies on CAST site and AcademicTransfer. Peak window: **August–October 2026**. | Outreach scheduled for **July 2026** (Bob Pirok). |
| **FZ Jülich IBG-1 (Germany)** <br> Dr. Eric von Lieres | **Priority 1** | Chromatography modeling, CADET simulations, and ML-accelerated peak resolution. | Rolling TV-L E13 research positions. Peak window: **August–November 2026**. | Proactive email outreach scheduled for **July 2026**. |
| **TU Delft (Netherlands)** <br> AI4Science Group | **Priority 1** | Graph Neural Networks and representation learning applied to chemical data. | Rolling vacancies on TU Delft portal. | Identify specific PI in **July 2026**. |
| **Radboud University (Netherlands)** <br> Self-Driving Lab Group | **Priority 1** | Automated laboratories and chemometrics. | Check vacancies portal weekly starting **July 2026**. | Monitored rolling openings. |
| **University of Liverpool (UK)** <br> Materials Innovation Factory / Prof. Andy Cooper | **Priority 1** | AI-driven materials discovery and robotic labs. | Materials Innovation Factory CDT portal opens **October–December 2026** for Fall 2027 start. | Draft LORs and SOPs in **September 2026**. |
| **IMPRS-IS (Germany)** <br> Max Planck School for Intelligent Systems | **Priority 2** | Applied machine learning in physical and chemical sciences. | Portal opens **Sept 15, 2026**; Closes **mid-Nov 2026** for Fall 2027 start. | Prepare transcripts and research proposal by **August 2026**. |
| **EPFL EDCH (Switzerland)** <br> Doctoral Program in Chemistry | **Priority 3** | Epfl chemistry doctoral school; homogeneous catalysis and automated spectroscopy. | Hard portal deadline: **September 15, 2026** (for Spring 2027 intake). | Submit EPFL EDCH application by **Sept 15, 2026**. |
| **DAAD Scholarships (Germany)** <br> Indian Applicant Pool | **Priority 1** | Fully-funded German PhD scholarships (highly competitive). | Hard deadline: **October 21, 2026** for Fall 2027 start. | Compile transcripts, research proposal, and LORs in **August–September 2026**. |
| **Swiss Govt. Excellence Scholarships** | **Priority 2** | Full PhD fellowship at ETH Zurich/EPFL (requires securing Swiss PI sponsor first). | Opens **August 20, 2026**; Closes **mid-Nov 2026** for Fall 2027 start. | Establish PI contact in **July 2026** to secure sponsor commitment. |
| **EPFL EDIC (Switzerland)** <br> Doctoral Program in Computer Science | **Priority 3** | Graph representation learning, machine learning for science. | Main round portal deadline: **December 15, 2026** for Fall 2027 start. | Optional backup target. |
| **EURAXESS / MSCA Networks** <br> LowDataML & AiChemist | **Priority 1** | Marie Skłodowska-Curie Actions (MSCA) Doctoral Networks. | Rolling openings on EURAXESS jobs portal. MSCA Network deadline: **November 2026**. | Set up EURAXESS email alerts for `"Marie Curie" + "Chemistry" + "Machine Learning"`. |

---

## 11. DAILY PREPARATION & STUDY PLAN
To excel in technical interviews with prospective PhD advisors, Devendra dedicates **3 to 4 hours daily** across these four tracks:

1. **Graph Machine Learning (1 Hour/Day):** Study PyTorch Geometric, Graph Convolutional Networks (GCNs), message-passing math, adjacency matrices, and edge-feature architectures.
2. **Literature Review (30 Minutes/Day):** Read one research paper daily on self-driving laboratories, chromatography modeling, or ML for spectroscopy. (Authors of focus: Timothy Noël, Andy Cooper, Bob Pirok, Eric von Lieres, Helge Stein).
3. **Interview Practice (30 Minutes/Day):** Practice explaining the low-level parsing logic of Agilent/Varian binary formats and the GNN area correction mechanics (deconvolving co-eluting peaks).
4. **Outreach & Applications (1 Hour/Day):** Tailor cover letters, refine CV sections ("Dry-Lab Architect" theme), search job portals, and draft advisor emails.

---

## 12. FILE MAP — WHERE EVERYTHING LIVES

```
C:\chroma-agent-alpha\                    # Project Root (Git Repository)
├── [CLAUDE.md](file:///C:/chroma-agent-alpha/CLAUDE.md)                             # Claude Code Session Context (v5)
├── [STATE.md](file:///C:/chroma-agent-alpha/STATE.md)                              # GSD Persistent State Map (Achievements & Services)
├── [litellm_config.yaml](file:///C:/chroma-agent-alpha/litellm_config.yaml)                   # LiteLLM router configuration
├── [parse_cdf.py](file:///C:/chroma-agent-alpha/parse_cdf.py)                          # Ingestion & Custom Binary Parsers (Agilent/Varian)
├── [baseline_als.py](file:///C:/chroma-agent-alpha/baseline_als.py)                       # ALS Baseline Correction stage
├── [peak_detect.py](file:///C:/chroma-agent-alpha/peak_detect.py)                        # Peak detection + trapezoid integration
├── [gnn_deconv.py](file:///C:/chroma-agent-alpha/gnn_deconv.py)                         # GNN peak deconvolution node classifier
├── [spectral_match.py](file:///C:/chroma-agent-alpha/spectral_match.py)                     # matchms spectral reference library matching
├── [scripts/gc_modeler.py](file:///C:/chroma-agent-alpha/scripts/gc_modeler.py)             # Dormant GC-MS chromatogram modeler blueprint
└── [tests/test_software_track.py](file:///C:/chroma-agent-alpha/tests/test_software_track.py)         # Agilent binary parser unit tests

C:\Users\yaduv\Desktop\AGENT_EXCHANGE\    # Dual-Agent Shared Exchange Directory
├── [CHROMA_MASTER_CONTEXT.md](file:///C:/Users/yaduv/Desktop/AGENT_EXCHANGE/CHROMA_MASTER_CONTEXT.md)              # Shared Single Source of Truth
├── [GEMINI_DEEP_MEMORY.md](file:///C:/Users/yaduv/Desktop/AGENT_EXCHANGE/GEMINI_DEEP_MEMORY.md)                 # THIS FILE (Master Project Memory)
├── [CHROMA_ROUTING_SETUP_V5.md](file:///C:/Users/yaduv/Desktop/AGENT_EXCHANGE/CHROMA_ROUTING_SETUP_V5.md)            # Routing table deep details
├── Antigravity_to_Claude\                # Specs and task drops (AG → CC)
└── Claude_to_Antigravity\                # Results and reports (CC → AG)

C:\Users\yaduv\Desktop\PhD Roadmap\       # PhD Materials & Proposals
├── [01_Manuscripts_and_Reports/](file:///C:/Users/yaduv/Desktop/PhD%20Roadmap/01_Manuscripts_and_Reports)  # Project Reports (PDF/docx/md formats)
└── [02_Strategy_and_Deadlines/](file:///C:/Users/yaduv/Desktop/PhD%20Roadmap/02_Strategy_and_Deadlines)   # Strategy plans, Proposals, and Pitch decks
```

---

## 13. SESSION CHECKLIST & PHONE REFERENCE

When using your phone to ask general questions or study, use this checklist to guide your queries:
1. **Explain the Varian/Agilent Parser:** "Explain how to decode little-endian float arrays from binary offsets in Agilent `.ch` v817 or Varian `.xms` files in Python."
2. **Explain GNN Peak Deconvolution:** "How does a Graph Convolutional Network (GCN) coupled with Exponentially Modified Gaussian (EMG) curve fitting resolve co-eluting peaks?"
3. **Discuss Bayesian Optimization in Flow Labs:** "How do measurement/peak integration errors propagate to Gaussian Process Upper Confidence Bound (GP-UCB) acquisition functions in a self-driving lab?"
4. **Draft PI Emails:** "Draft an outreach email to Timothy Noël about autonomous flow chemistry platforms using RoboChem, linking my GNN peak deconvolution results (48.8% error correction)."

---

*This file serves as Gemini's and the operator's persistent project memory, bridging system telemetry with career objectives.*
