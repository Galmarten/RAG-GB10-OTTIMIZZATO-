
const DEFAULT_SYSTEM_PROMPT = "Sei un assistente per l'Università Politecnica delle Marche (UNIVPM). Rispondi in italiano e basati solo sui regolamenti interni e i documenti indicizzati. Cita la fonte (titolo e numero chunk). Se non trovi la risposta nei documenti, dillo chiaramente. Tono professionale e conciso.";

let CURRENT_OFFICE = null;
let OFFICES = [];

// ============================================================================
// GESTIONE UFFICI (CRUD)
// ============================================================================

async function loadOffices() {
  try {
    const r = await fetch('/api/uffici');
    if (!r.ok) return;
    const data = await r.json();
    OFFICES = data.uffici || [];
    updateOfficeSelector();
    
    // Carica l'ufficio salvato in localStorage
    const savedOffice = localStorage.getItem('selectedAdminOffice');
    if (savedOffice && OFFICES.find(o => o.id === savedOffice)) {
      CURRENT_OFFICE = savedOffice;
    } else if (OFFICES.length > 0) {
      CURRENT_OFFICE = OFFICES[0].id;
    }
    
    if (CURRENT_OFFICE) {
      document.getElementById('adminOfficeSelector').value = CURRENT_OFFICE;
      localStorage.setItem('selectedAdminOffice', CURRENT_OFFICE);
    }
    
    refreshOfficesList();
  } catch (e) {
    console.error('Errore nel caricamento degli uffici:', e);
  }
}

function updateOfficeSelector() {
  const selector = document.getElementById('adminOfficeSelector');
  selector.innerHTML = '';
  
  for (const office of OFFICES) {
    const option = document.createElement('option');
    option.value = office.id;
    option.textContent = office.nome;
    selector.appendChild(option);
  }
}

function refreshOfficesList() {
  const list = document.getElementById('officesList');
  list.innerHTML = '';
  
  for (const office of OFFICES) {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <div style="flex:1;">
        <strong>${office.nome}</strong>
        <div class="muted" style="font-size:0.9em;">${office.descrizione}</div>
        <code style="font-size:0.85em;">ID: ${office.id}</code>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn-outline" onclick="editOffice('${office.id}')">Modifica</button>
        <button class="btn-danger" onclick="deleteOffice('${office.id}')">Elimina</button>
      </div>
    `;
    list.appendChild(row);
  }
}

function showCreateOfficeForm() {
  const modal = document.getElementById('officeModal');
  document.getElementById('officeModalTitle').textContent = 'Crea nuovo ufficio';
  document.getElementById('officeId').value = '';
  document.getElementById('officeName').value = '';
  document.getElementById('officeDescription').value = '';
  document.getElementById('officeId').disabled = false;
  modal.style.display = 'block';
}

function editOffice(officeId) {
  const office = OFFICES.find(o => o.id === officeId);
  if (!office) return;
  
  const modal = document.getElementById('officeModal');
  document.getElementById('officeModalTitle').textContent = 'Modifica ufficio';
  document.getElementById('officeId').value = office.id;
  document.getElementById('officeName').value = office.nome;
  document.getElementById('officeDescription').value = office.descrizione || '';
  document.getElementById('officeId').disabled = true;
  modal.style.display = 'block';
}

function closeOfficeModal() {
  document.getElementById('officeModal').style.display = 'none';
}

async function saveOffice() {
  const officeId = document.getElementById('officeId').value.trim();
  const nome = document.getElementById('officeName').value.trim();
  const descrizione = document.getElementById('officeDescription').value.trim();
  const msg = document.getElementById('officeMsg');
  
  if (!officeId || !nome) {
    msg.textContent = 'Errore: ID e nome sono obbligatori';
    return;
  }
  
  const isNew = !OFFICES.find(o => o.id === officeId);
  
  try {
    let res;
    if (isNew) {
      res = await fetch('/api/uffici', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: officeId, nome, descrizione })
      });
    } else {
      res = await fetch(`/api/uffici/${officeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, descrizione })
      });
    }
    
    if (!res.ok) {
      const data = await res.json();
      msg.textContent = 'Errore: ' + (data.error || res.statusText);
      return;
    }
    
    msg.textContent = isNew ? 'Ufficio creato ✔︎' : 'Ufficio aggiornato ✔︎';
    await loadOffices();
    closeOfficeModal();
  } catch (e) {
    msg.textContent = 'Errore: ' + e.message;
  }
}

