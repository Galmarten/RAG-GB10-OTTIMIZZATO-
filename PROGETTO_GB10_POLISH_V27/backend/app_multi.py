
import os, json, time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Request, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx

from rag.config import settings
from rag.retriever_multi import list_docs, retrieve, wipe_index, has_index
from rag.ingest_multi import ingest_files
from rag.runtime import get_runtime, update_runtime
from rag.selection import list_models, get_selection, set_selection, validate_model_quick, warmup_model, ps_models, stop_model
from rag.greeting_handler import should_skip_retrieval
from rag import offices

app = FastAPI(title="UNIVPM RAG Offline - Multi Ufficio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "static"))
if os.path.exists(STATIC_ROOT):
    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

@app.get("/health")
@app.get("/api/health")
async def health():
    ok_ollama = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ok_ollama = r.status_code == 200
    except Exception:
        ok_ollama = False
    
    # Controlla se almeno un ufficio ha un indice
    office_list = offices.list_offices()
    has_any_index = any(has_index(o["id"]) for o in office_list)
    
    return {"status": "ok", "ollama": ok_ollama, "has_index": has_any_index}

@app.get("/api/config")
async def get_config():
    sel = get_selection()
    rt = get_runtime()
    return {"DEFAULT_LLM": sel.get("llm", settings.DEFAULT_LLM), "EMBEDDING_MODEL": sel.get("embedding", settings.EMBEDDING_MODEL), "TOP_K": rt.get('top_k', settings.TOP_K), "TEMPERATURE": rt.get('temperature', settings.TEMPERATURE), "CHUNK_SIZE": rt.get('chunk_size', settings.CHUNK_SIZE), "CHUNK_OVERLAP": rt.get('chunk_overlap', settings.CHUNK_OVERLAP)}

# ============================================================================
# API PER LA GESTIONE UFFICI (CRUD)
# ============================================================================

@app.get("/api/uffici")
async def list_uffici():
    """Restituisce la lista di tutti gli uffici."""
    try:
        return {"uffici": offices.list_offices()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/uffici")
async def create_ufficio(payload: dict = Body(...)):
    """Crea un nuovo ufficio."""
    try:
        office_id = payload.get("id", "").strip()
        nome = payload.get("nome", "").strip()
        descrizione = payload.get("descrizione", "").strip()
        
        if not office_id or not nome:
            return JSONResponse({"error": "ID e nome sono obbligatori"}, status_code=400)
        
        # Valida l'ID dell'ufficio (solo caratteri alphanumerici e underscore)
        if not all(c.isalnum() or c == '_' for c in office_id):
            return JSONResponse({"error": "L'ID dell'ufficio può contenere solo lettere, numeri e underscore"}, status_code=400)
        
        office = offices.create_office(office_id, nome, descrizione)
        return {"ok": True, "office": office}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/uffici/{office_id}")
async def get_ufficio(office_id: str):
    """Restituisce i dettagli di un ufficio."""
    try:
        office = offices.get_office(office_id)
        if not office:
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        return {"office": office}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.put("/api/uffici/{office_id}")
async def update_ufficio(office_id: str, payload: dict = Body(...)):
    """Aggiorna i dettagli di un ufficio."""
    try:
        nome = payload.get("nome")
        descrizione = payload.get("descrizione")
        
        office = offices.update_office(office_id, nome=nome, descrizione=descrizione)
        return {"ok": True, "office": office}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/uffici/{office_id}")
async def delete_ufficio(office_id: str):
    """Elimina un ufficio e tutti i suoi dati."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        
        offices.delete_office(office_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# API PER LA GESTIONE MODELLI
# ============================================================================

@app.get("/api/models")
async def models():
    try:
        return {"models": list_models()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/selection")
async def read_selection():
    return get_selection()

@app.get("/api/ps")
async def api_ps():
    return {"running": ps_models()}

@app.post("/api/stop")
async def api_stop(payload: dict = Body(...)):
    name = payload.get("name", "")
    ok = stop_model(name)
    return {"ok": ok, "name": name}

@app.post("/api/select-model")
async def select_model(payload: dict = Body(...)):
    llm = payload.get("llm")
    embedding = payload.get("embedding")
    validate = payload.get("validate", True)
    previous = get_selection()
    prev_llm = previous.get("llm")

    if validate and llm:
        if not validate_model_quick(llm):
            return JSONResponse({"ok": False, "error": f"Il modello LLM '{llm}' non risponde (generate)."}, status_code=400)

    if llm and prev_llm and llm != prev_llm:
        stop_model(prev_llm)

    sel = set_selection(llm=llm, embedding=embedding)

    if llm:
        warmup_model(llm)

    return {"ok": True, "selection": sel}

# ============================================================================
# API PER LA GESTIONE DOCUMENTI (PER UFFICIO)
# ============================================================================

@app.get("/api/uffici/{office_id}/docs")
async def docs_list(office_id: str):
    """Restituisce la lista dei documenti di un ufficio."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        return {"docs": list_docs(office_id)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/uffici/{office_id}/ingest")
async def ingest(office_id: str, uploaded: List[UploadFile] = File(...), embed_model: Optional[str] = Form(None)):
    """Indicizza nuovi documenti per un ufficio."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        
        saved_paths = []
        docs_dir = offices.get_office_docs_dir(office_id)
        os.makedirs(docs_dir, exist_ok=True)
        
        for up in uploaded:
            dest = os.path.join(docs_dir, up.filename)
            with open(dest, "wb") as f:
                f.write(await up.read())
            saved_paths.append(dest)
        
        result = await ingest_files(office_id, saved_paths, embed_model=embed_model)
        return {"ok": True, **result}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/uffici/{office_id}/wipe-index")
async def wipe(office_id: str):
    """Cancella l'indice di un ufficio."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        wipe_index(office_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# API PER IL CHAT (PER UFFICIO)
# ============================================================================

def _get_stream_limits():
    rt = get_runtime()
    max_chars = rt.get('max_reply_chars', 50000)
    max_secs = rt.get('max_reply_seconds', 300)
    max_chars = max(200, min(max_chars, 200_000))
    max_secs = max(5, min(max_secs, 600))
    return max_chars, max_secs

def _sources_note(contexts, office_id: str = None):
    if not contexts:
        return ""
    import urllib.parse
    seen = set()
    lines = []
    for c in contexts:
        title = c.get("title", "Documento")
        page_num = c.get("page_number")
        doc_path = c.get("doc_path", "")
        key = (title, page_num)
        if key in seen:
            continue
        seen.add(key)
        
        # Estrai il nome del file dal percorso
        doc_filename = os.path.basename(doc_path) if doc_path else ""
        
        # Crea il link se abbiamo il nome del file e l'office_id
        if doc_filename and office_id:
            encoded_filename = urllib.parse.quote(doc_filename)
            link = f"[{title}](/api/uffici/{office_id}/docs/download/{encoded_filename})"
        else:
            link = title
        
        if page_num is None:
            lines.append(f"• {link}")
        else:
            lines.append(f"• {link} — pagina {page_num}")
    if not lines:
        return ""
    return "\n\n📎 Fonti:\n" + "\n".join(lines)

@app.post("/api/uffici/{office_id}/chat/stream")
async def chat_stream(office_id: str, request: Request):
    """Chat streaming per un ufficio specifico."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        
        form = await request.form()
        prompt = form.get("prompt", "")
        model = form.get("model")
        embed_model = form.get("embed_model")
        rt_defaults = get_runtime()
        temperature = float(form.get("temperature", str(rt_defaults.get('temperature', 0.2))))
        top_k = int(form.get("top_k", str(rt_defaults.get('top_k', 5))))

        sel = get_selection()
        if not model:
            model = sel.get("llm", settings.DEFAULT_LLM)
        if not embed_model:
            embed_model = sel.get("embedding", settings.EMBEDDING_MODEL)

        skip_retrieval, greeting_response = should_skip_retrieval(prompt)
        
        if skip_retrieval:
            # Per i saluti, non usare il system prompt di RAG, rispondi direttamente
            contexts = []
            context_text = ""
            # System prompt minimalista per i saluti
            system_greeting = "Sei un assistente amichevole. Rispondi in modo breve e naturale."
            messages = [
                {"role": "system", "content": system_greeting},
                {"role": "user", "content": greeting_response}
            ]
        else:
            contexts = await retrieve(prompt, office_id, top_k=top_k, embed_model=embed_model)
            context_text = "\n\n".join([f"[{c['title']} — pagina {c.get('page_number', c.get('chunk_index', '?'))}] {c['text']}" for c in contexts])

            system = rt_defaults.get('system_prompt', "Sei un assistente per l'Università Politecnica delle Marche (UNIVPM). Rispondi SEMPRE in italiano. Basati ESCLUSIVAMENTE sui regolamenti interni e i documenti indicizzati forniti. Cita sempre la fonte (titolo e numero pagina). Se la risposta non si trova nei documenti, dillo chiaramente e non inventare informazioni. Tono professionale, conciso e amichevole. Rispondi solo a domande pertinenti sui regolamenti, procedure e documentazione aziendale. IMPORTANTE: Non fornire mai informazioni generiche o non richieste. Rispondi solo a ciò che viene chiesto.")

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Contesto dai documenti:\n{context_text}\n\nDomanda: {prompt}"}
            ]

        MAX_REPLY_CHARS, MAX_REPLY_SECONDS = _get_stream_limits()

        async def generator():
            nonlocal MAX_REPLY_CHARS, MAX_REPLY_SECONDS
            start_time = time.monotonic()
            total_chars = 0
            url = f"{settings.OLLAMA_BASE_URL}/api/chat"
            payload = {"model": model, "messages": messages, "stream": True, "options": {"temperature": temperature}}
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", url, json=payload) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if await request.is_disconnected():
                                break
                            if not line:
                                continue
                            if line.startswith("data: "):
                                line = line[6:]
                            try:
                                j = json.loads(line)
                            except Exception:
                                continue
                            if j.get("done"):
                                note = _sources_note(contexts, office_id)
                                if note:
                                    yield f"data: {json.dumps({'delta': note}, ensure_ascii=False)}\n\n"
                                yield "event: done\ndata: {}\n\n"
                                return
                            delta = ""
                            if "message" in j and "content" in j["message"]:
                                delta = j["message"]['content']
                            elif "response" in j:
                                delta = j["response"]
                            if delta:
                                total_chars += len(delta)
                                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
                                if total_chars >= MAX_REPLY_CHARS or (time.monotonic() - start_time) >= MAX_REPLY_SECONDS:
                                    note = _sources_note(contexts, office_id)
                                    if note:
                                        yield f"data: {json.dumps({'delta': note}, ensure_ascii=False)}\n\n"
                                    notice = "\n\n[⛔ Risposta troncata automaticamente: limite superato]"
                                    yield f"data: {json.dumps({'delta': notice}, ensure_ascii=False)}\n\n"
                                    yield "event: done\ndata: {}\n\n"
                                    return
            except Exception as e:
                url = f"{settings.OLLAMA_BASE_URL}/api/generate"
                prompt_full = f"{system}\n\nContesto dai documenti:\n{context_text}\n\nDomanda: {prompt}\nRisposta:"
                payload = {"model": model, "prompt": prompt_full, "stream": True, "options": {"temperature": temperature}}
                try:
                    async with httpx.AsyncClient(timeout=None) as client:
                        async with client.stream("POST", url, json=payload) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if await request.is_disconnected():
                                    break
                                if not line:
                                    continue
                                if line.startswith("data: "):
                                    line = line[6:]
                                try:
                                    j = json.loads(line)
                                except Exception:
                                    continue
                                if j.get("done"):
                                    note = _sources_note(contexts, office_id)
                                    if note:
                                        yield f"data: {json.dumps({'delta': note}, ensure_ascii=False)}\n\n"
                                    yield "event: done\ndata: {}\n\n"
                                    return
                                if "response" in j:
                                    chunk = j['response']
                                    total_chars += len(chunk)
                                    yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
                                    if total_chars >= MAX_REPLY_CHARS or (time.monotonic() - start_time) >= MAX_REPLY_SECONDS:
                                        note = _sources_note(contexts, office_id)
                                        if note:
                                            yield f"data: {json.dumps({'delta': note}, ensure_ascii=False)}\n\n"
                                        notice = "\n\n[⛔ Risposta troncata automaticamente: limite superato]"
                                        yield f"data: {json.dumps({'delta': notice}, ensure_ascii=False)}\n\n"
                                        yield "event: done\ndata: {}\n\n"
                                        return
                except Exception as e2:
                    yield f"event: error\ndata: {json.dumps({'error': f'chat failed: {str(e)}; generate failed: {str(e2)}'})}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# API PER I PARAMETRI DI SISTEMA
# ============================================================================

@app.get("/api/runtime")
async def api_runtime_get():
    return get_runtime()

@app.post("/api/runtime")
async def api_runtime_post(payload: dict = Body(...)):
    # Validate bounds
    allowed = {"temperature", "top_k", "chunk_size", "chunk_overlap", "max_reply_chars", "max_reply_seconds", "system_prompt"}
    updates = {}
    for k, v in (payload or {}).items():
        if k not in allowed:
            continue
        if k == "system_prompt":
            if not isinstance(v, str) or len(v) < 10:
                return JSONResponse({"ok": False, "error": "system_prompt deve essere una stringa di almeno 10 caratteri"}, status_code=400)
            if len(v) > 5000:
                return JSONResponse({"ok": False, "error": "system_prompt non deve superare 5000 caratteri"}, status_code=400)
            updates[k] = v
        elif k == "temperature":
            try:
                v = float(v)
                if not (0 <= v <= 2):
                    return JSONResponse({"ok": False, "error": "temperature deve essere tra 0 e 2"}, status_code=400)
                updates[k] = v
            except Exception:
                return JSONResponse({"ok": False, "error": "temperature deve essere un numero"}, status_code=400)
        elif k in ("top_k", "chunk_size", "chunk_overlap", "max_reply_chars", "max_reply_seconds"):
            try:
                v = int(v)
                if k == "top_k" and not (1 <= v <= 50):
                    return JSONResponse({"ok": False, "error": "top_k deve essere tra 1 e 50"}, status_code=400)
                if k == "chunk_size" and not (200 <= v <= 8000):
                    return JSONResponse({"ok": False, "error": "chunk_size deve essere tra 200 e 8000"}, status_code=400)
                if k == "chunk_overlap" and not (0 <= v <= 2000):
                    return JSONResponse({"ok": False, "error": "chunk_overlap deve essere tra 0 e 2000"}, status_code=400)
                if k == "max_reply_chars" and not (200 <= v <= 200000):
                    return JSONResponse({"ok": False, "error": "max_reply_chars deve essere tra 200 e 200000"}, status_code=400)
                if k == "max_reply_seconds" and not (5 <= v <= 600):
                    return JSONResponse({"ok": False, "error": "max_reply_seconds deve essere tra 5 e 600"}, status_code=400)
                updates[k] = v
            except Exception:
                return JSONResponse({"ok": False, "error": f"{k} deve essere un numero"}, status_code=400)

    rt = update_runtime(updates)
    return {"ok": True, "runtime": rt}

# ============================================================================
# DOWNLOAD DOCUMENTI
# ============================================================================

@app.get("/api/uffici/{office_id}/docs/download/{doc_filename}")
async def download_document(office_id: str, doc_filename: str):
    """Scarica un documento PDF da un ufficio specifico."""
    try:
        if not offices.office_exists(office_id):
            return JSONResponse({"error": f"L'ufficio '{office_id}' non esiste"}, status_code=404)
        
        # Valida il nome del file per evitare path traversal
        if ".." in doc_filename or "/" in doc_filename or "\\" in doc_filename:
            return JSONResponse({"error": "Nome file non valido"}, status_code=400)
        
        doc_path = os.path.join(offices.get_office_docs_dir(office_id), doc_filename)
        
        # Verifica che il file esista e sia all'interno della directory dell'ufficio
        if not os.path.exists(doc_path) or not os.path.isfile(doc_path):
            return JSONResponse({"error": "Documento non trovato"}, status_code=404)
        
        # Verifica che il file sia effettivamente dentro la directory dell'ufficio
        real_doc_path = os.path.realpath(doc_path)
        real_office_dir = os.path.realpath(offices.get_office_docs_dir(office_id))
        if not real_doc_path.startswith(real_office_dir):
            return JSONResponse({"error": "Accesso negato"}, status_code=403)
        
        return FileResponse(doc_path, media_type="application/pdf", filename=doc_filename)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# PAGINE STATICHE
# ============================================================================

@app.get("/login")
async def page_login():
    return FileResponse(os.path.join(STATIC_ROOT, "login.html"))

@app.get("/")
async def page_index():
    return FileResponse(os.path.join(STATIC_ROOT, "index.html"))

@app.get("/admin")
async def page_admin():
    return FileResponse(os.path.join(STATIC_ROOT, "admin.html"))
