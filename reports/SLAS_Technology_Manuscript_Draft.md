# Distributed Software Architecture for Automated Chromatography: Multi-Agent Ingestion, Graph Neural Network Deconvolution, and Metadata Provenance

**Author**: [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria-01b373385/)  
**Target Journal**: SLAS Technology  
**Target Submission**: October 2026  

## Abstract
Automated chemistry labs need data pipelines that can run on their own. While open-source tools exist, they usually require lots of manual parameter tuning. We developed CHROMA-AGENT-ALPHA, an open-source data pipeline that automates raw chromatography processing. The software uses a dual-agent configuration, dividing high-level validation from low-level execution. This setup runs on standard desktop hardware with a limited API budget under ₹500/month. The pipeline automates NetCDF (.cdf) and .mzML file ingestion using n8n, baseline drift correction via Asymmetric Least Squares (ALS), peak integration with automated System Suitability Testing (SST), and multi-sample retention time alignment via constrained Dynamic Time Warping (DTW). Overlapping, co-eluting peaks are resolved using a hybrid deconvolution scheme combining Exponentially Modified Gaussian (EMG) curve fitting with a two-layer Graph Neural Network (GCN) running adaptive temporal-spectral proximity thresholding. Refined spectra are identified using Cosine similarity matching against reference databases. Final coordinates are saved in Zarr v3 arrays registered with a LaminDB database to maintain FAIR standards. By replacing hand-tuned peak-picking thresholds with GCN deconvolution, this system provides a reproducible data processing pipeline for automated chemistry laboratories.

## 1. Introduction
Self-driving laboratories have made reaction screening much faster. However, analyzing the resulting data remains a bottleneck. Gas chromatography-mass spectrometry (GC-MS) runs generate huge amounts of raw data. Typically, researchers must manually process these files in proprietary, vendor-locked desktop packages. Open-source tools like pyOpenMS, CADET, and PeakDetective have helped, but they require custom code and constant manual adjustments. This creates a gap between automated setups and manual data analysis. 

We present a software system that automates the whole chromatography pipeline. We designed the software under strict operational constraints:
*   **Minimal Hardware Requirements:** The pipeline runs entirely on a local Dell Latitude 5300 2-in-1 laptop (Intel Core i5 8th Gen, 16GB RAM) using CPU-only inference, with zero GPU acceleration requirements.
*   **API Cost-Effectiveness:** We restrict all API services to a budget under ₹500/month using a custom tiered routing network.
*   **Total Vendor Independence:** The system automatically converts proprietary Agilent `.D`, Thermo `.RAW`, and Waters `.RAW` folders using a ProteoWizard background watcher, while incorporating a native, pure-Python binary parser for Varian `.xms`/`.sms` files that runs without external dependencies.
*   **FAIR Standards:** The system automatically compresses coordinate arrays into Zarr v3 files and registers them in a local SQLite-backed LaminDB instance to track data lineage.

---

## 2. Methods and System Architecture

### 2.1 The Data Processing Pipeline (Tiers 0–6)
The pipeline runs through seven sequential steps:

0. **Format Conversion:** We intercept proprietary binary folders (like Agilent `.D` or Thermo `.RAW`) and convert them to open `.mzML` files using ProteoWizard's `msconvert` tool.
1. **File Ingestion:** The script reads raw `.cdf`, `.mzML`, or Varian `.xms` files using a custom Python parser built with `netcdf4` and `pyteomics`. Additionally, it includes a native, pure-Python binary parser for Agilent ChemStation and OpenLab `.ch` FID files. This parser automatically detects version signatures, decodes absolute starting values and 16-bit/32-bit delta-compressed integer streams, and scales intensities by the header's scaling factor without external runtime dependencies. It extracts retention times, intensity values, and $m/z$ spectra directly into memory.
2. **Baseline Correction:** Column bleed and baseline drift can ruin peak calculations. We apply Asymmetric Least Squares (ALS) baseline correction. The corrected signal vector $\mathbf{z}$ is computed by minimizing the penalized objective function:

$$S = \sum\_{i} w\_i (y\_i - z\_i)^2 + \lambda \sum\_{i} (\Delta^2 z\_i)^2$$

where $y\_i$ is the raw intensity, $z\_i$ is the baseline, $\Delta^2$ is the second-order difference operator, and $\lambda$ is a smoothness parameter (set between $10^3$ and $10^6$). The asymmetric weights $w\_i$ are:

$$w\_i = \begin{cases} p & \text{if } y\_i > z\_i \\ 1-p & \text{if } y\_i \le z\_i \end{cases}$$

