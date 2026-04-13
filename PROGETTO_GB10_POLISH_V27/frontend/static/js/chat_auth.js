
// Gestione della sessione di autenticazione
class AuthSession {
  constructor() {
    this.storageKey = 'authSession';
  }

  load() {
    const data = sessionStorage.getItem(this.storageKey);
    return data ? JSON.parse(data) : null;
  }

  isAuthenticated() {
    return this.load() !== null;
  }

  getCurrentOffice() {
    const session = this.load();
    return session ? session.office : null;
  }

  getCurrentUser() {
    const session = this.load();
    return session ? session.username : null;
  }

  logout() {
    sessionStorage.removeItem(this.storageKey);
    window.location.href = '/login';
  }
}

const auth = new AuthSession();

// Verifica l'autenticazione
function checkAuthentication() {
  if (!auth.isAuthenticated()) {
    window.location.href = '/login';
  }
}

let DEFAULTS = { TOP_K: 5, TEMPERATURE: 0.2 };
let CURRENT_OFFICE = null;
let OFFICES = [];

async function loadDefaults() {
  try {
    const r = await fetch('/api/config');
    if (r.ok) { DEFAULTS = await r.json(); }
  } catch { }
}

async function loadOffices() {
  try {
    const r = await fetch('/api/uffici');
    if (r.ok) {
      const data = await r.json();
      OFFICES = data.uffici || [];
      updateOfficeSelector();
      
      // Carica l'ufficio dalla sessione di autenticazione
      CURRENT_OFFICE = auth.getCurrentOffice();
      
      if (CURRENT_OFFICE) {
        document.getElementById('officeSelector').value = CURRENT_OFFICE;
      }
    }
  } catch (e) {
    console.error('Errore nel caricamento degli uffici:', e);
  }
}

function updateOfficeSelector() {
  const selector = document.getElementById('officeSelector');
  selector.innerHTML = '';
  
  for (const office of OFFICES) {
    const option = document.createElement('option');
    option.value = office.id;
    option.textContent = office.nome;
    selector.appendChild(option);
  }
}

function renderMarkdownWithLinks(text) {
  // Escapa l'HTML per evitare XSS
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#039;');
  
  // Renderizza i link markdown [testo](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
    // Valida l'URL per evitare javascript: e altri protocolli pericolosi
    if (url.startsWith('/') || url.startsWith('http://') || url.startsWith('https://')) {
      return `<a href="${url}" target="_blank" style="text-decoration: underline; color: #0066cc; cursor: pointer;">${text}</a>`;
    }
    return match;
  });
  
  return html;
}

function addMsg(role, text) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user' : 'assistant');
  const pre = document.createElement('pre');
  
  // Se è un messaggio dell'assistente, renderizza il markdown
  if (role === 'assistant') {
    pre.innerHTML = renderMarkdownWithLinks(text);
    pre.style.whiteSpace = 'pre-wrap';
    pre.style.wordWrap = 'break-word';
  } else {
    pre.textContent = text;
  }
  
  div.appendChild(pre);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return pre;
}

async function streamChat(fd, officeId) {
  const url = `/api/uffici/${officeId}/chat/stream`;
  const resp = await fetch(url, { method: 'POST', body: fd });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  return {
    async pump(onData, onDone) {
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          let event = 'message', data = '';
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (event === 'message') {
            try {
              const j = JSON.parse(data);
              if (j.delta) onData(j.delta);
            } catch { }
          } else if (event === 'done') {
            onDone && onDone();
            return;
          } else if (event === 'error') {
            onData("\n[ERRORE] " + data);
          }
        }
      }
      onDone && onDone();
    }
  };
}

document.addEventListener('DOMContentLoaded', async () => {
  // Verifica l'autenticazione
  checkAuthentication();
  
  // Mostra le informazioni dell'utente
  const username = auth.getCurrentUser();
  const officeId = auth.getCurrentOffice();
  if (username) {
    document.getElementById('userInfo').textContent = `Utente: ${username}`;
  }
  
  await loadDefaults();
  await loadOffices();
  
  // Event listener per il cambio di ufficio
  document.getElementById('officeSelector').addEventListener('change', (e) => {
    // Reindirizza al login quando si cambia ufficio
    auth.logout();
  });
  
  // Event listener per il logout
  document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm('Sei sicuro di voler effettuare il logout?')) {
      auth.logout();
    }
  });
  
  const form = document.getElementById('chatForm');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!CURRENT_OFFICE) {
      addMsg('assistant', 'Errore: nessun ufficio selezionato.');
      return;
    }
    
    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) return;
    
    addMsg('user', prompt);
    const out = addMsg('assistant', '');
    
    const fd = new FormData();
    fd.append('prompt', prompt);
    fd.append('top_k', String(DEFAULTS.TOP_K ?? 5));
    fd.append('temperature', String(DEFAULTS.TEMPERATURE ?? 0.2));
    
    try {
      const stream = await streamChat(fd, CURRENT_OFFICE);
      let fullText = "";
      let lastRender = 0;
      const RENDER_INTERVAL = 16; // 60fps circa per massima fluidità

      stream.pump(
        delta => { 
          fullText += delta;
          const now = Date.now();
          // Renderizza se è passato l'intervallo o se ci sono caratteri di interruzione
          if (now - lastRender > RENDER_INTERVAL || delta.includes('\n')) {
            // Usa requestAnimationFrame per non bloccare il thread UI durante il render
            requestAnimationFrame(() => {
              out.innerHTML = renderMarkdownWithLinks(fullText);
            });
            lastRender = now;
          }
        },
        () => { 
          // Render finale per assicurarsi che tutto sia visualizzato
          out.innerHTML = renderMarkdownWithLinks(fullText);
        }
      );
    } catch (error) {
      out.textContent += `\n[ERRORE] ${error.message}`;
    }
    
    form.reset();
    document.getElementById('prompt').focus();
  });
});
