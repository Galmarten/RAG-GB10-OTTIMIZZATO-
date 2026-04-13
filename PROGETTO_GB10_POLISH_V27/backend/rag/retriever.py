
import os, json, numpy as np, re, hashlib
from typing import List, Dict, Any
import httpx
from .config import settings
from .runtime import get_runtime
from . import offices

def _get_index_meta_path(office_id: str) -> str:
    """Restituisce il percorso del file metadati dell'indice per un ufficio."""
    return os.path.join(offices.get_office_index_dir(office_id), 'chunks.jsonl')

def _get_index_emb_path(office_id: str) -> str:
    """Restituisce il percorso del file embeddings dell'indice per un ufficio."""
    return os.path.join(offices.get_office_index_dir(office_id), 'embeddings.npy')

def _load_meta(office_id: str) -> List[Dict[str, Any]]:
    """Carica i metadati dell'indice per un ufficio."""
    path = _get_index_meta_path(office_id)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows

def _load_embeddings(office_id: str) -> np.ndarray:
    """Carica gli embeddings dell'indice per un ufficio."""
    path = _get_index_emb_path(office_id)
    if not os.path.exists(path):
        return np.zeros((0, 768), dtype=np.float32)
    return np.load(path)

def has_index(office_id: str) -> bool:
    """Verifica se un ufficio ha un indice."""
    meta_path = _get_index_meta_path(office_id)
    emb_path = _get_index_emb_path(office_id)
    return os.path.exists(meta_path) and os.path.exists(emb_path)

def list_docs(office_id: str) -> List[Dict[str, Any]]:
    """Restituisce la lista dei documenti indicizzati per un ufficio."""
    meta = _load_meta(office_id)
    by_doc = {}
    for row in meta:
        d = row['doc_path']
        by_doc.setdefault(d, {'doc_path': d, 'title': row.get('title', os.path.basename(d)), 'chunks': 0})
        by_doc[d]['chunks'] += 1
    return sorted(by_doc.values(), key=lambda x: x['title'].lower())

def _hash_embed(texts: List[str], dim: int = 768) -> np.ndarray:
    """Genera embeddings hash come fallback."""
    token_re = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+", re.UNICODE)
    vecs = np.zeros((len(texts), dim), dtype=np.float32)
    for i, t in enumerate(texts):
        counts = {}
        for w in token_re.findall(t.lower()):
            h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16) % dim
            counts[h] = counts.get(h, 0) + 1.0
        if counts:
            for k, v in counts.items():
                vecs[i, k] = v
            n = np.linalg.norm(vecs[i]) + 1e-9
            vecs[i] /= n
    return vecs

async def embed_texts(texts: List[str], model: str = None) -> np.ndarray:
    """Genera embeddings per i testi."""
    if model is None:
        model = settings.EMBEDDING_MODEL
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    try:
        vecs = []
        async with httpx.AsyncClient(timeout=120) as client:
            for t in texts:
                payload = {'model': model, 'input': t}
                r = await client.post(url, json=payload)
                r.raise_for_status()
                j = r.json()
                v = j.get('embedding') or j.get('data', [{}])[0].get('embedding')
                if v is None:
                    raise RuntimeError('Embedding response missing vector')
                import numpy as _np
                vecs.append(_np.array(v, dtype=_np.float32))
        import numpy as _np
        return _np.vstack(vecs)
    except Exception:
        return _hash_embed(texts)

async def retrieve(query: str, office_id: str, top_k: int = None, embed_model: str = None):
    """Recupera i documenti più rilevanti per una query da un ufficio specifico."""
    import numpy as _np
    if top_k is None:
        top_k = get_runtime().get('top_k', settings.TOP_K)
    
    meta = _load_meta(office_id)
    if not meta:
        return []
    
    E = _load_embeddings(office_id)
    qv = await embed_texts([query], model=embed_model)
    q = qv[0]
    
    def normalize(m):
        n = _np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
        return m / n
    
    En = normalize(E)
    qn = q / (_np.linalg.norm(q) + 1e-9)
    scores = En @ qn
    idxs = _np.argsort(scores)[::-1][:top_k]
    results = []
    for rank, i in enumerate(idxs):
        row = meta[int(i)]
        results.append({'rank': rank + 1, 'score': float(scores[i]), **row})
    return results

def wipe_index(office_id: str):
    """Cancella l'indice di un ufficio."""
    meta_path = _get_index_meta_path(office_id)
    emb_path = _get_index_emb_path(office_id)
    for p in [meta_path, emb_path]:
        if os.path.exists(p):
            os.remove(p)

def append_to_index(office_id: str, rows: List[Dict[str, Any]], embeddings: np.ndarray):
    """Aggiunge dati all'indice di un ufficio."""
    index_dir = offices.get_office_index_dir(office_id)
    os.makedirs(index_dir, exist_ok=True)
    
    meta_path = _get_index_meta_path(office_id)
    emb_path = _get_index_emb_path(office_id)
    
    with open(meta_path, 'a', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    
    import numpy as _np
    if os.path.exists(emb_path):
        E = _np.load(emb_path)
        if E.shape[1] != embeddings.shape[1]:
            _np.save(emb_path, embeddings.astype(_np.float32))
        else:
            E2 = _np.vstack([E, embeddings.astype(_np.float32)])
            _np.save(emb_path, E2)
    else:
        _np.save(emb_path, embeddings.astype(_np.float32))
