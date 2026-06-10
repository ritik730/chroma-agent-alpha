"""
alignment.py — Multi-sample chromatographic retention time alignment.
Uses Dynamic Time Warping (DTW) with a Sakoe-Chiba band constraint.
"""
import numpy as np

def dtw_sakoe_chiba(s1: np.ndarray, s2: np.ndarray, window: int = 100) -> list[tuple[int, int]]:
    """
    Compute the warping path between s1 (reference) and s2 (target)
    under a Sakoe-Chiba band constraint to prevent excessive warping
    and restrict computational/memory complexity to O(N).
    
    Parameters:
        s1: Reference signal array of shape (N,)
        s2: Target signal array of shape (M,)
        window: Index window constraint (max drift offset)
        
    Returns:
        List of coordinate tuples (i, j) representing the warping path.
    """
    N = len(s1)
    M = len(s2)
    
    # Pre-initialize cost matrix with infinity
    # We only populate and evaluate within the Sakoe-Chiba diagonal band
    cost = np.full((N, M), np.inf, dtype=np.float32)
    cost[0, 0] = np.abs(s1[0] - s2[0])
    
    # Dynamic Programming loop restricted to the diagonal band
    for i in range(N):
        # Calculate central j matching the diagonal scaling
        diag_j = int(round(i * M / N))
        j_min = max(0, diag_j - window)
        j_max = min(M - 1, diag_j + window)
        
        for j in range(j_min, j_max + 1):
            if i == 0 and j == 0:
                continue
            
            # Predecessor costs
            p1 = cost[i - 1, j] if i > 0 else np.inf
            p2 = cost[i, j - 1] if j > 0 else np.inf
            p3 = cost[i - 1, j - 1] if (i > 0 and j > 0) else np.inf
            
            min_pred = min(p1, p2, p3)
            if min_pred != np.inf:
                cost[i, j] = np.abs(s1[i] - s2[j]) + min_pred
                
    # Backtrack to find the warping path
    path = []
    i = N - 1
    j = M - 1
    path.append((i, j))
    
    while i > 0 or j > 0:
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            p1 = cost[i - 1, j]
            p2 = cost[i, j - 1]
            p3 = cost[i - 1, j - 1]
            
            min_val = min(p1, p2, p3)
            if min_val == p3:
                i -= 1
                j -= 1
            elif min_val == p1:
                i -= 1
            else:
                j -= 1
        path.append((i, j))
        
    path.reverse()
    return path


def align_chromatogram_signals(rt_ref: np.ndarray, int_ref: np.ndarray,
                               rt_target: np.ndarray, int_target: np.ndarray,
                               window_seconds: float = 15.0) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """
    Align target chromatogram signal to reference timeline.
    
    Parameters:
        rt_ref: Reference retention times (minutes)
        int_ref: Reference intensities
        rt_target: Target retention times (minutes)
        int_target: Target intensities
        window_seconds: Max allowable drift window in seconds
        
    Returns:
        tuple of (aligned_target_intensities, warping_path)
    """
    # Estimate sampling frequency (scans per second)
    if len(rt_ref) > 1:
        avg_scan_time_min = np.mean(np.diff(rt_ref))
        scans_per_sec = 1.0 / (avg_scan_time_min * 60.0)
    else:
        scans_per_sec = 1.0
        
    window_scans = max(5, int(round(window_seconds * scans_per_sec)))
    
    # Calculate warping path
    path = dtw_sakoe_chiba(int_ref, int_target, window_scans)
    
    # Build mapping from reference index to target index
    # (if multiple target indices map to a reference, take the average target index)
    ref_to_target_map = {}
    for i, j in path:
        if i not in ref_to_target_map:
            ref_to_target_map[i] = []
        ref_to_target_map[i].append(j)
        
    aligned_int = np.zeros_like(int_ref)
    for i in range(len(rt_ref)):
        mapped_indices = ref_to_target_map.get(i)
        if mapped_indices:
            # Take the average intensity of mapped target scans
            aligned_int[i] = np.mean(int_target[mapped_indices])
        else:
            # Fallback to predecessor
            aligned_int[i] = aligned_int[i - 1] if i > 0 else 0.0
            
    return aligned_int, path


def map_and_align_peaks(peaks_ref: list[dict], peaks_target: list[dict],
                        rt_ref: np.ndarray, rt_target: np.ndarray,
                        path: list[tuple[int, int]], rt_tolerance_min: float = 0.05) -> tuple[list[dict], list[dict]]:
    """
    Map target peaks to reference timeline and identify corresponding peaks.
    Adds 'aligned_rt' to target peaks and cross-references matching peak indices.
    
    Returns:
        tuple of (updated_peaks_ref, updated_peaks_target)
    """
    # Map target indices to reference indices
    # Create target_index -> reference_index map
    target_to_ref_map = {}
    for i, j in path:
        if j not in target_to_ref_map:
            target_to_ref_map[j] = []
        target_to_ref_map[j].append(i)
        
    # Process target peaks
    aligned_peaks_target = []
    for p in peaks_target:
        # Find nearest target scan index to peak apex
        apex_rt = p["retention_time"]
        target_idx = np.abs(rt_target - apex_rt).argmin()
        
        # Resolve mapped reference index
        mapped_ref_indices = target_to_ref_map.get(target_idx, [target_idx])
        mapped_ref_idx = int(round(np.mean(mapped_ref_indices)))
        mapped_ref_idx = max(0, min(mapped_ref_idx, len(rt_ref) - 1))
        
        aligned_rt = float(rt_ref[mapped_ref_idx])
        
        p_aligned = {
            **p,
            "aligned_rt": round(aligned_rt, 4),
            "matched_peak_index": None
        }
        aligned_peaks_target.append(p_aligned)
        
    # Cross-reference with reference peaks
    aligned_peaks_ref = [{**p, "matched_peak_index": None} for p in peaks_ref]
    
    for pt in aligned_peaks_target:
        # Search for closest reference peak in aligned RT space
        best_ref = None
        min_diff = rt_tolerance_min
        
        for pr in aligned_peaks_ref:
            diff = np.abs(pr["retention_time"] - pt["aligned_rt"])
            if diff < min_diff:
                min_diff = diff
                best_ref = pr
                
        if best_ref is not None:
            pt["matched_peak_index"] = best_ref["peak_index"]
            best_ref["matched_peak_index"] = pt["peak_index"]
            
    return aligned_peaks_ref, aligned_peaks_target


def reconstruct_chromatogram_from_peaks(rt: np.ndarray, peaks: list[dict]) -> np.ndarray:
    """
    Reconstruct continuous intensity profile from peaks list using Gaussian peak modeling.
    This creates a clean, baseline-corrected signal representation suitable for alignment.
    """
    intensity = np.zeros_like(rt)
    for p in peaks:
        h = p.get("peak_height_mAU", 1.0)
        tr = p.get("retention_time", 0.0)
        rt_start = p.get("rt_start", tr - 0.1)
        rt_end = p.get("rt_end", tr + 0.1)
        w = max(0.01, rt_end - rt_start)
        
        idx_start = np.abs(rt - rt_start).argmin()
        idx_end = np.abs(rt - rt_end).argmin()
        
        peak_rt = rt[idx_start:idx_end + 1]
        if len(peak_rt) > 0:
            peak_int = h * np.exp(-4.0 * np.log(2.0) * ((peak_rt - tr) / w) ** 2)
            intensity[idx_start:idx_end + 1] = np.maximum(intensity[idx_start:idx_end + 1], peak_int)
    return intensity
