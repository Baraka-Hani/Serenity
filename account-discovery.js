/* Account directory. Uses only public profile fields, and can be reused outside Chat. */
(() => {
  const root = document.querySelector('#accountDirectory');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  let version = 0, next = null, term = '', started = false, timer;
  function el(tag, className, text) {
    const node = document.createElement(tag); node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function card(person) {
    const item = el('article', 'account-card');
    const profile = el('a', 'account-card__identity');
    profile.href = `profile.html?id=${encodeURIComponent(person.public_id)}`;
    const info = el('span', 'account-card__name');
    info.append(el('strong', '', person.name), el('small', '', `@${person.username}`));
    profile.append(el('span', 'avatar', person.name.charAt(0).toUpperCase()), info);
    const bio = el('p', 'account-card__bio', person.bio || 'A new perspective on your next destination.');
    const stats = el('p', 'account-card__stats', `${person.trip_count} ${person.trip_count === 1 ? 'trip' : 'trips'} · ${person.video_count} ${person.video_count === 1 ? 'video' : 'videos'}`);
    const place = el('span', 'account-card__place', person.destination || 'No public destinations yet');
    const actions = el('div', 'account-card__actions');
    const view = el('a', '', 'View profile ↗'); view.href = profile.href;
    const message = el('a', 'account-card__message', 'Message ↗');
    message.href = window.RoamApp.messageUrl(person.public_id);
    message.onclick = event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      window.dispatchEvent(new CustomEvent('serenity:message-account', { detail: { id: person.public_id } }));
    };
    actions.append(view, message);
    item.append(profile);
    if (person.is_demo) item.append(el('span', 'demo-badge', 'TEST ACCOUNT'));
    item.append(bio, place, stats, actions);
    return item;
  }
  async function load(append = false) {
    const current = ++version;
    const q = $('#directoryQuery').value.trim();
    if (q.replace(/^@/, '').length === 1) {
      $('#directoryResults').replaceChildren(); $('#directoryMore').hidden = true;
      $('#directoryStatus').textContent = 'Type one more character, or clear to explore creators.';
      return;
    }
    if (!append) { next = null; term = q; $('#directoryResults').replaceChildren(); }
    $('#directoryMore').hidden = true;
    $('#directoryStatus').textContent = 'Finding travel perspectives…';
    try {
      const result = await window.RoamApp.findAccounts(term, append ? next : 0);
      if (current !== version || !started) return;
      $('#directoryResults').append(...result.accounts.map(card));
      next = result.next_offset;
      $('#directoryMore').hidden = !result.has_more;
      $('#directoryStatus').textContent = !$('#directoryResults').children.length
        ? 'No accounts found. Try a name, @username, or a destination from a published trip.'
        : term ? `Accounts matching “${term}”` : 'People sharing public trips. Find a perspective, then ask about the place.';
    } catch (error) {
      if (current !== version) return;
      $('#directoryStatus').textContent = error.message;
    }
  }
  $('#directoryForm').onsubmit = event => { event.preventDefault(); clearTimeout(timer); load(); };
  $('#directoryQuery').oninput = () => { clearTimeout(timer); version++; timer = setTimeout(() => load(), 300); };
  $('#directoryMore').onclick = () => load(true);
  window.SerenityAccountDiscovery = {
    start() { started = true; load(); },
    focus() { $('#directoryQuery').focus({ preventScroll: true }); if (started && !$('#directoryResults').children.length) load(); },
    clear() { version++; started = false; clearTimeout(timer); $('#directoryResults').replaceChildren(); $('#directoryQuery').value = ''; }
  };
})();
