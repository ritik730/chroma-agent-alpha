# CHROMA-AGENT-ALPHA // SCIENTIFIC GROUNDING & COMPLIANCE
# Auto-read by Claude Code & Antigravity to enforce physical chemistry constraints.

This document serves as the scientific ground-truth manifest for `CHROMA-AGENT-ALPHA`. All automated code changes, optimization loops, and data-processing scripts must comply with the physical models and mathematical bounds defined below. 

---

## 1. Unified Mathematical Models

### A. Column Pressure Drop (Kozeny-Carman Model)
For packed column chromatography (such as HPLC), the pressure drop across the column bed must satisfy the Kozeny-Carman relationship:

\[\Delta P = \frac{180 \eta L (1 - \epsilon)^2 u}{\epsilon^3 d_p^2}\]

Where:
- \(\Delta P\) = Column pressure drop (\(\text{Pa}\))
- \(\eta\) = Mobile phase dynamic viscosity (\(\text{Pa}\cdot\text{s}\))
- \(L\) = Column length (\(\text{m}\))
- \(\epsilon\) = Interstitial porosity of the column packing (\(\approx 0.38 - 0.45\))
- \(u\) = Mobile phase linear velocity (\(\text{m/s}\))
- \(d_p\) = Packing material particle diameter (\(\text{m}\))

#### Enforced Constraints:
- Any proposed flow rate/velocity that causes the calculated pressure drop \(\Delta P\) to exceed the column's physical pressure limit (e.g., \(400 \text{ bar}\) for standard HPLC systems, \(1000 \text{ bar}\) for UHPLC systems) must be rejected by the validation parser.

---

### B. Gas Chromatography Retention & Temperature (Clausius-Clapeyron Model)
The retention factor \(k'\) in gas chromatography relates to temperature \(T\) through the thermodynamic enthalpy of vaporization \(\Delta H_{\text{vap}}\), modeled via the log-linear Clausius-Clapeyron relationship:

\[\ln(k') = \frac{\Delta H_{\text{vap}}}{R T} - \frac{\Delta S_{\text{vap}}}{R} + \ln\left(\frac{V_S}{V_M}\right)\]

Where:
- \(k'\) = Retention factor
- \(R\) = Ideal gas constant (\(8.314 \text{ J/mol}\cdot\text{K}\))
- \(T\) = Absolute oven temperature (\(\text{K}\))
- \(\Delta H_{\text{vap}}\) = Enthalpy of adsorption/vaporization
- \(V_S, V_M\) = Volumes of stationary and mobile phases respectively

#### Enforced Constraints:
- **Retention Time Drift Rule:** In any GC optimization run, an increase in oven temperature \(T\) must result in a logarithmic decrease in the retention factor \(k'\) (and therefore retention time \(t_R\)). 
- Any code that predicts or simulates an increase in retention time as oven temperature increases is physically invalid and must trigger an assertion failure.

---

### C. Column Efficiency (van Deemter Equation)
The Height Equivalent to a Theoretical Plate (HETP, \(H\)) represents column efficiency as a function of mobile phase linear velocity \(u\):

\[H = A + \frac{B}{u} + C \cdot u\]

Where:
- \(H\) = HETP (\(\text{m}\) or \(\text{mm}\))
- \(A\) = Eddy diffusion (reflects packing uniformity)
- \(B\) = Longitudinal diffusion (dominant at low velocities)
- \(C\) = Mass transfer resistance (dominant at high velocities)
- \(u\) = Linear mobile phase velocity (\(\text{m/s}\) or \(\text{mm/s}\))

#### Enforced Constraints:
- Any method optimization script searching for the optimal flow rate must calculate the optimum velocity \(u_{\text{opt}} = \sqrt{B/C}\) to verify that the system runs near maximum chromatographic resolution.

---

### D. Capillary Flow Dynamics (Poiseuille's Law)
For open tubular capillary columns in gas chromatography, the flow rate \(F\) is governed by compressibility-corrected Poiseuille flow:

\[F = \frac{\pi r^4 (p_i^2 - p_o^2)}{16 \eta L p_o}\]

Where:
- \(F\) = Flow rate at column outlet reference pressure (\(\text{m}^3/\text{s}\))
- \(r\) = Capillary column internal radius (\(\text{m}\))
- \(p_i, p_o\) = Inlet and outlet absolute pressures respectively (\(\text{Pa}\))
- \(\eta\) = Carrier gas viscosity at column temperature (\(\text{Pa}\cdot\text{s}\))
- \(L\) = Capillary column length (\(\text{m}\))

#### Enforced Constraints:
- Capillary column gas flow must be computed using dynamic viscosity \(\eta(T)\) adjusted for oven temperature (as temperature increases, carrier gas viscosity increases, causing flow rates to decrease at constant pressure).

---

## 2. Double-Loop AI Verification Rules

To prevent code hallucination, all pipeline scripts processing data or generating optimization suggestions must run a **Double-Loop Audit**:

1.  **Loop 1 (Execution):** The script executes mathematical integration (using `numpy.trapz`) and peak deconvolution (using the spatial-temporal GCN and EMG curve fitting).
2.  **Loop 2 (Verification Assertions):** The code must run automated assertions testing physical constraints:
    ```python
    # Example assertion check
    assert calculated_baseline >= 0.0, "Physical error: negative baseline calculated"
    assert resolved_peak_area <= raw_unresolved_peak_area * 1.05, "Purity softmax error: resolved peak areas exceed raw signal bound"
    ```

Any file modifications that omit these validation assertions or violate the physical equations defined in this document must be rejected by the pre-commit checks.
