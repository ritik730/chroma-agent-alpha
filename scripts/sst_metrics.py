"""
sst_metrics.py — System Suitability Testing (SST) metrics for chromatography peaks.
Calculates tailing factor, resolution, plate count, and signal-to-noise ratio.
"""
import numpy as np


def interpolate_height_crossing(rt: np.ndarray, intensity: np.ndarray, 
                               start_idx: int, end_idx: int, target_height: float) -> float:
    """
    Find the retention time where the intensity crosses target_height 
    between start_idx and end_idx (inclusive) using linear interpolation.
    """
    # Safeguard boundary limits
    start_idx = max(0, min(start_idx, len(rt) - 1))
    end_idx = max(0, min(end_idx, len(rt) - 1))
    
    if start_idx == end_idx:
        return float(rt[start_idx])
        
    step = 1 if end_idx > start_idx else -1
    
    for idx in range(start_idx, end_idx, step):
        y1, y2 = intensity[idx], intensity[idx + step]
        x1, x2 = rt[idx], rt[idx + step]
        
        # Check if target_height lies between y1 and y2
        if (y1 <= target_height <= y2) or (y2 <= target_height <= y1):
            if abs(y2 - y1) < 1e-12:
                return float(x1)
            # Linear interpolation formula
            fraction = (target_height - y1) / (y2 - y1)
            return float(x1 + fraction * (x2 - x1))
            
    # Fallback to nearest if crossing not found
    return float(rt[end_idx])


def calculate_tailing_factor(rt: np.ndarray, intensity: np.ndarray, 
                             peak_idx: int, start_idx: int, end_idx: int) -> float:
    """
    Calculate the USP tailing factor (T) at 5% of peak height.
    Formula: T = W_0.05 / (2 * f)
      Where:
        W_0.05 is the width of the peak at 5% height.
        f is the distance from peak front to peak center at 5% height.
    """
    if len(rt) == 0 or peak_idx >= len(rt):
        return 1.0
        
    peak_height = intensity[peak_idx]
    target_height = 0.05 * peak_height
    
    # Locate front and back crossing points at 5% height
    t_front = interpolate_height_crossing(rt, intensity, peak_idx, start_idx, target_height)
    t_back = interpolate_height_crossing(rt, intensity, peak_idx, end_idx, target_height)
    t_apex = rt[peak_idx]
    
    w_05 = t_back - t_front
    f = t_apex - t_front
    
    if f <= 1e-8:
        return 1.0
        
    tailing_factor = w_05 / (2.0 * f)
    return round(float(tailing_factor), 3)


def calculate_theoretical_plates(rt: np.ndarray, intensity: np.ndarray, 
                                 peak_idx: int, start_idx: int, end_idx: int) -> int:
    """
    Calculate the column theoretical plates (N) using the FWHM method.
    Formula: N = 5.54 * (t_R / W_0.5)^2
      Where:
        t_R is the retention time of the peak apex.
        W_0.5 is the peak width at 50% of the peak height.
    """
    if len(rt) == 0 or peak_idx >= len(rt):
        return 0
        
    peak_height = intensity[peak_idx]
    target_height = 0.5 * peak_height
    
    t_front = interpolate_height_crossing(rt, intensity, peak_idx, start_idx, target_height)
    t_back = interpolate_height_crossing(rt, intensity, peak_idx, end_idx, target_height)
    t_apex = rt[peak_idx]
    
    w_05 = t_back - t_front
    
    if w_05 <= 1e-8:
        return 0
        
    plates = 5.54 * (t_apex / w_05) ** 2
    return int(round(plates))


def calculate_resolution(peak1: dict, peak2: dict) -> float:
    """
    Calculate the resolution (Rs) between two peaks.
    Formula: Rs = 2 * (tR2 - tR1) / (w1 + w2)
      Where:
        tR1, tR2 are retention times (tR2 > tR1).
        w1, w2 are the baseline widths of the peaks (rt_end - rt_start).
    """
    rt1 = peak1["retention_time"]
    rt2 = peak2["retention_time"]
    
    # Ensure peak2 is the later eluting peak
    if rt1 > rt2:
        peak1, peak2 = peak2, peak1
        rt1, rt2 = rt2, rt1
        
    w1 = peak1["rt_end"] - peak1["rt_start"]
    w2 = peak2["rt_end"] - peak2["rt_start"]
    
    if (w1 + w2) <= 1e-8:
        return 0.0
        
    res = 2.0 * (rt2 - rt1) / (w1 + w2)
    return round(float(res), 2)


def calculate_signal_to_noise(intensity: np.ndarray, peak_height: float, 
                              peak_regions: list[tuple[int, int]]) -> float:
    """
    Calculate the Signal-to-Noise (S/N) ratio.
    Estimates baseline noise standard deviation from signal points outside of all peak regions.
    """
    m = len(intensity)
    if m == 0:
        return 0.0
        
    # Build mask of peak regions
    peak_mask = np.zeros(m, dtype=bool)
    for start, end in peak_regions:
        peak_mask[start : end + 1] = True
        
    # Noise points are non-peak points
    noise_points = intensity[~peak_mask]
    
    if len(noise_points) < 5:
        # Fallback to absolute minimum standard deviation of quietest segment if too few non-peak points
        noise_std = np.std(intensity) * 0.1
    else:
        noise_std = np.std(noise_points)
        
    if noise_std <= 1e-8:
        return 999.0
        
    sn = peak_height / noise_std
    return round(float(sn), 1)
