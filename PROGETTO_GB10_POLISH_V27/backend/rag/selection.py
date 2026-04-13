
import os, json, subprocess
from typing import List, Dict, Any, Optional
from .config import settings

SELECT_FILE = os.path.join(settings.CONFIG_DIR, "selected.json")

def _read_selected_file() -> Dict[str, str]:
    if os.path.exists(SELECT_FILE):
        try:
            with open(SELECT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if os.path.exists(settings.LEGACY_SELECTED_PATH):
        try:
            with open(settings.LEGACY_SELECTED_PATH, "r", encoding="utf-8") as f:
                llm = f.read().strip()
                return {"llm": llm}
        except Exception:
            pass
    return {}

def _write_selected_file(sel: Dict[str, str]):
    os.makedirs(settings.CONFIG_DIR, exist_ok=True)
    with open(SELECT_FILE, "w", encoding="utf-8") as f:
        json.dump(sel, f, ensure_ascii=False, indent=2)
    try:
        with open(settings.LEGACY_SELECTED_PATH, "w", encoding="utf-8") as f:
            f.write(sel.get("llm", ""))
    except Exception:
        pass

def get_selection() -> Dict[str, str]:
    sel = _read_selected_file()
    if "llm" not in sel: sel["llm"] = settings.DEFAULT_LLM
    if "embedding" not in sel: sel["embedding"] = settings.EMBEDDING_MODEL
    return sel

def set_selection(llm: Optional[str] = None, embedding: Optional[str] = None) -> Dict[str, str]:
    sel = get_selection()
    if llm: sel["llm"] = llm
    if embedding: sel["embedding"] = embedding
    _write_selected_file(sel)
    return sel

def list_models_http() -> List[Dict[str, Any]]:
    import httpx
    url = f"{settings.OLLAMA_BASE_URL}/api/tags"
    with httpx.Client(timeout=20) as c:
        r = c.get(url); r.raise_for_status()
        models = r.json().get("models", [])
        out = []
        for m in models:
            name = m.get("name") or m.get("model")
            if not name: continue
            out.append({"name": name, "size": m.get("size"), "modified_at": m.get("modified_at"), "digest": m.get("digest")})
        out.sort(key=lambda x: x["name"].lower())
        return out

def list_models_cli() -> List[Dict[str, Any]]:
    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
        if res.returncode != 0: return []
        lines = res.stdout.strip().splitlines()
        models = []
        if len(lines) > 1:
            for line in lines[1:]:
                if not line.strip(): continue
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    model_id = parts[1] if len(parts) > 1 else ""
                    size = parts[2] if len(parts) > 2 else ""
                    modified = " ".join(parts[3:]) if len(parts) > 3 else ""
                    models.append({"name": name, "size": size, "modified_at": modified, "digest": model_id})
        return models
    except Exception:
        return []

def list_models() -> List[Dict[str, Any]]:
    try: return list_models_http()
    except Exception: return list_models_cli()

def validate_model_quick(model: str) -> bool:
    import httpx
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {"model": model, "prompt": "ok", "stream": False, "options": {"num_predict": 1}}
    try:
        with httpx.Client(timeout=20) as c:
            r = c.post(url, json=payload); r.raise_for_status()
            return True
    except Exception:
        return False

def warmup_model(model: str) -> bool:
    return validate_model_quick(model)

def ps_http() -> List[str]:
    import httpx
    url = f"{settings.OLLAMA_BASE_URL}/api/ps"
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(url)
            if r.status_code != 200: return []
            j = r.json()
            names = []
            for m in j.get("models", []):
                n = m.get("name") or m.get("model")
                if n: names.append(n)
            return names
    except Exception:
        return []

def ps_cli() -> List[str]:
    try:
        res = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=10)
        if res.returncode != 0: return []
        lines = res.stdout.strip().splitlines()
        names = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts: names.append(parts[0])
        return names
    except Exception:
        return []

def ps_models() -> List[str]:
    names = ps_http()
    if names: return names
    return ps_cli()

def stop_http(name: str) -> bool:
    import httpx
    url = f"{settings.OLLAMA_BASE_URL}/api/stop"
    try:
        with httpx.Client(timeout=10) as c:
            r = c.post(url, json={"name": name})
            return 200 <= r.status_code < 300
    except Exception:
        return False

def stop_cli(name: str) -> bool:
    try:
        res = subprocess.run(["ollama", "stop", name], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False

def stop_model(name: str) -> bool:
    if not name: return False
    if stop_http(name): return True
    return stop_cli(name)