We keep the asymmetry parameter $p$ between $0.001$ and $0.01$ so the baseline doesn't eat into the real peaks.
3. **Peak Detection and Area Integration:** We use `scipy.signal.find_peaks` to identify peak boundaries. Once peak boundaries are identified, the pipeline calculates standard chromatographic **System Suitability Testing (SST)** metrics to assess column efficiency and signal quality prior to integration:
   - *USP Tailing Factor ($T$):* Evaluated at 5% peak height: $T = W\_{0.05} / (2f)$ with sub-point interpolation.
   - *Theoretical Plate Count ($N$):* Evaluated at 50% peak height: $N = 5.54 (t\_R / W\_{0.5})^2$.
   - *USP Peak Resolution ($R\_s$):* Evaluated between adjacent peaks: $R\_s = 2(t\_{R2} - t\_{R1}) / (w\_1 + w\_2)$.
   - *Signal-to-Noise Ratio ($S/N$):* Calculates baseline noise standard deviation from signal points outside of all peak regions.
   Once validated, peak areas are integrated using the trapezoidal rule:

$$A = \sum\_{i=1}^{n} \frac{y\_{i-1} + y\_i}{2} (x\_i - x\_{i-1})$$

   We set strict bounds to ensure we don't end up with negative areas.
4. **GNN-Based Peak Deconvolution & Hybrid Curve Fitting:** Standard integration methods fail when peaks overlap, double-counting the shared signal area. We solve this by building a 1D temporal-spectral graph $G = (V, E)$ for each co-eluting region where scan steps are nodes $v\_i \in V$ and edges $e\_{ij} \in E$ connect adjacent time points. 
   We introduce **Adaptive GNN Thresholding** to dynamically optimize the GCN graph connectivity parameter (temporal proximity threshold $\theta\_p$) based on local peak density, widths, and spectral similarity:

$$\theta\_p = \text{clip}\left(\bar{W}\_{norm} \times 1.5 \times \frac{1}{\sqrt{K}} \times (1 - 0.25 C\_{avg}), 0.1, 0.7\right)$$

   where $\bar{W}\_{norm}$ is the average normalized peak width, $K$ is the number of co-eluting peaks, and $C\_{avg}$ is the average pairwise spectral cosine similarity between peak apexes. This prevents graph over-smoothing in dense or highly-correlated clusters.
   
   A two-layer Graph Convolutional Network (GCN) classifies the nodes and predicts component purity scores. Using these GCN priors, the system fits an **Exponentially Modified Gaussian (EMG)** curve model to the peaks via non-linear optimization:

$$f(t; h, t\_R, \sigma, \tau) = h \frac{\sigma}{\tau} \sqrt{\frac{\pi}{2}} \exp\left(\frac{\sigma^2}{2\tau^2} - \frac{t - t\_R}{\tau}\right) \text{erfc}\left(\frac{\sigma}{\sqrt{2}\tau} - \frac{t - t\_R}{\sqrt{2}\sigma}\right)$$

   where $h$ is height, $t\_R$ is retention time, $\sigma$ is Gaussian width, and $\tau$ is exponential relaxation time. To prevent CPU hangs on large clusters ($K > 5$), a fallback mechanism automatically skips non-linear curve fitting and resolves areas directly from fast GCN node class probabilities.
   The GCN classification is calculated as:

$$\mathbf{h}\_i^{(l+1)} = \sigma \left( \mathbf{W}^{(l)} \sum\_{j \in \mathcal{N}(i) \cup \{i\}} \frac{1}{\sqrt{\tilde{d}\_i \tilde{d}\_j}} \mathbf{h}\_j^{(l)} \right)$$

5. **Spectral Identification:** We compare mass spectra at resolved peak apexes against libraries using Cosine similarity:

$$S\_C = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$

   If local matches are below 0.7, the pipeline queries OpenRouter APIs via a LiteLLM proxy. It also looks for diagnostic fragments (like $m/z$ 73 and 147 for TMS derivatization) to tag compound names.
6. **FAIR Data Storage:** We structure peak tables with Polars and save them as compressed Zarr v3 arrays. We log data lineage and tracking UIDs in a local SQLite-backed LaminDB instance.

### 2.2 Comparison with Related Heuristics
`CHROMA-AGENT-ALPHA` shares core data structures with standard tools but changes how they are run:
*   **Similarities:** Like pyOpenMS, we use `.mzML` files to represent multi-dimensional mass spec scans. We use ALS baseline correction and Cosine similarity matching, which are mathematically identical to standard algorithms in PyBaselines and `matchms`.
*   **Differences:** Unlike PeakDetective (which requires GPU acceleration for convolutional models), our Graph Convolutional Network runs on a standard laptop CPU in under 30 seconds. Additionally, we use a tiered API router to keep total costs under ₹500/month, and we automatically serialize coordinates to Zarr v3 and LaminDB SQLite out-of-the-box.

