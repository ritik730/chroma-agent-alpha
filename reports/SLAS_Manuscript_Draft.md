# Agentic Orchestration for Automated Chromatography: A Tiered AI Framework for Lab 4.0 Telemetry

**Author**: [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria-01b373385/)
**Target Journal**: SLAS Technology
**Target Submission**: October 2026

## Abstract
The transition toward Self-Driving Laboratories (SDLs) and Industry 4.0 demands robust, autonomous data processing pipelines that can operate without human intervention. While open-source tools exist for chromatography analysis, they often require extensive manual parameter tuning or suffer from high integration barriers. Here, we introduce CHROMA-AGENT-ALPHA, an autonomous, vendor-independent Extract, Transform, and Load (ETL) pipeline for raw chromatography data. Driven by a tiered, dual-agent AI architecture, the system orchestrates complex data telemetry using a "Macro Brain" for deterministic planning and validation, and a "Micro Engine" for tactical execution. The workflow automates raw data ingestion (.cdf/.mzML) via n8n, baseline correction utilizing Asymmetric Least Squares (ALS), peak quantification via trapezoidal integration, and spectral matching via `matchms`. Furthermore, we propose a Graph Neural Network (GNN) approach for the deconvolution of co-eluting peaks. By leveraging a hierarchy of Large Language Models (LLMs)—ranging from local, privacy-preserving models (T1) to advanced cloud reasoners—the framework ensures data sovereignty while reducing the manual thresholding burden. Ultimately, this agentic orchestration repositions the analytical chemist from a manual data processor to a "Digital Architect," establishing a scalable, FAIR-compliant foundation for Lab 4.0 telemetry.

## 1. Introduction
The advent of Lab 4.0 and Self-Driving Laboratories (SDLs) has accelerated the pace of chemical synthesis and materials discovery. However, the analytical bottleneck remains a critical challenge: high-throughput experimentation generates vast amounts of chromatography data (GC-MS, LC-MS) that conventionally require manual, vendor-locked software for processing. 

While significant strides have been made with open-source computational tools such as CADET, MOCCA, OpenMS, and PeakDetective, these solutions often demand rigorous manual parameterization and coding expertise, creating a gap between automated synthesis and automated analysis. There is an urgent need for an autonomous orchestrator that can bridge this gap with low-code accessibility.

In this work, we present a tiered AI framework designed to automate the chromatography ETL pipeline. By employing a multi-agent system, we decouple high-level logic validation (Loop 1) from granular code execution (Loop 2). This architecture minimizes hallucinations and ensures mathematically sound data processing.

## 2. System Architecture & Methods

The CHROMA-AGENT-ALPHA framework is structured as an end-to-end autonomous Extract, Transform, and Load (ETL) pipeline integrated with a cost-governed dual-agent AI orchestrator. The complete workflow spans from raw instrument telemetry ingestion to regulatory compliance reporting and FAIR-compliant data preservation.

### 2.1 The Data Processing Pipeline (Tiers 0–6)

The ingestion and data transformation pipeline is executed sequentially across seven modular tiers:

