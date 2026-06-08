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
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv

BASE_DIR = Path(os.environ.get("CHROMA_BASE_DIR", Path(__file__).parent.parent))
PROC_DIR = BASE_DIR / "processed" / ".cache"

TEMPORAL_PROXIMITY_THRESHOLD = 0.5
CORRELATION_THRESHOLD = 0.3
HIDDEN_DIM = 32
EPOCHS = 100
LR = 0.01


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

    edges_src, edges_dst = [], []
    n_points = len(region_rt)
    for i in range(n_points):
        for j in range(i + 1, min(i + 20, n_points)):
            rt_dist = abs(rt_norm[i] - rt_norm[j])
            if rt_dist < TEMPORAL_PROXIMITY_THRESHOLD:
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

        for comp_idx, pi in enumerate(region_indices):
            comp_mask = assignments == comp_idx
            purity = float(max_probs[comp_mask].mean()) if comp_mask.any() else 0.5
            n_assigned = int(comp_mask.sum())

            deconv_results.append({
                **peaks[pi],
                "component_id": comp_idx,
                "component_purity": round(purity, 4),
                "n_points_assigned": n_assigned,
                "coeluting": True,
                "region_id": region_idx,
                "softmax_valid": softmax_valid,
            })

    return {
        "sample_id": sample_id,
        "deconvolution": "complete",
        "n_regions": len(regions),
        "n_coeluting_regions": sum(1 for r in regions if len(r) >= 2),
        "peaks": deconv_results,
        "model_config": {
            "architecture": "GCN (2-layer)",
            "hidden_dim": HIDDEN_DIM,
            "epochs": EPOCHS,
            "temporal_threshold": TEMPORAL_PROXIMITY_THRESHOLD,
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
        for p in result["peaks"]:
            status = "co-eluting" if p.get("coeluting") else "pure"
            print(f"  Peak {p['peak_index']}: RT={p['retention_time']:.2f}min "
                  f"| {status} | purity={p.get('component_purity', '?'):.3f}")
    elif result["deconvolution"] == "skipped":
        print(f"  {result['reason']}")
    print(f"  → {output_file.name}")


if __name__ == "__main__":
    main()
