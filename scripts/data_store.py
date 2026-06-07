"""
data_store.py — FAIR Storage Layer for CHROMA-AGENT-ALPHA.
Serializes raw chromatography profiles and peak telemetry to Zarr.
Registers generated storage assets and Excel deliverables in LaminDB.
"""
import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import zarr

# Cache directory configuration
PROC_DIR = Path(r"C:\chroma-agent-alpha\processed\.cache")
ZARR_STORE_PATH = r"C:\chroma-agent-alpha\processed\chroma_store.zarr"

def load_merged_peak_data(sample_id: str) -> dict:
    """Loads and merges peak data from intermediate stages (deconv, matched, enriched)."""
    parsed_file = PROC_DIR / f"{sample_id}.json"
    deconv_file = PROC_DIR / f"{sample_id}_deconvolved.json"
    matched_file = PROC_DIR / f"{sample_id}_matched.json"
    enriched_file = PROC_DIR / f"{sample_id}_enriched.json"

    data = {}
    if parsed_file.exists():
        try:
            with open(parsed_file, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[STORE] Warning: Could not read parsed file: {e}")

    if not data:
        # Fallback to loading whatever is available
        for f in [deconv_file, matched_file, enriched_file]:
            if f.exists():
                try:
                    with open(f, "r") as fp:
                        data = json.load(fp)
                        break
                except Exception:
                    pass

    if not data:
        raise FileNotFoundError(f"No parsed JSON result found for sample: {sample_id}")

    # Initialize keys
    if "peaks" not in data:
        data["peaks"] = []

    # Layer GNN deconvolution GCN data
    if deconv_file.exists():
        try:
            with open(deconv_file, "r") as f:
                deconv_data = json.load(f)
                if "peaks" in deconv_data:
                    data["peaks"] = deconv_data["peaks"]
        except Exception as e:
            print(f"[STORE] Warning: Could not merge GNN data: {e}")

    # Layer spectral matches
    matches_map = {}
    if matched_file.exists():
        try:
            with open(matched_file, "r") as f:
                matched_data = json.load(f)
                for match in matched_data.get("matches", []):
                    peak_idx = match.get("peak_index")
                    if peak_idx is not None:
                        matches_map[peak_idx] = match
                if "peaks" in matched_data:
                    data["peaks"] = matched_data["peaks"]
        except Exception as e:
            print(f"[STORE] Warning: Could not merge matches: {e}")

    # Layer AI enrichment classes & confidence
    enriched_peaks_map = {}
    if enriched_file.exists():
        try:
            with open(enriched_file, "r") as f:
                enriched_data = json.load(f)
                enriched_peaks_map = {p.get("peak_index"): p for p in enriched_data.get("peaks", [])}
        except Exception as e:
            print(f"[STORE] Warning: Could not merge enriched data: {e}")

    # Merge match names, scores, classes and confidence values back into peaks array
    for p in data["peaks"]:
        p_idx = p.get("peak_index")
        
        # Merge spectral matches
        if p_idx in matches_map:
            p["compound_name"] = matches_map[p_idx].get("compound_name", "unknown")
            p["match_score"] = matches_map[p_idx].get("cosine_similarity", 0.0)
        else:
            if "compound_name" not in p or p["compound_name"] in ("unknown", "unidentified"):
                p["compound_name"] = p.get("compound_name", "unknown")
            p["match_score"] = p.get("match_score", 0.0)

        # Merge AI classes
        if p_idx in enriched_peaks_map:
            p["compound_class"] = enriched_peaks_map[p_idx].get("compound_class", "unknown")
            p["confidence"] = enriched_peaks_map[p_idx].get("confidence", "unknown")
        else:
            if "compound_class" not in p or p["compound_class"] == "unknown":
                p["compound_class"] = p.get("compound_class", "unknown")
            if "confidence" not in p or p["confidence"] == "unknown":
                p["confidence"] = p.get("confidence", "unknown")

    return data

def save_run_to_zarr(
    sample_id: str, 
    raw_cdf_path: str,
    sample_weight: float = 0.1000,
    api_conc: float = 1.0000,
    calibrations: dict = None
) -> str:
    """Extracts raw chromatogram telemetry and merges peak tables to save to a Zarr Group."""
    print(f"[STORE] Initiating Zarr archive process for {sample_id}...")
    
    # 1. Parse raw CDF telemetry via parse_cdf
    import sys
    sys.path.append(str(Path(__file__).parent))
    import parse_cdf
    
    rt, intensity, meta = parse_cdf.load_any_file(raw_cdf_path)
    
    # 2. Load and merge peak tables
    merged_data = load_merged_peak_data(sample_id)
    peaks = merged_data.get("peaks", [])
    
    # 3. Construct Zarr Arrays
    # Open/Create global multi-sample Zarr group
    os.makedirs(os.path.dirname(ZARR_STORE_PATH), exist_ok=True)
    root = zarr.open_group(ZARR_STORE_PATH, mode="w")
    
    # Create or replace subgroup for this sample
    sample_group = root.create_group(sample_id, overwrite=True)
    
    # Write raw arrays
    rt_arr = sample_group.create_array("retention_times", shape=rt.shape, dtype="float32")
    rt_arr[:] = rt.astype(np.float32)
    
    int_arr = sample_group.create_array("intensities", shape=intensity.shape, dtype="float32")
    int_arr[:] = intensity.astype(np.float32)
    
    # Extract peak arrays
    num_peaks = len(peaks)
    peak_idx = np.array([p.get("peak_index", 0) for p in peaks], dtype=np.int32)
    peak_rt = np.array([p.get("retention_time", 0.0) for p in peaks], dtype=np.float32)
    peak_height = np.array([p.get("peak_height_mAU", 0.0) for p in peaks], dtype=np.float32)
    peak_area = np.array([p.get("peak_area_mAU", 0.0) for p in peaks], dtype=np.float32)
    peak_purity = np.array([p.get("component_purity", 1.0) for p in peaks], dtype=np.float32)
    peak_coeluting = np.array([1 if p.get("coeluting", False) else 0 for p in peaks], dtype=np.int8)
    
    peak_compound_name = [p.get("compound_name", "unknown") for p in peaks]
    peak_compound_class = [p.get("compound_class", "unknown") for p in peaks]
    peak_match_score = np.array([p.get("match_score", 0.0) for p in peaks], dtype=np.float32)
    peak_confidence = [p.get("confidence", "unknown") for p in peaks]
    
    # USP <467> Regulatory Limit Reference Library
    USP_467_LIMITS = {
        "benzene": 2.0,
        "carbon tetrachloride": 4.0,
        "1,2-dichloroethane": 5.0,
        "1,1-dichloroethene": 8.0,
        "1,1,1-trichloroethane": 10.0,
        "methanol": 3000.0,
        "acetonitrile": 410.0,
        "dichloromethane": 600.0,
        "hexane": 290.0,
        "toluene": 890.0,
        "ethanol": 5000.0,
        "acetone": 5000.0,
        "ethyl acetate": 5000.0,
        "tetrahydrofuran": 720.0,
        "isopropanol": 5000.0,
        "propanol": 5000.0,
        "1-propanol": 5000.0,
        "2-propanol": 5000.0,
        "butanol": 5000.0,
        "1-butanol": 5000.0,
        "2-butanol": 5000.0,
        "isobutanol": 5000.0
    }

    # Pre-populate default calibrations if none supplied
    if calibrations is None:
        calibrations = {
            "Methanol": {"CStd": 3000.0, "rStd": 15000000.0},
            "Ethanol": {"CStd": 5000.0, "rStd": 25000000.0},
            "Acetone": {"CStd": 5000.0, "rStd": 20000000.0},
            "Toluene": {"CStd": 890.0, "rStd": 8900000.0}
        }

    peak_ppm_vals = []
    peak_content_pct_vals = []
    peak_spec_status_vals = []

    for p in peaks:
        comp_name = p.get("compound_name", "unidentified")
        norm_name = comp_name.lower().strip()
        
        # Look up USP limit
        usp_limit = None
        for k, v in USP_467_LIMITS.items():
            if k in norm_name:
                usp_limit = v
                break
                
        # Look up calibration standard mapping
        matched_calib_key = None
        for calib_key in calibrations.keys():
            if calib_key.lower().strip() in norm_name:
                matched_calib_key = calib_key
                break
        
        ppm_computed = 0.0
        pct_computed = 0.0
        status_str = "N/A"
        
        if matched_calib_key:
            cal = calibrations[matched_calib_key]
            c_std = float(cal.get("CStd", 0))
            r_std_val = float(cal.get("rStd", 0))
            
            if c_std > 0 and r_std_val > 0:
                rf = r_std_val / c_std
                r_spl = p.get("peak_area_mAU", 0.0)
                
                if rf > 0 and sample_weight > 0:
                    ppm_computed = r_spl / (rf * sample_weight)
                    
                    if api_conc > 0:
                        pct_computed = (r_spl * c_std * 0.1) / (api_conc * r_std_val)
                        
                    if usp_limit is not None:
                        status_str = "FAIL" if ppm_computed > usp_limit else "PASS"
                    else:
                        status_str = "PASS"
                        
        peak_ppm_vals.append(ppm_computed)
        peak_content_pct_vals.append(pct_computed)
        peak_spec_status_vals.append(status_str)

    peak_ppm = np.array(peak_ppm_vals, dtype=np.float32)
    peak_content_pct = np.array(peak_content_pct_vals, dtype=np.float32)
    
    # Save peak numerical arrays
    idx_arr = sample_group.create_array("peak_index", shape=peak_idx.shape, dtype="int32")
    idx_arr[:] = peak_idx
    
    prt_arr = sample_group.create_array("peak_rt", shape=peak_rt.shape, dtype="float32")
    prt_arr[:] = peak_rt
    
    ph_arr = sample_group.create_array("peak_height", shape=peak_height.shape, dtype="float32")
    ph_arr[:] = peak_height
    
    pa_arr = sample_group.create_array("peak_area", shape=peak_area.shape, dtype="float32")
    pa_arr[:] = peak_area
    
    pp_arr = sample_group.create_array("peak_purity", shape=peak_purity.shape, dtype="float32")
    pp_arr[:] = peak_purity
    
    pc_arr = sample_group.create_array("peak_coeluting", shape=peak_coeluting.shape, dtype="int8")
    pc_arr[:] = peak_coeluting
    
    pppm_arr = sample_group.create_array("peak_ppm", shape=peak_ppm.shape, dtype="float32")
    pppm_arr[:] = peak_ppm
    
    ppct_arr = sample_group.create_array("peak_content_pct", shape=peak_content_pct.shape, dtype="float32")
    ppct_arr[:] = peak_content_pct
    
    # Save peak string arrays
    pname_arr = sample_group.create_array("peak_compound_name", shape=(num_peaks,), dtype="str")
    pname_arr[:] = np.array(peak_compound_name)
    
    pclass_arr = sample_group.create_array("peak_compound_class", shape=(num_peaks,), dtype="str")
    pclass_arr[:] = np.array(peak_compound_class)
    
    pconf_arr = sample_group.create_array("peak_confidence", shape=(num_peaks,), dtype="str")
    pconf_arr[:] = np.array(peak_confidence)
    
    pspec_arr = sample_group.create_array("peak_spec_status", shape=(num_peaks,), dtype="str")
    pspec_arr[:] = np.array(peak_spec_status_vals)
    
    # Save peak match score
    pms_arr = sample_group.create_array("peak_match_score", shape=peak_match_score.shape, dtype="float32")
    pms_arr[:] = peak_match_score
    
    # Set attributes
    sample_group.attrs["sample_id"] = sample_id
    sample_group.attrs["raw_file_name"] = Path(raw_cdf_path).name
    sample_group.attrs["created_at"] = datetime.now().isoformat()
    sample_group.attrs["num_peaks"] = num_peaks
    
    print(f"[STORE] Zarr archive generated successfully at {ZARR_STORE_PATH}/{sample_id} ({num_peaks} peaks archived).")
    return str(Path(ZARR_STORE_PATH) / sample_id)

def register_in_lamindb(sample_id: str, excel_report_path: str) -> dict:
    """Registers the updated Zarr store folder and Excel report file as metadata artifacts in LaminDB."""
    print(f"[STORE] Connecting to LaminDB to register assets for {sample_id}...")
    results = {"zarr_uid": None, "excel_uid": None, "error": None}
    
    try:
        import lamindb as ln
        
        # 1. Register Zarr group store
        # Note: We register the folder corresponding to the sample's subgroup inside Zarr
        zarr_sample_path = str(Path(ZARR_STORE_PATH) / sample_id)
        if os.path.exists(zarr_sample_path):
            zarr_artifact = ln.Artifact(
                zarr_sample_path, 
                description=f"Chromatography Zarr Array Telemetry for {sample_id}"
            )
            zarr_artifact.save()
            results["zarr_uid"] = zarr_artifact.uid
            print(f"[STORE] LaminDB registered Zarr artifact UID: {zarr_artifact.uid}")
        else:
            print(f"[STORE] Zarr folder not found at {zarr_sample_path}")

        # 2. Register Excel sheet report deliverable
        if os.path.exists(excel_report_path):
            excel_artifact = ln.Artifact(
                excel_report_path, 
                description=f"Chromatography Final Excel Report for {sample_id}"
            )
            excel_artifact.save()
            results["excel_uid"] = excel_artifact.uid
            print(f"[STORE] LaminDB registered Excel report artifact UID: {excel_artifact.uid}")
        else:
            print(f"[STORE] Excel report not found at {excel_report_path}")

    except Exception as e:
        print(f"[STORE] WARNING: LaminDB registration failed: {e}")
        results["error"] = str(e)
        
    return results
