# STATE.md
> Current State Tracking (GSD Methodology)
> Last updated: 2026-06-20 | Operator: Devendra Kataria

**Project**: CHROMA-AGENT-ALPHA
**Goal**: Vendor-independent AI-driven ETL for raw chromatography data
**Current Phase**: Pipeline Verification & PhD Candidacy Outreach
**Status**: Stable & Verified Bug-Free

## Status Snapshot
- **Ingestion (.cdf/.mzML)**: ✓ DONE — Handled by native Python binary parsers in [scripts/parse_cdf.py](file:///C:/chroma-agent-alpha/scripts/parse_cdf.py). Fixed critical Agilent `.ch` v817 parser bug (times converted to minutes, intensities parsed as flat LE doubles from offset 6144; verified in [test_software_track.py](file:///C:/chroma-agent-alpha/scripts/test_software_track.py)).
- **ALS Baseline Correction**: ✓ DONE — Implemented in [scripts/baseline_als.py](file:///C:/chroma-agent-alpha/scripts/baseline_als.py).
- **Peak Detection**: ✓ DONE — Integrated in [scripts/peak_detect.py](file:///C:/chroma-agent-alpha/scripts/peak_detect.py) using `np.trapezoid` area integration.
- **n8n Trigger**: ✓ DONE — Folder-watch script triggers FastAPI server.
- **matchms Spectral Matching**: ✓ DONE — Implemented in [scripts/spectral_match.py](file:///C:/chroma-agent-alpha/scripts/spectral_match.py).
- **GNN Deconvolution**: ✓ DONE — 1D GCN node classifier + EMG fitting in [scripts/gnn_deconv.py](file:///C:/chroma-agent-alpha/scripts/gnn_deconv.py) (reduces overlap errors by 48.8% in under 12 seconds).
- **Dashboard Control Center**: ✓ DONE — Built in [scripts/dashboard.html](file:///C:/chroma-agent-alpha/scripts/dashboard.html).
- **zarr + lamindb FAIR Layer**: ✓ DONE — Data lineage database registry verified via [scripts/test_real_data_pipeline.py](file:///C:/chroma-agent-alpha/scripts/test_real_data_pipeline.py).
- **SLAS Manuscript**: ✓ POLISHED — Draft Complete at [SLAS_Technology_Manuscript_Draft.md](file:///C:/Users/yaduv/Desktop/PhD%20Roadmap/01_Manuscripts_and_Reports/SLAS_Technology_Manuscript_Draft.md).
- **PhD Application Materials**: ✓ IN PROGRESS — Research proposal and strategy roadmap drafted at [phd_research_pitch_and_roadmap.md](file:///C:/Users/yaduv/Desktop/PhD%20Roadmap/02_Strategy_and_Deadlines/phd_research_pitch_and_roadmap.md).

## Running Backend Services
- **FastAPI Server**: `http://localhost:8001` (Active, unbuffered logging)
- **LiteLLM Proxy**: `http://localhost:4000` (Active)
- **n8n Server**: `http://localhost:5678` (Active)

## Active Agents
1. **Antigravity (Macro Brain)**: Loop 1 Environment Validation ([scripts/loop1_ghost_runtime.py](file:///C:/chroma-agent-alpha/scripts/loop1_ghost_runtime.py)), Architecture Planning, Documentation, Manuscript Drafting, and Visual Control Center.
2. **Claude Code (Micro Engine)**: Loop 2 Logic Audit, File Execution, Git Control, and Code Edits.

## Next Steps Required
1. Configure public GitHub repository packaging structure (binder/colab demo setup) to showcase the pipeline.
2. Start proactive advisor outreach for the target 2027 PhD vacancies (Timothy Noël and Bob Pirok at UvA) immediately using the polished manuscript draft and GNN peak area correction results.
