"""
parse_cdf.py — Extract chromatographic peaks from AIA/ANDI netCDF (.cdf) files.
Pipeline: load → ALS baseline correction → peak detection → np.trapezoid integration → JSON.
"""
import json
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np
from scipy import sparse
from scipy.signal import find_peaks
from scipy.sparse.linalg import spsolve


def load_cdf(filepath: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """Load retention time and intensity arrays from an AIA/ANDI .cdf chromatogram."""
    ds = nc.Dataset(filepath, "r")
    meta = {"source": Path(filepath).name}

    if "ordinate_values" in ds.variables:
        intensity = np.array(ds.variables["ordinate_values"][:], dtype=np.float64)
    else:
        raise KeyError(f"No ordinate_values in {filepath}. Variables: {list(ds.variables)}")

    if "actual_delay_time" in ds.variables and "actual_sampling_interval" in ds.variables:
        delay = float(ds.variables["actual_delay_time"][:])
        interval = float(ds.variables["actual_sampling_interval"][:])
        n = len(intensity)
        rt = delay + np.arange(n) * interval
    elif "raw_data_retention" in ds.variables:
        rt = np.array(ds.variables["raw_data_retention"][:], dtype=np.float64)
    else:
        n = len(intensity)
        run_length = float(ds.variables.get("actual_run_time_length", [n - 1])[0])
        rt = np.linspace(0.0, run_length, n)
        meta["rt_reconstructed"] = True

    if "detector_unit" in ds.ncattrs():
        meta["unit"] = ds.getncattr("detector_unit")

    ds.close()
    return rt, intensity, meta


def als_baseline(y: np.ndarray, lam: float = 1e6, p: float = 0.01, n_iter: int = 10) -> np.ndarray:
    """Asymmetric Least Squares baseline estimation (Eilers & Boelens 2005).
    Separates slowly-varying baseline drift from sharp chromatographic peaks."""
    m = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(m, m - 2), dtype=np.float64)
    H = lam * D.dot(D.T).tocsc()
    w = np.ones(m)
    for _ in range(n_iter):
        W = sparse.spdiags(w, 0, m, m)
        Z = W + H
        baseline = spsolve(Z, w * y)
        w = np.where(y > baseline, p, 1 - p)
    return baseline


def detect_peaks(rt: np.ndarray, corrected: np.ndarray,
                 height_pct: float = 0.10, distance_pts: int = 10,
                 prominence_pct: float = 0.05) -> list[dict]:
    """Find chromatographic peaks in baseline-corrected signal.
    height_pct and prominence_pct are fractions of max corrected intensity."""
    max_val = corrected.max()
    if max_val <= 0:
        return []

    indices, props = find_peaks(
        corrected,
        height=max_val * height_pct,
        distance=distance_pts,
        prominence=max_val * prominence_pct,
    )

    peaks = []
    for i, idx in enumerate(indices):
        left = int(props["left_bases"][i])
        right = int(props["right_bases"][i])
        area = float(np.trapezoid(y=corrected[left : right + 1], x=rt[left : right + 1]))
        peaks.append({
            "peak_index": int(idx),
            "retention_time": round(float(rt[idx]), 4),
            "peak_height_mAU": round(float(corrected[idx]), 4),
            "peak_area_mAU": round(area, 4),
            "rt_start": round(float(rt[left]), 4),
            "rt_end": round(float(rt[right]), 4),
        })
    return peaks


def validate_total_area(rt: np.ndarray, corrected: np.ndarray, peaks: list[dict]) -> float:
    """Cross-check: total trapezoid area of full corrected signal vs sum of peak areas."""
    total = float(np.trapezoid(y=corrected.clip(min=0), x=rt))
    peak_sum = sum(p["peak_area_mAU"] for p in peaks)
    return round(total, 4), round(peak_sum, 4)


def parse_cdf(filepath: str) -> dict:
    """Full pipeline: load .cdf → ALS baseline → peak detect → trapz validate → JSON dict."""
    rt, intensity, meta = load_cdf(filepath)

    baseline = als_baseline(intensity)
    corrected = intensity - baseline

    peaks = detect_peaks(rt, corrected)

    total_area, peak_sum = validate_total_area(rt, corrected, peaks)

    sample_id = Path(filepath).stem

    result = {
        "sample_id": sample_id,
        "retention_time": [round(float(t), 4) for t in rt],
        "peaks": peaks,
        "peak_area_mAU": [p["peak_area_mAU"] for p in peaks],
        "baseline_corrected": True,
        "trapz_validation": {
            "total_signal_area": total_area,
            "sum_peak_areas": peak_sum,
            "n_peaks": len(peaks),
        },
        "meta": meta,
    }
    return result


def main():
    if len(sys.argv) < 2:
        cdf_dir = Path(r"C:\chroma-agent-alpha\raw_data")
        files = list(cdf_dir.glob("*.cdf")) + list(cdf_dir.glob("*.CDF"))
        if not files:
            print(f"Usage: python parse_cdf.py <file.cdf>")
            print(f"   or: place .cdf files in {cdf_dir}")
            sys.exit(1)
    else:
        files = [Path(a) for a in sys.argv[1:]]

    out_dir = Path(r"C:\chroma-agent-alpha\processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        print(f"[PARSE] {f.name}")
        result = parse_cdf(str(f))
        out_path = out_dir / f"{result['sample_id']}.json"
        with open(out_path, "w") as fp:
            json.dump(result, fp, indent=2)
        n = result["trapz_validation"]["n_peaks"]
        total = result["trapz_validation"]["total_signal_area"]
        print(f"  → {n} peaks | total area {total:.2f} mAU·min | {out_path.name}")


if __name__ == "__main__":
    main()
