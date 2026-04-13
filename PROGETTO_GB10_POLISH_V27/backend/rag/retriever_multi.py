
import os, json, numpy as np, re, hashlib
from typing import List, Dict, Any, Tuple
import httpx
import asyncio
from .config import settings
from .runtime import get_runtime
from . import offices

# CACHE IN MEMORIA PER GLI INDICI (Caricati una sola volta)
_INDEX_CACHE: Dict[str, Tuple[List[Dict[str, Any]], np.ndarray]] = {}
_CACHE_LOCK = asyncio.Lock()

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
    """Genera embeddings con supporto robusto per /api/embed e /api/embeddings."""
    if not texts:
        return np.zeros((0, 768), dtype=np.float32)
    
    if model is None:
        model = settings.EMBEDDING_MODEL
    
    # Endpoint da provare in ordine
    endpoints = [
        f"{settings.OLLAMA_BASE_URL}/api/embed",
        f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    ]
    
    all_embeddings = []
    batch_size = 16 # Dimensione sicura per GB10
    
    async with httpx.AsyncClient(timeout=120.0, limits=httpx.Limits(max_connections=20)) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            success = False
            
            for url in endpoints:
                try:
                    # Prepariamo il payload in base all'endpoint
                    payload = {'model': model, 'input': batch if "embed" in url and not "embeddings" in url else batch[0]}
                    
                    # Se l'endpoint è /api/embeddings (vecchio), dobbiamo iterare il batch manualmente
                    if "embeddings" in url:
                        batch_vecs = []
                        for t in batch:
                            r = await client.post(url, json={'model': model, 'input': t})
                            if r.status_code == 200:
                                j = r.json()
                                v = j.get('embedding') or j.get('embeddings', [[]])[0]
                                batch_vecs.append(v)
                        if len(batch_vecs) == len(batch):
                            all_embeddings.extend(batch_vecs)
                            success = True
                            break
                    else:
                        # Nuovo endpoint /api/embed: invio batch diretto
                        r = await client.post(url, json={'model': model, 'input': batch})
                        if r.status_code == 200:
                            j = r.json()
                            # NOTA: Ollama restituisce 'embeddings' (plurale) per /api/embed
                            v = j.get('embeddings')
                            if v:
                                all_embeddings.extend(v)
                                success = True
                                break
                except Exception:
                    continue
            
            if not success:
                # Fallback estremo se entrambi gli endpoint falliscono per un batch
                print(f"FALLBACK HASH per batch {i}")
                all_embeddings.extend([_hash_embed([t])[0] for t in batch])
                
    return np.array(all_embeddings, dtype=np.float32)

def get_index_sync(office_id: str, force_reload: bool = False) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """Versione sincrona di get_index per compatibilità e caricamento iniziale."""
    global _INDEX_CACHE
    if force_reload or office_id not in _INDEX_CACHE:
        meta = _load_meta(office_id)
        if not meta:
            return [], np.zeros((0, 768), dtype=np.float32)
        
        E = _load_embeddings(office_id)
        if E.shape[0] > 0:
            if len(meta) != E.shape[0]:
                min_len = min(len(meta), E.shape[0])
                meta = meta[:min_len]
                E = E[:min_len]
            norm = np.linalg.norm(E, axis=1, keepdims=True) + 1e-9
            E = E / norm
        _INDEX_CACHE[office_id] = (meta, E)
    return _INDEX_CACHE.get(office_id, ([], np.zeros((0, 768), dtype=np.float32)))

async def get_index(office_id: str, force_reload: bool = False) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """Ottiene l'indice dalla RAM in modo thread-safe (async)."""
    global _INDEX_CACHE, _CACHE_LOCK
    async with _CACHE_LOCK:
        return get_index_sync(office_id, force_reload)

async def retrieve(query: str, office_id: str, top_k: int = None, embed_model: str = None) -> List[Dict[str, Any]]:
    """Retrieval ultra-veloce con cache in RAM e pre-normalizzazione."""
    if top_k is None:
        top_k = get_runtime().get('top_k', settings.TOP_K)
    
    # Se embed_model non è fornito, usa quello della selezione
    if not embed_model:
        from .selection import get_selection
        sel = get_selection()
        embed_model = sel.get("embedding", settings.EMBEDDING_MODEL)
    
    meta, E = await get_index(office_id)
    if not meta or E.shape[0] == 0:
        return []
    
    # Embedding della query
    qv = await embed_texts([query], model=embed_model)
    q = qv[0]
    
    # Normalizzazione query
    qn = q / (np.linalg.norm(q) + 1e-9)
    
    # Similarity (Prodotto scalare su vettori già normalizzati = Cosine Similarity)
    scores = E @ qn
    
    # Top-K
    top_k = min(top_k, len(scores))
    idxs = np.argpartition(scores, -top_k)[-top_k:]
    idxs = idxs[np.argsort(scores[idxs])[::-1]]
    
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
