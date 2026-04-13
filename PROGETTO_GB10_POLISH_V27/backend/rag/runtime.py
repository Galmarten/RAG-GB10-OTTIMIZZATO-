
import os, json
from typing import Dict, Any
from .config import settings

RUNTIME_PATH = os.path.join(settings.CONFIG_DIR, "runtime.json")

DEFAULT_SYSTEM_PROMPT = ("Sei un assistente per l'Università Politecnica delle Marche (UNIVPM). "
                       "Rispondi in italiano e basati solo sui regolamenti interni e i documenti indicizzati. "
                       "Cita la fonte (titolo e numero pagina). Se non trovi la risposta nei documenti, dillo chiaramente. "
                       "Tono professionale e conciso.")

DEFAULTS = {
    "temperature": float(getattr(settings, "TEMPERATURE", 0.2)),
    "top_k": int(getattr(settings, "TOP_K", 5)),
    "chunk_size": int(getattr(settings, "CHUNK_SIZE", 1500)),
    "chunk_overlap": int(getattr(settings, "CHUNK_OVERLAP", 200)),
    "max_reply_chars": int(os.getenv("MAX_REPLY_CHARS", "50000")),
    "max_reply_seconds": int(os.getenv("MAX_REPLY_SECONDS", "300")),
    "system_prompt": os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
}

def _coerce(name: str, value):
    if name in ("temperature",):
        return float(value)
    if name in ("system_prompt",):
        return str(value)
    return int(value)

def get_runtime() -> Dict[str, Any]:
    data = {}
    if os.path.exists(RUNTIME_PATH):
        try:
            with open(RUNTIME_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    out = DEFAULTS.copy()
    for k, v in (data or {}).items():
        if k in out:
            try:
                out[k] = _coerce(k, v)
            except Exception:
                pass
    return out

def update_runtime(updates: Dict[str, Any]) -> Dict[str, Any]:
    cur = get_runtime()
    changed = False
    for k, v in (updates or {}).items():
        if k in cur and v is not None:
            try:
                nv = _coerce(k, v)
            except Exception:
                continue
            if cur[k] != nv:
                cur[k] = nv
                changed = True
    if changed:
        os.makedirs(settings.CONFIG_DIR, exist_ok=True)
        with open(RUNTIME_PATH, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=2)
    return cur
