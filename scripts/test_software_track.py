"""
test_software_track.py — Unit and integration tests for System Suitability Metrics, 
EMG Peak Fitting, and Agilent .ch Ingestion.
"""
import io
import os
import struct
import numpy as np
import scipy.optimize as opt
import sst_metrics
import gnn_deconv
import parse_cdf


def generate_synthetic_gaussian(rt: np.ndarray, height: float, t_R: float, w: float) -> np.ndarray:
    """Generate a mathematically perfect Gaussian peak."""
    return height * np.exp(-4.0 * np.log(2.0) * ((rt - t_R) / w) ** 2)


def test_sst_metrics():
    print("[TEST] Running System Suitability Testing (SST) calculations...")
    rt = np.linspace(0.0, 10.0, 1000)
    
    # 1. Perfect Gaussian Peak (height=100.0, t_R=5.0, width=0.4)
    height, t_R, w = 100.0, 5.0, 0.4
    intensity = generate_synthetic_gaussian(rt, height, t_R, w)
    
    peak_idx = int(np.abs(rt - t_R).argmin())
    start_idx = int(np.abs(rt - (t_R - w)).argmin())
    end_idx = int(np.abs(rt - (t_R + w)).argmin())
    
    tailing = sst_metrics.calculate_tailing_factor(rt, intensity, peak_idx, start_idx, end_idx)
    plates = sst_metrics.calculate_theoretical_plates(rt, intensity, peak_idx, start_idx, end_idx)
    
    print(f"  Gaussian Peak - Tailing (expected ~1.0): {tailing}")
    print(f"  Gaussian Peak - Theoretical Plates: {plates}")
    
    assert 0.95 <= tailing <= 1.05, f"Expected tailing factor ~1.0, got {tailing}"
    assert plates > 0, f"Expected positive plate count, got {plates}"
    
    # 2. Tailing Peak using EMG model
    # EMG params: h=80, t_R=4.8, sigma=0.08, tau=0.15 (heavy tailing)
    intensity_tailing = gnn_deconv.emg_model(rt, 80.0, 4.8, 0.08, 0.15)
    peak_idx_tail = int(intensity_tailing.argmax())
    start_idx_tail = int(np.abs(rt - 4.0).argmin())
    end_idx_tail = int(np.abs(rt - 6.5).argmin())
    
    tailing_val = sst_metrics.calculate_tailing_factor(rt, intensity_tailing, peak_idx_tail, start_idx_tail, end_idx_tail)
    print(f"  EMG Tailing Peak - Tailing factor (expected > 1.2): {tailing_val}")
    assert tailing_val > 1.2, f"Expected tailing factor > 1.2, got {tailing_val}"
    
    # 3. Peak Resolution
    p1 = {"retention_time": 4.5, "rt_start": 4.3, "rt_end": 4.7}
    p2 = {"retention_time": 5.0, "rt_start": 4.8, "rt_end": 5.2}
    res = sst_metrics.calculate_resolution(p1, p2)
    print(f"  Resolution (expected 1.25): {res}")
    assert np.isclose(res, 1.25, atol=0.05)
    
    # 4. Signal to Noise
    noise_regions = [(start_idx, end_idx)]
    sn = sst_metrics.calculate_signal_to_noise(intensity, height, noise_regions)
    print(f"  Signal-to-Noise Ratio: {sn}")
    assert sn > 0
    
    print("[PASS] sst_metrics calculations validated successfully!")


def test_emg_peak_fitting():
    print("[TEST] Running EMG non-linear curve fitting verification...")
    rt = np.linspace(4.0, 6.0, 400)
    
    # Generate synthetic co-eluting peaks
    # Peak 1: h=100.0, t_R=4.7, sigma=0.08, tau=0.04
    # Peak 2: h=80.0,  t_R=5.1, sigma=0.07, tau=0.08
    y1 = gnn_deconv.emg_model(rt, 100.0, 4.7, 0.08, 0.04)
    y2 = gnn_deconv.emg_model(rt, 80.0, 5.1, 0.07, 0.08)
    mixed_signal = y1 + y2
    
    # Fitting guesses
    p0 = [90.0, 4.65, 0.1, 0.05, 75.0, 5.15, 0.1, 0.05]
    bounds_min = [0.0, 4.0, 1e-4, 1e-4, 0.0, 4.0, 1e-4, 1e-4]
    bounds_max = [np.inf, 6.0, 2.0, 2.0, np.inf, 6.0, 2.0, 2.0]
    
    popt, _ = opt.curve_fit(
        gnn_deconv.fit_multi_emg,
        rt,
        mixed_signal,
        p0=p0,
        bounds=(bounds_min, bounds_max),
        maxfev=5000
    )
    
    print(f"  Fitted Peak 1 - Height: {popt[0]:.2f} (expected ~100.0), RT: {popt[1]:.3f} (expected ~4.7)")
    print(f"  Fitted Peak 2 - Height: {popt[4]:.2f} (expected ~80.0), RT: {popt[5]:.3f} (expected ~5.1)")
    
    assert np.isclose(popt[0], 100.0, rtol=0.05)
    assert np.isclose(popt[1], 4.7, rtol=0.05)
    assert np.isclose(popt[4], 80.0, rtol=0.05)
    assert np.isclose(popt[5], 5.1, rtol=0.05)
    
    print("[PASS] EMG peak fitting converged and parameters validated successfully!")


