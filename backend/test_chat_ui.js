/* Pure UI-state tests: a fake DOM, not browser automation. Also runnable with Node. */
async function runChatUiTests(sources) {
  const assert = (ok, text) => { if (!ok) throw new Error(text); };
  const flush = async () => { for (let i = 0; i < 35; i++) await Promise.resolve(); };
  const people = [
    { public_id: 'b'.repeat(16), username: 'demo_maya', name: 'Maya · Demo', bio: 'Sample coast videos', is_demo: 1, trip_count: 2, video_count: 17, destination: 'Coast · unconfirmed' },
    { public_id: 'c'.repeat(16), username: 'demo_jules', name: 'Jules · Demo', bio: 'Sample streets', trip_count: 2, video_count: 10, destination: 'Streets · unconfirmed' }
  ];
  const nodes = new Map(), listeners = new Map(), sent = [], stored = [];
  let currentUser = { public_id: 'a'.repeat(16), username: 'tester' }, sequence = 0, interval, readCalls = 0;
  let delayedPeer = null, release;
  const location = { search: '', pathname: '/search.html' };
  const document = { hidden: false, activeElement: null };
  class Node {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attrs = {}; this.value = '';
      this.hidden = false; this.disabled = false; this.className = ''; this._text = ''; this.scrollHeight = 100; this.clientHeight = 100; this.scrollTop = 0;
      this.classList = {
        add: (...names) => { this.className = [...new Set([...this.className.split(' ').filter(Boolean), ...names])].join(' '); },
        remove: (...names) => { this.className = this.className.split(' ').filter(name => !names.includes(name)).join(' '); },
        contains: name => this.className.split(' ').includes(name)
      };
    }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map(node => node.textContent).join(''); }
    set innerHTML(_) { throw new Error('Untrusted UI text must not use innerHTML'); }
    querySelector(selector) { return document.querySelector(selector); }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; this._text = ''; }
    setAttribute(key, value) { this.attrs[key] = value; }
    removeAttribute(key) { delete this.attrs[key]; }
    addEventListener(key, fn) { this['event_'+key] = fn; }
    focus() { document.activeElement = this; }
    requestSubmit() { return this.onsubmit({ preventDefault() {} }); }
  }
  document.querySelector = selector => { if (!nodes.has(selector)) nodes.set(selector, new Node()); return nodes.get(selector); };
  document.createElement = tag => new Node(tag);
  document.addEventListener = (type, fn) => { listeners.set('document:'+type, fn); };
  const $ = document.querySelector;
  $('#messenger').hidden = true; $('#conversationContent').hidden = true;
  const event = () => ({ preventDefault() {}, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false });
  const threadFor = id => ({ id: id.repeat(2), participant: people.find(person => person.public_id === id), unread_count: 0, blocked: false, can_send: true });
  const window = {
    history: { replaceState(_, __, value) { location.search = value.includes('?') ? value.slice(value.indexOf('?')) : ''; } },
    addEventListener(type, fn) { listeners.set(type, fn); },
    dispatchEvent(event) { listeners.get(event.type)?.(event); },
    RoamApp: {
      me: async () => currentUser,
      messageUrl: (id, post) => `search.html?to=${id}${post ? '&post='+post : ''}`,
      findAccounts: async () => ({ accounts: people, has_more: false, next_offset: null }),
      postContext: async id => ({ creator: people[0], travel: { destination: 'Coastal demo trip' }, post_id: id })
    },
    SerenityMessages: {
      async inbox() { return { threads: stored.length ? [{ ...threadFor(people[0].public_id), last_message: stored.at(-1) }] : [], next_before: null }; },
      async conversation(id) {
        if (id === delayedPeer) await new Promise(resolve => { release = resolve; });
        return { participant: people.find(person => person.public_id === id), thread: stored.length ? threadFor(id) : null,
          messages: stored.filter(item => item.recipient === id), has_more: false };
      },
      async send(payload) {
        sent.push(payload);
        const item = { id: ++sequence, recipient: payload.recipient, body: payload.body, is_mine: true, created_at: 1000, has_context: Boolean(payload.post_id), context: payload.post_id ? { id: payload.post_id, feed_id: 12, destination: 'Coast', trip_name: 'Sailing' } : null };
        stored.push(item);
        return { message: item, thread: threadFor(payload.recipient) };
      },
      async read(id) { readCalls++; return { thread: threadFor(id.slice(0,16)) }; },
      async block(id, blocked) { return { thread: { ...threadFor(id.slice(0,16)), blocked, can_send: !blocked } }; }
    }
  };
  class CustomEvent { constructor(type, options) { this.type = type; this.detail = options.detail; } }
  class Params {
    constructor(input = '') { this.map = new Map(typeof input === 'string' ? input.replace(/^\?/, '').split('&').filter(Boolean).map(pair => pair.split('=').map(decodeURIComponent)) : Object.entries(input)); }
    get(key) { return this.map.get(key) || null; } set(key, value) { this.map.set(key, value); }
    get size() { return this.map.size; } toString() { return [...this.map].map(([key,value]) => encodeURIComponent(key)+'='+encodeURIComponent(value)).join('&'); }
  }
  const args = ['window','document','location','crypto','CustomEvent','setInterval','clearInterval','setTimeout','clearTimeout','matchMedia','confirm','URLSearchParams'];
  const values = [window, document, location, { randomUUID: () => 'test-message-key-'+(++sequence) }, CustomEvent, fn => { interval = fn; return 1; }, () => {}, () => 1, () => {}, () => ({ matches: false }), () => true, typeof URLSearchParams === 'undefined' ? Params : URLSearchParams];
  new Function(...args, sources.directory)(...values);
  new Function(...args, sources.messages)(...values);
  await flush();
  assert(!$('#messenger').hidden && $('#directoryResults').children.length === 2, 'Signed-in users should see a working directory, not a blank Chat panel');
  assert($('#messageBody').disabled !== false || !$('#conversationContent').hidden === false, 'No active account must not expose an active conversation');
  const firstCard = $('#directoryResults').children[0];
  assert(firstCard.textContent.includes('TEST ACCOUNT'), 'Demo people must be visibly labeled');
  firstCard.children.at(-1).children[1].onclick(event()); await flush();
  assert($('#conversationName').textContent === people[0].name, 'Message on a directory card must open that exact account: '+$('#conversationName').textContent+' / '+$('#sendStatus').textContent);
  assert($('#sendMessage').disabled, 'An empty draft must not be sendable');
  $('#messageBody').value = '<img src=x onerror=alert(1)> Where was this filmed?'; $('#messageBody').oninput();
  await $('#messageForm').onsubmit(event()); await flush();
  assert(sent.length === 1 && sent[0].recipient === people[0].public_id, 'Send must target the selected account');
  assert($('#messageList').textContent.includes('<img src=x'), 'Message text must render literally, never as HTML');
  assert($('#messageBody').value === '' && $('#sendStatus').textContent === 'Message sent.', 'Acknowledged sends must clear the draft and show success');
  assert(readCalls > 0, 'Visible messages should advance the read cursor');
  $('#messageBody').value = 'Unsent draft'; $('#messageBody').oninput();
  window.dispatchEvent(new CustomEvent('serenity:message-account', { detail: { id: people[1].public_id } })); await flush();
  assert($('#messageBody').value === '', 'Drafts must not leak between accounts');
  window.dispatchEvent(new CustomEvent('serenity:message-account', { detail: { id: people[0].public_id } })); await flush();
  assert($('#messageBody').value === 'Unsent draft', 'Switching back should restore the unsent draft');
  await $('#blockAccount').onclick();
  assert($('#messageBody').disabled && $('#sendMessage').disabled, 'Blocking must disable the composer');
  await $('#blockAccount').onclick();
  assert(!$('#messageBody').disabled, 'Unblocking should restore the composer');
  stored.push({ id: ++sequence, recipient: people[0].public_id, body: 'Demo reply received in this inbox.', is_mine: false, created_at: 1020, has_context: false, context: null });
  await interval(); await flush();
  assert($('#messageList').textContent.includes('Demo reply received in this inbox.'), 'Polling must render incoming replies, not only sent messages');
  const videoId = 'e'.repeat(32);
  location.search = `?to=${people[0].public_id}&post=${videoId}`;
  listeners.get('pageshow')({ persisted: true }); await flush();
  assert(!$('#composeContext').hidden && $('#composeContextLabel').textContent.includes('Coastal demo trip'), 'A video question must retain its verified trip context');
  $('#messageBody').value = 'Question about this particular video'; $('#messageBody').oninput();
  await $('#messageForm').onsubmit(event()); await flush();
  assert(sent.at(-1).post_id === videoId, 'Sending a video question must include that selected video, not another trip');
  delayedPeer = people[0].public_id;
  window.dispatchEvent(new CustomEvent('serenity:message-account', { detail: { id: people[0].public_id } }));
  window.dispatchEvent(new CustomEvent('serenity:message-account', { detail: { id: people[1].public_id } }));
  await flush(); release(); await flush(); delayedPeer = null;
  assert($('#conversationName').textContent === people[1].name, 'An older slow request must not replace the selected conversation');
  currentUser = { public_id: 'd'.repeat(16), username: 'other_account' };
  await interval(); await flush();
  assert($('#messenger').hidden && !$('#messagesGate').hidden, 'An account change must close the previous private inbox');
  assert(!$('#messageList').children.length && !$('#directoryResults').children.length, 'Account changes must erase private UI and directory state');
  return 'Chat UI tests passed: discovery, demo labels, safe text, send/receive state, drafts, read positions, blocking, stale requests, and account isolation.';
}
if (typeof module !== 'undefined' && require.main === module) {
  const fs = require('fs'), path = require('path');
  runChatUiTests({ directory: fs.readFileSync(path.join(__dirname,'../account-discovery.js'),'utf8'), messages: fs.readFileSync(path.join(__dirname,'../messages.js'),'utf8') })
    .then(console.log).catch(error => { console.error(error); process.exitCode = 1; });
}
