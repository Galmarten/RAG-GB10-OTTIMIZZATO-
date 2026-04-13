# Guida di Integrazione - Sistema RAG Multi-Ufficio

## Panoramica

Il sistema RAG è stato esteso per supportare **molteplici uffici**, ciascuno con la propria knowledge base isolata. Questo documento spiega come integrare e utilizzare il nuovo sistema.

## Struttura del Progetto

```
univpm-rag/
├── backend/
│   ├── app.py                 (VECCHIA versione - single office)
│   ├── app_multi.py           (NUOVA versione - multi office)
│   ├── rag/
│   │   ├── config.py          (Aggiornato con supporto multi-ufficio)
│   │   ├── offices.py         (NUOVO - gestione CRUD uffici)
│   │   ├── retriever.py       (VECCHIA versione)
│   │   ├── retriever_multi.py (NUOVA versione)
│   │   ├── ingest.py          (VECCHIA versione)
│   │   ├── ingest_multi.py    (NUOVA versione)
│   │   └── ... (altri moduli)
│   └── requirements.txt
├── frontend/
│   └── static/
│       ├── index.html         (VECCHIA versione)
│       ├── index_multi.html   (NUOVA versione)
│       ├── admin.html         (VECCHIA versione)
│       ├── admin_multi.html   (NUOVA versione)
│       ├── js/
│       │   ├── chat.js        (VECCHIA versione)
│       │   ├── chat_multi.js  (NUOVA versione)
│       │   ├── admin.js       (VECCHIA versione)
│       │   └── admin_multi.js (NUOVA versione)
│       ├── css/
│       │   └── styles.css
│       └── img/
│           └── univpm-logo.svg
└── data/
    ├── config/
    │   ├── uffici.json        (NUOVO - configurazione uffici)
    │   ├── runtime.json
    │   └── selection.json
    └── uffici/                (NUOVO - directory per uffici)
        ├── default/
        │   ├── docs/
        │   └── index/
        ├── marketing/
        │   ├── docs/
        │   └── index/
        └── ... (altri uffici)
```

## Passaggi di Integrazione

### 1. Backup del Sistema Attuale

Prima di procedere, esegui un backup del sistema attuale:

```bash
cp backend/app.py backend/app.py.backup
cp frontend/static/index.html frontend/static/index.html.backup
cp frontend/static/admin.html frontend/static/admin.html.backup
cp frontend/static/js/chat.js frontend/static/js/chat.js.backup
cp frontend/static/js/admin.js frontend/static/js/admin.js.backup
```

### 2. Sostituisci i File Principali

Sostituisci i file principali con le versioni multi-ufficio:

```bash
# Backend
cp backend/app_multi.py backend/app.py

# Frontend
cp frontend/static/index_multi.html frontend/static/index.html
cp frontend/static/admin_multi.html frontend/static/admin.html
cp frontend/static/js/chat_multi.js frontend/static/js/chat.js
cp frontend/static/js/admin_multi.js frontend/static/js/admin.js
```

### 3. Verifica le Dipendenze

Assicurati che tutte le dipendenze siano installate:

```bash
pip install -r backend/requirements.txt
```

### 4. Avvia il Sistema

Avvia il sistema con gunicorn:

```bash
cd backend
gunicorn -c gunicorn_conf.py app:app
```

Oppure usa lo script di avvio:

```bash
cd backend
./run.sh
```

### 5. Accedi all'Interfaccia

- **Chat**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin

## Utilizzo del Sistema

### Per gli Utenti (Chat)

1. Accedi alla pagina di chat
2. Seleziona l'ufficio desiderato dal menu a tendina
3. Scrivi la tua domanda
4. Invia la domanda

Il sistema recupererà le informazioni dalla knowledge base dell'ufficio selezionato.

### Per gli Amministratori

#### Gestione Uffici

1. Accedi alla pagina di amministrazione
2. Nella sezione "Gestione Uffici", puoi:
   - **Creare un nuovo ufficio**: Clicca su "Crea nuovo ufficio", inserisci ID, nome e descrizione
   - **Modificare un ufficio**: Clicca su "Modifica" accanto all'ufficio desiderato
   - **Eliminare un ufficio**: Clicca su "Elimina" (attenzione: elimina anche tutti i dati)

#### Gestione Documenti per Ufficio

1. Seleziona l'ufficio desiderato dal menu a tendina "Seleziona ufficio"
2. Nella sezione "Documenti indicizzati", puoi visualizzare i documenti dell'ufficio
3. Nella sezione "Indicizza nuovi PDF", puoi caricare nuovi documenti per l'ufficio selezionato
4. Clicca su "Svuota indice" per cancellare tutti i documenti dell'ufficio

#### Gestione Modelli e Parametri

I modelli e i parametri di sistema sono globali (non specifici per ufficio):

