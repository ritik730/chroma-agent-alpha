# SPECIFICATION: Ingestion & Vendor-Independent Binary Parsers
> Prepared by: Antigravity (Macro Brain) | Date: 2026-03-15
> Task: [TASK → CC] T3: Write pure-Python binary parsers for Agilent .ch and Varian .xms/.sms files.

## 1. Goal
Read raw chromatography instrument telemetry without vendor GUI wrappers or proprietary software licenses (Agilent ChemStation/Waters Empower). Extract time and abundance arrays into a unified pandas/numpy data structure.

## 2. Requirements
*   **Varian Parser (.xms/.sms):** Read raw byte arrays, map double-precision float structures, and parse scan indexes.
*   **Agilent Parser (.ch):** Locate data offsets, handle header metadata, and convert byte streams to chromatogram coordinates.
*   **Output Format:** Standard JSON dictionary containing `{sample_id, retention_time: list[float], abundance: list[float]}`.
*   **Validation:** Verify against open-source NetCDF4 standards.