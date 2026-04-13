# Guida all'Ottimizzazione Hardware per NVIDIA Grace Blackwell GB10

Il sistema è stato configurato per sfruttare la potenza della tua architettura **NVIDIA GB10**. Per ottenere le massime prestazioni (risposte istantanee), segui queste indicazioni:

## 1. Variabili d'Ambiente Ollama
Prima di avviare Ollama, imposta queste variabili per permettere il caricamento parallelo e l'uso massivo della VRAM:

```bash
# Permette a Ollama di gestire più richieste in parallelo (ideale per il ciclo di verifica)
export OLLAMA_NUM_PARALLEL=4

# Mantiene i modelli caricati in memoria per evitare ritardi di caricamento
export OLLAMA_MAX_LOADED_MODELS=2

# Assicura che Ollama ascolti su tutte le interfacce se necessario
export OLLAMA_HOST=0.0.0.0
```

## 2. Ottimizzazioni nel Codice (Già Applicate)
Ho aggiornato il backend (`app.py`) con i seguenti parametri ottimizzati:

- **num_thread: 16**: Sfrutta i core della CPU Grace per il pre-processing dei prompt.
- **num_ctx: 8192**: Espande la finestra di contesto per gestire documenti complessi senza perdita di precisione.
- **httpx.Limits**: Aumentato il limite di connessioni simultanee tra il backend Python e Ollama per evitare colli di bottiglia nel passaggio dei dati.
- **num_gpu: 1**: Forza l'offload completo sulla Blackwell.

## 3. Suggerimento Modelli
Per la tua configurazione, consiglio l'uso di modelli che supportano bene il parallelismo:
- **Llama 3 (8B o 70B)**: Estremamente veloce sulla GB10.
- **Mistral / Mixtral**: Ottimi per il ragionamento RAG.

Con queste impostazioni, il "Failed to fetch" e la lentezza dovrebbero sparire, lasciando spazio a una generazione fluida e immediata.