async function deleteOffice(officeId) {
  if (!confirm(`Sei sicuro di voler eliminare l'ufficio "${officeId}"? Tutti i dati e documenti saranno persi.`)) return;
  
  try {
    const res = await fetch(`/api/uffici/${officeId}`, { method: 'DELETE' });
    if (!res.ok) {
      alert('Errore nell\'eliminazione dell\'ufficio');
      return;
    }
    await loadOffices();
  } catch (e) {
    alert('Errore: ' + e.message);
  }
}

// ============================================================================
// GESTIONE PARAMETRI RUNTIME
// ============================================================================

async function loadRuntime() {
  try {
    const r = await fetch('/api/runtime');
    if (!r.ok) return;
    const j = await r.json();
    document.getElementById('rt_temperature').value = j.temperature ?? 0.2;
    document.getElementById('rt_topk').value = j.top_k ?? 5;
    document.getElementById('rt_chunksize').value = j.chunk_size ?? 1500;
    document.getElementById('rt_overlap').value = j.chunk_overlap ?? 200;
    document.getElementById('rt_maxchars').value = j.max_reply_chars ?? 50000;
    document.getElementById('rt_maxsecs').value = j.max_reply_seconds ?? 300;
    document.getElementById('rt_systemprompt').value = j.system_prompt ?? DEFAULT_SYSTEM_PROMPT;
  } catch { }
}

async function saveRuntime() {
  const msg = document.getElementById('rt_msg');
  const payload = {
    temperature: parseFloat(document.getElementById('rt_temperature').value),
    top_k: parseInt(document.getElementById('rt_topk').value, 10),
    chunk_size: parseInt(document.getElementById('rt_chunksize').value, 10),
    chunk_overlap: parseInt(document.getElementById('rt_overlap').value, 10),
  };
  const res = await fetch('/api/runtime', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) { const txt = await res.text(); msg.textContent = 'Errore: ' + txt; return; }
  const j = await res.json();
  msg.textContent = 'Salvato ✔︎';
  loadConfigInfo();
}

async function saveResponseRuntime() {
  const msg = document.getElementById('rt_response_msg');
  const payload = {
    max_reply_chars: parseInt(document.getElementById('rt_maxchars').value, 10),
    max_reply_seconds: parseInt(document.getElementById('rt_maxsecs').value, 10),
  };
  const res = await fetch('/api/runtime', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) { const txt = await res.text(); msg.textContent = 'Errore: ' + txt; return; }
  const j = await res.json();
  msg.textContent = 'Parametri risposta salvati ✔︎';
}

async function saveSystemPrompt() {
  const msg = document.getElementById('rt_systemprompt_msg');
  const prompt = document.getElementById('rt_systemprompt').value.trim();
  if (prompt.length < 10) {
    msg.textContent = 'Errore: il prompt deve avere almeno 10 caratteri';
    return;
  }
  if (prompt.length > 5000) {
    msg.textContent = 'Errore: il prompt non deve superare 5000 caratteri';
    return;
  }
  const payload = { system_prompt: prompt };
  const res = await fetch('/api/runtime', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) { const txt = await res.text(); msg.textContent = 'Errore: ' + txt; return; }
  const j = await res.json();
  msg.textContent = 'System Prompt salvato ✔︎';
}

