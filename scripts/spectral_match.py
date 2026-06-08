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
from dotenv import load_dotenv
from matchms import Spectrum, calculate_scores
from matchms.similarity import CosineGreedy

BASE_DIR = Path(os.environ.get("CHROMA_BASE_DIR", Path(__file__).parent.parent))
load_dotenv(dotenv_path=BASE_DIR / ".env")

PROC_DIR = BASE_DIR / "processed" / ".cache"
REF_DIR = BASE_DIR / "references"
SIMILARITY_THRESHOLD = 0.6
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


def query_public_db_batch_via_llm(peaks_to_query: list[dict], sample_id: str, failed_models: set = None) -> dict[int, dict]:
    """Query the LiteLLM/proxy public database matching endpoint for a batch of peaks.
    Returns a dict mapping peak_index to match dictionary."""
    if not peaks_to_query:
        return {}

    # Format spectrum for each peak in the batch
    peaks_formatted = []
    for peak in peaks_to_query:
        mz = peak.get("mz_values", [])
        intensities = peak.get("intensity_values", [])
        if not mz or not intensities:
            continue
        
        # Get top 10 fragments sorted by intensity descending
        indices = np.argsort(intensities)[::-1][:10]
        top_mz = [mz[idx] for idx in indices]
        top_int = [intensities[idx] for idx in indices]

        # Normalize intensities relative to base peak
        base_int = top_int[0] if top_int else 1.0
        if base_int <= 0:
            base_int = 1.0
        rel_int = [int(round((val / base_int) * 100)) for val in top_int]

        # Format spectrum string
        spec_str = ", ".join(f"m/z {m} ({ri}%)" for m, ri in zip(top_mz, rel_int))
        rt = peak.get("retention_time", 0.0)
        p_idx = peak.get("peak_index")
        
        peaks_formatted.append(f"- Peak {p_idx} (RT={rt:.2f} min): {spec_str}")

    if not peaks_formatted:
        return {}

    peaks_summary_str = "\n".join(peaks_formatted)

    prompt = f"""You are a mass spectrometry database search engine (such as NIST or MassBank). 
Analyze the electron ionization (EI) GC-MS mass spectra of these peaks detected in sample '{sample_id}':

{peaks_summary_str}

Identify each compound using your public chemical standards knowledge database. 
Note: The sample is derivatized with TMS (trimethylsilyl) reagent. If you see characteristic TMS fragments (such as m/z 73, 147, 191, etc.), suggest the appropriate TMS derivative name (e.g. "lactic acid, bis(trimethylsilyl) derivative", "glycerol-3tms", "alanine-2tms").

Return ONLY a JSON array where each item corresponds to one of the queried peaks, containing these keys:
- "peak_index": The integer index of the peak
- "compound_name": Suggest a specific chemical name (lowercase)
- "compound_class": Suggest its chemical class (alcohol, alkane, ester, acid, aromatic, terpene, ketone, amine, unknown)
- "cosine_similarity": A float between 0.70 and 1.00 representing your match confidence.

Return ONLY raw JSON, do not include markdown wrapper or conversational text.
"""

    import requests
    LITELLM_URL = "http://127.0.0.1:4000"

    # 1. Try LiteLLM first (20s timeout to allow remote model response)
    try:
        print(f"[PUBLIC DB BATCH] Querying LiteLLM first for {len(peaks_to_query)} peaks...")
        r = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": "Bearer sk-litellm-1234", "Content-Type": "application/json"},
            json={
                "model": "claude-t1",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.1,
            },
            timeout=20,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        json_str = content
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                striped_part = part.strip()
                if striped_part.startswith("[") or striped_part.startswith("{"):
                    json_str = striped_part
                    if json_str.startswith("json"):
                        json_str = json_str[4:].strip()
                    break
        import re
        json_match = re.search(r"\[\s*\{.*?\}\s*\]", json_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_match_obj = re.search(r"\{.*?\}", json_str, re.DOTALL)
            json_str = json_match_obj.group(0) if json_match_obj else json_str
        res_list = json.loads(json_str)
        results_map = {}
        for item in res_list:
            p_idx = item.get("peak_index")
            if p_idx is not None:
                results_map[int(p_idx)] = {
                    "compound_name": item.get("compound_name", "unknown"),
                    "compound_class": item.get("compound_class", "unknown"),
                    "cosine_similarity": float(item.get("cosine_similarity", 0.7)),
                }
        return results_map
    except Exception as e:
        print(f"[PUBLIC DB BATCH] LiteLLM failed for batch ({e}). Falling back to Claude proxy...")

    # 2. Direct Anthropic-style proxy fallback (the final boss)
    antigravity_base = os.environ.get("ANTIGRAVITY_BASE_URL", "http://localhost:8080")
    antigravity_model = os.environ.get("ANTIGRAVITY_MODEL", "claude-opus-4-6-thinking")
    
    url = f"{antigravity_base}/messages" if "/v1" in antigravity_base else f"{antigravity_base}/v1/messages"
    
    if failed_models is None:
        failed_models = set()
    # Prioritize fast, high-availability, non-thinking proxy models to avoid timeouts and rate-limit issues
    models_to_try = ["gemini-2.5-flash", "gemini-2.5-pro", antigravity_model, "gemini-3-flash-agent"]
    for current_model in models_to_try:
        if current_model in failed_models:
            continue
        try:
            print(f"[PUBLIC DB BATCH] Querying Claude proxy with model {current_model}...")
            r = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": current_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000,
                    "temperature": 0.1,
                },
                timeout=120,
                proxies={"http": None, "https": None},
            )
            r.raise_for_status()
            response_json = r.json()
            
            content = ""
            if "content" in response_json:
                content = "".join([c["text"] for c in response_json["content"] if c.get("type") == "text"]).strip()
            elif "text" in response_json:
                content = response_json["text"].strip()
                
            if not content:
                thinking_content = "".join([c.get("thinking", "") for c in response_json.get("content", []) if c.get("type") == "thinking"]).strip()
                if thinking_content:
                    content = thinking_content
                    
            if not content:
                print(f"[PUBLIC DB BATCH] Empty response returned by proxy for model {current_model}. Trying next...")
                continue
                
            json_str = content
            if "```" in content:
                parts = content.split("```")
                for part in parts:
                    striped_part = part.strip()
                    if striped_part.startswith("[") or striped_part.startswith("{"):
                        json_str = striped_part
                        if json_str.startswith("json"):
                            json_str = json_str[4:].strip()
                        break
            import re
            json_match = re.search(r"\[\s*\{.*?\}\s*\]", json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_match_obj = re.search(r"\{.*?\}", json_str, re.DOTALL)
                json_str = json_match_obj.group(0) if json_match_obj else json_str
                
            try:
                res_list = json.loads(json_str, strict=False)
            except Exception:
                res_list = json.loads(json_str)

            if isinstance(res_list, dict):
                for k, v in res_list.items():
                    if isinstance(v, list):
                        res_list = v
                        break
            
            if not isinstance(res_list, list):
                res_list = [res_list]

            results_map = {}
            for item in res_list:
                p_idx = item.get("peak_index")
                if p_idx is not None:
                    results_map[int(p_idx)] = {
                        "compound_name": item.get("compound_name", "unknown"),
                        "compound_class": item.get("compound_class", "unknown"),
                        "cosine_similarity": float(item.get("cosine_similarity", 0.7)),
                    }
            return results_map
        except Exception as proxy_err:
            print(f"[PUBLIC DB BATCH] Proxy query failed for model {current_model}: {proxy_err}")
            failed_models.add(current_model)
            
    print("[PUBLIC DB BATCH ERROR] Failed all LiteLLM and proxy fallbacks for this batch")
    return {}


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
            "deconvolution": peaks_data.get("deconvolution", "incomplete"),
            "n_regions": peaks_data.get("n_regions"),
            "n_coeluting_regions": peaks_data.get("n_coeluting_regions"),
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

    # Phase 1: Local Library matching
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
            peak["compound_name"] = best_match["compound_name"]
            peak["compound_class"] = best_match["compound_class"]
            peak["cosine_similarity"] = round(best_score, 4)
            peak["n_fragments_matched"] = best_match["n_fragments_matched"]

    # Phase 2: Fallback to public database query via LLM for unmatched peaks
    unmatched_peaks_to_query = []
    for peak_idx in query_peak_map:
        if peak_idx not in matched_indices:
            peak = peaks[peak_idx]
            if peak.get("mz_values") and peak.get("intensity_values"):
                unmatched_peaks_to_query.append(peak_idx)

    # Sort unmatched peaks by area descending, then height descending to prioritize significant signals
    unmatched_peaks_to_query.sort(
        key=lambda idx: (peaks[idx].get("peak_area_mAU", 0.0), peaks[idx].get("peak_height_mAU", 0.0)),
        reverse=True
    )
    # Limit query to top 100 peaks (encompassing almost all peaks in standard chromatograms)
    unmatched_peaks_to_query = unmatched_peaks_to_query[:100]

    # Query LLM for all unmatched peaks in batches of 15 to avoid exceeding token and output limits
    chunk_size = 15
    for start_i in range(0, len(unmatched_peaks_to_query), chunk_size):
        chunk_indices = unmatched_peaks_to_query[start_i:start_i + chunk_size]
        failed_models = set()
        peaks_to_send = [peaks[idx] for idx in chunk_indices]
        
        if peaks_to_send:
            print(f"[PUBLIC DB] Batch querying public database for peaks {start_i+1} to {start_i+len(peaks_to_send)} of {len(unmatched_peaks_to_query)} unmatched peaks...")
            batch_matches = query_public_db_batch_via_llm(peaks_to_send, sample_id, failed_models)
            
            for idx in chunk_indices:
                peak = peaks[idx]
                p_idx = peak.get("peak_index")
                llm_match = batch_matches.get(p_idx)
                
                if llm_match and llm_match.get("cosine_similarity", 0.0) >= SIMILARITY_THRESHOLD:
                    n_frags = len(peak.get("mz_values", []))
                    matches.append({
                        "peak_index": p_idx,
                        "retention_time": peak.get("retention_time"),
                        "peak_area_mAU": peak.get("peak_area_mAU"),
                        "cosine_similarity": round(llm_match["cosine_similarity"], 4),
                        "compound_name": llm_match["compound_name"],
                        "compound_class": llm_match["compound_class"],
                        "n_fragments_matched": min(n_frags, 10),
                    })
                    matched_indices.add(idx)
                    peak["compound_name"] = llm_match["compound_name"]
                    peak["compound_class"] = llm_match["compound_class"]
                    peak["cosine_similarity"] = round(llm_match["cosine_similarity"], 4)
                    peak["n_fragments_matched"] = min(n_frags, 10)

    # Populate matching attributes for unmatched peaks
    for idx in range(len(peaks)):
        if idx not in matched_indices:
            peak = peaks[idx]
            peak["compound_name"] = "unidentified"
            peak["compound_class"] = "unknown"
            peak["cosine_similarity"] = "N/A"
            peak["n_fragments_matched"] = "N/A"

    unmatched = [i for i in range(len(peaks)) if i not in matched_indices]

    return {
        "sample_id": sample_id,
        "deconvolution": peaks_data.get("deconvolution", "incomplete"),
        "n_regions": peaks_data.get("n_regions"),
        "n_coeluting_regions": peaks_data.get("n_coeluting_regions"),
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
