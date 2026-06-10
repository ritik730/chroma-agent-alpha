"""
parse_cdf.py — Extract chromatographic peaks from AIA/ANDI netCDF (.cdf) files.
Pipeline: load → ALS baseline correction → peak detection → np.trapezoid integration → JSON.
"""
import json
import struct
import sys
from io import BytesIO
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
    elif "total_intensity" in ds.variables:
        intensity = np.array(ds.variables["total_intensity"][:], dtype=np.float64)
        if "scan_acquisition_time" in ds.variables:
            # Typically scan_acquisition_time is in seconds, convert to minutes
            rt = np.array(ds.variables["scan_acquisition_time"][:], dtype=np.float64) / 60.0
        else:
            n = len(intensity)
            rt = np.linspace(0.0, n - 1, n)
            meta["rt_reconstructed"] = True
    else:
        raise KeyError(f"No ordinate_values or total_intensity in {filepath}. Variables: {list(ds.variables)}")

    if "detector_unit" in ds.ncattrs():
        meta["unit"] = ds.getncattr("detector_unit")

    ds.close()
    return rt, intensity, meta


def load_mzml(filepath: str) -> tuple[np.ndarray, np.ndarray, dict, list]:
    """Load retention time, intensity arrays (TIC), metadata, and scan spectra from an mzML file."""
    from pyteomics import mzml
    
    rt_list = []
    intensity_list = []
    spectra_data = []
    
    with mzml.read(filepath) as reader:
        for spec in reader:
            # 1. Extract retention time
            scan_time = None
            if 'scanList' in spec and 'scan' in spec['scanList']:
                scan = spec['scanList']['scan'][0]
                if 'scan start time' in scan:
                    scan_time = scan['scan start time']
                    
                    # Convert to minutes if scan start time is in seconds
                    unit_str = str(getattr(scan_time, 'unit_info', '')).lower()
                    unit_name = ""
                    scan_start_time_val = scan.get('scan start time', {})
                    if isinstance(scan_start_time_val, dict):
                        unit_name = scan_start_time_val.get('unitName', '').lower()
                    if 'second' in unit_str or 'second' in unit_name:
                        scan_time = float(scan_time) / 60.0
                    else:
                        scan_time = float(scan_time)
            
            if scan_time is None:
                # Default fallback index-based retention time
                scan_time = len(rt_list) * 0.01
                
            rt_list.append(scan_time)
            
            # 2. Extract total intensity (TIC)
            tic = spec.get('total ion current')
            if tic is not None:
                intensity_list.append(float(tic))
            else:
                # Sum the intensity array if TIC is missing
                intensities = spec.get('intensity array')
                if intensities is not None and len(intensities) > 0:
                    intensity_list.append(float(np.sum(intensities)))
                else:
                    intensity_list.append(0.0)
                    
            # 3. Store m/z and intensity arrays
            mz_arr = spec.get('m/z array')
            int_arr = spec.get('intensity array')
            if mz_arr is not None and int_arr is not None:
                spectra_data.append((mz_arr, int_arr))
            else:
                spectra_data.append((np.array([]), np.array([])))
                
    rt = np.array(rt_list, dtype=np.float64)
    # Heuristic fallback: if maximum RT is extremely large, it's in seconds
    if len(rt) > 0 and rt.max() > 150:
        rt = rt / 60.0
        
    intensity = np.array(intensity_list, dtype=np.float64)
    meta = {
        "source": Path(filepath).name,
        "format": "mzML"
    }
    return rt, intensity, meta, spectra_data


def decode_sms_val(first_byte: int, additional_bytes: bytes) -> int:
    """
    Decode variable-width packed mass spectrometry telemetry values using the Varian 
    bit-masking logic. Converts packed binary structures into numeric peak 
    intensities or m/z delta steps for chemical fragment reconstruction.
    """
    val = first_byte
    for b in additional_bytes:
        val = (val << 8) | b
    length = 1 + len(additional_bytes)
    value_bits = 8 * length - 4
    d = (val >> value_bits) & 0xF
    # Custom mask override for Varian .xms files (d >= 8 uses 12-bit mask to prevent integer overflow)
    bit_map = {
        4: 13, 5: 13,
        6: 14, 7: 14,
        8: 12, 9: 12, 10: 12, 11: 12,
        12: 12, 13: 12, 14: 12, 15: 12
    }
    n_bits = bit_map.get(d, 12)
    mask = (1 << n_bits) - 1
    return val & mask


