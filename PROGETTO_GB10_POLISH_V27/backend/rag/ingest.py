
import os
from typing import List, Dict, Any
import fitz
from .utils import clean_text, chunk_text
from .config import settings
from .runtime import get_runtime
from .retriever_multi import append_to_index, embed_texts
from . import offices

def extract_text_from_pdf(path: str) -> List[Dict[str, Any]]:
    """Estrae testo e numeri di pagina dal PDF."""
    doc = fitz.open(path)
    pages_data = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text('text')
        if text.strip():
            pages_data.append({'page_number': page_num, 'text': text})
    return pages_data

async def ingest_files(office_id: str, paths: List[str], title_overrides: Dict[str, str] = None, embed_model: str = None) -> Dict[str, Any]:
    """Indicizza i file per un ufficio specifico."""
    # Verifica che l'ufficio esista
    if not offices.office_exists(office_id):
        raise ValueError(f"L'ufficio '{office_id}' non esiste.")
    
    title_overrides = title_overrides or {}
    all_rows, all_chunks = [], []
    
    for p in paths:
        title = title_overrides.get(p) or os.path.basename(p)
        pages_data = extract_text_from_pdf(p)
        
        if not pages_data:
            continue
        
        rt = get_runtime()
        cs = int(rt.get('chunk_size', settings.CHUNK_SIZE))
        co = int(rt.get('chunk_overlap', settings.CHUNK_OVERLAP))
        
        # Processa ogni pagina
        for page_info in pages_data:
            page_num = page_info['page_number']
            page_text = clean_text(page_info['text'])
            
            # Chunka il testo della pagina
            for chunk_idx, chunk in enumerate(chunk_text(page_text, cs, co)):
                row = {
                    'doc_path': os.path.abspath(p),
                    'title': title,
                    'page_number': page_num,
                    'chunk_index': chunk_idx,
                    'text': chunk
                }
                all_rows.append(row)
                all_chunks.append(chunk)
    
    if not all_rows:
        return {'added_chunks': 0, 'added_docs': 0}
    
    embs = await embed_texts(all_chunks, model=embed_model)
    append_to_index(office_id, all_rows, embs)
    return {'added_chunks': len(all_rows), 'added_docs': len(paths)}
