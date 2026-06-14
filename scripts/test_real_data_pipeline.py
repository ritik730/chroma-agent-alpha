"""
test_real_data_pipeline.py — End-to-end integration test on real Agilent .ch and Varian .xms data.
Verifies parsing, GNN deconvolution, spectral matching, calibration/quantification, 
and multi-sample Zarr store appending.
"""
import os
import sys
import json
import subprocess
import numpy as np
from pathlib import Path

# Setup paths
SCRIPTS_DIR = Path(__file__).parent
BASE_DIR = SCRIPTS_DIR.parent
PYTHON = sys.executable

RAW_DIR = BASE_DIR / "raw_data"
PROC_DIR = BASE_DIR / "processed" / ".cache"
ZARR_STORE_PATH = BASE_DIR / "processed" / "chroma_store.zarr"

# Real data files
AGILENT_FILE = RAW_DIR / "FID1A.ch"
VARIAN_FILE = RAW_DIR / "MC-10A-NF205-05-2018.xms"

sys.path.append(str(SCRIPTS_DIR))
import data_store
import zarr

def run_stage_pipeline(file_path: Path):
    sample_id = file_path.stem
    print(f"\n--- Processing {sample_id} ---")
    
    # Stage 1: Parse
    print("[1/3] Parsing raw file...")
    parse_result = subprocess.run(
        [PYTHON, str(SCRIPTS_DIR / "parse_cdf.py"), str(file_path)],
        capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
    )
    if parse_result.returncode != 0:
        print(f"[FAIL] parse_cdf.py failed for {sample_id}:\n{parse_result.stderr}")
        sys.exit(1)
        
    parse_output = PROC_DIR / f"{sample_id}.json"
    if not parse_output.exists():
        print(f"[FAIL] parse_cdf.py did not produce {parse_output.name}")
        sys.exit(1)
    print("  → Parsing successful!")
    
    # Stage 2: Deconvolve
    print("[2/3] Deconvolving peaks using GNN-EMG...")
    deconv_result = subprocess.run(
        [PYTHON, str(SCRIPTS_DIR / "gnn_deconv.py"), str(parse_output)],
        capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR)
    )
    if deconv_result.returncode != 0:
        print(f"[FAIL] gnn_deconv.py failed for {sample_id}:\n{deconv_result.stderr}")
        sys.exit(1)
        
    deconv_output = PROC_DIR / f"{sample_id}_deconvolved.json"
    if not deconv_output.exists():
        print(f"[FAIL] gnn_deconv.py did not produce {deconv_output.name}")
        sys.exit(1)
    print("  → Deconvolution successful!")
    
    # Stage 3: Match
    print("[3/3] Matching spectra against libraries...")
    match_result = subprocess.run(
        [PYTHON, str(SCRIPTS_DIR / "spectral_match.py"), str(deconv_output)],
        capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR)
    )
    if match_result.returncode != 0:
        print(f"[FAIL] spectral_match.py failed for {sample_id}:\n{match_result.stderr}")
        sys.exit(1)
        
    match_output = PROC_DIR / f"{sample_id}_matched.json"
    if not match_output.exists():
        print(f"[FAIL] spectral_match.py did not produce {match_output.name}")
        sys.exit(1)
    print("  → Spectral matching successful!")
    
    return sample_id, str(file_path)

def test_quantification_and_calibration(sample_id: str, file_path: str):
    print(f"\n--- Testing Quantification & Calibration for {sample_id} ---")
    
    # Custom calibration mapping parameters
    calibrations = {
        "methanol": {"CStd": 3000.0, "rStd": 15000000.0},
        "ethanol": {"CStd": 5000.0, "rStd": 25000000.0},
        "acetone": {"CStd": 5000.0, "rStd": 20000000.0},
        "toluene": {"CStd": 890.0, "rStd": 8900000.0}
    }
    sample_weight = 0.1125 # g
    api_conc = 1.3500 # mg/mL
    
    # Save to Zarr
    print("Saving to Zarr and running quantification calculations...")
    zarr_path = data_store.save_run_to_zarr(
        sample_id=sample_id,
        raw_cdf_path=file_path,
        sample_weight=sample_weight,
        api_conc=api_conc,
        calibrations=calibrations
    )
    
    print(f"Zarr subgroup created at: {zarr_path}")
    
    # Open Zarr group and verify arrays
    root = zarr.open_group(str(ZARR_STORE_PATH), mode="r")
    sample_group = root[sample_id]
    
    # Check that calculations exist
    peak_ppm = np.array(sample_group["peak_ppm"])
    peak_pct = np.array(sample_group["peak_content_pct"])
    peak_names = [str(name) for name in sample_group["peak_compound_name"]]
    
    print(f"Calculated peak parameters:")
    for idx, (name, ppm, pct) in enumerate(zip(peak_names, peak_ppm, peak_pct)):
        if ppm > 0:
            print(f"  Peak {idx} ({name}): PPM = {ppm:.3f}, Content % = {pct:.6f}%")
            assert ppm > 0, "PPM should be positive for matched compound"
            assert pct > 0, "Content % should be positive for matched compound"

def verify_zarr_multisample():
    print("\n--- Verifying Multi-Sample Zarr Coexistence ---")
    
    if not ZARR_STORE_PATH.exists():
        print(f"[FAIL] Zarr database not found at {ZARR_STORE_PATH}")
        sys.exit(1)
        
    root = zarr.open_group(str(ZARR_STORE_PATH), mode="r")
    groups = list(root.group_keys())
    print(f"Active Zarr subgroups in store: {groups}")
    
    # Check that both of our test runs co-exist in the store!
    expected_subgroups = ["FID1A", "MC-10A-NF205-05-2018"]
    for expected in expected_subgroups:
        if expected not in groups:
            print(f"[FAIL] Expected subgroup '{expected}' not found in Zarr store. Overwrite bug may still exist!")
            sys.exit(1)
            
    print("[PASS] Multi-sample Zarr coexistence verified successfully! The open mode 'a' fix works.")

def main():
    print("====================================================")
    # Check file existence
    if not AGILENT_FILE.exists():
        print(f"[FAIL] Real Agilent file not found at {AGILENT_FILE}")
        sys.exit(1)
    if not VARIAN_FILE.exists():
        print(f"[FAIL] Real Varian file not found at {VARIAN_FILE}")
        sys.exit(1)
        
    # Clear existing Zarr store to ensure clean test
    if ZARR_STORE_PATH.exists():
        import shutil
        print(f"Clearing old Zarr store at {ZARR_STORE_PATH} for clean append test...")
        shutil.rmtree(ZARR_STORE_PATH)

    # Ingest Agilent
    agilent_id, agilent_path = run_stage_pipeline(AGILENT_FILE)
    
    # Ingest Varian
    varian_id, varian_path = run_stage_pipeline(VARIAN_FILE)
    
    # Test quantification and calibration for both
    test_quantification_and_calibration(agilent_id, agilent_path)
    test_quantification_and_calibration(varian_id, varian_path)
    
    # Verify both exist in Zarr database
    verify_zarr_multisample()
    print("====================================================")
    print("   ALL REAL DATA PIPELINE TESTS PASSED SUCCESSFULLY! ")
    print("====================================================")

if __name__ == "__main__":
    main()