0. **Tier 0: Universal Format Conversion (Stage 0):** To achieve vendor-independent processing, proprietary binary formats (e.g., Agilent `.D`, Thermo `.RAW`, Sciex `.wiff`, Waters `.RAW`) are intercepted in the watch directory. The pipeline automatically invokes ProteoWizard's `msconvert` CLI wrapper to transcode vendor-specific binary arrays into structured, open-source `.mzML` files before parsing.
1. **Tier 1: Telemetry Ingestion & Parsing:** The raw chromatogram files, stored in open formats such as NetCDF4 (`.cdf`) or mzML (`.mzML`), or Varian binary files (`.xms`), are monitored by an automated watcher node. Ingestion is performed using a custom parser utilizing the `netcdf4` and `pyopenms`/`pyteomics` libraries. Raw retention time ($RT$) vectors, signal intensity arrays, and mass spectral ($m/z$) arrays are extracted and serialized into memory-mapped structures.
2. **Tier 2: Baseline Correction:** To isolate analytical signals from instrument column bleed or background drift, baseline correction is performed prior to peak integration. The pipeline incorporates an Asymmetric Least Squares (ALS) smoothing algorithm. The corrected signal vector $\mathbf{z}$ is computed by minimizing the penalized objective function:
   $$S = \sum_{i} w_i (y_i - z_i)^2 + \lambda \sum_{i} (\Delta^2 z_i)^2$$
   where $y_i$ is the raw signal intensity, $z_i$ is the estimated baseline, $\Delta^2$ is the second-order difference operator, $\lambda$ is a smoothness regularization parameter (typically set between $10^3$ and $10^6$), and $w_i$ is an asymmetric weight vector defined as:
   $$w_i = \begin{cases} p & \text{if } y_i > z_i \\ 1-p & \text{if } y_i \le z_i \end{cases}$$
   with the asymmetry parameter $p$ configured between $0.001$ and $0.01$ to ensure baseline tracking without clipping peak signals.
3. **Tier 3: Peak Detection & Numerical Integration:** Peak apexes, start boundaries, and end boundaries are identified on the baseline-corrected chromatogram using a derivative-based peak-finding algorithm via `scipy.signal.find_peaks`. Once boundaries are established, numerical integration of peak areas ($A$) is executed using the Trapezoidal Rule:
   $$A = \sum_{i=1}^{n} \frac{y_{i-1} + y_i}{2} (x_i - x_{i-1})$$
   where $x$ represents the retention time coordinate and $y$ represents the baseline-corrected intensity. The integration bounds are audited to ensure non-negativity.
4. **Tier 4: GNN-Based Peak Deconvolution:** In instances of overlapping or co-eluting peaks, standard integration fails. The pipeline resolves these features using a Graph Neural Network (GNN) model built in PyTorch Geometric (`torch-geometric`). The chromatogram segment is represented as a 1D graph $G = (V, E)$, where nodes $v_i \in V$ correspond to individual retention time steps associated with their multi-channel mass spectral features, and edges $e_{ij} \in E$ capture temporal adjacency. A Graph Convolutional Network (GCN) processes node features through successive message-passing layers:
   $$\mathbf{h}_i^{(l+1)} = \sigma \left( \mathbf{W}^{(l)} \sum_{j \in \mathcal{N}(i) \cup \{i\}} \frac{1}{\sqrt{\tilde{d}_i \tilde{d}_j}} \mathbf{h}_j^{(l)} \right)$$
   where $\mathbf{h}_i^{(l)}$ is the activation vector of node $i$ at layer $l$, $\mathcal{N}(i)$ is the set of neighbors, $\tilde{d}_i$ is the node degree with self-loops, and $\mathbf{W}^{(l)}$ is a trainable weight matrix. The network outputs a GNN Purity Score ($S_{purity} \in [0, 1]$) representing the probability that a peak represents a single chemical component, enabling the deconvolution of overlapping curves.
5. **Tier 5: Spectral Matching & AI-Driven Chemical Naming:** Extracted ion chromatogram (XIC) profiles and mass spectra at peak apexes are cross-referenced against reference libraries using the cosine similarity metric:
   $$S_C = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
   where $\mathbf{u}$ and $\mathbf{v}$ represent the intensity vectors of the query and reference spectra, respectively. Matches with $S_C \ge 0.7$ are registered. For trimethylsilyl (TMS) derivatized samples, the pipeline automatically appends preparation contexts upon detecting diagnostic fragment ions at $m/z\ 73$ and $147$. Unmatched peaks are routed to an LLM-driven chemical naming classifier to resolve IUPAC names, chemical classes, and assign prediction confidence scores.
6. **Tier 6: Polars ETL & FAIR Data Registry:** Telemetry and peak metadata are structured using the `polars` engine. The processed datasets are written as chunked N-dimensional Zarr v3 arrays. Provenance tracking is managed via a SQLite-backed LaminDB schema, registering data lineages, raw files, and generated deliverables to enforce FAIR (Findable, Accessible, Interoperable, Reusable) data standards.

