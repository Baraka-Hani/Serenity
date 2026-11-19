/* Account feature: independent of the landing page and video studio. */
(() => {
  const $ = selector => document.querySelector(selector);
  let mode = 'signin';
  let passwordMax = 128;
  let pendingGoogleCredential = null;
  let googleReady = false;

  async function request(path, options = {}) {
    if (location.protocol === 'file:') throw new Error('Accounts need the Serenity server. Start it, then open http://127.0.0.1:8765/auth.html instead of this file.');
    let response;
    try { response = await fetch(path, { credentials: 'same-origin', ...options }); }
    catch (_) { throw new Error('Cannot reach the Serenity server. Run python3 backend/server.py, then open http://127.0.0.1:8765/auth.html.'); }
    if (!response.headers.get('Content-Type')?.includes('application/json')) {
      throw new Error('This page is not being served by the Serenity backend. Open http://127.0.0.1:8765/auth.html.');
    }
    const data = await response.json();
    if (!response.ok) throw Object.assign(new Error(data.error || 'Request failed.'), { status: response.status, data });
    return data;
  }

  function message(text, kind = 'info') {
    const status = $('#status');
    status.textContent = text;
    status.className = `status show ${kind}`;
  }

  function setMode(next) {
    mode = next;
    const signup = mode === 'signup';
    $('#signinTab').classList.toggle('active', !signup);
    $('#signupTab').classList.toggle('active', signup);
    $('#nameField').classList.toggle('hidden', !signup);
    $('#authTitle').textContent = signup ? 'Create your account.' : 'Welcome back.';
    $('#authSubtitle').textContent = signup ? 'Start sharing the places you love.' : 'Your next trip starts with a story.';
    $('#submitButton').textContent = signup ? 'Create account' : 'Sign in with email';
    $('#password').autocomplete = signup ? 'new-password' : 'current-password';
    $('#password').minLength = signup ? 8 : 0;
    $('#password').maxLength = passwordMax;
    $('#password').type = 'password';
    $('#passwordToggle').textContent = 'Show';
    $('#passwordToggle').setAttribute('aria-label', 'Show password');
    $('#passwordToggle').setAttribute('aria-pressed', 'false');
    $('#status').className = 'status';
    renderGoogleButton();
  }

  // Send people back to the page they were on, so sign-in works from anywhere in the app.
  function safeReturnPath(value) {
    if (!value) return null;
    try {
      const url = new URL(value, location.origin);
      if (url.origin !== location.origin || /\/auth\.html$/.test(url.pathname) || url.pathname.startsWith('/api/')) return null;
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_) { return null; }
  }

  function showUser(user) {
    $('#accountName').textContent = `Welcome, ${user.name}`;
    $('#accountEmail').textContent = user.email;
    $('#avatar').textContent = user.name.charAt(0).toUpperCase();
    const next = new URLSearchParams(location.search);
    if (next.get('next') === 'messages') {
      const conversation = new URLSearchParams();
      const peer = next.get('to');
      const post = next.get('post');
      if (/^[0-9a-f]{16}$/.test(peer || '')) conversation.set('to', peer);
      if (/^[0-9a-f]{32}$/.test(post || '')) conversation.set('post', post);
      location.replace(`search.html${conversation.size ? `?${conversation}` : ''}`);
      return;
    }
    const named = { studio: 'studio.html', account: 'account.html', clips: 'account.html#published-trips', map: 'map.html', home: 'home.html', feed: 'app.html' }[next.get('next')];
    const destination = named || safeReturnPath(next.get('next')) || safeReturnPath(document.referrer);
    if (destination) { location.replace(destination); return; }
    location.replace('account.html');
  }

  function showAuth() {
    $('#authPanel').classList.remove('hidden');
    $('#accountPanel').classList.remove('show');
  }

  $('#signinTab').onclick = () => setMode('signin');
  $('#signupTab').onclick = () => setMode('signup');
  $('#passwordToggle').onclick = () => {
    const visible = $('#password').type === 'password';
    $('#password').type = visible ? 'text' : 'password';
    $('#passwordToggle').textContent = visible ? 'Hide' : 'Show';
    $('#passwordToggle').setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    $('#passwordToggle').setAttribute('aria-pressed', String(visible));
  };
  $('#emailForm').onsubmit = async event => {
    event.preventDefault();
    const email = $('#email').value.trim();
    const password = $('#password').value;
    const name = $('#name').value.trim();
    if (!email || (mode === 'signup' && (!name || password.length < 8 || password.length > passwordMax)) || (mode === 'signin' && !password)) {
      return message(mode === 'signup' ? 'Enter your name, email, and a password of at least 8 characters.' : 'Enter your email and password.', 'error');
    }
    $('#submitButton').disabled = true;
    try {
      const body = mode === 'signup' ? { name, email, password } : { email, password };
      const result = await request(mode === 'signup' ? '/api/register' : '/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      message(`Welcome, ${result.user.name}. Opening your account…`, 'success');
      showUser(result.user);
    } catch (error) {
      if (error.data?.google_only) highlightGoogle();
      message(error.message, 'error');
    }
    finally { $('#submitButton').disabled = false; }
  };

  $('#signoutButton').onclick = async () => {
    try { await request('/api/logout', { method: 'POST' }); showAuth(); }
    catch (error) { message(error.message, 'error'); }
  };

  function highlightGoogle() {
    $('#googleSlot').animate?.([{ transform: 'scale(1)' }, { transform: 'scale(1.03)' }, { transform: 'scale(1)' }], { duration: 450 });
  }

  function googleNote(text) {
    $('#googleNote').textContent = text;
    $('#googleNote').hidden = !text;
  }

  function renderGoogleButton() {
    if (!googleReady) return;
    const target = $('#googleButton');
    target.replaceChildren();
    window.google.accounts.id.renderButton(target, {
      type: 'standard', theme: 'outline', size: 'large', shape: 'rectangular', logo_alignment: 'center',
      text: mode === 'signup' ? 'signup_with' : 'continue_with',
      width: Math.max(200, Math.min(400, Math.round($('#googleSlot').clientWidth || 360)))
    });
    target.classList.remove('hidden');
    $('#googleFallback').classList.add('hidden');
  }

  async function finishGoogle(payload) {
    message('Signing you in with Google…', 'info');
    try {
      const result = await request('/api/auth/google', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      pendingGoogleCredential = null;
      $('#linkForm').classList.add('hidden');
      message(`Welcome, ${result.user.name}. Opening your account…`, 'success');
      showUser(result.user);
    } catch (error) {
      if (error.data?.link_required) {
        pendingGoogleCredential = payload.credential;
        $('#linkCopy').textContent = `You already have a Serenity account for ${error.data.email}. Enter its password once to connect Google — after that, either way signs you in.`;
        $('#linkForm').classList.remove('hidden');
        $('#emailForm').classList.add('hidden');
        $('#linkPassword').focus();
        if (payload.password) message(error.message, 'error');
        else $('#status').className = 'status';
        return;
      }
      message(error.message, 'error');
    }
  }

  $('#linkForm').onsubmit = async event => {
    event.preventDefault();
    const password = $('#linkPassword').value;
    if (!pendingGoogleCredential) return message('Your Google sign-in expired. Choose Continue with Google again.', 'error');
    if (!password) return message('Enter your Serenity password.', 'error');
    $('#linkButton').disabled = true;
    try { await finishGoogle({ credential: pendingGoogleCredential, password }); }
    finally { $('#linkButton').disabled = false; $('#linkPassword').value = ''; }
  };
  $('#linkCancel').onclick = () => {
    pendingGoogleCredential = null;
    $('#linkForm').classList.add('hidden');
    $('#emailForm').classList.remove('hidden');
    $('#status').className = 'status';
  };

  function startGoogle(clientId) {
    if (!clientId) {
      googleNote('Google sign-in isn’t switched on for this server yet. Use your email for now.');
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onerror = () => googleNote('Google sign-in could not load. Check your connection, or use your email.');
    script.onload = () => {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: response => finishGoogle({ credential: response.credential }),
        ux_mode: 'popup',
        auto_select: false,
        cancel_on_tap_outside: true,
        itp_support: true,
        use_fedcm_for_prompt: true,
        use_fedcm_for_button: true,
        context: mode === 'signup' ? 'signup' : 'signin'
      });
      googleReady = true;
      renderGoogleButton();
      window.google.accounts.id.prompt();
    };
    document.head.append(script);
  }

  setMode(new URLSearchParams(location.search).get('mode') === 'signup' ? 'signup' : 'signin');
  request('/api/me').then(data => {
    if (data.user) return showUser(data.user);
    showAuth();
    return request('/api/auth/config').then(config => {
      passwordMax = config.password_max || passwordMax;
      $('#password').maxLength = passwordMax;
      startGoogle(config.google_client_id);
    });
  }).catch(error => { message(error.message, 'error'); googleNote(''); });
})();
