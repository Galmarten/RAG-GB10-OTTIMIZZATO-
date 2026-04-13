
// Gestione della sessione di autenticazione
class AuthSession {
  constructor() {
    this.storageKey = 'authSession';
  }

  // Salva la sessione di autenticazione
  save(username, office) {
    const session = {
      username,
      office,
      timestamp: Date.now()
    };
    sessionStorage.setItem(this.storageKey, JSON.stringify(session));
  }

  // Carica la sessione di autenticazione
  load() {
    const data = sessionStorage.getItem(this.storageKey);
    return data ? JSON.parse(data) : null;
  }

  // Verifica se l'utente è autenticato
  isAuthenticated() {
    return this.load() !== null;
  }

  // Ottiene l'ufficio corrente
  getCurrentOffice() {
    const session = this.load();
    return session ? session.office : null;
  }

  // Ottiene l'utente corrente
  getCurrentUser() {
    const session = this.load();
    return session ? session.username : null;
  }

  // Effettua il logout
  logout() {
    sessionStorage.removeItem(this.storageKey);
  }
}

const auth = new AuthSession();

// Carica gli uffici disponibili
async function loadOffices() {
  try {
    const response = await fetch('/api/uffici');
    if (!response.ok) {
      throw new Error('Errore nel caricamento degli uffici');
    }
    const data = await response.json();
    const offices = data.uffici || [];
    
    const officeSelect = document.getElementById('office');
    officeSelect.innerHTML = '';
    
    if (offices.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'Nessun ufficio disponibile';
      option.disabled = true;
      officeSelect.appendChild(option);
      return;
    }
    
    for (const office of offices) {
      const option = document.createElement('option');
      option.value = office.id;
      option.textContent = office.nome;
      officeSelect.appendChild(option);
    }
    
    // Seleziona il primo ufficio di default
    if (officeSelect.options.length > 0) {
      officeSelect.selectedIndex = 0;
    }
  } catch (error) {
    console.error('Errore nel caricamento degli uffici:', error);
    const officeSelect = document.getElementById('office');
    officeSelect.innerHTML = '<option value="">Errore nel caricamento degli uffici</option>';
  }
}

// Gestisce il submit del form di login
async function handleLogin(e) {
  e.preventDefault();
  
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  const office = document.getElementById('office').value;
  
  const errorMessage = document.getElementById('errorMessage');
  const loading = document.getElementById('loading');
  const loginButton = document.getElementById('loginButton');
  
  // Validazione di base
  if (!username) {
    errorMessage.textContent = 'Inserisci il nome utente';
    errorMessage.classList.add('show');
    return;
  }
  
  if (!password) {
    errorMessage.textContent = 'Inserisci la password';
    errorMessage.classList.add('show');
    return;
  }
  
  if (!office) {
    errorMessage.textContent = 'Seleziona un ufficio';
    errorMessage.classList.add('show');
    return;
  }
  
  errorMessage.classList.remove('show');
  loading.classList.add('show');
  loginButton.disabled = true;
  
  // Simula un delay di autenticazione (mock)
  setTimeout(() => {
    // Mock: accetta qualsiasi combinazione di username e password
    // In futuro, questo sarà sostituito da una vera autenticazione AD
    
    // Salva la sessione
    auth.save(username, office);
    
    // Reindirizza alla pagina di chat
    window.location.href = '/';
  }, 800);
}

// Controlla se l'utente è già autenticato
function checkAuthentication() {
  if (auth.isAuthenticated()) {
    // Se l'utente è già autenticato, reindirizza alla chat
    window.location.href = '/';
  }
}

// Inizializzazione
document.addEventListener('DOMContentLoaded', () => {
  checkAuthentication();
  loadOffices();
  
  const loginForm = document.getElementById('loginForm');
  loginForm.addEventListener('submit', handleLogin);
  
  // Permetti di premere Enter nel campo password
  document.getElementById('password').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      loginForm.dispatchEvent(new Event('submit'));
    }
  });
});