def test_agilent_ch_ingestion():
    print("[TEST] Running Agilent .ch binary parsing verification...")
    
    # Create mock Agilent .ch bytes
    # Version signature (big-endian 179)
    version = 179
    # Start time = 1.0 min
    start_time = 1.0
    # End time = 10.0 min
    end_time = 10.0
    # Number of points = 100
    num_points = 100
    # Scaling factor = 2.0
    scale = 2.0
    
    # Build header bytes (at least 6144 bytes)
    header = bytearray(6144)
    struct.pack_into(">H", header, 0, version)
    struct.pack_into(">f", header, 282, start_time)
    struct.pack_into(">f", header, 286, end_time)
    struct.pack_into(">I", header, 564, num_points)
    struct.pack_into(">d", header, 580, scale)
    
    # Data block: start with an absolute value 1000
    # followed by 99 deltas of +10
    data = bytearray()
    data.extend(struct.pack(">i", 1000))
    for _ in range(99):
        # standard 16-bit delta
        data.extend(struct.pack(">h", 10))
        
    mock_file_path = "processed/mock_agilent.ch"
    with open(mock_file_path, "wb") as f:
        f.write(header)
        f.write(data)
        
    try:
        rt, intensity, meta = parse_cdf.load_agilent_ch(mock_file_path)
        print(f"  Parsed {meta['points']} points from mock Agilent .ch")
        print(f"  Start Time: {rt[0]:.2f} (expected 1.0), End Time: {rt[-1]:.2f} (expected 10.0)")
        print(f"  First point intensity: {intensity[0]:.2f} (expected 2000.0)")
        print(f"  Last point intensity: {intensity[-1]:.2f} (expected 3980.0)")
        
        assert meta["points"] == 100
        assert np.isclose(rt[0], 1.0)
        assert np.isclose(rt[-1], 10.0)
        assert np.isclose(intensity[0], 2000.0) # 1000 * 2.0
        assert np.isclose(intensity[-1], 3980.0) # (1000 + 99 * 10) * 2.0
        print("[PASS] Agilent .ch binary parser successfully validated!")
    finally:
        if os.path.exists(mock_file_path):
            os.remove(mock_file_path)