def parse_val(f) -> int | None:
    """
    Read and parse a single variable-width chunk from the Varian binary 
    mass spectra stream. Decodes telemetry offsets and peak intensities representing 
    eluted chemical fragments.
    """
    b = f.read(1)
    if not b or b == b'\x00':
        return None
    first_byte = b[0]
    hex1 = first_byte >> 4
    if hex1 < 4:
        return first_byte
    else:
        add_len = hex1 // 4
        add_bytes = f.read(add_len)
        if len(add_bytes) < add_len:
            return None
        return decode_sms_val(first_byte, add_bytes)


def read_ms_block(f) -> list[tuple[float, int]]:
    """
    Read a single scan block from the Varian spectra stream, decoding 
    sequential peaks. Reconstructs cumulative m/z values and matching 
    intensities for chemical compound identification.
    """
    mz_accum = 0
    spectrum = []
    
    b = f.read(1)
    if not b or b == b'\x00':
        return []
    f.seek(-1, 1)
    
    is_first = True
    while True:
        b_next = f.read(1)
        if not b_next or b_next == b'\x00':
            break
        f.seek(-1, 1)
        
        mz_delta = parse_val(f)
        if mz_delta is None:
            break
        intensity = parse_val(f)
        if intensity is None:
            break
            
        if is_first:
            mz_accum = mz_delta
            is_first = False
        else:
            mz_accum += mz_delta
            
        spectrum.append((mz_accum / 10.0, intensity))
        
    return spectrum


def skip_null_bytes(f) -> None:
    """
    Skip padding null bytes between sequential mass spectra blocks in the 
    instrument telemetry data stream to align scan reading heads.
    """
    while True:
        b = f.read(1)
        if not b:
            break
        if b != b'\x00':
            f.seek(-1, 1)
            break


def load_xms(filepath: str) -> tuple[np.ndarray, np.ndarray, dict, list]:
    """
    Parse a proprietary Varian .xms chromatography data file to extract 
    retention times, total ion chromatogram (TIC) intensities, file metadata, 
    and mass spectra. This native parser acts as a vital tool for recovering 
    chemical profiles directly from instrument telemetry when external 
    preprocessors (like ProteoWizard msconvert) are unavailable.
    """
    with open(filepath, "rb") as f:
        # Directory entries start at offset 38
        f.seek(38)
        entries = []
        for _ in range(64):
            data = f.read(50)
            if len(data) < 50:
                break
            start_off, end_off, idx = struct.unpack("<IIH", data[:10])
            if start_off == 0 and end_off == 0:
                break
            name = data[18:50].split(b"\x00")[0].decode("ascii", errors="ignore")
            entries.append({"name": name, "start": start_off, "end": end_off})
            
        msdata = next((e for e in entries if e["name"] == "MSData"), None)
        if not msdata:
            raise ValueError("MSData section not found in .xms file.")
            
        f.seek(msdata["start"])
        msdata_bytes = f.read(msdata["end"] - msdata["start"])
        
    f_mem = BytesIO(msdata_bytes)
    
    # Telemetry starts at 7966 relative to MSData start
    # Spectra starts at 1373974 relative to MSData start
    start_offset = 7966
    stride = 282
    n_records = (1373974 - start_offset) // stride
    
    # 1. Parse telemetry to get RT values and active range
    rts = []
    active_indices = []
    for i in range(n_records):
        offset = start_offset + i * stride
        rt = struct.unpack("<f", msdata_bytes[offset+4 : offset+8])[0]
        rts.append(rt)
        # We only want the active run scans, say where 0.5 <= rt <= 120.0 minutes
        if 0.5 <= rt <= 120.0:
            active_indices.append(i)
            
    if not active_indices:
        raise ValueError("No active scans found in RT range [0.5, 120.0] min.")
        
    start_active = active_indices[0]
    end_active = active_indices[-1]
    n_active = end_active - start_active + 1
    
    # 2. Seek to the start of spectra stream and skip to the start_active block
    f_mem.seek(1373974)
    skip_null_bytes(f_mem)
    
    # Skip blocks before start_active
    for _ in range(start_active):
        read_ms_block(f_mem)
        skip_null_bytes(f_mem)
        
    # 3. Read active spectra blocks
    rt_list = []
    intensity_list = []
    spectra_data = []
    
    for i in range(n_active):
        scan_idx = start_active + i
        rt_val = rts[scan_idx]
        
        spec = read_ms_block(f_mem)
        skip_null_bytes(f_mem)
        
        # Filter peaks to standard GC-MS mass range [45.0, 650.0]
        filtered = [(mz, val) for mz, val in spec if 45.0 <= mz <= 650.0]
        
        # TIC is sum of intensities of filtered peaks
        tic = sum(val for mz, val in filtered)
        
        rt_list.append(rt_val)
        intensity_list.append(tic)
        
        if filtered:
            mz_arr = np.array([p[0] for p in filtered], dtype=np.float64)
            int_arr = np.array([p[1] for p in filtered], dtype=np.float64)
        else:
            mz_arr = np.array([], dtype=np.float64)
            int_arr = np.array([], dtype=np.float64)
            
        spectra_data.append((mz_arr, int_arr))
        
    rt = np.array(rt_list, dtype=np.float64)
    intensity = np.array(intensity_list, dtype=np.float64)
    meta = {
        "source": Path(filepath).name,
        "format": "XMS"
    }
    return rt, intensity, meta, spectra_data