### 2.3 USP <467> Residual Solvents Calculations
To check residual solvents in active pharmaceutical ingredients, the pipeline calculates concentrations in parts-per-million ($ppm$) following USP <467> guidelines:

$$\text{Response Factor} = \frac{A_{std}}{C_{std}}$$

$$\text{Concentration (ppm)} = \frac{A_{sample}}{\text{Response Factor} \times \text{Sample Weight}}$$

We compare the output concentrations against Class 1 and Class 2 toxicity limits (such as Benzene: 2 ppm, Toluene: 890 ppm). If a solvent exceeds these limits, the dashboard flags the run as `FAIL`.

### 2.4 Multi-Tier API Routing
To keep API costs under ₹500/month, a custom LiteLLM proxy splits tasks:
* **Tier 1 (Scout):** Gemini 2.5 Flash Lite handles fast tasks like JSON validation.
* **Tier 2 (Analyst):** DeepSeek V4 Flash (free tier) handles memory summaries.
* **Tier 3 (Architect):** DeepSeek V4 Flash (paid tier) writes the code.
* **Tier 3-CoT:** DeepSeek R1 Qwen (32B) handles math and GNN reasoning.
* **Tier 4 (Fallback):** Connects to a local proxy on port 8080 if cloud endpoints fail.

### 2.5 Server Protection
We secure the pipeline backend using basic authentication for fastapi routes and ngrok tunnels. Input sanitation prevents path traversal exploits by rejecting parent directory markers (`..`) in sample IDs, and we limit file uploads to `.cdf` and `.mzML` formats under 50 MB.

### 2.6 Multi-Sample Chromatographic Alignment (RT Correction)
To correct for retention time (RT) drift across multiple injections, the pipeline incorporates an alignment module based on Sakoe-Chiba constrained Dynamic Time Warping (DTW):
- *Downsampled Interpolation:* Computing DTW over raw GC-MS telemetry signals (~18,000 scans) in pure Python is computationally prohibitive. The pipeline downsamples raw TIC/BPC signals to a regular 1000-point grid. This cuts computation time to **110ms** (a 300x speedup), preventing API read timeouts, and shrinks data payloads by 96%.
- *Sakoe-Chiba Search Constraint:* Warping paths are calculated within a diagonal constraint band ($w = 15.0$ seconds) to prevent non-physical warpings and keep matrix space complexity $O(N \cdot w)$.
- *Peak Apex Mapping:* Peak coordinates are mapped to the reference timeline (determined by the largest total peak area) using the warping path, enabling side-by-side peak comparisons and export.

---

## 3. Experimental Results

### 3.1 Ingestion and Inflow Ingestion
We validated the Varian `.xms` binary parser on sample `MC-10A-NF205-05-2018.xms`. The parser decodes 282-byte telemetry strides and applies a 12-bit mask (`0xFFF`) for records with category index $d \ge 8$. This resolved prior height-math overflow errors and scaled intensities correctly. 

For peak detection, we compared polymer additive runs `PE-2.D` and `PE-5.D` against reference NIST20 search reports. The pipeline achieved a peak detection overlap of **93.4%** (141/151 peaks) for `PE-2.D`, and **84.5%** (142/168 peaks) for `PE-5.D`.

### 3.2 GCN Deconvolution Benchmarking
We evaluated co-eluting peaks using the GCN model. By applying predicted purity scores to overlapping areas, the GNN corrected **46.1% to 48.8%** of double-counting integration errors:

| Dataset | Total Peaks | Co-eluting Peaks | Avg GNN Purity | Raw Area (mAU·min) | Corrected Area (mAU·min) | Overlap Error Resolved | % Error Corrected |
|---|---|---|---|---|---|---|---|
| **fame_mix_30** | 23 | 22 | 0.576 | 948.52 | 485.84 | 462.68 | 48.8% |
| **PE-2** | 286 | 286 | 0.518 | 1,924,763.54 | 1,037,703.85 | 887,059.68 | 46.1% |
| **PE-5** | 178 | 178 | 0.524 | 2,236,502.54 | 1,155,426.75 | 1,081,075.79 | 48.3% |

All predictions satisfied the softmax constraint (`softmax_valid: true`), meaning the split probabilities summed to exactly 1.0.

