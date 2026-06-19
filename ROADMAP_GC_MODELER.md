# PhD Research Proposal: Physics-Informed ML for Autonomous GC Method Development
**Project Roadmap: Integrating Predictive Chromatogram Simulation into CHROMA-AGENT-ALPHA**  
**Author:** Devendra Kataria (MSc Chemistry, 82% | 2027 PhD Target)  
**Status:** Research Proposal Draft & Project Roadmap  

---

## 1. Executive Summary

Autonomous Self-Driving Laboratories (SDLs) represent the frontier of high-throughput chemical discovery. However, a major bottleneck remains the dynamic optimization of online chromatography methods (GC-MS, HPLC). Current systems rely either on passive data post-processing or manual method translation. When analytical runs experience peak co-elution, the closed-loop optimization fails due to area double-counting errors (up to 48%).

This proposal outlines a hybrid, **Physics-Informed Machine Learning (PIML)** approach to bridge this gap. By combining a Graph Neural Network (GNN) for Quantitative Structure-Property Relationship (QSPR) thermodynamic predictions with classical capillary flow gas dynamics, the system will simulate gas chromatography separations *in silico*. This predictive modeler will act as a closed-loop controller: when co-elution is detected, the agent simulates alternative separation methods and dynamically updates the instrument's parameters for the next physical injection.

---

## 2. Scientific & Mathematical Foundations

The proposed simulator combines deep learning on molecular structures with three main pillars of physical chemistry, already mapped out in the core project manifest:

### A. Molecular Thermodynamics (Clausius-Clapeyron Model)
The retention factor $k'$ of an analyte on a stationary phase is governed by its enthalpy ($\Delta H_{\text{vap}}$) and entropy ($\Delta S_{\text{vap}}$) of vaporization/adsorption:

