# OPERATOR DIRECTION: Spectral Matching & FAIR Data Archiving (SLAS Spec)
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-06-03
> To: Dual-Agent System (Antigravity & Claude Code)

Our GNN peak deconvolution is resolving overlapping areas. Now we need to identify the deconvolved peaks and secure our data lineage for the *SLAS Technology* manuscript.

**My Requirements:**
1. Implement spectral library matching. Match our mass spectra against open reference libraries (like GNPS) to identify the compounds (enforce a similarity score threshold of 0.7).
2. For the data archiving layer, we must follow FAIR data principles. Store our data arrays in a chunked Zarr format and track every transformation step using a LaminDB database backend. This gives us a complete, auditable lineage from the raw instrument file to the final tables.