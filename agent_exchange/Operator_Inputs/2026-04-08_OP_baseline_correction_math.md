# OPERATOR DIRECTION: Chemometrics Design — Baseline Correction & Peak Area Math
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-04-08
> To: Dual-Agent System (Antigravity & Claude Code)

Ingestion is running successfully. Now we need to implement the core analytical chemistry logic. 

Our raw chromatograms have significant baseline drift (instrumental noise and column bleed) which distort peak heights and areas. To get publishable results, we must resolve this baseline drift before we try to detect peaks.

**My Requirements:**
1. Implement an iterative Asymmetric Least Squares (ALS) baseline correction. It is the standard chemometrics method to smooth out baseline drift. Subtract this baseline from the raw signal.
2. Once corrected, implement a peak detection routine to identify the compound retention times.
3. Calculate the peak areas for concentration quantification. I don't write python code, but make sure to use the most current libraries. Specifically, use `numpy.trapezoid` for the area math—do not use the deprecated `np.trapz` to avoid runtime warnings in our console.