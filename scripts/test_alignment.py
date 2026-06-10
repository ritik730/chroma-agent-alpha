"""
test_alignment.py — Unit tests for chromatographic alignment.
"""
import numpy as np
import alignment

def generate_synthetic_peak_signal(rt: np.ndarray, height: float, t_R: float, w: float) -> np.ndarray:
    return height * np.exp(-4.0 * np.log(2.0) * ((rt - t_R) / w) ** 2)

def test_dtw_alignment():
    print("[TEST] Running Sakoe-Chiba DTW signal alignment tests...")
    
    # 1. Create reference timeline (0 to 10 minutes, 10Hz sampling)
    rt_ref = np.linspace(0.0, 10.0, 1000)
    # Generate reference signal with two peaks (t_R=3.0 and t_R=7.0)
    int_ref = (generate_synthetic_peak_signal(rt_ref, 100.0, 3.0, 0.4) + 
               generate_synthetic_peak_signal(rt_ref, 80.0, 7.0, 0.5))
               
    # 2. Create target timeline (shifted/drifted by +0.15 minutes / +9 seconds)
    rt_target = np.linspace(0.0, 10.0, 1000)
    # Shifted peaks: t_R=3.15 and t_R=7.15
    int_target = (generate_synthetic_peak_signal(rt_target, 100.0, 3.15, 0.4) + 
                  generate_synthetic_peak_signal(rt_target, 80.0, 7.15, 0.5))
                  
    # Run alignment with a 15-second window
    aligned_int, path = alignment.align_chromatogram_signals(
        rt_ref, int_ref, rt_target, int_target, window_seconds=15.0
    )
    
    # Calculate correlation before and after alignment
    corr_before = np.corrcoef(int_ref, int_target)[0, 1]
    corr_after = np.corrcoef(int_ref, aligned_int)[0, 1]
    
    print(f"  Correlation before alignment: {corr_before:.4f}")
    print(f"  Correlation after alignment:  {corr_after:.4f}")
    print(f"  Warping path coordinates: {len(path)} mappings")
    
    assert corr_after > 0.98, f"Expected high correlation after alignment, got {corr_after:.4f}"
    assert corr_after > corr_before, "Alignment should improve the signal correlation"
    print("[PASS] Signal alignment validated successfully!")


def test_peak_cross_referencing():
    print("[TEST] Running peak cross-referencing and mapping tests...")
    
    rt_ref = np.linspace(0.0, 10.0, 1000)
    rt_target = np.linspace(0.0, 10.0, 1000)
    
    # Mock reference peaks
    peaks_ref = [
        {"peak_index": 0, "retention_time": 3.00, "rt_start": 2.6, "rt_end": 3.4},
        {"peak_index": 1, "retention_time": 7.00, "rt_start": 6.5, "rt_end": 7.5}
    ]
    
    # Mock target peaks (shifted by +0.15 minutes)
    peaks_target = [
        {"peak_index": 0, "retention_time": 3.15, "rt_start": 2.75, "rt_end": 3.55},
        {"peak_index": 1, "retention_time": 7.15, "rt_start": 6.65, "rt_end": 7.65}
    ]
    
    # Generate warping path representing the +0.15 min (+15 scans) shift
    # Path maps target index j to reference index i where i = j - 15
    path = []
    for j in range(1000):
        i = max(0, min(j - 15, 999))
        path.append((i, j))
        
    updated_ref, updated_target = alignment.map_and_align_peaks(
        peaks_ref, peaks_target, rt_ref, rt_target, path, rt_tolerance_min=0.05
    )
    
    # Verify that target peaks got mapped to reference timeline
    print(f"  Target Peak 0 aligned RT: {updated_target[0]['aligned_rt']} (expected ~3.0)")
    print(f"  Target Peak 1 aligned RT: {updated_target[1]['aligned_rt']} (expected ~7.0)")
    print(f"  Target Peak 0 match: {updated_target[0]['matched_peak_index']} (expected 0)")
    print(f"  Target Peak 1 match: {updated_target[1]['matched_peak_index']} (expected 1)")
    
    assert np.isclose(updated_target[0]["aligned_rt"], 3.00, atol=0.02)
    assert np.isclose(updated_target[1]["aligned_rt"], 7.00, atol=0.02)
    assert updated_target[0]["matched_peak_index"] == 0
    assert updated_target[1]["matched_peak_index"] == 1
    assert updated_ref[0]["matched_peak_index"] == 0
    assert updated_ref[1]["matched_peak_index"] == 1
    
    print("[PASS] Peak mapping and matching validated successfully!")


def main():
    print("====================================================")
    print("   CHROMA-AGENT-ALPHA: RUNNING ALIGNMENT TESTS       ")
    print("====================================================")
    test_dtw_alignment()
    print("-" * 50)
    test_peak_cross_referencing()
    print("====================================================")
    print("   ALL ALIGNMENT TESTS PASSED SUCCESSFULLY!         ")
    print("====================================================")

if __name__ == "__main__":
    main()
