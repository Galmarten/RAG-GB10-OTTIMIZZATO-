
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
      
      // Carica l'ufficio salvato in localStorage
      const savedOffice = localStorage.getItem('selectedOffice');
      if (savedOffice && OFFICES.find(o => o.id === savedOffice)) {
        CURRENT_OFFICE = savedOffice;
      } else if (OFFICES.length > 0) {
        CURRENT_OFFICE = OFFICES[0].id;
      }
      
      if (CURRENT_OFFICE) {
        document.getElementById('officeSelector').value = CURRENT_OFFICE;
        localStorage.setItem('selectedOffice', CURRENT_OFFICE);
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

function addMsg(role, text) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user' : 'assistant');
  const pre = document.createElement('pre');
  pre.textContent = text;
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
  await loadDefaults();
  await loadOffices();
  
  // Event listener per il cambio di ufficio
  document.getElementById('officeSelector').addEventListener('change', (e) => {
    CURRENT_OFFICE = e.target.value;
    localStorage.setItem('selectedOffice', CURRENT_OFFICE);
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
      stream.pump(
        delta => { out.textContent += delta; },
        () => { }
      );
    } catch (error) {
      out.textContent += `\n[ERRORE] ${error.message}`;
    }
    
    form.reset();
    document.getElementById('prompt').focus();
  });
});
