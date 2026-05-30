"""
pipeline_server.py — FastAPI HTTP server wrapping the chroma pipeline scripts.
n8n calls these endpoints instead of using Execute Command (unreliable on Windows).

Endpoints:
  GET  /health              → liveness check
  POST /run/parse_cdf       → runs parse_cdf.py on a .cdf file → returns peaks JSON
  POST /run/enrich          → calls T2 LiteLLM to enrich compound names
  GET  /results/{sample_id} → fetch a previously processed result

Start: python scripts/pipeline_server.py
Port:  8001
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR    = Path(__file__).parent.parent
RAW_DIR     = BASE_DIR / "raw_data"
PROC_DIR    = BASE_DIR / "processed"
SCRIPTS_DIR = BASE_DIR / "scripts"
PYTHON      = sys.executable
LITELLM_URL = "http://localhost:4000"

PROC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="CHROMA-AGENT-ALPHA Pipeline Server",
    description="HTTP API wrapping GC-MS chromatography pipeline stages for n8n orchestration.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Serve Dashboard ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the chromatography control center dashboard HTML page."""
    dashboard_path = SCRIPTS_DIR / "dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="dashboard.html not found in scripts folder")
    return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))


# ── Request / Response models ────────────────────────────────────────

class ParseRequest(BaseModel):
    file: str          # filename only, e.g. "sample_01.cdf" — must be in raw_data/
    min_height: float = 100.0
    prominence: float = 50.0

class EnrichRequest(BaseModel):
    sample_id: str
    peaks: list        # list of peak dicts from /run/parse_cdf
    context: str = "GC-MS chromatography, chemical analysis"

class DeconvRequest(BaseModel):
    sample_id: str

class MatchRequest(BaseModel):
    sample_id: str


# ── Instrument File Upload Endpoint ──────────────────────────────────

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    """Upload a raw chromatography file (.cdf or .mzML) to raw_data/ directory."""
    if not (file.filename.endswith(".cdf") or file.filename.endswith(".mzML")):
        raise HTTPException(status_code=400, detail="Only .cdf and .mzML files are supported.")

    output_path = RAW_DIR / file.filename
    try:
        content = file.file.read()
        output_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

    return {
        "status": "ok",
        "filename": file.filename,
        "message": f"Successfully uploaded {file.filename} to raw_data/"
    }


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe — n8n checks this before starting a workflow."""
    litellm_ok = False
    try:
        r = requests.get(f"{LITELLM_URL}/health", timeout=10, proxies={"http": None, "https": None})
        litellm_ok = r.status_code == 200
    except Exception as e:
        print(f"[HEALTH CHECK ERROR] Failed to connect to LiteLLM: {e}")
        pass
    return {
        "status": "ok" if litellm_ok else "degraded",
        "server": "pipeline_server",
        "litellm_proxy": "up" if litellm_ok else "down",
        "raw_data_files": [f.name for f in RAW_DIR.glob("*.cdf")] + [f.name for f in RAW_DIR.glob("*.mzML")],
        "processed_files": [f.name for f in PROC_DIR.glob("*.json")],
    }


@app.post("/run/parse_cdf")
def run_parse_cdf(req: ParseRequest):
    """
    Run parse_cdf.py on a raw .cdf file.
    Logic: ALS baseline correction → scipy peak detection → np.trapz integration → JSON.
    Returns: {sample_id, peaks: [{retention_time, peak_area_mAU, baseline_corrected}], ...}
    """
    input_file = RAW_DIR / req.file
    if not req.file.strip():
        raise HTTPException(status_code=400, detail="Filename parameter 'file' is empty.")
    if not input_file.exists() or not input_file.is_file():
        raise HTTPException(status_code=404, detail=f"File not found or is a directory: {req.file}")

    sample_id = input_file.stem
    output_file = PROC_DIR / f"{sample_id}.json"

    try:
        result = subprocess.run(
            [PYTHON, str(SCRIPTS_DIR / "parse_cdf.py"), str(input_file)],
            capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="parse_cdf.py timed out after 120s")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail={
            "error": "parse_cdf.py failed",
            "stderr": result.stderr[-1000:],
            "stdout": result.stdout[-500:],
        })

    # parse_cdf.py writes JSON to processed/{sample_id}.json and prints summary to stdout
    if not output_file.exists():
        raise HTTPException(status_code=500, detail={
            "error": f"parse_cdf.py ran but did not produce {output_file.name}",
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
        })

    try:
        data = json.loads(output_file.read_text())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail={
            "error": f"{output_file.name} is not valid JSON",
        })

    return {
        "status": "ok",
        "sample_id": sample_id,
        "output_file": str(output_file),
        "peak_count": len(data.get("peaks", [])),
        "data": data,
    }


@app.post("/run/enrich")
def run_enrich(req: EnrichRequest):
    """
    Call T2 LiteLLM (DeepSeek V4 Flash free) to enrich compound names from peak list.
    Logic: peaks have RT and area — T2 suggests compound class based on retention windows.
    Returns: enriched peak list with compound_class suggestions.
    """
    if not req.peaks:
        raise HTTPException(status_code=400, detail="peaks list is empty")

    summary_lines = []
    for i, p in enumerate(req.peaks[:20]):
        rt_val = p.get('retention_time')
        rt_str = f"{rt_val:.2f}" if isinstance(rt_val, (int, float)) else str(rt_val if rt_val is not None else '?')
        area_val = p.get('peak_area_mAU') or p.get('area')
        area_str = f"{area_val:.1f}" if isinstance(area_val, (int, float)) else str(area_val if area_val is not None else '?')
        summary_lines.append(f"  Peak {i+1}: RT={rt_str}min, area={area_str} mAU")
    peak_summary = "\n".join(summary_lines)

    prompt = f"""You are a chromatography expert. Given these GC-MS peaks from sample '{req.sample_id}':