async function resetSystemPrompt() {
  if (!confirm('Sei sicuro di voler ripristinare il prompt di default?')) return;
  const payload = { system_prompt: DEFAULT_SYSTEM_PROMPT };
  const res = await fetch('/api/runtime', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) {
    document.getElementById('rt_systemprompt_msg').textContent = 'Errore nel ripristino';
    return;
  }
  document.getElementById('rt_systemprompt').value = DEFAULT_SYSTEM_PROMPT;
  document.getElementById('rt_systemprompt_msg').textContent = 'Prompt ripristinato al default ✔︎';
}

async function loadConfigInfo() {
  try {
    const r = await fetch('/api/config');
    if (!r.ok) return;
    const j = await r.json();
    const box = document.getElementById('configInfo');
    box.innerHTML = `
      <span class="badge">LLM selezionato: <strong>${j.DEFAULT_LLM}</strong></span>
      <span class="badge">Embedding: <strong>${j.EMBEDDING_MODEL}</strong></span>
      <span class="badge">Temperature chat: <strong>${j.TEMPERATURE}</strong></span>
      <span class="badge">Top-K retrieval: <strong>${j.TOP_K}</strong></span>
    `;
  } catch { }
}

// ============================================================================
// GESTIONE MODELLI
// ============================================================================

function radioRow(name, selected) {
  const row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = `<label style="display:flex;gap:10px;align-items:center;">
    <input type="radio" name="modelRadio" value="${name}" ${selected ? 'checked' : ''}>
    <code style="font-weight:600">${name}</code>
  </label>`;
  return row;
}

function radioRowEmbed(name, selected) {
  const row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = `<label style="display:flex;gap:10px;align-items:center;">
    <input type="radio" name="embedRadio" value="${name}" ${selected ? 'checked' : ''}>
    <code>${name}</code>
  </label>`;
  return row;
}

async function loadSelection() {
  const r = await fetch('/api/selection');
  if (!r.ok) return {};
  return await r.json();
}

async function loadModels() {
  const listLLM = document.getElementById('llmList');
  const listEMB = document.getElementById('embedList');
  const sel = await loadSelection();
  listLLM.innerHTML = '';
  listEMB.innerHTML = '';
  const res = await fetch('/api/models');
  const j = await res.json();
  const models = j.models || [];
  for (const m of models) {
    const name = m.name || m.model || m;
    listLLM.appendChild(radioRow(name, sel.llm === name));
    if (name.toLowerCase().includes('embed') || name.toLowerCase().includes('nomic') || name.toLowerCase().includes('snowflake')) {
      listEMB.appendChild(radioRowEmbed(name, sel.embedding === name));
    }
  }
  if (listEMB.children.length === 0 && sel.embedding) {
    listEMB.appendChild(radioRowEmbed(sel.embedding, true));
  }
}

