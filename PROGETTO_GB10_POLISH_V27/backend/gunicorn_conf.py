"""
Configurazione Gunicorn per UNIVPM RAG
Ottimizzato per ambienti multi-utente e uffici
"""

import os
import multiprocessing

# Binding
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Worker configuration
# Usa il numero di CPU disponibili, con minimo 2 e massimo 8
cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", max(2, min(cpu_count, 8))))

# Worker class: uvicorn per supportare FastAPI async
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout (in secondi) - aumentato per supportare richieste lunghe
timeout = int(os.getenv("GUNICORN_TIMEOUT", "600"))

# Keepalive (in secondi)
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Max requests per worker prima di restart (prevenire memory leak)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Logging
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# Process naming
proc_name = "univpm-rag"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (opzionale)
keyfile = os.getenv("GUNICORN_KEYFILE", None)
certfile = os.getenv("GUNICORN_CERTFILE", None)

# Server hooks
def on_starting(server):
    """Eseguito quando il server sta per avviarsi"""
    print(f"[UNIVPM RAG] Avvio server Gunicorn con {workers} worker(s)")
    print(f"[UNIVPM RAG] Binding: {bind}")
    print(f"[UNIVPM RAG] Timeout: {timeout}s")

def on_exit(server):
    """Eseguito quando il server sta per terminare"""
    print("[UNIVPM RAG] Server Gunicorn in arresto")

def when_ready(server):
    """Eseguito quando il server è pronto ad accettare richieste"""
    print("[UNIVPM RAG] Server Gunicorn pronto per ricevere richieste")
