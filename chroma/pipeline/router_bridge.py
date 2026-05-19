# chroma/pipeline/router_bridge.py
# Python wrapper to call the Node.js router from Python

import subprocess
import json
import sys
from pathlib import Path

ROUTER_ROOT = Path(__file__).parent.parent.parent  # repo root

def ask(purpose: str, prompt: str, system: str = None, **kwargs) -> dict:
    """Call the Node.js tiered-ask router from Python."""
    payload = {"purpose": purpose, "prompt": prompt}
    if system:
        payload["system"] = system
    payload.update(kwargs)

    result = subprocess.run(
        ["node", "-e", f"""
const {{ ask }} = require('./lib/tiered-ask.cjs');
ask({json.dumps(payload)}).then(r => {{
  console.log(JSON.stringify(r));
  process.exit(0);
}}).catch(e => {{
  console.error(JSON.stringify({{error: e.message}}));
  process.exit(1);
}});
        """],
        capture_output=True, text=True, cwd=str(ROUTER_ROOT), timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"Router error: {result.stderr[:500]}")
    return json.loads(result.stdout.strip())


# CHROMA-specific helper functions

def classify_peaks(peak_data: list) -> dict:
    """T1: Classify peaks as true/noise/artifact."""
    prompt = f"Classify each GC-MS peak. Return JSON with 'id' and 'label' (true_peak/noise/artifact).\nPeaks: {json.dumps(peak_data)}"
    return ask("classify", prompt)

def enrich_compound(matchms_hit: dict) -> dict:
    """T2: Enrich compound name from spectral match."""
    prompt = f"Enrich this GC-MS compound hit with IUPAC name, molecular formula, and CAS if known.\nHit: {json.dumps(matchms_hit)}"
    return ask("enrich", prompt)

def design_gnn_architecture(problem_desc: str) -> dict:
    """T3: Design GNN architecture for peak deconvolution."""
    return ask("gnn_architecture", problem_desc, max_tokens=3000)

def write_manuscript_section(section: str, content_notes: str) -> dict:
    """Antigravity: Write manuscript section (manual, budget-aware)."""
    system = "You are a scientific writer for SLAS Technology journal. Write in formal academic English."
    prompt = f"Write the {section} section of the CHROMA-AGENT-ALPHA manuscript.\nNotes: {content_notes}"
    return ask("manuscript", prompt, system=system, max_tokens=4096)