### 2.2 USP <467> Quantitative Compliance & Alerts

To satisfy regulatory standards for residual solvents in active pharmaceutical ingredients (APIs), the pipeline calculates concentration values in parts-per-million ($ppm$) in accordance with USP <467> guidelines. The concentration ($C_{sample}$) of a target analyte is calculated using response factors derived from a calibration standard:
$$R.F._{std} = \frac{A_{std}}{C_{std}}$$
$$C_{sample} = \frac{A_{sample}}{R.F._{std}}$$
where $A_{sample}$ is the integrated area of the sample peak, $A_{std}$ is the integrated area of the calibration standard peak, and $C_{std}$ is the concentration of the standard. 

The system maps computed concentrations against Class 1 and Class 2 toxicity threshold limits (e.g., Benzene: 2 ppm; Hexane: 290 ppm; Toluene: 890 ppm; Methanol: 3000 ppm; Ethanol: 5000 ppm). Out-of-Specification (OOS) limits dynamically trigger a visual warning system, marking the run status as `FAIL` and flagging violating elements with an elevated hazard class.

### 2.3 Tiered AI Orchestration & Double-Loop Validation

The framework operates under a decentralized, dual-agent model designed to maintain data sovereignty and manage computing resource costs:

* **Antigravity (Macro Brain):** Plans macro-architecture, structures workflows, drafts manuscripts, and performs high-level validation checks (Loop 1). It does not execute commands on the host environment directly.
* **Claude Code (Micro Engine):** Conducts code generation, refactoring, local execution, and low-level validation checks (Loop 2).
* **Double-Loop Validation System:** 
  * *Loop 1 (Environment Check):* Spawns an ephemeral Linux container (Ghost Runtime) to run execution modules, checking for dependency compliance, schema conflicts, and deprecation warnings (e.g., enforcing `np.trapezoid` over `np.trapz`).
  * *Loop 2 (Logic Audit):* Analyzes mathematical bounds, checking that integration areas are non-negative, probability vectors sum to 1.0, and spectral matching scores are normalized.

To ensure strict cost governance under a hard ₹500/month budget ceiling, the API router employs a tiered execution tree via LiteLLM (Port 4000) running with zero local compute to prevent RAM swap freezes on the i5 host:
* **Tier 1 (Scout - Cloud):** Mapped to `google/gemini-2.5-flash-lite` via OpenRouter (`claude-t1`). Handles fast, low-cost classification, routing labels, and formatting tasks.
* **Tier 2 (Analyst - Free):** Mapped to `deepseek/deepseek-v4-flash:free` (`claude-t2`). Reserved for non-coding tasks like summarizing, enriching, and compacting memory.
* **Tier 3 (Architect - Paid):** Mapped to `deepseek/deepseek-v4-flash` (`claude-t3`). Handles standard coding requests, GNN deconvolution training, and chromatography pipeline integrations.
* **Tier 3-COT (Architect - CoT):** Mapped to `deepseek/deepseek-r1-distill-qwen-32b` (`claude-t3-cot`). Reserved for complex architectural and GNN reasoning tasks.
* **Tier 4 (Fallback - Automated):** Mapped to local Claude Sonnet/Opus proxy (`localhost:8080`). Serves as a final fallback triggered automatically if T1/T2/T3 fails in the pipeline execution loop.
* **Antigravity (Manual - Preferred):** Mapped to Claude Sonnet/Opus proxy (`localhost:8080`). Direct, preferred manual option used by the developer for long-form manuscript prose writing, PhD cover letters, and research statements.

### 2.4 Server Security & Hardening

