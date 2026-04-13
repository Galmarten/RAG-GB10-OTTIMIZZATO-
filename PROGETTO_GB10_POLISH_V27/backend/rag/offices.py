
import os
import json
import shutil
from typing import List, Dict, Any, Optional
from .config import settings

OFFICES_CONFIG_PATH = os.path.join(settings.CONFIG_DIR, "uffici.json")
OFFICES_DATA_DIR = os.path.join(settings.DATA_DIR, "uffici")

def _ensure_offices_dir():
    """Assicura che la directory uffici esista."""
    os.makedirs(OFFICES_DATA_DIR, exist_ok=True)
    os.makedirs(settings.CONFIG_DIR, exist_ok=True)

def _load_offices() -> List[Dict[str, Any]]:
    """Carica la lista degli uffici dal file di configurazione."""
    if not os.path.exists(OFFICES_CONFIG_PATH):
        return []
    try:
        with open(OFFICES_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def _save_offices(offices: List[Dict[str, Any]]):
    """Salva la lista degli uffici nel file di configurazione."""
    _ensure_offices_dir()
    with open(OFFICES_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(offices, f, ensure_ascii=False, indent=2)

def get_office_data_dir(office_id: str) -> str:
    """Restituisce il percorso della directory dati per un ufficio."""
    return os.path.join(OFFICES_DATA_DIR, office_id)

def get_office_docs_dir(office_id: str) -> str:
    """Restituisce il percorso della directory documenti per un ufficio."""
    return os.path.join(get_office_data_dir(office_id), "docs")

def get_office_index_dir(office_id: str) -> str:
    """Restituisce il percorso della directory indice per un ufficio."""
    return os.path.join(get_office_data_dir(office_id), "index")

def list_offices() -> List[Dict[str, Any]]:
    """Restituisce la lista di tutti gli uffici."""
    return _load_offices()

def get_office(office_id: str) -> Optional[Dict[str, Any]]:
    """Restituisce i dettagli di un ufficio specifico."""
    offices = _load_offices()
    for office in offices:
        if office.get("id") == office_id:
            return office
    return None

def office_exists(office_id: str) -> bool:
    """Verifica se un ufficio esiste."""
    return get_office(office_id) is not None

def create_office(office_id: str, nome: str, descrizione: str = "") -> Dict[str, Any]:
    """Crea un nuovo ufficio."""
    if office_exists(office_id):
        raise ValueError(f"L'ufficio '{office_id}' esiste già.")
    
    # Crea la struttura di directory
    office_dir = get_office_data_dir(office_id)
    docs_dir = get_office_docs_dir(office_id)
    index_dir = get_office_index_dir(office_id)
    
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(index_dir, exist_ok=True)
    
    # Aggiungi l'ufficio alla lista
    offices = _load_offices()
    new_office = {
        "id": office_id,
        "nome": nome,
        "descrizione": descrizione
    }
    offices.append(new_office)
    _save_offices(offices)
    
    return new_office

def update_office(office_id: str, nome: Optional[str] = None, descrizione: Optional[str] = None) -> Dict[str, Any]:
    """Aggiorna i dettagli di un ufficio."""
    offices = _load_offices()
    for office in offices:
        if office.get("id") == office_id:
            if nome is not None:
                office["nome"] = nome
            if descrizione is not None:
                office["descrizione"] = descrizione
            _save_offices(offices)
            return office
    
    raise ValueError(f"L'ufficio '{office_id}' non esiste.")

def delete_office(office_id: str):
    """Elimina un ufficio e tutti i suoi dati."""
    offices = _load_offices()
    offices = [o for o in offices if o.get("id") != office_id]
    _save_offices(offices)
    
    # Elimina la directory dell'ufficio
    office_dir = get_office_data_dir(office_id)
    if os.path.exists(office_dir):
        shutil.rmtree(office_dir)

def init_default_office():
    """Inizializza un ufficio di default se non esiste nessun ufficio."""
    if not list_offices():
        create_office("default", "Ufficio Principale", "Ufficio principale dell'organizzazione")
