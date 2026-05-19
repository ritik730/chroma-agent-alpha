# Agentic Orchestration for Automated Chromatography: A Tiered AI Framework for Lab 4.0 Telemetry

**Authors:** Devendra Kataria, et al.  
**Target Journal:** SLAS Technology  
**Status:** DRAFT (Abstract & Methods)  

---

## Abstract
The transition toward Self-Driving Laboratories (SDL) necessitates automated, reliable interpretation of analytical telemetry. Chromatography, a cornerstone of chemical analysis, suffers from highly manual data processing workflows that are prone to subjective human error and proprietary vendor lock-in. We introduce CHROMA-AGENT-ALPHA, a vendor-independent, AI-driven ETL pipeline designed for automated extraction, processing, and deconvolution of raw chromatographic data (e.g., .cdf, .mzML). By orchestrating a tiered multi-agent architecture—comprising a Macro Brain (Gemini) for architectural planning and a Micro Engine (Claude Code) for localized logic execution—we demonstrate a highly robust, low-code operational paradigm. The pipeline successfully executes Asymmetric Least Squares (ALS) baseline correction, standard trapezoidal peak quantification, and advanced Graph Neural Network (GNN) deconvolution for co-eluting peaks, matched against `matchms` spectral libraries. This "Digital Architect" approach eliminates repetitive analytical bottlenecks, enforces FAIR data principles via `zarr` and `lamindb`, and significantly advances the capabilities of closed-loop chemical discovery.

---

## 2. Methods

### 2.1 Multi-Agent System Architecture
The automation framework was engineered using a dual-agent configuration guided by a strict separation of concerns, termed the "Get Shit Done" (GSD) methodology. The architectural components include:
*   **Macro Brain (Antigravity/Gemini):** Responsible for overarching pipeline design, environment validation (Loop 1 Ghost Runtimes), and documentation synthesis.
*   **Micro Engine (Claude Code):** Responsible for discrete, deterministic execution of code modules and logic verification (Loop 2 Audit). 

To optimize computational efficiency and avoid API rate limitations (e.g., 429 errors), the Micro Engine utilizes a custom Claude Code Router (CCR) enabling a Quad-Stack model structure. Lightweight operations (docstring generation, syntax verification) are routed to a local `phi4-mini` model, whereas heavy data transformation scripts are directed to higher-tier cloud models (`deepseek-v4-flash` and `deepseek-v3.2-speciale`).

### 2.2 Pipeline Design & Data Processing
The continuous ETL (Extract, Transform, Load) pipeline is triggered autonomously by an `n8n` folder-watch orchestrator upon the deposition of raw telemetry files (.cdf, .mzML). 
1.  **Ingestion & Correction:** Raw datasets are converted to structured formats. Baseline drift is eliminated utilizing Asymmetric Least Squares (ALS) correction, effectively decoupling the slowly varying baseline drift from the sharp chemical peaks.
2.  **Peak Detection & Quantification:** True peaks are localized using customized local maxima algorithms (e.g., `scipy.signal.find_peaks`). Area under the curve is quantified leveraging standard trapezoidal integration ($A \approx \sum \frac{(y_{i-1}+y_i)}{2} \times (x_i - x_{i-1})$) mapping tightly to retention time.
3.  **Deconvolution (GNN):** For overlapping or co-eluting peaks, a Graph Convolutional Network (GCN) is implemented via `torch-geometric`, mapping mass-to-charge ($m/z$) and intensity temporal features to separate pure-component signals.
4.  **Spectral Matching:** Isolated spectra are queried against standard reference libraries using the `matchms` library, utilizing cosine similarity scoring with a pre-defined threshold of $\ge 0.70$ for successful identification.

### 2.3 FAIR Data Lineage
To satisfy Lab 4.0 standardizations, output datasets are persisted utilizing `zarr` for chunked array storage, facilitating rapid down-stream query capability. Concurrently, data provenance and pipeline execution parameters are comprehensively tracked via `lamindb`, ensuring that every parsed spectrum is Findable, Accessible, Interoperable, and Reusable (FAIR).
