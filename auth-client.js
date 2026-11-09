/* Account feature: independent of the landing page and video studio. */
(() => {
  const $ = selector => document.querySelector(selector);
  let mode = 'signin';

  async function request(path, options = {}) {
    if (location.protocol === 'file:') throw new Error('Accounts need the Serenity server. Start it, then open http://127.0.0.1:8765/auth.html instead of this file.');
    let response;
    try { response = await fetch(path, { credentials: 'same-origin', ...options }); }
    catch (_) { throw new Error('Cannot reach the Serenity server. Run python3 backend/server.py, then open http://127.0.0.1:8765/auth.html.'); }
    if (!response.headers.get('Content-Type')?.includes('application/json')) {
      throw new Error('This page is not being served by the Serenity backend. Open http://127.0.0.1:8765/auth.html.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed.');
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
    $('#password').maxLength = signup ? 16 : 256;
    $('#password').type = 'password';
    $('#passwordToggle').textContent = 'Show';
    $('#passwordToggle').setAttribute('aria-label', 'Show password');
    $('#passwordToggle').setAttribute('aria-pressed', 'false');
    $('#status').className = 'status';
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
    if (!email || (mode === 'signup' && (!name || password.length < 8 || password.length > 16)) || (mode === 'signin' && !password)) {
      return message(mode === 'signup' ? 'Enter your name, email, and a password of 8–16 characters.' : 'Enter your email and password.', 'error');
    }
    $('#submitButton').disabled = true;
    try {
      const body = mode === 'signup' ? { name, email, password } : { email, password };
      const result = await request(mode === 'signup' ? '/api/register' : '/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      message(`Welcome, ${result.user.name}. Opening your account…`, 'success');
      showUser(result.user);
    } catch (error) { message(error.message, 'error'); }
    finally { $('#submitButton').disabled = false; }
  };

  $('#signoutButton').onclick = async () => {
    try { await request('/api/logout', { method: 'POST' }); showAuth(); }
    catch (error) { message(error.message, 'error'); }
  };

  document.querySelectorAll('[data-provider]').forEach(button => {
    button.disabled = true;
    button.title = 'Social sign-in needs provider credentials and is not connected yet.';
  });
  $('#chatgptButton').disabled = true;
  $('#chatgptButton').title = 'Sign in with ChatGPT requires partner access.';

  setMode(new URLSearchParams(location.search).get('mode') === 'signup' ? 'signup' : 'signin');
  request('/api/me').then(data => data.user ? showUser(data.user) : showAuth())
    .catch(error => message(error.message, 'error'));
})();
