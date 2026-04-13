
import os
from pydantic import BaseModel


def normalize_base(url: str) -> str:
    u = (url or "").strip()
    # Avoid using 0.0.0.0 as a client target; map to localhost
    if u.startswith("http://0.0.0.0"):
        u = u.replace("0.0.0.0", "127.0.0.1", 1)
    if u.startswith("0.0.0.0"):
        u = "http://127.0.0.1" + u[7:]
    if u and not u.startswith("http"):
        u = "http://" + u
    return u.rstrip("/")

class Settings(BaseModel):
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))
    OLLAMA_BASE_URL: str = normalize_base(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
    DEFAULT_LLM: str = os.getenv("DEFAULT_LLM", "phi3:latest")
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")))
    DOCS_DIR: str = os.path.join(DATA_DIR, "docs")
    INDEX_DIR: str = os.path.join(DATA_DIR, "index")
    CONFIG_DIR: str = os.path.join(DATA_DIR, "config")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    LEGACY_SELECTED_PATH: str = os.getenv("OLLAMA_SELECTED_FILE", os.path.expanduser("~/.ollama_selected_model"))
    
    def get_office_docs_dir(self, office_id: str) -> str:
        """Restituisce il percorso della directory documenti per un ufficio."""
        return os.path.join(self.DATA_DIR, "uffici", office_id, "docs")
    
    def get_office_index_dir(self, office_id: str) -> str:
        """Restituisce il percorso della directory indice per un ufficio."""
        return os.path.join(self.DATA_DIR, "uffici", office_id, "index")

settings = Settings()
os.makedirs(settings.CONFIG_DIR, exist_ok=True)

# Inizializza il modulo offices al caricamento di config
try:
    from . import offices
    offices.init_default_office()
except Exception:
    pass
