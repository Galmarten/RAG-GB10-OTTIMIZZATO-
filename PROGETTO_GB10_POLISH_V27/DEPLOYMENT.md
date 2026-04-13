# UNIVPM RAG - Guida al Deployment

## Panoramica

Questo documento descrive come distribuire UNIVPM RAG in un ambiente multi-utente utilizzando **Gunicorn** come application server.

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (Browser)                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Reverse Proxy (Nginx/Apache)                   │
│                  (Opzionale ma consigliato)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Gunicorn Server                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Worker 1   │  │   Worker 2   │  │   Worker N   │      │
│  │  (Uvicorn)   │  │  (Uvicorn)   │  │  (Uvicorn)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        ▲                   ▲                   ▲             │
│        └───────────────────┴───────────────────┘             │
│              FastAPI Application                            │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │ Ollama │      │ Indice │      │ Config │
    │  LLM   │      │ Vector │      │ Runtime│
    └────────┘      └────────┘      └────────┘
```

## Avvio Rapido

### Linux/Unix

```bash
cd backend
./run.sh prod
```

Oppure in modalità sviluppo:
```bash
./run.sh dev
```

### Windows

```cmd
cd backend
start.bat prod
```

Oppure in modalità sviluppo:
```cmd
start.bat dev
```

## Configurazione Gunicorn

### Variabili d'Ambiente

Puoi personalizzare il comportamento di Gunicorn tramite variabili d'ambiente:

```bash
# Numero di worker (default: numero di CPU, min 2, max 8)
export GUNICORN_WORKERS=4

# Binding (default: 0.0.0.0:8000)
export GUNICORN_BIND=0.0.0.0:8000

# Timeout in secondi (default: 600)
export GUNICORN_TIMEOUT=600

# Keepalive in secondi (default: 5)
export GUNICORN_KEEPALIVE=5

# Max richieste per worker prima di restart (default: 1000)
export GUNICORN_MAX_REQUESTS=1000

# Livello di log (default: info)
export GUNICORN_LOGLEVEL=info
```

### Esempio di Avvio con Configurazione Personalizzata

```bash
export GUNICORN_WORKERS=8
export GUNICORN_TIMEOUT=300
./run.sh prod
```

## Deployment con Nginx (Consigliato)

### 1. Installa Nginx

```bash
sudo apt-get install nginx
```

### 2. Configura Nginx come Reverse Proxy

Crea il file `/etc/nginx/sites-available/univpm-rag`:

```nginx
upstream univpm_rag {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://univpm_rag;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Per streaming responses
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /static/ {
        alias /path/to/univpm-rag/frontend/static/;
        expires 1d;
    }
}
```

### 3. Abilita la Configurazione

```bash
sudo ln -s /etc/nginx/sites-available/univpm-rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Deployment con Systemd (Linux)

### 1. Crea il File di Servizio

Crea `/etc/systemd/system/univpm-rag.service`:

```ini
[Unit]
Description=UNIVPM RAG Backend
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/univpm-rag/backend
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m gunicorn app:app --config gunicorn_conf.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Abilita e Avvia il Servizio

```bash
sudo systemctl daemon-reload
sudo systemctl enable univpm-rag
sudo systemctl start univpm-rag
sudo systemctl status univpm-rag
```

### 3. Visualizza i Log

```bash
sudo journalctl -u univpm-rag -f
```

## Monitoraggio

### Verificare i Worker Attivi

```bash
ps aux | grep gunicorn
```

### Controllare l'Utilizzo di Risorse

```bash
top -p $(pgrep -f gunicorn | tr '\n' ',' | sed 's/,$//')
```

### Log di Accesso

I log di accesso sono disponibili in stdout (reindirizzati da systemd o supervisord).

## Scaling Orizzontale

Per distribuire il carico su più server:

1. **Usa un Load Balancer** (es. HAProxy, AWS ELB)
2. **Condividi l'Indice Vector**: Salva l'indice su storage condiviso (NFS, S3)
3. **Condividi la Configurazione**: Usa un database per i parametri di runtime

## Troubleshooting

### Errore: "Address already in use"

```bash
# Libera la porta 8000
sudo lsof -ti:8000 | xargs kill -9
```

### Errore: "Worker timeout"

Aumenta il timeout:
```bash
export GUNICORN_TIMEOUT=900
./run.sh prod
```

### Errore: "Too many open files"

Aumenta il limite di file aperti:
```bash
ulimit -n 65536
./run.sh prod
```

## Performance Tips

1. **Aumenta i Worker**: Se hai CPU disponibili, aumenta `GUNICORN_WORKERS`
2. **Usa un Reverse Proxy**: Nginx è molto più efficiente di Gunicorn nel servire file statici
3. **Abilita Caching**: Configura Nginx per cachare le risorse statiche
4. **Monitora la Memoria**: Usa `GUNICORN_MAX_REQUESTS` per prevenire memory leak
5. **Usa HTTPS**: Configura SSL/TLS per la sicurezza

## Versione

- **Gunicorn**: 23.0.0
- **Uvicorn Worker**: Incluso in uvicorn[standard]
- **FastAPI**: 0.115.0
- **Python**: 3.8+

## Supporto

Per problemi o domande, consulta la documentazione ufficiale:
- [Gunicorn Docs](https://docs.gunicorn.org/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Docs](https://www.uvicorn.org/)
