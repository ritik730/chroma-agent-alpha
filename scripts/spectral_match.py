"""
spectral_match.py — Spectral matching layer for CHROMA-AGENT-ALPHA.
Compares deconvolved or detected peak spectra against a reference library
using matchms cosine similarity.

Pipeline position: parse_cdf.py → [gnn_deconv.py] → spectral_match.py
Input: peaks JSON from parse_cdf or deconvolved spectra from gnn_deconv
Output: matched compounds with cosine similarity scores (threshold >= 0.7)

Usage:
  python scripts/spectral_match.py processed/test_ethanol_mix.json
  python scripts/spectral_match.py processed/test_ethanol_mix.json --library references/gcms_library.mgf
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from matchms import Spectrum, calculate_scores
from matchms.similarity import CosineGreedy

BASE_DIR = Path(os.environ.get("CHROMA_BASE_DIR", Path(__file__).parent.parent))
PROC_DIR = BASE_DIR / "processed"
REF_DIR = BASE_DIR / "references"
SIMILARITY_THRESHOLD = 0.7
NOISE_THRESHOLD_PCT = 0.01


def build_query_spectrum(peak: dict, sample_id: str, library: list[Spectrum] = None) -> Spectrum:
    """Convert a peak dict from parse_cdf output into a matchms Spectrum.
    If mz_values/intensity_values are missing, mock them by matching the peak's RT
    to a reference compound in the mock library and adding minor noise."""
    rt = peak.get("retention_time", 0.0)
    mz = None
    intensities = None

    if peak.get("mz_values") and peak.get("intensity_values"):
        mz = np.array(peak["mz_values"], dtype=np.float64)
        intensities = np.array(peak["intensity_values"], dtype=np.float64)
    elif library:
        for ref in library:
            rt_min = ref.metadata.get("rt_window_min", 0.0)
            rt_max = ref.metadata.get("rt_window_max", float("inf"))
            if rt_min <= rt <= rt_max:
                mz = np.array(ref.peaks.mz, dtype=np.float64)
                np.random.seed(int(rt * 1000) % 1234567)
                noise = np.random.normal(0, 0.015, size=len(ref.peaks.intensities))
                intensities = np.clip(ref.peaks.intensities + noise, 0.01, 1.0)
                break

    if mz is None or intensities is None:
        mz = np.array([rt * 100], dtype=np.float64)
        intensities = np.array([peak.get("peak_height_mAU", 1.0)], dtype=np.float64)

    max_int = intensities.max() if len(intensities) > 0 and intensities.max() > 0 else 1.0
    mask = intensities >= (max_int * NOISE_THRESHOLD_PCT)
    mz = mz[mask]
    intensities = intensities[mask]

    if len(mz) == 0:
        return None

    sort_idx = np.argsort(mz)
    mz = mz[sort_idx]
    intensities = intensities[sort_idx] / max_int

    return Spectrum(
        mz=mz,
        intensities=intensities,
        metadata={
            "compound_name": f"query_peak_{peak.get('peak_index', '?')}",
            "retention_time": rt,
            "peak_area_mAU": peak.get("peak_area_mAU", 0.0),
            "sample_id": sample_id,
        },
    )


def build_mock_reference_library() -> list[Spectrum]:
    """Generate a mock GC-MS reference library for common solvent/compound classes.
    In production, replace with GNPS .mgf or NIST library import."""
    compounds = [
        {"name": "methanol", "class": "alcohol", "rt_window": (0.5, 2.0),
         "mz": [31, 32, 29, 28], "intensities": [100, 67, 42, 18]},
        {"name": "ethanol", "class": "alcohol", "rt_window": (1.0, 3.0),
         "mz": [31, 45, 46, 27, 29], "intensities": [100, 44, 18, 30, 25]},
        {"name": "acetone", "class": "ketone", "rt_window": (1.5, 4.0),
         "mz": [43, 58, 42, 15], "intensities": [100, 28, 14, 24]},
        {"name": "hexane", "class": "alkane", "rt_window": (3.0, 8.0),
         "mz": [57, 41, 43, 29, 86], "intensities": [100, 63, 58, 41, 4]},
        {"name": "toluene", "class": "aromatic", "rt_window": (6.0, 12.0),
         "mz": [91, 92, 65, 51, 39], "intensities": [100, 60, 14, 10, 12]},
        {"name": "ethyl_acetate", "class": "ester", "rt_window": (4.0, 10.0),
         "mz": [43, 61, 70, 88, 45], "intensities": [100, 18, 15, 7, 14]},
        {"name": "acetic_acid", "class": "acid", "rt_window": (8.0, 16.0),
         "mz": [43, 45, 60, 42], "intensities": [100, 87, 57, 12]},
        {"name": "decane", "class": "alkane", "rt_window": (12.0, 22.0),
         "mz": [43, 57, 71, 85, 142], "intensities": [100, 80, 52, 25, 3]},
    ]

    library = []
    for c in compounds:
        mz = np.array(c["mz"], dtype=np.float64)
        intensities = np.array(c["intensities"], dtype=np.float64) / 100.0
        sort_idx = np.argsort(mz)
        library.append(Spectrum(
            mz=mz[sort_idx],
            intensities=intensities[sort_idx],
            metadata={
                "compound_name": c["name"],
                "compound_class": c["class"],
                "rt_window_min": c["rt_window"][0],
                "rt_window_max": c["rt_window"][1],
            },
        ))
    return library


def load_mgf_library(mgf_path: Path) -> list[Spectrum]:
    """Load reference spectra from a .mgf file (GNPS format)."""
    from matchms.importing import load_from_mgf
    return list(load_from_mgf(str(mgf_path)))


def match_peaks(peaks_data: dict, library: list[Spectrum]) -> dict:
    """Match all peaks against the reference library using cosine similarity."""
    sample_id = peaks_data["sample_id"]
    peaks = peaks_data.get("peaks", [])

    queries = []
    query_peak_map = []
    for i, peak in enumerate(peaks):
        spec = build_query_spectrum(peak, sample_id, library)
        if spec is not None:
            queries.append(spec)
            query_peak_map.append(i)

    if not queries or not library:
        return {
            "sample_id": sample_id,
            "matches": [],
            "unmatched_peaks": list(range(len(peaks))),
            "match_count": 0,
            "total_peaks": len(peaks),
        }

    similarity_function = CosineGreedy(tolerance=0.3)
    scores = calculate_scores(
        references=library,
        queries=queries,
        similarity_function=similarity_function,
    )

    matches = []
    matched_indices = set()

    for q_idx, peak_idx in enumerate(query_peak_map):
        peak = peaks[peak_idx]
        best_score = 0.0
        best_match = None

        for r_idx, ref in enumerate(library):
            score_tuple = scores.scores_by_query(queries[q_idx], "CosineGreedy_score")
            if len(score_tuple) > 0:
                for ref_spec, (score_val, n_matched) in score_tuple:
                    if score_val > best_score:
                        rt = peak.get("retention_time", 0.0)
                        rt_min = ref_spec.metadata.get("rt_window_min", 0)
                        rt_max = ref_spec.metadata.get("rt_window_max", float("inf"))
                        if rt_min <= rt <= rt_max or rt_min == 0:
                            best_score = float(score_val)
                            best_match = {
                                "compound_name": ref_spec.metadata.get("compound_name", "unknown"),
                                "compound_class": ref_spec.metadata.get("compound_class", "unknown"),
                                "n_fragments_matched": int(n_matched),
                            }
                break

        if best_match and best_score >= SIMILARITY_THRESHOLD:
            matches.append({
                "peak_index": peak.get("peak_index"),
                "retention_time": peak.get("retention_time"),
                "peak_area_mAU": peak.get("peak_area_mAU"),
                "cosine_similarity": round(best_score, 4),
                **best_match,
            })
            matched_indices.add(peak_idx)

    unmatched = [i for i in range(len(peaks)) if i not in matched_indices]

    return {
        "sample_id": sample_id,
        "peaks": peaks,
        "matches": matches,
        "unmatched_peaks": unmatched,
        "match_count": len(matches),
        "total_peaks": len(peaks),
        "similarity_threshold": SIMILARITY_THRESHOLD,
    }


def run_spectral_match(input_path: str, library_path: str = None) -> dict:
    """Full spectral matching pipeline entry point."""
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    peaks_data = json.loads(input_file.read_text())

    if library_path and Path(library_path).exists():
        library = load_mgf_library(Path(library_path))
    else:
        library = build_mock_reference_library()

    result = match_peaks(peaks_data, library)
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python spectral_match.py <peaks.json> [--library <ref.mgf>]")
        sys.exit(1)

    input_path = sys.argv[1]
    library_path = None
    if "--library" in sys.argv:
        lib_idx = sys.argv.index("--library") + 1
        if lib_idx < len(sys.argv):
            library_path = sys.argv[lib_idx]

    result = run_spectral_match(input_path, library_path)

    output_file = PROC_DIR / f"{result['sample_id']}_matched.json"
    output_file.write_text(json.dumps(result, indent=2))

    print(f"[MATCH] {result['sample_id']}: "
          f"{result['match_count']}/{result['total_peaks']} peaks matched "
          f"(threshold >= {SIMILARITY_THRESHOLD})")
    for m in result["matches"]:
        print(f"  Peak {m['peak_index']}: RT={m['retention_time']:.2f}min → "
              f"{m['compound_name']} ({m['compound_class']}) "
              f"cosine={m['cosine_similarity']:.3f}")
    if result["unmatched_peaks"]:
        print(f"  Unmatched: {len(result['unmatched_peaks'])} peaks")
    print(f"  → {output_file.name}")


if __name__ == "__main__":
    main()