- **Selezione modello LLM**: Seleziona il modello da usare per tutte le chat
- **Parametri di sistema**: Configura temperature, top-k, chunk size, etc.
- **System Prompt**: Personalizza il comportamento dell'assistente

## API REST

### Gestione Uffici

```http
GET /api/uffici
Restituisce la lista di tutti gli uffici

POST /api/uffici
Crea un nuovo ufficio
Body: {"id": "marketing", "nome": "Ufficio Marketing", "descrizione": "..."}

GET /api/uffici/{office_id}
Restituisce i dettagli di un ufficio

PUT /api/uffici/{office_id}
Aggiorna i dettagli di un ufficio
Body: {"nome": "Nuovo nome", "descrizione": "..."}

DELETE /api/uffici/{office_id}
Elimina un ufficio e tutti i suoi dati
```

### Gestione Documenti per Ufficio

```http
GET /api/uffici/{office_id}/docs
Restituisce la lista dei documenti dell'ufficio

POST /api/uffici/{office_id}/ingest
Indicizza nuovi documenti per l'ufficio
Body: FormData con file PDF

POST /api/uffici/{office_id}/wipe-index
Cancella l'indice dell'ufficio
```

### Chat per Ufficio

```http
POST /api/uffici/{office_id}/chat/stream
Chat streaming per un ufficio specifico
Body: FormData con prompt, temperature, top_k, etc.
Response: Server-Sent Events (SSE)
```

## Migrazione dei Dati Esistenti

Se hai dati già indicizzati nel sistema precedente, puoi migrarli al nuovo sistema:

1. I dati esistenti rimangono nella directory `data/docs` e `data/index`
2. Crea un ufficio "default" (fatto automaticamente al primo avvio)
3. Copia i file dall'indice precedente all'indice del nuovo ufficio:

```bash
cp data/docs/* data/uffici/default/docs/
cp data/index/* data/uffici/default/index/
```

## Configurazione Avanzata

### Variabili di Ambiente

Il sistema supporta le seguenti variabili di ambiente:

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

# Directory dati
DATA_DIR=/path/to/data
```

### Personalizzazione del System Prompt

Puoi personalizzare il comportamento dell'assistente modificando il system prompt nella pagina di amministrazione. Alcuni esempi:

**Per un assistente generico:**
```
Sei un assistente utile e amichevole. Rispondi alle domande in modo chiaro e conciso.
```

**Per un assistente specializzato:**
```
Sei un esperto di risorse umane. Rispondi alle domande relative alle politiche aziendali, 
ai contratti e alle procedure di gestione del personale. Basati solo sui documenti forniti.
```

## Troubleshooting

### Problema: "L'ufficio non esiste"

**Soluzione**: Assicurati che l'ufficio sia stato creato dalla pagina di amministrazione prima di provare a usarlo.

### Problema: I documenti non vengono trovati

**Soluzione**: 
1. Verifica che l'ufficio sia selezionato correttamente
2. Assicurati che i documenti siano stati indicizzati per quell'ufficio
3. Controlla i log per eventuali errori di indicizzazione

### Problema: La chat non risponde

**Soluzione**:
1. Verifica che Ollama sia in esecuzione
2. Controlla che il modello LLM sia selezionato e disponibile
3. Verifica la connessione a Ollama dalla pagina di amministrazione

### Problema: Errore durante l'indicizzazione

**Soluzione**:
1. Assicurati che il file PDF sia valido e contenga testo selezionabile
2. Verifica che lo spazio su disco sia sufficiente
3. Controlla i log del server per dettagli dell'errore

## Performance e Scalabilità

### Ottimizzazioni Consigliate

1. **Chunk Size**: Aumenta per documenti lunghi, diminuisci per documenti brevi
2. **Top-K**: Aumenta per risultati più completi, diminuisci per risposte più veloci
3. **Temperature**: Diminuisci per risposte più coerenti, aumenta per più creatività

### Limiti Noti

- Ogni ufficio ha il proprio indice vettoriale separato
- L'indicizzazione è sequenziale (non parallela)
- La ricerca è limitata a 50 risultati massimi

## Supporto e Contributi

Per segnalare bug o suggerire miglioramenti, contatta il team di sviluppo.

## Changelog

### Versione 2.0 (Multi-Ufficio)

- Aggiunto supporto per molteplici uffici
- Ogni ufficio ha la propria knowledge base isolata
- Interfaccia CRUD per la gestione degli uffici
- Selezione dell'ufficio nella pagina di chat
- Gestione documenti per-ufficio nella pagina di amministrazione

### Versione 1.0 (Single Office)

- Sistema RAG di base per un singolo ufficio
- Indicizzazione di documenti PDF
- Chat con retrieval augmented generation
- Interfaccia di amministrazione