async function saveSelection(validate = true) {
  const llm = (document.querySelector('input[name="modelRadio"]:checked') || {}).value;
  const emb = (document.querySelector('input[name="embedRadio"]:checked') || {}).value;
  const payload = { llm, embedding: emb, validate };
  const res = await fetch('/api/select-model', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const j = await res.json();
  const box = document.getElementById('selectionStatus');
  if (res.ok && j.ok) {
    box.textContent = `Selezione salvata e avviata: LLM=${j.selection.llm} • EMB=${j.selection.embedding}`;
  } else {
    box.textContent = 'Errore: ' + (j.error || res.statusText);
  }
}

async function refreshPS() {
  const res = await fetch('/api/ps');
  const j = await res.json();
  const box = document.getElementById('psBox');
  box.textContent = 'Processi attivi: ' + (j.running || []).join(', ');
}

async function stopSelected() {
  const llm = (document.querySelector('input[name="modelRadio"]:checked') || {}).value;
  if (!llm) {
    document.getElementById('selectionStatus').textContent = 'Seleziona prima un LLM.';
    return;
  }
  const res = await fetch('/api/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: llm }) });
  const j = await res.json();
  document.getElementById('selectionStatus').textContent = j.ok ? `Arrestato: ${llm}` : `Impossibile arrestare: ${llm}`;
  refreshPS();
}

// ============================================================================
// GESTIONE DOCUMENTI (PER UFFICIO)
// ============================================================================

async function refreshDocs() {
  if (!CURRENT_OFFICE) return;
  
  const res = await fetch(`/api/uffici/${CURRENT_OFFICE}/docs`);
  if (!res.ok) return;
  
  const j = await res.json();
  const list = document.getElementById('docsList');
  list.innerHTML = '';
  
  for (const d of j.docs) {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<strong>${d.title}</strong><span class="badge">${d.chunks} chunks</span><code style="flex:1;overflow:hidden;text-overflow:ellipsis">${d.doc_path}</code>`;
    list.appendChild(row);
  }
}

async function wipeOfficeIndex() {
  if (!CURRENT_OFFICE) {
    alert('Seleziona un ufficio prima');
    return;
  }
  if (!confirm('Sicuro di voler svuotare completamente l\'indice di questo ufficio?')) return;
  
  const res = await fetch(`/api/uffici/${CURRENT_OFFICE}/wipe-index`, { method: 'POST' });
  if (res.ok) {
    document.getElementById('docsList').innerHTML = '';
  }
}

// ============================================================================
// INIZIALIZZAZIONE
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Event listeners per la gestione uffici
  document.getElementById('createOfficeBtn').addEventListener('click', showCreateOfficeForm);
  document.getElementById('saveOfficeBtn').addEventListener('click', saveOffice);
  document.getElementById('closeOfficeModalBtn').addEventListener('click', closeOfficeModal);
  
  // Event listener per il cambio di ufficio
  document.getElementById('adminOfficeSelector').addEventListener('change', (e) => {
    CURRENT_OFFICE = e.target.value;
    localStorage.setItem('selectedAdminOffice', CURRENT_OFFICE);
    refreshDocs();
  });
  
  // Event listeners per i modelli
  document.getElementById('refreshModels').addEventListener('click', loadModels);
  document.getElementById('refreshPS').addEventListener('click', refreshPS);
  document.getElementById('stopPrev').addEventListener('click', stopSelected);
  document.getElementById('saveSelection').addEventListener('click', () => saveSelection(true));
  document.getElementById('testSelection').addEventListener('click', () => saveSelection(true));
  
  // Event listeners per i documenti
  document.getElementById('refreshDocs').addEventListener('click', refreshDocs);
  document.getElementById('wipeIndex').addEventListener('click', wipeOfficeIndex);
  
  document.getElementById('ingestForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!CURRENT_OFFICE) {
      document.getElementById('ingestMsg').textContent = 'Errore: seleziona un ufficio';
      return;
    }
    
    const files = document.getElementById('pdfs').files;
    if (!files.length) return;
    
    const fd = new FormData();
    for (const f of files) {
      fd.append('uploaded', f);
    }
    
    const res = await fetch(`/api/uffici/${CURRENT_OFFICE}/ingest`, { method: 'POST', body: fd });
    if (!res.ok) {
      const txt = await res.text();
      document.getElementById('ingestMsg').textContent = 'Errore: ' + txt;
      return;
    }
    
    const j = await res.json();
    document.getElementById('ingestMsg').textContent = JSON.stringify(j);
    await refreshDocs();
  });
  
  // Event listeners per i parametri
  document.getElementById('rt_save').addEventListener('click', saveRuntime);
  document.getElementById('rt_response_save').addEventListener('click', saveResponseRuntime);
  document.getElementById('rt_systemprompt_save').addEventListener('click', saveSystemPrompt);
  document.getElementById('rt_systemprompt_reset').addEventListener('click', resetSystemPrompt);
  
  // Caricamento iniziale
  loadOffices();
  loadModels();
  refreshPS();
  loadConfigInfo();
  loadRuntime();
});