def load_agilent_ch(filepath: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Parse a proprietary Agilent ChemStation/OpenLab .ch chromatography binary file.
    Reads delta-compressed 16-bit and 32-bit values and scales them to abundance units.
    """
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    if len(file_bytes) < 4:
        raise ValueError("Empty or invalid Agilent .ch file.")

    # Determine endianness and version
    version = struct.unpack(">H", file_bytes[0:2])[0]
    is_little = False
    if version > 1000:
        version = struct.unpack("<H", file_bytes[0:2])[0]
        is_little = True

    endian = "<" if is_little else ">"

    try:
        start_time = struct.unpack(f"{endian}f", file_bytes[282:286])[0]
        end_time = struct.unpack(f"{endian}f", file_bytes[286:290])[0]
    except Exception:
        start_time = 0.0
        end_time = 60.0

    try:
        scale = struct.unpack(f"{endian}d", file_bytes[580:588])[0]
    except Exception:
        scale = 1.333e-4

    data_offset = 6144
    if len(file_bytes) < data_offset:
        data_offset = 1024

    idx = data_offset
    y_values = []

    # Read first absolute value (32-bit integer)
    if idx + 4 <= len(file_bytes):
        curr_val = struct.unpack(f"{endian}i", file_bytes[idx : idx+4])[0]
        y_values.append(curr_val)
        idx += 4
    else:
        curr_val = 0

    while idx < len(file_bytes):
        if idx + 2 > len(file_bytes):
            break
        delta16 = struct.unpack(f"{endian}h", file_bytes[idx : idx+2])[0]
        idx += 2

        if delta16 == -32768:  # 0x8000 escape code for 32-bit delta
            if idx + 4 > len(file_bytes):
                break
            delta32 = struct.unpack(f"{endian}i", file_bytes[idx : idx+4])[0]
            idx += 4
            curr_val += delta32
        else:
            curr_val += delta16

        y_values.append(curr_val)

    intensity = np.array(y_values, dtype=np.float64) * scale
    n = len(intensity)
    
    if n > 1:
        rt = np.linspace(start_time, end_time, n)
    else:
        rt = np.array([start_time])

    meta = {
        "source": Path(filepath).name,
        "format": "Agilent .ch",
        "points": n,
        "version": version
    }
    return rt, intensity, meta


def load_any_file(filepath: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Unified loader that routes to the correct format parser (.cdf, .mzml, .xms, or .ch) 
    based on the file suffix. Serves as a single entry point for all raw instrument files.
    """
    path = Path(filepath)
    if path.is_dir():
        ch_files = list(path.glob("*.ch")) + list(path.glob("*.CH"))
        if ch_files:
            filepath = str(ch_files[0])
            path = Path(filepath)
        else:
            raise FileNotFoundError(f"No .ch files found in directory {filepath}")

    suffix = path.suffix.lower()
    if suffix == ".mzml":
        rt, intensity, meta, _ = load_mzml(str(path))
    elif suffix in (".xms", ".sms"):
        rt, intensity, meta, _ = load_xms(str(path))
    elif suffix in (".ch", ".CH"):
        rt, intensity, meta = load_agilent_ch(str(path))
    else:
        rt, intensity, meta = load_cdf(str(path))
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
                 height_pct: float = 0.01, distance_pts: int = 10,
                 prominence_pct: float = 0.005) -> list[dict]:
    """Find chromatographic peaks in baseline-corrected signal.
    height_pct and prominence_pct are fractions of max corrected intensity.
    Adaptive thresholds: caps the relative threshold to prevent massive dominant peaks from inflating it."""
    max_val = corrected.max()
    if max_val <= 0:
        return []

    # Calculate relative threshold and apply a cap to protect minor peaks in high dynamic range samples
    calc_height = max_val * height_pct
    calc_prominence = max_val * prominence_pct
    
    height_threshold = min(calc_height, 10000.0)
    prominence_threshold = min(calc_prominence, 5000.0)

    indices, props = find_peaks(
        corrected,
        height=height_threshold,
        distance=distance_pts,
        prominence=prominence_threshold,
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
    """Full pipeline: load .cdf/.mzML/.xms/.ch → ALS baseline → peak detect → trapz validate → JSON dict."""
    filepath_path = Path(filepath)
    if filepath_path.is_dir():
        ch_files = list(filepath_path.glob("*.ch")) + list(filepath_path.glob("*.CH"))
        if ch_files:
            filepath_path = ch_files[0]
            filepath = str(filepath_path)
            
    suffix = filepath_path.suffix.lower()
    
    spectra_data = None
    if suffix == ".mzml":
        rt, intensity, meta, spectra_data = load_mzml(filepath)
    elif suffix in (".xms", ".sms"):
        rt, intensity, meta, spectra_data = load_xms(filepath)
    elif suffix in (".ch", ".CH"):
        rt, intensity, meta = load_agilent_ch(filepath)
    else:
        rt, intensity, meta = load_cdf(filepath)

    baseline = als_baseline(intensity)
    corrected = intensity - baseline

    peaks = detect_peaks(rt, corrected)

    if suffix in (".mzml", ".xms", ".sms"):
        if spectra_data:
            for p in peaks:
                idx = p["peak_index"]
                if idx < len(spectra_data):
                    mz_vals, int_vals = spectra_data[idx]
                    if len(mz_vals) > 0:
                        p["mz_values"] = [round(float(m), 2) for m in mz_vals]
                        p["intensity_values"] = [round(float(val), 1) for val in int_vals]
    elif suffix in (".ch", ".CH", ".cdf", ".CDF"):
        # For FID signals (.ch or 1D .cdf), there are no mass spectra fragments.
        # We set default peak mz/intensity values to represent FID detection.
        for p in peaks:
            p["mz_values"] = [0.0]
            p["intensity_values"] = [round(p["peak_height_mAU"], 1)]
    else:
        ds = nc.Dataset(filepath, "r")
        if "scan_index" in ds.variables and "mass_values" in ds.variables and "intensity_values" in ds.variables and "point_count" in ds.variables:
            for p in peaks:
                idx = p["peak_index"]
                if idx < len(ds.variables["scan_index"]):
                    start_ptr = int(ds.variables["scan_index"][idx])
                    count = int(ds.variables["point_count"][idx])
                    if count > 0:
                        p["mz_values"] = [round(float(m), 2) for m in ds.variables["mass_values"][start_ptr : start_ptr + count]]
                        p["intensity_values"] = [round(float(val), 1) for val in ds.variables["intensity_values"][start_ptr : start_ptr + count]]
        ds.close()

    total_area, peak_sum = validate_total_area(rt, corrected, peaks)

    sample_id = filepath_path.stem

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
        files = (list(cdf_dir.glob("*.cdf")) + list(cdf_dir.glob("*.CDF")) + 
                 list(cdf_dir.glob("*.mzml")) + list(cdf_dir.glob("*.mzML")) +
                 list(cdf_dir.glob("*.xms")) + list(cdf_dir.glob("*.XMS")) +
                 list(cdf_dir.glob("*.sms")) + list(cdf_dir.glob("*.SMS")) +
                 list(cdf_dir.glob("*.ch")) + list(cdf_dir.glob("*.CH")) +
                 list(cdf_dir.glob("*.d")) + list(cdf_dir.glob("*.D")))
        if not files:
            print(f"Usage: python parse_cdf.py <file.cdf/.mzml/.xms>")
            print(f"   or: place chromatogram files in {cdf_dir}")
            sys.exit(1)
    else:
        files = [Path(a) for a in sys.argv[1:]]

    out_dir = Path(r"C:\chroma-agent-alpha\processed\.cache")
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
