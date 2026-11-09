/* Inbox UI. Drafts stay in memory, never in shared browser storage or offline caches. */
(() => {
  const $ = selector => document.querySelector(selector);
  const api = window.SerenityMessages;
  if (!api || !$('#messenger')) return;
  const history = $('#messageHistory');
  const drafts = new Map();
  const states = new Map();
  let me = null, peer = null, thread = null, messages = [], context = null;
  let threads = [], nextInbox = null, generation = 0, searching = 0, polling = false, sending = false;
  let inboxRequest = 0, markedThrough = 0, peopleTimer, refreshTimer;
  const validPeer = value => /^[0-9a-f]{16}$/.test(value || '');
  const validPost = value => /^[0-9a-f]{32}$/.test(value || '');
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function fail(error, target = $('#messagesStatus')) {
    if (error.status === 401) return signedOut('Your session ended. Sign in to continue your conversations.');
    target.textContent = error.message || 'Cannot reach Serenity. Please try again.';
  }
  function signedOut(text = '') {
    generation++; me = null; peer = null; thread = null; messages = []; context = null;
    drafts.clear(); states.clear(); threads = [];
    searching++; inboxRequest++; clearTimeout(peopleTimer);
    window.SerenityAccountDiscovery?.clear();
    $('#threadList').replaceChildren(); $('#messageList').replaceChildren(); $('#peopleResults').replaceChildren();
    $('#messageBody').value = '';
    $('#messenger').hidden = true; $('#messagesGate').hidden = false;
    $('#messagesStatus').textContent = text;
    const next = new URLSearchParams({ next: 'messages' });
    const current = new URLSearchParams(location.search);
    if (validPeer(current.get('to'))) next.set('to', current.get('to'));
    if (validPost(current.get('post'))) next.set('post', current.get('post'));
    $('#messagesSignin').href = `auth.html?${next}`;
    $('#messagesAccount').href = `auth.html?${next}`; $('#messagesAccount').textContent = 'Sign in ↗';
  }
  function saveDraft() {
    if (peer) drafts.set(peer.public_id, { body: $('#messageBody').value, context });
  }
  function setUrl(id, post) {
    const query = new URLSearchParams();
    if (id) query.set('to', id);
    if (post) query.set('post', post);
    window.history.replaceState(null, '', `search.html${query.size ? `?${query}` : ''}`);
  }
  function atBottom() { return history.scrollHeight - history.scrollTop - history.clientHeight < 75; }
  function isViewing() {
    return !document.hidden && $('#messenger').classList.contains('has-conversation') && !$('#messenger').hidden;
  }
  function updateContext() {
    $('#composeContext').hidden = !context;
    $('#composeContextLabel').textContent = context ? `Question about ${context.label}` : '';
  }
  function updateThread() {
    const allowed = Boolean(peer) && !sending && (!thread || thread.can_send);
    $('#messageBody').disabled = !allowed;
    $('#sendMessage').disabled = !allowed || !$('#messageBody').value.trim();
    $('#sendMessage').textContent = sending ? 'Sending…' : 'Send ↗';
    $('#blockAccount').hidden = !thread;
    $('#blockAccount').textContent = thread?.blocked ? 'Unblock' : 'Block';
    $('#composeHelp').textContent = thread && !thread.can_send
      ? (thread.blocked ? 'You blocked this account. Unblock to send messages.' : 'Messaging is unavailable for this conversation.')
      : 'Private message · Enter to send · Shift + Enter for a new line';
    $('#conversationHint').textContent = !messages.length ? 'No messages yet. Ask a travel question or say hello.' : '';
  }
  function renderInbox() {
    const active = document.activeElement?.dataset.peer;
    const filter = $('#inboxSearch').value.trim().toLocaleLowerCase();
    const filtered = threads.filter(item => `${item.participant.name} ${item.participant.username} ${item.last_message.body}`.toLocaleLowerCase().includes(filter));
    const nodes = filtered.map(item => {
      const person = item.participant;
      const button = el('button', `thread-button${peer?.public_id === person.public_id ? ' is-current' : ''}`);
      button.type = 'button'; button.dataset.peer = person.public_id;
      button.setAttribute('aria-label', `${person.name}${item.unread_count ? `, ${item.unread_count} unread messages` : ''}`);
      if (peer?.public_id === person.public_id) button.setAttribute('aria-current', 'true');
      const copy = el('span', 'thread-copy');
      copy.append(el('strong', '', person.name), el('small', '', `${item.last_message.is_mine ? 'You: ' : ''}${item.last_message.body}`));
      const meta = el('span', 'thread-meta');
      meta.append(el('time', '', new Date(item.last_message.created_at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })));
      if (item.unread_count) meta.append(el('span', 'unread', item.unread_count > 99 ? '99+' : item.unread_count));
      button.append(el('span', 'avatar', person.name.charAt(0).toUpperCase()), copy, meta);
      button.onclick = () => openConversation(person.public_id);
      return button;
    });
    if (!nodes.length) nodes.push(el('p', 'muted', filter ? 'No matching conversations in your loaded inbox.' : 'No conversations yet. Use Find people, or ask a creator about their video.'));
    $('#threadList').replaceChildren(...nodes);
    if (active) [...$('#threadList').children].find(node => node.dataset.peer === active)?.focus({ preventScroll: true });
    $('#inboxMore').hidden = !nextInbox;
  }
  async function loadInbox(append = false) {
    const version = ++inboxRequest;
    const result = await api.inbox(append ? nextInbox : null);
    if (!me || version !== inboxRequest) return;
    if (append) {
      const known = new Set(threads.map(item => item.id));
      threads.push(...result.threads.filter(item => !known.has(item.id)));
    } else {
      const incoming = new Set(result.threads.map(item => item.id));
      threads = [...result.threads, ...threads.filter(item => !incoming.has(item.id))];
    }
    nextInbox = result.next_before;
    renderInbox();
    $('#messagesStatus').textContent = 'Your private travel conversations';
  }
  function messageNode(item) {
    const node = el('article', `message${item.is_mine ? ' is-mine' : ''}`);
    node.dataset.messageId = item.id;
    node.setAttribute('aria-label', `${item.is_mine ? 'You' : peer.name} said`);
    const bubble = el('div', 'message-bubble');
    if (item.has_context) {
      const ref = item.context;
      const attachment = el(ref ? 'a' : 'span', 'message-context');
      if (ref) {
        attachment.href = `feed.html?feed=${encodeURIComponent(ref.feed_id)}&post=${encodeURIComponent(ref.id)}`;
        attachment.append(el('span', '', 'Question about a video ↗'), el('strong', '', `${ref.trip_name || 'Trip'} · ${ref.destination}`));
      } else attachment.textContent = 'Referenced video is private or no longer available.';
      bubble.append(attachment);
    }
    bubble.append(el('span', '', item.body));
    const time = el('time', '', `${item.is_mine ? 'You · ' : ''}${new Date(item.created_at * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`);
    time.dateTime = new Date(item.created_at * 1000).toISOString();
    node.append(bubble, time);
    return node;
  }
  function mergeMessages(items, { prepend = false, bottom = false } = {}) {
    const wasBottom = atBottom(), oldHeight = history.scrollHeight, top = history.scrollTop;
    const known = new Map(messages.map(item => [item.id, item]));
    let incoming = false;
    for (const item of items) { if (!known.has(item.id) && !item.is_mine) incoming = true; known.set(item.id, item); }
    messages = [...known.values()].sort((a, b) => a.id - b.id);
    $('#messageList').replaceChildren(...messages.map(messageNode));
    updateThread();
    if (prepend) history.scrollTop = top + history.scrollHeight - oldHeight;
    else if (bottom || wasBottom) scrollBottom();
    else { history.scrollTop = top; if (incoming) $('#newMessagesNotice').hidden = false; }
  }
  function scrollBottom() {
    history.scrollTop = history.scrollHeight;
    $('#newMessagesNotice').hidden = true;
    markRead();
  }
  async function markRead() {
    const last = messages.at(-1)?.id;
    if (!thread || !last || last <= markedThrough || !isViewing() || !atBottom()) return;
    const version = generation, target = thread.id;
    markedThrough = last;
    try {
      const result = await api.read(target, last);
      if (version !== generation || thread?.id !== target) return;
      thread = result.thread;
      const item = threads.find(item => item.id === target);
      if (item) { item.unread_count = thread.unread_count; renderInbox(); }
    } catch (error) { if (version === generation) { markedThrough = 0; fail(error); } }
  }
  async function openConversation(id, postId = null) {
    if (!validPeer(id)) { $('#messagesStatus').textContent = 'This message link has an invalid account ID.'; return; }
    saveDraft();
    const version = ++generation;
    peer = null; thread = null; messages = []; context = null; markedThrough = 0;
    $('#messenger').classList.remove('is-discovering');
    $('#messenger').classList.add('has-conversation');
    $('#conversationEmpty').hidden = true; $('#conversationContent').hidden = false;
    $('#conversationName').textContent = 'Opening conversation…'; $('#conversationUsername').textContent = '';
    $('#conversationProfile').removeAttribute('href'); $('#conversationAvatar').textContent = '';
    $('#messageList').replaceChildren(); $('#olderMessages').hidden = true;
    $('#messageBody').value = ''; $('#messageBody').disabled = true; $('#sendMessage').disabled = true;
    $('#blockAccount').hidden = true; $('#sendStatus').textContent = ''; $('#conversationHint').textContent = '';
    $('#newMessagesNotice').hidden = true; updateContext();
    setUrl(id, validPost(postId) ? postId : null);
    try {
      const result = await api.conversation(id);
      if (version !== generation || !me) return;
      peer = result.participant; thread = result.thread;
      $('#conversationName').textContent = peer.name; $('#conversationUsername').textContent = `@${peer.username}`;
      $('#conversationAvatar').textContent = peer.name.charAt(0).toUpperCase();
      $('#conversationProfile').href = `profile.html?id=${encodeURIComponent(id)}`;
      const draft = drafts.get(id);
      $('#messageBody').value = draft?.body || ''; context = draft?.context || null;
      if (validPost(postId)) {
        // Keep the composer closed while verifying the public video belongs to this creator.
        try {
          const source = await window.RoamApp.postContext(postId);
          if (version !== generation) return;
          if (source.creator.public_id !== id) throw new Error('That video belongs to a different creator.');
          context = { id: postId, label: source.travel.destination };
        } catch (error) {
          if (version !== generation) return;
          context = null;
          $('#sendStatus').textContent = `Video reference unavailable. You can still send a direct message. ${error.message}`;
        }
      }
      updateContext();
      mergeMessages(result.messages, { bottom: true });
      $('#olderMessages').hidden = !result.has_more;
      renderInbox(); updateThread();
      $('#messageBody').focus({ preventScroll: true });
    } catch (error) {
      if (version !== generation) return;
      fail(error, $('#sendStatus'));
      $('#conversationName').textContent = 'Cannot open conversation';
    }
  }
  $('#messageBody').oninput = () => { saveDraft(); updateThread(); };
  $('#messageBody').onkeydown = event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !matchMedia('(pointer: coarse)').matches) {
      event.preventDefault(); if (!$('#sendMessage').disabled) $('#messageForm').requestSubmit();
    }
  };
  $('#removeContext').onclick = () => { context = null; updateContext(); saveDraft(); if (peer) setUrl(peer.public_id); };
  $('#messageForm').onsubmit = async event => {
    event.preventDefault();
    if (!peer || sending || (thread && !thread.can_send)) return;
    const body = $('#messageBody').value.trim();
    if (!body) return;
    const id = peer.public_id, source = context?.id || null, version = generation;
    const previous = states.get(id);
    const key = previous?.body === body && previous?.post_id === source ? previous.client_key : crypto.randomUUID();
    const payload = { recipient: id, body, post_id: source, client_key: key };
    states.set(id, payload); sending = true; updateThread(); $('#sendStatus').textContent = '';
    try {
      const result = await api.send(payload);
      states.delete(id); drafts.delete(id);
      if (version === generation) {
        thread = result.thread;
        $('#messageBody').value = ''; context = null; updateContext(); setUrl(id);
        mergeMessages([result.message], { bottom: true });
        $('#sendStatus').textContent = 'Message sent.';
      }
      await loadInbox();
    } catch (error) { if (version === generation) fail(error, $('#sendStatus')); }
    finally { sending = false; updateThread(); if (version === generation) $('#messageBody').focus({ preventScroll: true }); }
  };
  $('#olderMessages').onclick = async () => {
    if (!peer || !messages.length) return;
    const version = generation, target = peer.public_id;
    $('#olderMessages').disabled = true;
    try {
      const result = await api.conversation(target, { before: messages[0].id });
      if (version !== generation) return;
      mergeMessages(result.messages, { prepend: true }); $('#olderMessages').hidden = !result.has_more;
    } catch (error) { if (version === generation) fail(error); }
    finally { $('#olderMessages').disabled = false; }
  };
  $('#blockAccount').onclick = async () => {
    if (!thread || !peer) return;
    const version = generation, blocked = !thread.blocked;
    if (blocked && !confirm(`Block @${peer.username}? Neither of you can send new messages until you unblock. Existing messages will remain.`)) return;
    try {
      const result = await api.block(thread.id, blocked);
      if (version !== generation) return;
      thread = result.thread; updateThread();
      $('#sendStatus').textContent = blocked ? 'Account blocked. You can unblock here at any time.' : 'Account unblocked.';
    } catch (error) { if (version === generation) fail(error); }
  };
  async function searchPeople() {
    const version = ++searching;
    $('#peopleStatus').textContent = 'Finding accounts…'; $('#peopleResults').replaceChildren();
    try {
      const result = await window.RoamApp.findAccounts($('#peopleQuery').value.trim());
      if (version !== searching || !me) return;
      $('#peopleStatus').textContent = result.accounts.length ? 'Choose an account to message, or open their profile.' : 'No matching accounts. Try a name, username, or published destination.';
      for (const person of result.accounts.slice(0, 5)) {
        const row = el('div', 'people-result');
        const button = el('button', 'person-result'); button.type = 'button';
        const copy = el('span', 'thread-copy'); copy.append(el('strong', '', person.name), el('small', '', `@${person.username}`));
        button.append(el('span', 'avatar', person.name.charAt(0).toUpperCase()), copy);
        button.onclick = () => { $('#peopleResults').replaceChildren(); $('#peopleStatus').textContent = ''; openConversation(person.public_id); };
        const profile = el('a', '', 'Profile ↗'); profile.href = `profile.html?id=${encodeURIComponent(person.public_id)}`;
        row.append(button, profile); $('#peopleResults').append(row);
      }
    } catch (error) { if (version === searching) fail(error, $('#peopleStatus')); }
  }
  $('#peopleSearch').onsubmit = event => { event.preventDefault(); clearTimeout(peopleTimer); searchPeople(); };
  $('#peopleQuery').oninput = () => { clearTimeout(peopleTimer); searching++; peopleTimer = setTimeout(searchPeople, 300); };
  $('#inboxSearch').oninput = renderInbox;
  function inboxView() {
    saveDraft(); generation++; peer = null; thread = null; messages = []; context = null;
    $('#messenger').classList.remove('has-conversation');
    $('#messenger').classList.remove('is-discovering');
    $('#conversationEmpty').hidden = false; $('#conversationContent').hidden = true;
    $('#messageBody').value = ''; $('#messageList').replaceChildren(); setUrl(); renderInbox();
  }
  $('#backToInbox').onclick = inboxView;
  function discoverPeople() {
    inboxView(); $('#messenger').classList.add('is-discovering');
    window.SerenityAccountDiscovery?.focus();
  }
  $('#newMessage').onclick = discoverPeople;
  $('#discoverPeople').onclick = discoverPeople;
  $('#directoryBack').onclick = inboxView;
  window.addEventListener('serenity:message-account', event => {
    if (me && validPeer(event.detail?.id)) openConversation(event.detail.id);
  });
  $('#inboxMore').onclick = async () => {
    $('#inboxMore').disabled = true;
    try { await loadInbox(true); } catch (error) { fail(error); }
    finally { $('#inboxMore').disabled = false; }
  };
  $('#showNewMessages').onclick = scrollBottom;
  history.addEventListener('scroll', () => { if (atBottom()) { $('#newMessagesNotice').hidden = true; markRead(); } }, { passive: true });
  async function refresh() {
    if (!me || document.hidden || polling || sending) return;
    polling = true;
    try {
      // Detect logout/account switching in another tab before showing any response.
      const current = await window.RoamApp.me();
      if (!current || current.public_id !== me?.public_id) return signedOut('Your account session changed. Sign in to open your inbox.');
      await loadInbox();
      const version = generation;
      if (peer && isViewing()) {
        const target = peer.public_id;
        const result = await api.conversation(target, messages.length ? { after: messages.at(-1).id } : {});
        if (version !== generation || !me) return;
        thread = result.thread;
        mergeMessages(result.messages);
        // Revalidate visible video references; a creator may have made them private.
        if (messages.some(item => item.has_context)) {
          const recent = await api.conversation(target);
          if (version !== generation || !me) return;
          const visibleIds = new Set(messages.map(item => item.id));
          mergeMessages(recent.messages.filter(item => visibleIds.has(item.id)));
        }
        if (!messages.length || !result.has_more) markRead();
        // Catch up in bounded pages on later polls instead of an unbounded request loop.
        if (result.has_more) $('#messagesStatus').textContent = 'Catching up on your conversation…';
        updateThread();
      }
    } catch (error) { fail(error); }
    finally { polling = false; }
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  window.addEventListener('online', refresh);
  window.addEventListener('pagehide', () => { clearInterval(refreshTimer); signedOut(); });
  window.addEventListener('pageshow', event => { if (event.persisted) start(); });
  $('#refreshMessages').onclick = async () => {
    $('#refreshMessages').disabled = true;
    try { await refresh(); } finally { $('#refreshMessages').disabled = false; }
  };
  async function start() {
    try {
      me = await window.RoamApp.me();
      if (!me) return signedOut();
      $('#messenger').hidden = false; $('#messagesGate').hidden = true;
      $('#messagesAccount').textContent = `@${me.username} ↗`;
      await loadInbox();
      window.SerenityAccountDiscovery?.start();
      const current = new URLSearchParams(location.search);
      if (current.get('to')) await openConversation(current.get('to'), current.get('post'));
      clearInterval(refreshTimer); refreshTimer = setInterval(refresh, 6000);
    } catch (error) { fail(error); }
  }
  start();
})();
