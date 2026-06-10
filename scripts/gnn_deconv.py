"""
gnn_deconv.py — Graph Neural Network deconvolution for co-eluting chromatographic peaks.
Uses torch-geometric GCN/GAT to separate mixed signals into pure-component spectra.

Pipeline position: parse_cdf.py → gnn_deconv.py → spectral_match.py
Input: peaks + raw signal from parse_cdf.py output
Output: deconvolved peak assignments with softmax-validated component probabilities

Architecture:
  - Nodes: data points in co-eluting regions (m/z, intensity, RT features)
  - Edges: temporal proximity + spectral correlation between points
  - Model: 2-layer GCN with softmax output for component assignment

Usage:
  python scripts/gnn_deconv.py processed/test_ethanol_mix.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import scipy.optimize as opt
import scipy.special as special
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
import sst_metrics

BASE_DIR = Path(os.environ.get("CHROMA_BASE_DIR", Path(__file__).parent.parent))
PROC_DIR = BASE_DIR / "processed" / ".cache"

TEMPORAL_PROXIMITY_THRESHOLD = 0.5
CORRELATION_THRESHOLD = 0.3
HIDDEN_DIM = 32
EPOCHS = 100
LR = 0.01


def emg_model(t: np.ndarray, h: float, t_R: float, sigma: float, tau: float) -> np.ndarray:
    """Exponentially Modified Gaussian (EMG) model."""
    sigma = max(1e-6, sigma)
    tau = max(1e-6, tau)
    term_a = (sigma ** 2) / (2.0 * (tau ** 2)) - (t - t_R) / tau
    term_b = sigma / (np.sqrt(2.0) * tau) - (t - t_R) / (np.sqrt(2.0) * sigma)
    term_a = np.clip(term_a, -100.0, 100.0)
    return h * (sigma / tau) * np.sqrt(np.pi / 2.0) * np.exp(term_a) * special.erfc(term_b)


def fit_multi_emg(t: np.ndarray, *params) -> np.ndarray:
    """Sum of multiple EMG peaks."""
    n_comps = len(params) // 4
    total = np.zeros_like(t)
    for c in range(n_comps):
        offset = c * 4
        h, t_R, sigma, tau = params[offset:offset+4]
        total += emg_model(t, h, t_R, sigma, tau)
    return total


class PeakDeconvGCN(torch.nn.Module):
    """2-layer GCN for assigning data points to pure-component peaks."""

    def __init__(self, in_features: int, hidden_dim: int, n_components: int):
        super().__init__()
        self.conv1 = GCNConv(in_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, n_components)

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv2(x, edge_index)
        return F.softmax(x, dim=1)


def find_coeluting_regions(peaks: list[dict]) -> list[list[int]]:
    """Identify clusters of peaks whose RT ranges overlap (co-elution)."""
    if len(peaks) <= 1:
        return [[i] for i in range(len(peaks))]

    sorted_idx = sorted(range(len(peaks)), key=lambda i: peaks[i]["rt_start"])
    regions = []
    current_region = [sorted_idx[0]]
    current_end = peaks[sorted_idx[0]]["rt_end"]

    for idx in sorted_idx[1:]:
        if peaks[idx]["rt_start"] < current_end:
            current_region.append(idx)
            current_end = max(current_end, peaks[idx]["rt_end"])
        else:
            regions.append(current_region)
            current_region = [idx]
            current_end = peaks[idx]["rt_end"]
    regions.append(current_region)

    return regions


def calculate_region_spectral_similarity(peaks: list[dict], region_indices: list[int]) -> float:
    """Calculate the average pairwise cosine similarity between apex spectra of the peaks in this region."""
    n_peaks = len(region_indices)
    if n_peaks < 2:
        return 0.0

    spectra = []
    for idx in region_indices:
        if idx >= len(peaks):
            continue
        peak = peaks[idx]
        mz = peak.get("mz_values", [])
        intensities = peak.get("intensity_values", [])
        if not mz or mz == [0.0]:
            continue
        # Align spectra on an integer grid
        vec = {}
        for m, val in zip(mz, intensities):
            int_mz = int(round(m))
            vec[int_mz] = vec.get(int_mz, 0.0) + val
        spectra.append(vec)

    if len(spectra) < 2:
        return 0.0

    similarities = []
    for i in range(len(spectra)):
        for j in range(i + 1, len(spectra)):
            vec1 = spectra[i]
            vec2 = spectra[j]
            mzs = set(vec1.keys()).union(set(vec2.keys()))
            dot = sum(vec1.get(m, 0.0) * vec2.get(m, 0.0) for m in mzs)
            norm1 = np.sqrt(sum(v**2 for v in vec1.values()))
            norm2 = np.sqrt(sum(v**2 for v in vec2.values()))
            if norm1 > 0 and norm2 > 0:
                sim = dot / (norm1 * norm2)
                similarities.append(sim)
            else:
                similarities.append(1.0)
                
    return float(np.mean(similarities)) if similarities else 0.0


def build_graph_from_region(
    rt_array: np.ndarray,
    intensity_array: np.ndarray,
    peaks: list[dict],
    region_indices: list[int],
) -> tuple[Data, np.ndarray]:
    """Build a PyG graph from a co-eluting region.

    Nodes: sampled data points in the region's RT window.
    Features: [normalized_rt, normalized_intensity, rt_gradient].
    Edges: connect points within temporal proximity threshold.
    """
    region_peaks = [peaks[i] for i in region_indices]
    rt_min = min(p["rt_start"] for p in region_peaks)
    rt_max = max(p["rt_end"] for p in region_peaks)

    mask = (rt_array >= rt_min) & (rt_array <= rt_max)
    region_rt = rt_array[mask]
    region_int = intensity_array[mask]

    if len(region_rt) < 2:
        return None, None

    max_points = 200
    if len(region_rt) > max_points:
        step = len(region_rt) // max_points
        region_rt = region_rt[::step]
        region_int = region_int[::step]

    rt_norm = (region_rt - rt_min) / max(rt_max - rt_min, 1e-8)
    int_max = region_int.max() if region_int.max() > 0 else 1.0
    int_norm = region_int / int_max

    gradient = np.gradient(int_norm)
    gradient = gradient / (np.abs(gradient).max() + 1e-8)

    features = np.column_stack([rt_norm, int_norm, gradient])
    x = torch.tensor(features, dtype=torch.float32)

    # Adaptive GNN Proximity Thresholding calculations
    avg_spec_corr = calculate_region_spectral_similarity(peaks, region_indices)
    rt_span = max(rt_max - rt_min, 1e-8)
    widths = [(p["rt_end"] - p["rt_start"]) for p in region_peaks]
    avg_width_norm = float(np.mean(widths) / rt_span) if rt_span > 0 else 0.5

    # Design adaptive rule:
    # 1. Base threshold scales with average normalized peak width.
    # 2. Shrinks with component count (density) to prevent over-smoothing.
    # 3. Shrinks with spectral similarity to force localization for difficult separations.
    base_thresh = avg_width_norm * 1.5
    scale_components = 1.0 / np.sqrt(len(region_indices))
    scale_spectral = 1.0 - 0.25 * avg_spec_corr
    adaptive_proximity_threshold = base_thresh * scale_components * scale_spectral
    adaptive_proximity_threshold = float(np.clip(adaptive_proximity_threshold, 0.1, 0.7))

    edges_src, edges_dst = [], []
    n_points = len(region_rt)
    for i in range(n_points):
        for j in range(i + 1, min(i + 20, n_points)):
            rt_dist = abs(rt_norm[i] - rt_norm[j])
            if rt_dist < adaptive_proximity_threshold:
                edges_src.extend([i, j])
                edges_dst.extend([j, i])

    if not edges_src:
        for i in range(n_points - 1):
            edges_src.extend([i, i + 1])
            edges_dst.extend([i + 1, i])

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)

    n_components = len(region_indices)
    labels = torch.zeros(n_points, dtype=torch.long)
    for comp_idx, peak in enumerate(region_peaks):
        peak_rt = peak["retention_time"]
        distances = np.abs(region_rt - peak_rt)
        nearest = distances.argmin()
        window = max(1, n_points // (n_components * 3))
        start = max(0, nearest - window)
        end = min(n_points, nearest + window + 1)
        labels[start:end] = comp_idx

    data = Data(x=x, edge_index=edge_index, y=labels)
    data.n_components = n_components
    data.adaptive_proximity_threshold = adaptive_proximity_threshold
    data.avg_spec_corr = avg_spec_corr

    return data, region_rt


def train_deconv_model(data: Data) -> PeakDeconvGCN:
    """Train a GCN model to deconvolve a co-eluting region."""
    n_components = data.n_components
    in_features = data.x.shape[1]

    model = PeakDeconvGCN(in_features, HIDDEN_DIM, n_components)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)

    model.train()
    for epoch in range(EPOCHS):
        optimizer.zero_grad()
        out = model(data)
        loss = F.cross_entropy(out, data.y)
        loss.backward()
        optimizer.step()

    return model


def validate_softmax(predictions: torch.Tensor) -> bool:
    """Loop 2 constraint: softmax outputs must sum to 1.0 per node."""
    row_sums = predictions.sum(dim=1)
    return torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5)


def deconvolve_peaks(peaks_data: dict) -> dict:
    """Full GNN deconvolution pipeline."""
    peaks = peaks_data.get("peaks", [])
    rt_array = np.array(peaks_data.get("retention_time", []))
    sample_id = peaks_data["sample_id"]

    if len(peaks) < 2:
        return {
            "sample_id": sample_id,
            "deconvolution": "skipped",
            "reason": "fewer than 2 peaks, no co-elution possible",
            "peaks": peaks,
        }

    baseline_corrected = peaks_data.get("baseline_corrected", False)
    if not baseline_corrected:
        return {
            "sample_id": sample_id,
            "deconvolution": "error",
            "reason": "input must be baseline-corrected",
        }

    total_area = peaks_data.get("trapz_validation", {}).get("total_signal_area", 0)
    intensity_array = np.zeros_like(rt_array)
    for p in peaks:
        idx = p.get("peak_index", 0)
        if idx < len(intensity_array):
            intensity_array[idx] = p.get("peak_height_mAU", 0)

    if len(rt_array) > 0 and total_area > 0:
        scale = total_area / max(np.trapezoid(intensity_array, rt_array), 1e-8)
        intensity_array = intensity_array * min(scale, 10.0)

    regions = find_coeluting_regions(peaks)

    deconv_results = []
    region_diagnostics = []
    for region_idx, region_indices in enumerate(regions):
        if len(region_indices) < 2:
            for pi in region_indices:
                deconv_results.append({
                    **peaks[pi],
                    "component_id": 0,
                    "component_purity": 1.0,
                    "coeluting": False,
                    "region_id": region_idx,
                })
            continue

        graph_data, region_rt = build_graph_from_region(
            rt_array, intensity_array, peaks, region_indices
        )

        if graph_data is None:
            for pi in region_indices:
                deconv_results.append({
                    **peaks[pi],
                    "component_id": 0,
                    "component_purity": 0.5,
                    "coeluting": True,
                    "region_id": region_idx,
                    "deconv_status": "insufficient_data",
                })
            continue

        model = train_deconv_model(graph_data)
        model.eval()
        with torch.no_grad():
            predictions = model(graph_data)

        softmax_valid = validate_softmax(predictions)

        assignments = predictions.argmax(dim=1).numpy()
        max_probs = predictions.max(dim=1).values.numpy()

        region_diagnostics.append({
            "region_id": region_idx,
            "n_components": len(region_indices),
            "avg_spectral_similarity": round(float(graph_data.avg_spec_corr), 4),
            "adaptive_proximity_threshold": round(float(graph_data.adaptive_proximity_threshold), 4),
        })

        # Run EMG Curve Fitting on the region
        rt_min = min(peaks[pi]["rt_start"] for pi in region_indices)
        rt_max = max(peaks[pi]["rt_end"] for pi in region_indices)
        mask = (rt_array >= rt_min) & (rt_array <= rt_max)
        region_full_rt = rt_array[mask]
        region_full_int = intensity_array[mask]
        
        p0 = []
        bounds_min = []
        bounds_max = []
        n_components = len(region_indices)
        
        for pi in region_indices:
            h_guess = peaks[pi]["peak_height_mAU"]
            tr_guess = peaks[pi]["retention_time"]
            w_guess = max(0.01, (peaks[pi]["rt_end"] - peaks[pi]["rt_start"]) / 4.0)
            p0.extend([h_guess, tr_guess, w_guess, 0.05])
            bounds_min.extend([0.0, rt_min - 0.2, 1e-4, 1e-4])
            bounds_max.extend([np.inf, rt_max + 0.2, 2.0, 2.0])
            
        fit_success = False
        popt = p0
        # Only attempt non-linear EMG curve fitting for smaller co-eluting regions (<= 5 peaks)
        # to prevent computational hangs/exponential slowdowns on massive co-eluting clusters.
        if n_components <= 5 and len(region_full_rt) >= 4 * n_components:
            try:
                popt, _ = opt.curve_fit(
                    fit_multi_emg,
                    region_full_rt,
                    region_full_int,
                    p0=p0,
                    bounds=(bounds_min, bounds_max),
                    maxfev=5000
                )
                fit_success = True
            except Exception:
                popt = p0

        for comp_idx, pi in enumerate(region_indices):
            comp_mask = assignments == comp_idx
            purity = float(max_probs[comp_mask].mean()) if comp_mask.any() else 0.5
            n_assigned = int(comp_mask.sum())

            h_fit, tr_fit, sigma_fit, tau_fit = popt[comp_idx*4 : (comp_idx+1)*4]
            comp_intensity = emg_model(rt_array, h_fit, tr_fit, sigma_fit, tau_fit)
            area_fitted = float(np.trapezoid(comp_intensity[mask], rt_array[mask]))
            height_fitted = float(comp_intensity.max())
            apex_idx = comp_intensity.argmax()
            rt_fitted = float(rt_array[apex_idx]) if comp_intensity[apex_idx] > 1e-3 else tr_fit
            
            area_gnn = peaks[pi]["peak_area_mAU"] * purity
            
            # If fit is successful and reasonable, use it. Otherwise fallback to GNN.
            final_area = area_fitted if (fit_success and area_fitted > 0.05 * peaks[pi]["peak_area_mAU"]) else area_gnn
            final_height = height_fitted if (fit_success and height_fitted > 0.05 * peaks[pi]["peak_height_mAU"]) else peaks[pi]["peak_height_mAU"]
            final_rt = rt_fitted if fit_success else peaks[pi]["retention_time"]

            deconv_results.append({
                **peaks[pi],
                "retention_time": round(final_rt, 4),
                "peak_height_mAU": round(final_height, 4),
                "peak_area_mAU": round(final_area, 4),
                "component_id": comp_idx,
                "component_purity": round(purity, 4),
                "n_points_assigned": n_assigned,
                "coeluting": True,
                "region_id": region_idx,
                "softmax_valid": softmax_valid,
                "emg_fit_success": fit_success,
                "emg_fit_params": [round(float(v), 5) for v in [h_fit, tr_fit, sigma_fit, tau_fit]] if fit_success else None
            })

    # Post-Process System Suitability Metrics for ALL peaks
    peak_regions = []
    for p in deconv_results:
        start_idx = np.abs(rt_array - p["rt_start"]).argmin()
        end_idx = np.abs(rt_array - p["rt_end"]).argmin()
        peak_regions.append((start_idx, end_idx))
        
    for idx, p in enumerate(deconv_results):
        peak_index = p["peak_index"]
        start_idx = np.abs(rt_array - p["rt_start"]).argmin()
        end_idx = np.abs(rt_array - p["rt_end"]).argmin()
        
        if p.get("emg_fit_success") and p.get("emg_fit_params"):
            h, tr, sigma, tau = p["emg_fit_params"]
            peak_profile = emg_model(rt_array, h, tr, sigma, tau)
        else:
            peak_profile = np.zeros_like(intensity_array)
            peak_profile[start_idx : end_idx + 1] = intensity_array[start_idx : end_idx + 1]
            
        tailing = sst_metrics.calculate_tailing_factor(rt_array, peak_profile, peak_index, start_idx, end_idx)
        plates = sst_metrics.calculate_theoretical_plates(rt_array, peak_profile, peak_index, start_idx, end_idx)
        sn = sst_metrics.calculate_signal_to_noise(intensity_array, p["peak_height_mAU"], peak_regions)
        
        resolution = 0.0
        if idx > 0:
            resolution = sst_metrics.calculate_resolution(deconv_results[idx - 1], p)
            
        p["tailing_factor"] = tailing
        p["theoretical_plates"] = plates
        p["signal_to_noise"] = sn
        p["resolution"] = resolution

    return {
        "sample_id": sample_id,
        "deconvolution": "complete",
        "n_regions": len(regions),
        "n_coeluting_regions": sum(1 for r in regions if len(r) >= 2),
        "peaks": deconv_results,
        "region_diagnostics": region_diagnostics,
        "model_config": {
            "architecture": "GCN (2-layer)",
            "hidden_dim": HIDDEN_DIM,
            "epochs": EPOCHS,
            "temporal_threshold": "adaptive",
        },
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python gnn_deconv.py <peaks.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    peaks_data = json.loads(input_path.read_text())
    result = deconvolve_peaks(peaks_data)

    output_file = PROC_DIR / f"{result['sample_id']}_deconvolved.json"
    output_file.write_text(json.dumps(result, indent=2))

    print(f"[DECONV] {result['sample_id']}: {result.get('deconvolution', 'unknown')}")
    if result["deconvolution"] == "complete":
        print(f"  Regions: {result['n_regions']} total, "
              f"{result['n_coeluting_regions']} co-eluting")
        if result.get("region_diagnostics"):
            print("  Adaptive Thresholding Diagnostics:")
            for diag in result["region_diagnostics"]:
                print(f"    Region {diag['region_id']}: {diag['n_components']} peaks | "
                      f"Avg Spec Sim = {diag['avg_spectral_similarity']:.3f} | "
                      f"Adaptive Thresh = {diag['adaptive_proximity_threshold']:.3f}")
        for p in result["peaks"]:
            status = "co-eluting" if p.get("coeluting") else "pure"
            print(f"  Peak {p['peak_index']}: RT={p['retention_time']:.2f}min "
                  f"| {status} | purity={p.get('component_purity', '?'):.3f} "
                  f"| tailing={p.get('tailing_factor', '?')} "
                  f"| plates={p.get('theoretical_plates', '?')} "
                  f"| resolution={p.get('resolution', '?')}")
    elif result["deconvolution"] == "skipped":
        print(f"  {result['reason']}")
    print(f"  → {output_file.name}")


if __name__ == "__main__":
    main()