{peak_summary}

Context: {req.context}

For each peak, suggest:
1. Likely compound class (alcohol, alkane, ester, acid, aromatic, unknown)
2. Confidence: high/medium/low

Return ONLY a JSON array: [{{"peak_index": 1, "compound_class": "...", "confidence": "..."}}]"""

    try:
        r = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": "Bearer sk-litellm-1234", "Content-Type": "application/json"},
            json={
                "model": "claude-t2",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.2,
            },
            timeout=60,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LiteLLM T2 call failed: {e}")

    raw_text = r.json()["choices"][0]["message"]["content"].strip()

    # Try to parse JSON from response
    enriched = []
    try:
        # Extract JSON array if wrapped in markdown
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1].replace("json", "").strip()
        enriched = json.loads(raw_text)
    except json.JSONDecodeError:
        enriched = [{"peak_index": i+1, "compound_class": "parse_error", "confidence": "low"} for i in range(len(req.peaks))]

    # Merge enrichment back into peaks
    enriched_map = {e["peak_index"]: e for e in enriched}
    peaks_enriched = []
    for i, p in enumerate(req.peaks):
        merged = {**p, **(enriched_map.get(i+1, {}))}
        peaks_enriched.append(merged)

    # Save enriched result
    output_file = PROC_DIR / f"{req.sample_id}_enriched.json"
    output_file.write_text(json.dumps({
        "sample_id": req.sample_id,
        "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model_used": "claude-t2 (deepseek-v4-flash:free)",
        "peaks": peaks_enriched,
    }, indent=2))

    return {
        "status": "ok",
        "sample_id": req.sample_id,
        "peaks_enriched": len(peaks_enriched),
        "output_file": str(output_file),
        "peaks": peaks_enriched,
    }


@app.post("/run/deconv")
def run_deconv(req: DeconvRequest):
    """
    Run gnn_deconv.py on a processed sample peaks JSON.
    Uses Graph Neural Network GCN to deconvolve mixed signals.
    """
    input_file = PROC_DIR / f"{req.sample_id}.json"
    if not input_file.exists():
        raise HTTPException(status_code=404, detail=f"Processed peak file not found: {req.sample_id}.json")

    output_file = PROC_DIR / f"{req.sample_id}_deconvolved.json"

    try:
        result = subprocess.run(
            [PYTHON, str(SCRIPTS_DIR / "gnn_deconv.py"), str(input_file)],
            capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="gnn_deconv.py timed out after 120s")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail={
            "error": "gnn_deconv.py failed",
            "stderr": result.stderr[-1000:],
            "stdout": result.stdout[-500:],
        })

    if not output_file.exists():
        raise HTTPException(status_code=500, detail={
            "error": f"gnn_deconv.py ran but did not produce {output_file.name}",
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
        })

    try:
        data = json.loads(output_file.read_text())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail={
            "error": f"{output_file.name} is not valid JSON",
        })

    return data


@app.post("/run/match")
def run_match(req: MatchRequest):
    """
    Run spectral_match.py on deconvolved or raw peaks JSON.
    """
    # Prefer deconvolved peaks if they exist
    input_file = PROC_DIR / f"{req.sample_id}_deconvolved.json"
    if not input_file.exists():
        input_file = PROC_DIR / f"{req.sample_id}.json"

    if not input_file.exists():
        raise HTTPException(status_code=404, detail=f"No peak JSON file found to match for sample: {req.sample_id}")

    output_file = PROC_DIR / f"{req.sample_id}_matched.json"

    try:
        result = subprocess.run(
            [PYTHON, str(SCRIPTS_DIR / "spectral_match.py"), str(input_file)],
            capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR)
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="spectral_match.py timed out after 300s")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail={
            "error": "spectral_match.py failed",
            "stderr": result.stderr[-1000:],
            "stdout": result.stdout[-500:],
        })

    if not output_file.exists():
        raise HTTPException(status_code=500, detail={
            "error": f"spectral_match.py ran but did not produce {output_file.name}",
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
        })

    try:
        data = json.loads(output_file.read_text())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail={
            "error": f"{output_file.name} is not valid JSON",
        })

    # Ensure peaks is returned if not written to matched.json yet
    if "peaks" not in data:
        try:
            data["peaks"] = json.loads(input_file.read_text()).get("peaks", [])
        except Exception:
            pass

    return data


@app.get("/results/{sample_id}")
def get_results(sample_id: str):
    """Fetch a previously processed result from processed/ folder."""
    enriched_file = PROC_DIR / f"{sample_id}_enriched.json"
    raw_file = PROC_DIR / f"{sample_id}.json"

    data = None
    if enriched_file.exists():
        data = json.loads(enriched_file.read_text())
    elif raw_file.exists():
        data = json.loads(raw_file.read_text())

    if data is None:
        raise HTTPException(status_code=404, detail=f"No results found for sample_id: {sample_id}")

    # If this is a matched result, try to merge peaks back into it so the UI has peak coords
    if sample_id.endswith("_matched") and "peaks" not in data:
        base_id = sample_id[:-8]
        # Try deconvolved first
        deconv_file = PROC_DIR / f"{base_id}_deconvolved.json"
        base_file = PROC_DIR / f"{base_id}.json"

        peaks = None
        if deconv_file.exists():
            try:
                peaks = json.loads(deconv_file.read_text()).get("peaks")
            except Exception:
                pass
        if not peaks and base_file.exists():
            try:
                peaks = json.loads(base_file.read_text()).get("peaks")
            except Exception:
                pass

        if peaks:
            data["peaks"] = peaks

    return data


@app.get("/export/{sample_id}")
def export_excel(sample_id: str):
    """Generate and download an Excel (.xlsx) report for a processed sample.
    Merges peaks + match data into a formatted spreadsheet saved to processed/."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # --- Load the best available data ---
    matched_file = PROC_DIR / f"{sample_id}_matched.json"
    deconv_file = PROC_DIR / f"{sample_id}_deconvolved.json"
    base_file = PROC_DIR / f"{sample_id}.json"

    peaks = []
    matches = []
    source_label = "raw"

    if matched_file.exists():
        data = json.loads(matched_file.read_text())
        peaks = data.get("peaks", [])
        matches = data.get("matches", [])
        source_label = "matched"
    elif deconv_file.exists():
        data = json.loads(deconv_file.read_text())
        peaks = data.get("peaks", [])
        source_label = "deconvolved"
    elif base_file.exists():
        data = json.loads(base_file.read_text())
        peaks = data.get("peaks", [])
        source_label = "parsed"
    else:
        raise HTTPException(status_code=404, detail=f"No processed data found for sample: {sample_id}")

    if not peaks:
        raise HTTPException(status_code=404, detail=f"No peaks found in data for sample: {sample_id}")

    # Build match lookup
    match_map = {}
    for m in matches:
        match_map[m.get("peak_index")] = m

    # --- Create workbook ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Peak Results"

    # Styles
    header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    data_font = Font(name="Calibri", size=10)
    data_align = Alignment(horizontal="center", vertical="center")
    match_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    nomatch_fill = PatternFill(start_color="FCE4EC", end_color="FCE4EC", fill_type="solid")

    # Title row
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = f"CHROMA-AGENT-ALPHA — Peak Report: {sample_id}"
    title_cell.font = Font(name="Calibri", bold=True, size=14, color="1F4E79")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Metadata row
    ws.merge_cells("A2:I2")
    meta_cell = ws["A2"]
    meta_cell.value = f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} | Source: {source_label} | Total Peaks: {len(peaks)}"
    meta_cell.font = Font(name="Calibri", size=9, italic=True, color="808080")
    meta_cell.alignment = Alignment(horizontal="center")

    # Headers
    headers = [
        "Peak Index", "RT (min)", "Height (mAU)", "Area (mAU·min)",
        "GNN Purity", "Compound ID", "Compound Class", "Match Score", "Fragments Matched"
    ]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Data rows
    for row_idx, p in enumerate(peaks, 5):
        pidx = p.get("peak_index", "")
        match = match_map.get(pidx)
        row_fill = match_fill if match else nomatch_fill

        values = [
            pidx,
            round(p.get("retention_time", 0), 4),
            round(p.get("peak_height_mAU", 0), 2),
            round(p.get("peak_area_mAU", 0), 2),
            round(p.get("component_purity", 0), 3) if p.get("component_purity") is not None else "N/A",
            match["compound_name"] if match else "unidentified",
            match["compound_class"] if match else "unknown",
            round(match["cosine_similarity"], 4) if match else "N/A",
            match.get("n_fragments_matched", "N/A") if match else "N/A",
        ]

        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.alignment = data_align
            cell.border = thin_border
            cell.fill = row_fill

    # Column widths
    col_widths = [12, 12, 14, 16, 12, 35, 18, 14, 18]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Freeze header row
    ws.freeze_panes = "A5"

    # Summary sheet
    ws2 = wb.create_sheet(title="Summary")
    ws2["A1"] = "CHROMA-AGENT-ALPHA Pipeline Summary"
    ws2["A1"].font = Font(name="Calibri", bold=True, size=14, color="1F4E79")
    summary_data = [
        ("Sample ID", sample_id),
        ("Total Peaks", len(peaks)),
        ("Matched Peaks", len(matches)),
        ("Unmatched Peaks", len(peaks) - len(matches)),
        ("Match Rate", f"{len(matches)/len(peaks)*100:.1f}%" if peaks else "0%"),
        ("Pipeline Stage", source_label),
        ("Export Time", time.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    for row_idx, (label, value) in enumerate(summary_data, 3):
        ws2.cell(row=row_idx, column=1, value=label).font = Font(name="Calibri", bold=True, size=10)
        ws2.cell(row=row_idx, column=2, value=value).font = Font(name="Calibri", size=10)
    ws2.column_dimensions["A"].width = 20
    ws2.column_dimensions["B"].width = 30

    # Save and return
    output_path = PROC_DIR / f"{sample_id}_results.xlsx"
    wb.save(str(output_path))

    return FileResponse(
        path=str(output_path),
        filename=f"{sample_id}_results.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/run/full_pipeline")
def run_full_pipeline(req: ParseRequest):
    """Run the full pipeline: parse_cdf → gnn_deconv → spectral_match in sequence."""
    # Stage 1: Parse CDF
    input_file = RAW_DIR / req.file
    if not req.file.strip():
        raise HTTPException(status_code=400, detail="Filename parameter 'file' is empty.")
    if not input_file.exists() or not input_file.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file}")

    sample_id = input_file.stem
    stages_completed = []

    # Parse
    try:
        result = subprocess.run(
            [PYTHON, str(SCRIPTS_DIR / "parse_cdf.py"), str(input_file)],
            capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail={"error": "parse_cdf.py failed", "stage": "parse", "stderr": result.stderr[-500:]})
        stages_completed.append("parse")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="parse_cdf.py timed out")

    # Deconvolve
    parse_output = PROC_DIR / f"{sample_id}.json"
    if parse_output.exists():
        try:
            result = subprocess.run(
                [PYTHON, str(SCRIPTS_DIR / "gnn_deconv.py"), str(parse_output)],
                capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
            )
            if result.returncode == 0:
                stages_completed.append("deconv")
        except subprocess.TimeoutExpired:
            pass  # Continue to match even if deconv times out

    # Match
    match_input = PROC_DIR / f"{sample_id}_deconvolved.json"
    if not match_input.exists():
        match_input = parse_output

    if match_input.exists():
        try:
            result = subprocess.run(
                [PYTHON, str(SCRIPTS_DIR / "spectral_match.py"), str(match_input)],
                capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR)
            )
            if result.returncode == 0:
                stages_completed.append("match")
        except subprocess.TimeoutExpired:
            print("[FULL PIPELINE] Matching timed out after 300s.")
            pass

    # Load final result
    final_file = PROC_DIR / f"{sample_id}_matched.json"
    if not final_file.exists():
        final_file = PROC_DIR / f"{sample_id}_deconvolved.json"
    if not final_file.exists():
        final_file = parse_output

    final_data = {}
    if final_file.exists():
        final_data = json.loads(final_file.read_text())

    return {
        "status": "ok",
        "sample_id": sample_id,
        "stages_completed": stages_completed,
        "peak_count": len(final_data.get("peaks", [])),
        "match_count": len(final_data.get("matches", [])),
    }


if __name__ == "__main__":
    print("=" * 55)
    print("  CHROMA-AGENT-ALPHA Pipeline Server")
    print("  http://localhost:8001")
    print("  Docs: http://localhost:8001/docs")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
