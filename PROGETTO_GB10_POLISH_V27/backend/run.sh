#!/bin/bash

# Script di avvio UNIVPM RAG con Gunicorn
# Uso: ./run.sh [dev|prod]

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Determina la modalità (dev o prod)
MODE="${1:-prod}"

# Verifica che Python sia disponibile
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Errore: Python 3 non trovato${NC}"
    exit 1
fi

# Verifica che pip sia disponibile
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Errore: pip3 non trovato${NC}"
    exit 1
fi

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  UNIVPM RAG - Backend Server${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"

# Installa le dipendenze
echo -e "${YELLOW}[1/3] Installazione dipendenze...${NC}"
pip3 install -q -r requirements.txt

# Crea le directory necessarie
echo -e "${YELLOW}[2/3] Preparazione directory...${NC}"
mkdir -p data/docs data/index data/config

# Avvia il server
echo -e "${YELLOW}[3/3] Avvio server...${NC}"
echo -e "${GREEN}Modalità: ${MODE}${NC}"

if [ "$MODE" = "dev" ]; then
    # Modalità sviluppo: uvicorn diretto con reload
    echo -e "${GREEN}Server in modalità SVILUPPO (con auto-reload)${NC}"
    python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
else
    # Modalità produzione: gunicorn con worker multipli
    echo -e "${GREEN}Server in modalità PRODUZIONE (Gunicorn multi-worker)${NC}"
    python3 -m gunicorn app:app --config gunicorn_conf.py
fi
