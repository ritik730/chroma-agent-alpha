# SPECIFICATION: matchms Spectral Matching & FAIR LaminDB Layer
> Prepared by: Antigravity (Macro Brain) | Date: 2026-06-05
> Task: [TASK → CC] T3: Integrate matchms spectral matching and LaminDB/Zarr data storage.

## 1. Goal
Identify deconvolved compounds by matching mass spectra against reference databases, and store final datasets in a FAIR-compliant Zarr array format with complete database lineage tracking.

## 2. Requirements
*   **Spectral Matching:** Use `matchms` to calculate cosine similarity against local reference spectral libraries. Enforce `cosine >= 0.7`.
*   **FAIR Storage:** Export parsed data arrays to Zarr v3. Register transformation steps and data lineage in the LaminDB SQLite database instance.