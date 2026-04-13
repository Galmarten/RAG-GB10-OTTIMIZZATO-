"""
Modulo per la gestione intelligente dei saluti e delle query brevi.
Evita di fare retrieval su input non pertinenti come "Ciao", "Grazie", ecc.
Le risposte ai saluti sono minimaliste e non forniscono informazioni specifiche.
"""

import re
from typing import Tuple

# Saluti comuni in italiano e inglese
GREETINGS = {
    'ciao', 'hello', 'hi', 'buongiorno', 'buonasera', 'buonanotte',
    'arrivederci', 'goodbye', 'bye', 'arrivederla', 'salve', 'ehi',
    'ok', 'okay', 'va bene', 'grazie', 'thanks', 'prego', 'di nulla',
    'perfetto', 'bene', 'male', 'così così', 'ehm', 'mmmh',
    'si', 'sì', 'no', 'nope', 'yep', 'yeah', 'nah',
    'cosa', 'come', 'quando', 'dove', 'perché', 'chi', 'quale',
    'aiuto', 'help', 'scusa', 'sorry', 'permesso', 'excuse me',
    'come stai', 'how are you', 'come va', 'tutto bene', 'all good'
}

# Pattern per rilevare query non pertinenti
NON_PERTINENT_PATTERNS = [
    r'^[a-z\s\?\!\.]+$',  # Solo lettere, spazi e punteggiatura
    r'^(ciao|hello|hi|buongiorno|buonasera|grazie|thanks|ok|okay|si|sì|no)[\s\?\!\.]*$',
    r'^(come|cosa|quando|dove|perché|chi|quale)\s*[\?\!\.]*$',
    r'^come\s+(stai|va|vai)[\s\?\!\.]*$',
    r'^(tutto\s+)?(bene|male|così\s+così)[\s\?\!\.]*$',
]

def is_greeting_or_small_talk(prompt: str) -> bool:
    """
    Verifica se il prompt è un saluto o una conversazione banale.
    
    Args:
        prompt: Il testo inserito dall'utente
        
    Returns:
        True se è un saluto/small talk, False altrimenti
    """
    if not prompt or len(prompt.strip()) == 0:
        return True
    
    # Normalizza il prompt
    normalized = prompt.strip().lower()
    
    # Se è molto corto (meno di 3 caratteri), è probabilmente un saluto
    if len(normalized) < 3:
        return True
    
    # Se è una parola singola e è un saluto noto
    if ' ' not in normalized and normalized in GREETINGS:
        return True
    
    # Controlla i pattern non pertinenti
    for pattern in NON_PERTINENT_PATTERNS:
        if re.match(pattern, normalized):
            # Verifica se contiene almeno una parola di saluto
            words = normalized.split()
            if any(word.rstrip('?!.') in GREETINGS for word in words):
                return True
    
    return False

def is_question_about_documents(prompt: str) -> bool:
    """
    Verifica se il prompt è una domanda che richiede il retrieval dai documenti.
    
    Args:
        prompt: Il testo inserito dall'utente
        
    Returns:
        True se è una domanda pertinente, False altrimenti
    """
    if is_greeting_or_small_talk(prompt):
        return False
    
    # Controlla se contiene parole chiave di domande
    question_keywords = [
        'quale', 'quali', 'cosa', 'come', 'quando', 'dove', 'perché', 'chi',
        'quanti', 'quanto', 'qual è', 'quali sono', 'cos è', 'come si',
        'quando si', 'dove si', 'chi è', 'chi sono',
        'regolamento', 'norma', 'regola', 'procedura', 'processo',
        'documento', 'policy', 'politica', 'linea guida', 'guida',
        'requisito', 'condizione', 'criterio', 'limite', 'scadenza',
        'diritto', 'dovere', 'obbligo', 'permesso', 'vietato',
        'informazione', 'dato', 'dettaglio', 'spiegazione', 'chiarimento'
    ]
    
    normalized = prompt.lower()
    for keyword in question_keywords:
        if keyword in normalized:
            return True
    
    # Se è lungo e non è un saluto, probabilmente è una domanda
    if len(prompt.strip()) > 10:
        return True
    
    return False

def get_greeting_response(prompt: str) -> str:
    """
    Restituisce una risposta minimalista e appropriata per i saluti.
    Le risposte sono brevi e non forniscono informazioni specifiche.
    
    Args:
        prompt: Il testo inserito dall'utente
        
    Returns:
        Una risposta di saluto appropriata e minimalista
    """
    normalized = prompt.strip().lower()
    
    # Risposte minimaliste per saluti comuni
    # Tutte le risposte sono brevi e non forniscono informazioni specifiche
    greeting_responses = {
        'ciao': 'Ciao! 👋',
        'hello': 'Hello! 👋',
        'hi': 'Hi! 👋',
        'buongiorno': 'Buongiorno! ☀️',
        'buonasera': 'Buonasera! 🌙',
        'buonanotte': 'Buonanotte! 😴',
        'grazie': 'Prego! 😊',
        'thanks': 'You\'re welcome! 😊',
        'ok': 'Va bene!',
        'okay': 'Okay!',
        'si': 'Sì! ✓',
        'sì': 'Sì! ✓',
        'no': 'No. ✗',
        'bene': 'Bene! 😊',
        'male': 'Mi dispiace. 😞',
        'così così': 'Capisco. 😐',
        'arrivederci': 'Arrivederci! 👋',
        'goodbye': 'Goodbye! 👋',
        'bye': 'Bye! 👋',
    }
    
    # Cerca una corrispondenza esatta
    if normalized in greeting_responses:
        return greeting_responses[normalized]
    
    # Cerca una corrispondenza parziale
    for greeting, response in greeting_responses.items():
        if greeting in normalized:
            return response
    
    # Risposta generica minimalista
    return 'Ciao! 👋'

def should_skip_retrieval(prompt: str) -> Tuple[bool, str]:
    """
    Determina se il retrieval dovrebbe essere saltato e fornisce una risposta alternativa.
    
    Args:
        prompt: Il testo inserito dall'utente
        
    Returns:
        Una tupla (skip_retrieval, response_message)
        - skip_retrieval: True se il retrieval dovrebbe essere saltato
        - response_message: La risposta da fornire (vuota se retrieval non deve essere saltato)
    """
    if is_greeting_or_small_talk(prompt):
        response = get_greeting_response(prompt)
        return True, response
    
    return False, ""
