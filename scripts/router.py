"""
Chroma-Agent-Alpha Python Router v2
Routes chromatography pipeline tasks to correct model tier.
T1=Ollama local | T2=OpenRouter free | T3=OpenRouter paid
Bug fixed: _call_openrouter now passes headers and json separately.
"""
import os, requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\chroma-agent-alpha\.env")

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OR_URL     = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_KEY     = os.getenv("OPENROUTER_API_KEY", "")

MODELS = {
    "t1_code"   : os.getenv("TIER1_MODEL"),
    "t1_reason" : os.getenv("TIER1_FALLBACK"),
    "t2_code"   : os.getenv("TIER2_MODEL"),
    "t2_fb"     : os.getenv("TIER2_FALLBACK"),
    "t2_summ"   : os.getenv("TIER2_MODEL"),
    "t3"        : os.getenv("TIER3_MODEL"),
    "t3_cot"    : os.getenv("TIER3_COT_MODEL"),
}

ROUTING = {
    "parse_cdf"    : ("t1", "t1_code"),
    "parse_mzml"   : ("t1", "t1_code"),
    "baseline_als" : ("t1", "t1_code"),
    "peak_detect"  : ("t1", "t1_code"),
    "trapz_verify" : ("t1", "t1_reason"),
    "debug_math"   : ("t1", "t1_reason"),
    "n8n_workflow" : ("t2", "t2_code"),
    "gnn_design"   : ("t3", "t3_cot"),
    "literature"   : ("t2", "t2_summ"),
    "phd_email"    : ("t2", "t2_summ"),
    "manuscript"   : ("t3", "t3"),
    "full_pipeline": ("t3", "t3"),
    "cadet_design" : ("t3", "t3"),
}

def route(task: str, prompt: str, system: str = None) -> dict:
    """Route task to tier. Baseline correction always precedes peak detection."""
    if task not in ROUTING:
        raise ValueError(f"Unknown task: '{task}'. Valid: {list(ROUTING.keys())}")
    tier, mkey = ROUTING[task]
    model = MODELS[mkey]
    print(f"[ROUTER] {task} → {tier.upper()} | {model}")
    return _call_openrouter(model, prompt, system, tier=tier)

def _call_ollama(model: str, prompt: str, system: str = None) -> dict:
    """T1: local Ollama. Zero cost. Chromatography data stays on-device."""
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(f"{OLLAMA_URL}/api/chat",
                      json={"model": model, "messages": msgs, "stream": False},
                      timeout=120)
    r.raise_for_status()
    text = r.json()["message"]["content"]
    return {"tier": "T1", "model": model, "response": text, "cost_inr": 0}

def _call_openrouter(model: str, prompt: str, system: str = None, tier: str = "T2/T3") -> dict:
    """T1/T2/T3: OpenRouter. Fully migrated pipeline."""
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    headers = {
        "Authorization": f"Bearer {OR_KEY}",
        "HTTP-Referer": "https://github.com/chroma-agent-alpha",
        "X-Title": "Chroma-Agent-Alpha",
        "Content-Type": "application/json"
    }
    payload = {"model": model, "messages": msgs}
    r = requests.post(f"{OR_URL}/chat/completions",
                      headers=headers,
                      json=payload,
                      timeout=120)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return {"tier": tier.upper(), "model": model, "response": text}

def math_verify(y: list, x: list) -> float:
    """Trapezoidal Rule verification: A = sum (y_{i-1}+y_i)/2 * (x_i - x_{i-1})"""
    import numpy as np
    area = float(np.trapz(y=y, x=x))
    print(f"[MATH CHECK] Trapezoidal area = {area:.4f} mAU·min")
    return area

if __name__ == "__main__":
    print("=== T1 Router Test ===")
    result = route(
        task="parse_cdf",
        prompt="Write Python: open netCDF4 file, print variable names. 5 lines max.",
        system="You are a chromatography data engineer. Output code only."
    )
    print(f"Tier: {result['tier']} | Model: {result['model']}")
    print(f"Response:\n{result['response']}")
