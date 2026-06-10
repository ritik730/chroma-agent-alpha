# Connecting Flow Reactors to Neural Networks and Multi-Agent Systems for Automated Chemistry

**PhD Candidacy Project Proposal (2027)**  
**Applicant:** [Devendra Kataria](https://www.linkedin.com/in/devendra-kataria-01b373385/)  
**Target Group:** Flow Chemistry Group (Prof. Timothy Noël), University of Amsterdam  

---

## Abstract
Automated platforms, or self-driving labs, are replacing manual bench work to screen reactions quickly. But tracking reactions on the fly is still hard. Why? Inline sensors like UV-Vis simply can't resolve similar products, whereas HPLC and GC-MS separations introduce long column delays and generate overlapping peaks that require manual integration. This proposal solves that. We link our pipeline, CHROMA-AGENT-ALPHA, to continuous flow systems. A Graph Neural Network (GNN) separates the co-eluting peaks, and a tiered agent framework uses these results to tune the pumps and heaters. It is a closed loop. We can monitor and optimize chemistry as it runs.

---

## 1. Context and Problem Statement
Continuous flow setups run reactions in a moving stream. This setup gives you excellent heat transfer, tight parameter control, and simple scaling. Because of this, chemists now use self-optimizing flow platforms that adjust settings based on active learning algorithms.

But the analytical tools in these feedback loops cause problems:
1.  **Inline Spectroscopy:** UV-Vis and IR instruments are fast. But their signals overlap when mixtures are complex. This hides impurities and structural isomers.
2.  **Chromatography:** HPLC and GC-MS give detailed separations. However, they introduce delay as compounds move through columns. They also create raw data that requires manual peak integration, especially when peaks overlap.

We built CHROMA-AGENT-ALPHA to solve this. It automates raw chromatography parsing, applies Asymmetric Least Squares (ALS) baseline correction, and uses a two-layer Graph Convolutional Network (GCN) to resolve overlapping peaks. In tests on polymer mixtures, this pipeline corrected up to 49% of the signal double-counting errors caused by peak overlaps. This PhD project will connect our pipeline directly to a flow reactor, creating a self-driving lab that analyzes and optimizes reactions without human intervention.

---

## 2. Project Goals
*   **Link Flow Reactors to the Pipeline:** Build an automated fluid-handling interface between a Vapourtec flow reactor outlet and a GC-MS or HPLC instrument.
*   **Speed Up GNN Predictions:** Optimize the Graph Neural Network to run deconvolution in under 30 seconds so the system can estimate yields quickly.
*   **Run Closed-Loop Control:** Deploy a dual-agent system. A high-level agent plans the experiments using Bayesian optimization, while a low-level agent adjusts pump flow rates and temperatures.
*   **Validate on Multi-Step Synthesis:** Validate the platform by optimizing a multi-step reaction, like photocatalytic C-H activation, that generates complex chromatography profiles.

---

## 3. How We Will Build It

```
                  ┌────────────────────────────────────────┐
                  ▼                                        │
    ┌─────────────────────────┐               ┌────────────┴────────────┐
    │  Continuous Flow Setup  │               │   Macro Agent (T3/T4)   │
    │  (Pumps, Temp, Light)   │               │   Active Learning Loop  │
    └────────────┬────────────┘               └────────────▲────────────┘
                 │                                         │
                 ▼ (Auto-Sampling)                         │ (New Parameters)
    ┌─────────────────────────┐                            │
    │  GC-MS / HPLC Analysis  │               ┌────────────┴────────────┐
    └────────────┬────────────┘               │   Micro Agent (T1/T2)   │
                 │                               - Parse Yield & Purity │
                 ▼ (Raw Telemetry)               - Check Safety Bounds  │
    ┌─────────────────────────┐               └────────────▲────────────┘
    │   CHROMA Ingestion &    │                            │
    │   ALS Baseline stage    │                            │ (Clean Data)
    └────────────┬────────────┘                            │
                 │                                         │
                 ▼                                         │
    ┌─────────────────────────┐                            │
    │   GCN Deconvolution &   ├────────────────────────────┘
    │   matchms Identification│
    └─────────────────────────┘
```

### 3.1 Flow Reactor to GC-MS Interface
We will build an automated sampling loop to run GC-MS/HPLC analysis without human help. When the flow reactor reaches steady state, a liquid-handling robot will dilute and inject the reaction stream. The chromatography files are then saved to a watched folder.

### 3.2 Real-Time Processing Pipeline
Saving a raw file triggers the data processing steps:
1.  **File Ingestion:** The system parses raw NetCDF or mzML files into Polars dataframes.
2.  **Graph Setup:** For overlapping peak zones, the script builds a 1D graph where nodes represent scans and edges connect adjacent time points.
3.  **GNN Inference:** The GCN classifies the nodes and predicts component purity scores, which adjusts the integration area.
4.  **Spectral Matching:** The matchms library matches mass spectra against libraries to identify products and byproducts.

### 3.3 Bayesian Active Learning Loop
The high-level agent uses the identified compounds and corrected peak areas to compute reaction yields. It then uses a Bayesian active learning loop to calculate the next set of parameters (temperature, residence time, reactant ratios). The agent translates these parameters into pump speeds and heater commands to run the next experiment.

---

## 4. Expected Impact
Adding this chromatography loop will:
*   **Solve complex mixtures** containing structural isomers or transient intermediates that standard inline sensors cannot resolve.
*   **Save raw files and run decisions** in Zarr v3 arrays registered with LaminDB, keeping data open and reproducible.
*   **Provide a low-compute framework** (using under ₹500/month in API costs) that lets smaller labs run automated experiments without paying for expensive enterprise software.

This project aligns with the focus of the UvA flow group. It adds GNN-assisted chromatography to flow chemistry, offering a practical path toward autonomous discovery.