$$\ln(k') = \frac{\Delta H_{\text{vap}}}{R T} - \frac{\Delta S_{\text{vap}}}{R} + \ln\left(\frac{V_S}{V_M}\right)$$

Where $R$ is the gas constant, $T$ is the oven temperature, and $V_S/V_M$ is the phase volume ratio. Instead of relying on static databases of known values, **a GNN will predict $\Delta H_{\text{vap}}$ and $\Delta S_{\text{vap}}$ directly from molecular structure graphs**, allowing the system to simulate chromatograms for novel, synthesized molecules.

### B. Capillary Gas Dynamics (Compressibility-Corrected Poiseuille Flow)
As the oven temperature $T(t)$ increases, carrier gas viscosity $\eta(t)$ rises, causing carrier gas velocity $u(t)$ to drift. Capillary flow is governed by Poiseuille flow under compressibility:

$$F_{\text{out}}(t) = \frac{\pi r^4 (p_i^2 - p_o^2)}{16 \eta(T(t)) L p_o}$$

Where $r$ and $L$ are column dimensions, and $p_i$ and $p_o$ are inlet/outlet absolute pressures.

### C. Column Efficiency & Peak Shape (van Deemter & EMG Models)
Column efficiency ($N$, theoretical plates) is modeled using the van Deemter equation:

$$H(t) = A + \frac{B}{u(t)} + C \cdot u(t) \quad \text{where} \quad N(t) = \frac{L}{H(t)}$$

Peak profiles are simulated by combining elution times $t_R$ and peak variances $\sigma^2 = t_R^2 / N$ into an **Exponentially Modified Gaussian (EMG)** function to model physical peak tailing ($\tau$):

$$f(t) = \frac{A_0}{\tau} \exp\left( \frac{\sigma^2}{2\tau^2} - \frac{t - t_R}{\tau} \right) \cdot \Phi\left( \frac{t - t_R}{\sigma} - \frac{\sigma}{\tau} \right)$$

---

## 3. Implementation Roadmap & PhD Milestones

The integration of the modeler into `CHROMA-AGENT-ALPHA` will proceed across four key academic milestones during the PhD candidacy:

```
[Phase 1: GNN-QSPR Data Prep] ──► [Phase 2: Numerical Solver] ──► [Phase 3: Closed-Loop API] ──► [Phase 4: Lab Validation]
```

### Phase 1: GNN-QSPR Framework & Dataset Curation (Months 1–12)
*   **Objective:** Develop the deep learning layer that maps 2D chemical structure graphs to thermodynamic parameters.
*   **Key Tasks:**
    *   Compile reference retention index datasets (e.g., NIST, PubChem) across common stationary phases (HP-5MS, DB-Wax).
    *   Build a Graph Neural Network (such as a Graph Convolutional Network or Graph Attention Network) using PyTorch Geometric.
    *   Apply scaffold-splitting methods during validation to evaluate the model's prediction accuracy on structurally novel ("cold-start") molecules.
*   **Deliverable:** A trained, CPU-optimized GNN model that outputs $(\Delta H_{\text{vap}}, \Delta S_{\text{vap}})$ predictions from a molecular SMILES string.

### Phase 2: Capillary Migration Numerical Solver (Months 12–18)
*   **Objective:** Code the physical dynamic migration solver in Python.
*   **Key Tasks:**
    *   Write a numerical integration solver (using Euler or Runge-Kutta methods) to calculate analyte column migration $X(t)$ under complex, multi-step oven temperature ramps $T(t)$.
    *   Implement temperature-dependent gas viscosity corrections and column compressibility factors.
    *   Generate synthetic `.mzML` raw mass spectrometry data files from simulated chromatographic peaks.
*   **Deliverable:** A functional simulation engine (`chroma/simulation/gc_modeler.py`) validated against empirical retention times with $R^2 \ge 0.98$.

### Phase 3: Closed-Loop Decision Engine & Web API (Months 18–24)
*   **Objective:** Wire the simulator into the automated n8n and FastAPI pipeline.
*   **Key Tasks:**
    *   Develop a decision-making layer: if downstream peak suitability checks report peak resolution $R_s < 1.0$, trigger the simulator.
    *   Implement a Bayesian optimization loop (using libraries like BoTorch) that queries the simulator to evaluate alternative oven temperature rates and carrier gas pressures.
    *   Select the method that maximizes peak separation while minimizing analysis time.
*   **Deliverable:** A local REST API endpoint (`POST /run/optimize-method`) that outputs optimized instrument settings when deconvolution limits are exceeded.

### Phase 4: Self-Driving Lab Deployment & Validation (Months 24–36)
*   **Objective:** Connect the pipeline to physical GC-MS instruments and automated sample handling systems.
*   **Key Tasks:**
    *   Integrate with continuous-flow reactors and autosamplers via instrument communication scripts (e.g., Agilent ChemStation macro commands or open-source control layers).
    *   Run automated closed-loop screenings of multi-component synthesis mixtures.
    *   Evaluate run times, deconvolution accuracy, and Bayesian optimizer convergence speed.
*   **Deliverable:** A fully autonomous, closed-loop self-driving laboratory setup.

---

## 4. Academic Publication & Dissemination Plan

This research roadmap is structured to yield high-impact peer-reviewed publications:

1.  **Paper 1 (Phase 1–2):** *"Physics-Informed Graph Neural Networks for Predicting Gas Chromatography Retention of Novel Synthesized Chemical Species."*  
    *   *Target Journal:* **Journal of Chemical Information and Modeling** or **Bioinformatics**.
2.  **Paper 2 (Phase 3):** *"An Autonomous Agentic Framework for Chromatographic Method Development in Lab 4.0 Telemetry."*  
    *   *Target Journal:* **Analytical Chemistry** or **Journal of Chromatography A**.
3.  **Paper 3 (Phase 4 - Thesis Core):** *"Closed-Loop Automated Synthesis of Multi-Component Libraries via Real-Time GNN Deconvolution and Physics-Informed Method Optimization."*  
    *   *Target Journal:* **SLAS Technology** or **Nature Synthesis**.

---

## 5. Summary of Integration in CHROMA-AGENT-ALPHA

The structural skeleton for this roadmap is physically documented in your repository:
*   **Mathematical Grounding:** [GROUNDING.md](file:///C:/chroma-agent-alpha/GROUNDING.md) defines the physical bounds and assertions required to prevent model hallucinations.
*   **Code Blueprint:** [scripts/gc_modeler.py](file:///C:/chroma-agent-alpha/scripts/gc_modeler.py) provides the non-functional skeleton containing viscosity, flow, and elution equations, ready to be activated.
*   **Roadmap Reference:** [README.md](file:///C:/chroma-agent-alpha/README.md#8-future-roadmap-predictive-chromatogram-simulation) features the high-level roadmap to demonstrate your project vision to PhD admissions boards.