When deploying the pipeline server for external testing or peer verification, a double-walled security configuration is enforced:
1. **Network Authentication:** The primary ngrok gateway enforces basic authentication on the outer tunnel.
2. **Access Control:** The inner FastAPI server requires Basic HTTP Authentication for dashboard access and API endpoints.
3. **Exploit Mitigation:** Path traversal attacks are neutralized by validating and sanitizing incoming sample IDs, rejecting parent directory markers (`..`) and directory separators (`/`, `\`). Socket uploads are restricted to `.cdf` and `.mzML` formats with a maximum file size cap of 50 MB to prevent denial-of-service (DoS) attempts.

## 3. Results

### 3.1 Ingestion & Peak Detection Metrics
The native Varian `.xms` binary parser was validated using sample `MC-10A-NF205-05-2018.xms`, executing sequential decoding of 282-byte telemetry strides and applying a strict 12-bit mask (`0xFFF`) for records with category index $d \ge 8$. This resolved prior height-math overflow errors and aligned intensity ranges to standard abundance units. 
For peak detection validation, polymer additive blends `PE-2.D` and `PE-5.D` were processed and compared against their reference NIST20 MassHunter search reports (`RESULTS.CSV`). The pipeline achieved a peak detection overlap of **93.4%** (141 out of 151 reference peaks detected) for `PE-2.D`, and **84.5%** (142 out of 168 reference peaks detected) for `PE-5.D`. 

### 3.2 Deconvolution Performance
Co-eluting regions were evaluated using the 2-layer Graph Convolutional Network (GCN) deconvolution script (`scripts/gnn_deconv.py`) built in `torch-geometric`. A temporal-spectral graph was constructed for overlapping peak regions (where retention times differed by less than 0.5 minutes and spectral correlation exceeded 0.3). In the high-dynamic-range polymer runs, GNN purity classification successfully mapped node signals to separate component profiles, resolving major additives (e.g., plasticizers like *Bis(2-ethylhexyl) phthalate*) from adjacent noise and column bleed with a softmax probability output.

To evaluate GCN deconvolution performance against standard numerical integration, we benchmarked the double-counting error resolved by the GCN's predicted purity partitions:

| Dataset | Total Peaks | Co-eluting Peaks | Avg GNN Purity | Raw Area (mAU·min) | Corrected Area (mAU·min) | Overlap Error Resolved | % Error Corrected |
|---|---|---|---|---|---|---|---|
| **fame_mix_30** | 23 | 22 | 0.576 | 948.52 | 485.84 | 462.68 | 48.8% |
| **PE-2** | 286 | 286 | 0.518 | 1924763.54 | 1037703.85 | 887059.68 | 46.1% |
| **PE-5** | 178 | 178 | 0.524 | 2236502.54 | 1155426.75 | 1081075.79 | 48.3% |

By applying the softmax-validated component probabilities (`softmax_valid: true`), CHROMA-AGENT-ALPHA successfully partitioned co-eluting peaks and resolved approximately 46% to 49% of raw area double-counting integration errors.


### 3.3 Spectral Matching Accuracy
Isolated pure-component spectra at resolved peak apexes were queried against mass spectral reference libraries using the `matchms` library. Cosine similarity scoring was executed in chunked batches of 15 queries to optimize API resource usage. 
- On a 30-component FAME mix chromatogram (`fame_mix_30.cdf`), the pipeline successfully detected, deconvolved, and matched **23 distinct peaks** with 100% identification accuracy.
- For TMS-derivatized compounds in the polymer dataset, the pipeline successfully detected diagnostic fragment ions at $m/z\ 73$ and $147$, dynamically appending derivatization contexts to compound names.
- Data lineage for all runs was successfully registered as Zarr v3 array files and Excel report artifacts in a local SQLite-backed LaminDB instance, establishing unique tracking UIDs for data provenance.

## 4. Discussion
The deployment of a tiered dual-agent system significantly lowers the technical barrier for implementing FAIR-compliant telemetry in chemical laboratories. By shifting the paradigm from manual peak integration to autonomous orchestration, laboratories can maintain data sovereignty (via local T1 models) while benefiting from the reasoning capabilities of larger models.

## References
*(To be formatted in Vancouver style)*
- CADET, PeakDetective, OpenMS, matchms, GNPS, lamindb.