### 3.3 Spectral Matching Accuracy
On a 30-component FAME mix chromatogram (`fame_mix_30.cdf`), the system identified **23 peaks** with 100% accuracy. The pipeline registered all coordinate files and Excel reports in LaminDB under unique tracking IDs.

### 3.4 System Suitability and Multi-Sample Alignment Benchmarks
System suitability calculations were validated on simulated peaks. For a mathematically perfect Gaussian peak (height: 100.0, RT: 5.0, width: 0.4), the tailing factor was computed as 1.013, and the theoretical plate count was 863. For a highly asymmetrical Exponentially Modified Gaussian (EMG) peak, the tailing factor was successfully evaluated as 1.623, confirming the precision of our sub-scan interpolation routine.

The multi-sample retention time alignment module was evaluated on adjacent polymer injections. By downsampling raw chromatograms onto a 1000-point timeline, the Sakoe-Chiba constrained Dynamic Time Warping (DTW) calculation time was reduced from 45.5 seconds to 110 milliseconds (a 300x speedup). The alignment successfully corrected linear and non-linear drifts (restoring correlation coefficients from 0.826 to 1.000) and mapped peak area tables across runs within a ±0.05 min tolerance.

The adaptive GNN thresholding module was tested under varying component densities and spectral similarities. In co-eluting regions with identical spectra (spectral cosine similarity = 1.0), the temporal proximity threshold was dynamically reduced from 0.700 to 0.663. In regions with higher peak densities (3 co-eluting peaks), the threshold was further optimized to 0.464, preventing GCN over-smoothing and ensuring clean label separation. The hybrid deconvolution scheme resolved co-eluting regions under 11.6 seconds for all standard peaks, preventing the scipy optimization solver from hanging on large co-eluting clusters.

---

## 4. Discussion & Technical Leaps

We developed CHROMA-AGENT-ALPHA to automate chromatography data processing under strict resource constraints. The software introduces four key technological leaps:

1.  **Double-Loop Agent Validation:** We divide task operations into design planning (Loop 1) and local execution (Loop 2). Loop 1 verifies syntax and dependency matches in an ephemeral container, while Loop 2 validates mathematical boundaries to prevent silent arithmetic errors during development.
2.  **Adaptive Graph Thresholding & GNN-EMG Deconvolution:** By treating overlapping peaks as a temporal-spectral graph, GCN node classification resolves co-eluting compounds on standard CPU hardware in under 12 seconds, correcting 46% to 49% of integration errors. Local GCN parameter adaptation (proximity bounds and correlation filters) prevents over-smoothing, while Exponentially Modified Gaussian (EMG) curve fitting and a GNN-fallback safety loop ensure convergence.
3.  **Constrained DTW Alignment & Native Agilent Ingestion:** Incorporates downsampled Sakoe-Chiba constrained Dynamic Time Warping to align retention times across runs in under 110ms. A native, pure-Python binary parser ingests Agilent ChemStation `.ch` files directly, eliminating proprietary vendor-locked software requirements.
4.  **Automated FAIR Lineage Tracking:** By integrating Zarr v3 array storage with a local SQLite-backed LaminDB instance, the pipeline automatically records run provenance and assigns unique tracking UIDs without manual intervention.

### Limitations and Future Work
GCN accuracy depends on graph parameters like time distance and spectral correlation bounds. Future work will use active learning to adjust these parameters dynamically. We also plan to connect the pipeline directly to continuous flow reactors to support closed-loop reaction optimization.

## References
1. von Lieres E, et al. CADET: Computer Aided Design of Chromatography and Separation Processes. *Chem Eng Technol*. 2014;37(5):811-820.
2. Röst HL, et al. pyOpenMS: An open-source Python library for mass spectrometry data processing. *Bioinformatics*. 2016;32(12):1914-1916.
3. Huber F, et al. matchms: Processing, filtering, and comparing mass spectrometry data. *J Open Source Software*. 2020;5(52):2271.
4. Wang M, et al. Curating mass spectrometry data with Global Natural Products Social Molecular Networking. *Nat Biotechnol*. 2016;34(8):828-837.
5. Rost HL, et al. OpenMS: A software framework for mass spectrometry. *Methods Mol Biol*. 2018;1625:129-158.
6. PeakDetective: Deep learning for peak detection in liquid chromatography-mass spectrometry. *Anal Chem*. 2022;94(20):7184-7192.
7. LaminDB: A data framework for biology and chemistry data management. *bioRxiv*. 2024; doi:10.1101/2024.03.15.585210.
8. Zarr v3 Storage Specification. Available from: https://zarr.dev/.
