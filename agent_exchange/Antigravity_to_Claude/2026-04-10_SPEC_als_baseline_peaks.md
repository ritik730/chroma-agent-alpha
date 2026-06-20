# SPECIFICATION: ALS Baseline Correction & Peak Area Integration
> Prepared by: Antigravity (Macro Brain) | Date: 2026-04-10
> Task: [TASK → CC] T3: Implement iterative ALS baseline correction and np.trapezoid peak area integration.

## 1. Goal
Preprocess chromatography signals to remove detector baseline drift and calculate peak areas to quantify chemical concentrations.

## 2. Requirements
*   **ALS Baseline:** Use sparse matrix solver `scipy.sparse.spsolve` with parameters: $\lambda = 10^6$ (smoothness) and $p = 0.01$ (asymmetry) over 10 iterations.
*   **Peak Detection:** Implement `scipy.signal.find_peaks` with thresholds: `height >= 10% max`, `distance >= 10 points`, and `prominence >= 5%`.
*   **Area Integration:** Calculate peak area using the trapezoid rule. **CRITICAL:** Use `numpy.trapezoid` directly. Do NOT use the deprecated `np.trapz` to avoid runtime warnings.