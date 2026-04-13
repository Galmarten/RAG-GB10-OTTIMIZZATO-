# UNIVPM RAG - Sistema Multi-Ufficio

## Descrizione

Questo è il sistema RAG (Retrieval Augmented Generation) esteso dell'Università Politecnica delle Marche, ora con supporto completo per **molteplici uffici**. Ogni ufficio ha la propria knowledge base isolata, permettendo una gestione centralizzata di diverse aree organizzative.

## Caratteristiche Principali

✅ **Multi-Ufficio**: Supporto per molteplici uffici con knowledge base separate  
✅ **CRUD Uffici**: Gestione completa (Create, Read, Update, Delete) degli uffici  
✅ **Chat Intelligente**: Chat con retrieval augmented generation per ogni ufficio  
✅ **Indicizzazione PDF**: Indicizzazione automatica di documenti PDF  
✅ **Modelli Offline**: Utilizzo di Ollama per esecuzione offline  
✅ **Interfaccia Web**: Interfaccia web moderna e intuitiva  
✅ **Admin Panel**: Pannello di amministrazione completo  

## Architettura

### Backend
- **FastAPI**: Framework web moderno e veloce
- **Ollama**: Esecuzione offline di modelli LLM e embedding
- **Numpy**: Operazioni vettoriali per il retrieval
- **PyMuPDF (fitz)**: Estrazione di testo da PDF

### Frontend
- **HTML5**: Markup semantico
- **CSS3**: Styling moderno e responsive
- **JavaScript Vanilla**: Nessuna dipendenza esterna

### Struttura Dati
```
data/
├── config/
│   ├── uffici.json        # Configurazione uffici
│   ├── runtime.json       # Parametri runtime
│   └── selection.json     # Selezione modelli
└── uffici/
    ├── default/
    │   ├── docs/          # Documenti PDF
    │   └── index/         # Indice vettoriale
    ├── marketing/
    │   ├── docs/
    │   └── index/
    └── ... (altri uffici)
```

## Installazione

### Prerequisiti

- Python 3.8+
- Ollama (per i modelli)
- pip (gestore pacchetti Python)

### Passi di Installazione

1. **Clona il repository**
```bash
cd univpm-rag
```

2. **Installa le dipendenze**
```bash
pip install -r backend/requirements.txt
```

3. **Avvia Ollama** (in un terminale separato)
```bash
ollama serve
```

4. **Avvia il server**
```bash
cd backend
gunicorn -c gunicorn_conf.py app:app
```

5. **Accedi all'interfaccia**
- Chat: http://localhost:8000/
- Admin: http://localhost:8000/admin

## Utilizzo

### Per gli Utenti

1. Vai a http://localhost:8000/
2. Seleziona l'ufficio desiderato
3. Scrivi la tua domanda
4. Leggi la risposta con le fonti citate

### Per gli Amministratori

1. Vai a http://localhost:8000/admin
2. **Gestione Uffici**: Crea, modifica o elimina uffici
3. **Selezione Ufficio**: Seleziona l'ufficio su cui lavorare
4. **Indicizzazione**: Carica PDF per l'ufficio selezionato
5. **Configurazione**: Personalizza i modelli e i parametri

## API REST

### Uffici
```
GET    /api/uffici                    # Lista uffici
POST   /api/uffici                    # Crea ufficio
GET    /api/uffici/{id}               # Dettagli ufficio
PUT    /api/uffici/{id}               # Aggiorna ufficio
DELETE /api/uffici/{id}               # Elimina ufficio
```

### Documenti
```
GET    /api/uffici/{id}/docs          # Lista documenti
POST   /api/uffici/{id}/ingest        # Indicizza documenti
POST   /api/uffici/{id}/wipe-index    # Cancella indice
```

### Chat
```
POST   /api/uffici/{id}/chat/stream   # Chat streaming
```

### Configurazione
```
GET    /api/config                    # Configurazione globale
GET    /api/runtime                   # Parametri runtime
POST   /api/runtime                   # Aggiorna parametri
GET    /api/models                    # Modelli disponibili
POST   /api/select-model              # Seleziona modello
```