def test_adaptive_gnn_thresholding():
    print("[TEST] Running Adaptive GNN Thresholding verification...")
    
    # Create mock peaks with specific spectra
    # Case A: Identical spectra (avg_spec_corr = 1.0)
    p1_identical = {
        "peak_index": 0, "retention_time": 4.5, "rt_start": 4.0, "rt_end": 5.0, "peak_height_mAU": 100.0, "peak_area_mAU": 200.0,
        "mz_values": [100.0, 200.0], "intensity_values": [50.0, 100.0]
    }
    p2_identical = {
        "peak_index": 1, "retention_time": 4.7, "rt_start": 4.2, "rt_end": 5.2, "peak_height_mAU": 80.0, "peak_area_mAU": 160.0,
        "mz_values": [100.0, 200.0], "intensity_values": [50.0, 100.0]
    }
    
    sim_identical = gnn_deconv.calculate_region_spectral_similarity([p1_identical, p2_identical], [0, 1])
    print(f"  Identical Spectra Cosine Similarity (expected 1.0): {sim_identical:.4f}")
    assert np.isclose(sim_identical, 1.0, atol=1e-3)
    
    # Case B: Completely orthogonal spectra (avg_spec_corr = 0.0)
    p1_orthogonal = {
        "peak_index": 0, "retention_time": 4.5, "rt_start": 4.0, "rt_end": 5.0, "peak_height_mAU": 100.0, "peak_area_mAU": 200.0,
        "mz_values": [100.0], "intensity_values": [100.0]
    }
    p2_orthogonal = {
        "peak_index": 1, "retention_time": 4.7, "rt_start": 4.2, "rt_end": 5.2, "peak_height_mAU": 80.0, "peak_area_mAU": 160.0,
        "mz_values": [200.0], "intensity_values": [100.0]
    }
    
    sim_orthogonal = gnn_deconv.calculate_region_spectral_similarity([p1_orthogonal, p2_orthogonal], [0, 1])
    print(f"  Orthogonal Spectra Cosine Similarity (expected 0.0): {sim_orthogonal:.4f}")
    assert np.isclose(sim_orthogonal, 0.0, atol=1e-3)
    
    # Case C: Partially overlapping spectra
    p1_partial = {
        "peak_index": 0, "retention_time": 4.5, "rt_start": 4.0, "rt_end": 5.0, "peak_height_mAU": 100.0, "peak_area_mAU": 200.0,
        "mz_values": [100.0, 150.0], "intensity_values": [100.0, 50.0]
    }
    p2_partial = {
        "peak_index": 1, "retention_time": 4.7, "rt_start": 4.2, "rt_end": 5.2, "peak_height_mAU": 80.0, "peak_area_mAU": 160.0,
        "mz_values": [100.0, 200.0], "intensity_values": [100.0, 50.0]
    }
    sim_partial = gnn_deconv.calculate_region_spectral_similarity([p1_partial, p2_partial], [0, 1])
    print(f"  Partial Spectra Cosine Similarity (expected 0.8): {sim_partial:.4f}")
    assert np.isclose(sim_partial, 0.8, atol=1e-3)
    
    # Test Adaptive Threshold calculation
    rt = np.linspace(3.5, 6.0, 500)
    intensity = np.zeros_like(rt)
    
    # Case A: Identical spectra (should shrink the threshold more)
    graph_data_identical, _ = gnn_deconv.build_graph_from_region(rt, intensity, [p1_identical, p2_identical], [0, 1])
    thresh_identical = graph_data_identical.adaptive_proximity_threshold
    
    # Case B: Orthogonal spectra (should have a larger threshold)
    graph_data_orthogonal, _ = gnn_deconv.build_graph_from_region(rt, intensity, [p1_orthogonal, p2_orthogonal], [0, 1])
    thresh_orthogonal = graph_data_orthogonal.adaptive_proximity_threshold
    
    print(f"  Adaptive Threshold - Identical Spectra (highly similar): {thresh_identical:.4f}")
    print(f"  Adaptive Threshold - Orthogonal Spectra (distinct): {thresh_orthogonal:.4f}")
    
    assert thresh_identical < thresh_orthogonal, "Expected identical spectra to result in smaller temporal proximity threshold to force GCN localization."
    
    # Case D: Increasing density (more peaks in the region)
    # Add a 3rd co-eluting peak
    p3_identical = {
        "peak_index": 2, "retention_time": 4.9, "rt_start": 4.4, "rt_end": 5.4, "peak_height_mAU": 60.0, "peak_area_mAU": 120.0,
        "mz_values": [100.0, 200.0], "intensity_values": [50.0, 100.0]
    }
    
    graph_data_3peaks, _ = gnn_deconv.build_graph_from_region(rt, intensity, [p1_identical, p2_identical, p3_identical], [0, 1, 2])
    thresh_3peaks = graph_data_3peaks.adaptive_proximity_threshold
    print(f"  Adaptive Threshold - 3 overlapping peaks (higher density): {thresh_3peaks:.4f}")
    
    assert thresh_3peaks < thresh_identical, "Expected increasing component density to reduce the adaptive proximity threshold to prevent GCN oversmoothing."
    
    print("[PASS] Adaptive GNN Thresholding calculations validated successfully!")


def main():
    print("====================================================")
    print("   CHROMA-AGENT-ALPHA: RUNNING SOFTWARE TRACK TESTS  ")
    print("====================================================")
    test_sst_metrics()
    print("-" * 50)
    test_emg_peak_fitting()
    print("-" * 50)
    test_agilent_ch_ingestion()
    print("-" * 50)
    test_adaptive_gnn_thresholding()
    print("====================================================")
    print("   ALL SOFTWARE TRACK TESTS PASSED SUCCESSFULLY!    ")
    print("====================================================")


if __name__ == "__main__":
    main()
