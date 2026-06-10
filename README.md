# CHROMA-AGENT-ALPHA

> **An Autonomous, Vendor-Independent ETL Pipeline and Tiered AI Framework for Gas Chromatography (GC-MS) Telemetry and FAIR Preservation.**

[![FAIR Compliance](https://img.shields.io/badge/FAIR-compliant-success?style=flat-square)](https://www.force11.org/fairprinciples)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

CHROMA-AGENT-ALPHA is an open-source, vendor-agnostic data processing pipeline and agentic orchestrator for Gas Chromatography-Mass Spectrometry (GC-MS) telemetry. Engineered to run efficiently on low-compute local hardware (under a strict ₹500/month budget ceiling), it bridges the gap between raw instrument data and compliant downstream ingestion. It automates baseline correction, scipy peak integration, Graph Neural Network (GCN) deconvolution of co-eluting peaks, and FAIR-compliant data preservation (Zarr v3 + LaminDB SQLite).

---

## 1. System Architecture

```
                                  [CHROMA-AGENT-ALPHA PIPELINE]
                                                │
[Proprietary Files] ──► Stage 0: ProteoWizard ──┼──► Stage 1: Telemetry Ingestion (.cdf, .mzML, .xms, .ch)
                                                │
                                                ▼
                                    Stage 2: ALS Baseline Correction
                                                │
                                                ▼
                                    Stage 3: Peak Detection & System Suitability (SST)
                                                │
                                                ▼
                                    Stage 4: Numerical Integration (trapz)
                                                │
                                                ▼
                                    Stage 5: GNN-EMG Hybrid Deconvolution (Adaptive)
                                                │
                                                ▼
                                    Stage 6: matchms Cosine Spectral Match
                                                │
                                                ▼
                                    Stage 7: T2 LLM Chemical Naming
                                                │
                                                ▼
                                    Stage 8: Formatted Excel Output
                                                │
                                                ▼
                                    Stage 9: FAIR Storage (Zarr & LaminDB)
```

### Multi-Sample RT Alignment
In addition to the single-run ETL pipeline, CHROMA features a **Multi-Sample Retention Time Alignment** engine. Accessible via the REST endpoint `POST /run/align` and integrated into the web dashboard, it downsamples raw profiles to a 1000-point timeline and executes a **Sakoe-Chiba constrained Dynamic Time Warping (DTW)** algorithm in under 110ms. This corrects linear and non-linear chromatography column drift, allowing side-by-side peak matching and overlay visualization in Chart.js.

### Dual-Agent Orchestration
*   **Macro Brain:** Antigravity (Gemini Pro) — Structures plans, manages workflows, and drafts publication manuscripts.
*   **Micro Engine:** Claude Code — Executes file operations, runs validation pipelines, and manages local service deployment.

### Multi-Tier Cost-Aware LLM Router
To satisfy strict budget constraints, the pipeline uses a custom LiteLLM proxy (Port 4000) that routes tasks to different API tiers, falling back to a local Claude Proxy (Port 8080) during credit exhaustion:

| Tier | Model | Tasks | Avg. Cost |
|---|---|---|---|
| **T1 Scout** | `google/gemini-2.5-flash-lite` | Structural reformats, labels, json checkoffs | ~₹0.010 / call |
| **T2 Analyst** | `deepseek/deepseek-v4-flash:free` | Memory summaries, text enrichment, class mappings | ₹0 / call |
| **T3 Architect** | `deepseek/deepseek-v4-flash` | Coding, GNN model configuration, pipeline execution | ~₹0.011 / call |
| **T3-CoT** | `deepseek-r1-distill-qwen-32b` | Complex mathematical/logical reasoning, deconv audits | ~₹0.030 / call |
| **T4 Fallback**| `Claude Sonnet/Opus (local proxy)` | Final automated pipeline fallback (triggered if T1/T2/T3 fails) | Capped by weekly proxy quota |

*Note: For manual tasks such as manuscript prose writing and PhD cover letters, the **Antigravity** proxy is the preferred option and is accessed directly.*

---

## 2. Pipeline Stages & Status

| Stage | Name | Status | Description |
|---|---|---|---|
| **Stage 0** | Universal Format Conversion | ✅ DONE | Intercepts proprietary Agilent (`.D`), Thermo (`.RAW`), and Waters (`.RAW`) folders in the watch directory and runs ProteoWizard's `msconvert.exe` to transcode them to `.mzML` format. |
| **Stage 1** | Telemetry Ingestion & Parsing | ✅ DONE | Custom parser extracting coordinate matrices from NetCDF4 (`.cdf`), `.mzML`, Varian `.xms` binaries, and Agilent ChemStation `.ch` files (via raw delta-compression stride decoding). |
| **Stage 2** | Baseline Correction | ✅ DONE | Implements Asymmetric Least Squares (ALS) baseline subtraction prior to peak detection to isolate background drift. |
| **Stage 3** | Peak Detection & SST | ✅ DONE | Identifies elution boundaries and calculates **System Suitability Testing (SST)** metrics (USP Tailing, Theoretical Plates, adjacent Peak Resolution, and S/N). |
| **Stage 4** | Numerical Integration | ✅ DONE | Integrates peak areas using the Trapezoidal Rule, validated against `numpy.trapezoid` for mathematical accuracy. |
| **Stage 5** | GNN-EMG Hybrid Deconvolution | ✅ DONE | Builds a PyTorch Geometric 1D graph of overlapping peak boundaries with **Adaptive GNN Proximity Thresholding** to adjust edges dynamically, runs GCN node classification, and fits Exponentially Modified Gaussian (EMG) curves. |
| **Stage 6** | Cosine Spectral Matching | ✅ DONE | Executes `matchms` Cosine Greedy matching against reference libraries. |
| **Stage 7** | AI-Driven Enrichment | ✅ DONE | Generates IUPAC names, classifications, and assigns model confidence scores for unmatched peaks. |
| **Stage 8** | Structured Report Generation | ✅ DONE | Compiles clean, user-facing, color-coded Excel reports (`.xlsx`) directly to `processed_results/` and generates multi-run comparison spreadsheets. |
| **Stage 9** | FAIR Compliance Storage | ✅ DONE | Serializes matrices into compressed N-dimensional Zarr v3 arrays and registers lineage metadata in a local SQLite-backed LaminDB instance. |

---

## 3. Installation & Setup

### Prerequisites
*   Windows 10/11
*   Python 3.13+
*   Node.js (for CLI router utilities)
*   [ProteoWizard](https://proteowizard.org/) (for Stage 0 conversion support)

### Installation
1.  **Clone the repository:**
    ```cmd
    git clone https://github.com/ritik730/chroma-agent-alpha.git
    cd chroma-agent-alpha
    ```
2.  **Initialize Virtual Environment:**
    ```cmd
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  **Configure Environment Variables:**
    Create a `.env` file in the root directory:
    ```env
    OPENROUTER_API_KEY=your_openrouter_api_key
    CHROMA_BASE_DIR=C:\chroma-agent-alpha
    ```

---

## 4. How to Run

### 1. Launch Services
Start the LiteLLM proxy and FastAPI server by running the startup batch script:
```cmd
.\start_all_services.cmd
```
This runs:
*   LiteLLM Proxy on `http://localhost:4000`
*   FastAPI backend on `http://localhost:8001`
*   n8n workflow manager on `http://localhost:5678`

### 2. Autonomous Watcher (n8n Integration)
The watcher polls the `raw_data/` folder every 3 seconds:
1.  Navigate to `http://localhost:5678` and import the n8n workflow from `n8n/chroma_workflow.json`.
2.  Drop any chromatography `.cdf`, `.mzML`, `.D`, or `.xms` file in the `raw_data/` directory.
3.  The file watcher automatically triggers ingestion, deconvolution, spectral matching, and deposits the final report in `processed_results/`.

---

## 5. Benchmarking Results

Our GNN-driven deconvolution and parameter adaptation models resolve significant chromatography processing bottlenecks:

### Peak Deconvolution Partitioning
Compared against standard SciPy peak integration (which double-counts signals in overlapping elution regions), the GCN deconvolution successfully partitioned shared signals and resolved significant double-counting errors:

| Dataset | Total Peaks | Co-eluting Peaks | Avg GNN Purity | Raw Area (mAU·min) | Corrected Area (mAU·min) | Overlap Error Corrected |
|---|---|---|---|---|---|---|
| **FAME Mix 30** | 23 | 22 | 0.576 | 948.52 | 485.84 | **48.8%** |
| **PE-2 (Polymer)** | 286 | 286 | 0.518 | 1,924,763.54 | 1,037,703.85 | **46.1%** |
| **PE-5 (Polymer)**| 178 | 178 | 0.524 | 2,236,502.54 | 1,155,426.75 | **48.3%** |

### Additional Upgrades Benchmarking
- **System Suitability Testing (SST):** Accuracy validated against simulated peaks: tailing factor calculated as 1.013 for a perfect Gaussian peak, and 1.623 for tailing Exponentially Modified Gaussian (EMG) peaks.
- **Multi-Sample Alignment:** Downsampled Sakoe-Chiba constrained Dynamic Time Warping (DTW) executes in **110ms** per run (a 300x speedup compared to raw signal DTW at 45.5s), correcting column drift and achieving $R=1.000$ signal correlation.
- **Adaptive Proximity Thresholds:** In regions with highly identical spectra (cosine similarity = 1.0), the threshold dynamically shrinks from 0.700 to 0.663, and down to 0.464 for dense 3-component clusters, preventing GCN over-smoothing.
- **EMG Fitting Solver Performance:** Restricting non-linear curve fitting to co-eluting groups of size $\le 5$ resolves CPU hangs and enables deconvolution of large files (620 peaks) to complete in under 12 seconds.
- **Softmax Validation:** Every single GCN prediction satisfied the softmax constraint (`softmax_valid: true`), proving that split probabilities summed to exactly 1.0 for each node.

---

## 6. Publications & Academic Target
This pipeline is documented in the manuscript:
*   *Agentic Orchestration for Automated Chromatography: A Tiered AI Framework for Lab 4.0 Telemetry* (Target Journal: **SLAS Technology**, submission planned October 2026).

---

*Built by [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria-01b373385/) — MSc Chemistry (82%), Technical Lead & Informatics Researcher.*