## Configurazione

### Variabili di Ambiente

```bash
# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Modelli
DEFAULT_LLM=phi3:latest
EMBEDDING_MODEL=nomic-embed-text:latest

# Parametri RAG
TEMPERATURE=0.2
TOP_K=5
CHUNK_SIZE=1500
CHUNK_OVERLAP=200
```

### File di Configurazione

**`data/config/uffici.json`**
```json
[
  {
    "id": "default",
    "nome": "Ufficio Principale",
    "descrizione": "Ufficio principale dell'organizzazione"
  },
  {
    "id": "marketing",
    "nome": "Ufficio Marketing",
    "descrizione": "Documentazione relativa alle strategie di marketing"
  }
]
```

## Esempi di Utilizzo

### Creare un Nuovo Ufficio

```bash
curl -X POST http://localhost:8000/api/uffici \
  -H "Content-Type: application/json" \
  -d '{
    "id": "risorse_umane",
    "nome": "Ufficio Risorse Umane",
    "descrizione": "Regolamenti e procedure per il personale"
  }'
```

### Indicizzare Documenti

```bash
curl -X POST http://localhost:8000/api/uffici/risorse_umane/ingest \
  -F "uploaded=@documento.pdf"
```

### Fare una Domanda

```bash
curl -X POST http://localhost:8000/api/uffici/risorse_umane/chat/stream \
  -F "prompt=Quali sono le politiche di ferie?" \
  -F "temperature=0.2" \
  -F "top_k=5"
```

## Migrazione dal Sistema Single-Office

Se hai dati dal sistema precedente:

1. I dati rimangono in `data/docs` e `data/index`
2. Un ufficio "default" viene creato automaticamente
3. Copia i dati all'ufficio default:
```bash
cp data/docs/* data/uffici/default/docs/
cp data/index/* data/uffici/default/index/
```

## Performance

### Ottimizzazioni Consigliate

- **Chunk Size**: 1500 caratteri (default)
- **Chunk Overlap**: 200 caratteri (default)
- **Top-K**: 5 risultati (default)
- **Temperature**: 0.2 (default, risposte coerenti)

### Limiti

- Massimo 50 risultati per ricerca
- Massimo 200.000 caratteri per risposta
- Massimo 600 secondi per risposta

## Troubleshooting

### Errore: "Ollama non disponibile"
- Verifica che Ollama sia in esecuzione
- Controlla la configurazione di `OLLAMA_BASE_URL`

### Errore: "L'ufficio non esiste"
- Crea l'ufficio dalla pagina di amministrazione
- Verifica l'ID dell'ufficio

### Documenti non trovati
- Assicurati che i documenti siano stati indicizzati
- Verifica che l'ufficio sia selezionato correttamente

## Struttura del Codice

```
backend/
├── app.py                 # Applicazione FastAPI
├── rag/
│   ├── config.py         # Configurazione
│   ├── offices.py        # Gestione uffici
│   ├── retriever.py      # Retrieval vettoriale
│   ├── ingest.py         # Indicizzazione documenti
│   ├── runtime.py        # Parametri runtime
│   ├── selection.py      # Selezione modelli
│   └── utils.py          # Utilità
├── gunicorn_conf.py      # Configurazione Gunicorn
└── requirements.txt      # Dipendenze Python

frontend/
└── static/
    ├── index.html        # Pagina chat
    ├── admin.html        # Pagina admin
    ├── css/
    │   └── styles.css    # Stili
    ├── js/
    │   ├── chat.js       # Script chat
    │   └── admin.js      # Script admin
    └── img/
        └── univpm-logo.svg
```

## Contributi

Per segnalare bug o suggerire miglioramenti, contatta il team di sviluppo.

## Licenza

Questo progetto è proprietario dell'Università Politecnica delle Marche.

## Supporto

Per domande o problemi, consulta la [Guida di Integrazione](GUIDA_INTEGRAZIONE_MULTI_UFFICIO.md).
