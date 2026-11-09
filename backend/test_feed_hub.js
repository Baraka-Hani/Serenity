/* Dependency-free event tests: node backend/test_feed_hub.js */
async function runFeedHubTests(source) {
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  class Node {
    constructor(tag = 'div', className = '') {
      this.tagName = tag.toUpperCase(); this.className = className;
      this.children = []; this.listeners = {}; this.attributes = {}; this.scrollLeft = 0;
      this.clientWidth = 400; this.paused = true; this.inert = false; this.style = {}; this.dataset = {};
      this.classList = {
        add: name => { this.className += ` ${name}`; },
        remove: name => { this.className = this.className.split(' ').filter(x => x !== name).join(' '); },
        contains: name => this.className.split(' ').includes(name),
        toggle: (name, force) => {
          const enabled = force === undefined ? !this.classList.contains(name) : force;
          this.classList[enabled ? 'add' : 'remove'](name);
          return enabled;
        }
      };
    }
    get isConnected() { return this === doc.body || Boolean(this.parentElement?.isConnected); }
    get textContent() { return (this.text || '') + this.children.map(x => x.textContent).join(' '); }
    set textContent(value) { this.text = value; }
    append(...items) { for (const node of items) { node.parentElement = this; this.children.push(node); } }
    prepend(node) { node.parentElement = this; this.children.unshift(node); }
    replaceChildren(...items) { this.children = []; this.append(...items); }
    setAttribute(key, value) { this.attributes[key] = value; }
    getAttribute(key) { return this.attributes[key]; }
    addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
    dispatch(type, props = {}) {
      const event = { target: this, button: 0, pointerId: 1, preventDefault() { this.prevented = true; }, stopPropagation() {}, ...props };
      for (const listener of this.listeners[type] || []) listener(event);
      this[`on${type}`]?.(event);
      return event;
    }
    closest(selector) {
      const matches = selector.split(',').some(tag => tag.trim().toUpperCase() === this.tagName);
      return matches ? this : this.parentElement?.closest(selector);
    }
    querySelector(selector) {
      for (const child of this.children) {
        if (selector === '[aria-expanded]' && child.attributes['aria-expanded'] !== undefined ||
          selector.startsWith('.') && child.classList.contains(selector.slice(1)) || child.tagName === selector.toUpperCase()) return child;
        const match = child.querySelector(selector); if (match) return match;
      }
      return null;
    }
    querySelectorAll(selector) {
      const matches = [];
      for (const child of this.children) {
        if (child.tagName === selector.toUpperCase() || selector.startsWith('.') && child.classList.contains(selector.slice(1))) matches.push(child);
        matches.push(...child.querySelectorAll(selector));
      }
      return matches;
    }
    scrollTo({ left }) { this.scrollLeft = left; }
    scrollBy() {}
    setPointerCapture() {}
    focus() { doc.activeElement = this; }
    click() { this.dispatch('click'); }
    play() { this.paused = false; this.dispatch('play'); return Promise.resolve(); }
    pause() { this.paused = true; this.dispatch('pause'); }
    load() {}
  }
  const doc = { body: new Node('body'), hidden: false, listeners: {}, createElement: tag => new Node(tag), addEventListener(type, listener) { this.listeners[type] = listener; } };
  doc.body.dataset = {};
  const list = new Node(); doc.body.append(list);
  doc.querySelector = () => list;
  const frames = [];
  let io;
  class IO { constructor(callback) { this.callback = callback; io = this; } observe() {} unobserve() {} }
  class RO { constructor(callback) { this.callback = callback; } observe() {} disconnect() {} }
  const window = { addEventListener() {}, RoamApp: {
    async postContext() { return {
      travel: { destination: 'Kyoto', summary: 'Public story', tip: 'Public tip' },
      creator: { name: 'Alex', username: 'alex', public_id: 'a'.repeat(16) },
      related_trips: [{ id: 42, name: 'Earlier Kyoto trip', destination: 'Kyoto', video_count: 2, preview_post_id: 'p', same_destination: true }]
    }; },
    postVideoUrl: id => `/api/posts/${id}/video`
  } };
  new Function('document', 'window', 'IntersectionObserver', 'ResizeObserver', 'matchMedia', 'requestAnimationFrame', 'location', 'localStorage', source)(
    doc, window, IO, RO, () => ({ matches: false }), callback => frames.push(callback), { hash: '#home-feed' }, { getItem: () => null });
  function fixture(id) {
    const card = new Node('article'), media = new Node(), video = new Node('video'), body = new Node(), comments = new Node(), input = new Node('input');
    comments.append(input); comments.hidden = true;
    const commentButton = new Node('button'); commentButton.setAttribute('aria-expanded', 'false'); body.append(commentButton);
    const slides = new Node('div', 'social-post__slides'); slides.append(video); media.append(slides);
    const hub = window.SerenityFeedHub.create({ id }, card, media, new Node(), body, comments);
    card.append(hub.root); list.append(card);
    return { card, video, media, hub, body, comments, input, viewport: hub.root.children[1], tabs: hub.root.children[0].children[0].children };
  }
  const first = fixture('one'); const second = fixture('two');
  frames.forEach(callback => callback());
  assert(first.viewport.scrollLeft === 400, 'The video must be the initial center panel');
  assert(first.viewport.children[0].inert && first.viewport.children[2].inert, 'Inactive panels must not receive keyboard focus');
  io.callback([{ target: first.card, isIntersecting: true, intersectionRatio: 1 }]);
  assert(!first.video.paused && second.video.paused, 'Only the visible post may play');
  assert(!doc.body.classList.contains('home-toolbar-icons'), 'The first post must retain the full toolbar');
  function swipe(fixture, x, y = 0, target) {
    const viewport = fixture.viewport;
    viewport.dispatch('pointerdown', { clientX: 200, clientY: 100, target: target || viewport });
    const move = viewport.dispatch('pointermove', { clientX: 200 + x, clientY: 100 + y });
    viewport.dispatch('pointerup', { clientX: 200 + x, clientY: 100 + y });
    return move;
  }
  assert(swipe(first, 120).prevented, 'A deliberate horizontal swipe must be handled');
  assert(first.viewport.scrollLeft === 0 && first.tabs[0].attributes['aria-selected'] === 'true', 'Right swipe must open travel details on the left');
  assert(first.video.paused, 'Opening travel details must pause the video');
  await Promise.resolve(); await Promise.resolve();
  assert(first.viewport.children[0].textContent.includes('Kyoto'), 'Travel details must use the current post context');
  assert(first.viewport.children[0].textContent.includes('Experience this place'), 'Travel details must focus on visiting the destination');
  assert(first.viewport.children[0].textContent.includes('Explore the travel map'), 'Unpinned trips must offer map discovery without inventing coordinates');
  swipe(first, -120); swipe(first, -120);
  assert(first.viewport.scrollLeft === 800, 'Left swipe from video must open creator history on the right');
  const related = first.viewport.children[2].querySelector('.hub-related-trip');
  assert(related?.href === 'feed.html?feed=42', 'Related trip links must resolve to the actual public feed route');
  first.tabs[1].click();
  assert(!swipe(first, 10, 140).prevented && first.viewport.scrollLeft === 400, 'Vertical swipes must remain available to the timeline');
  swipe(first, -140, 0, first.tabs[1]);
  assert(first.viewport.scrollLeft === 400, 'Dragging a control must not swipe a post');
  first.tabs[1].dispatch('keydown', { key: 'ArrowLeft' });
  assert(first.viewport.scrollLeft === 0, 'Keyboard navigation must open the same travel panel');
  first.viewport.dispatch('keydown', { key: 'Escape' });
  assert(first.viewport.scrollLeft === 400, 'Escape must return to the video');
  first.hub.setCommentsOpen(true);
  assert(first.video.paused && (first.video.inert || first.video.parentElement.inert) && doc.activeElement === first.input, 'Comments must pause playback and receive focus');
  first.hub.setCommentsOpen(false);
  io.callback([{ target: first.card, isIntersecting: false, intersectionRatio: 0 }, { target: second.card, isIntersecting: true, intersectionRatio: 1 }]);
  assert(first.video.paused && !second.video.paused, 'Moving vertically must transfer playback to the new post');
  assert(doc.body.classList.contains('home-toolbar-icons'), 'The toolbar must become icon-only on the second post');
  doc.hidden = true; doc.listeners.visibilitychange();
  assert(first.video.paused && second.video.paused, 'Background tabs must pause all videos');
  window.SerenityFeedHub.reset();
  assert(first.video.paused && second.video.paused, 'Refreshing the timeline must stop old players');
  assert(!doc.body.classList.contains('home-toolbar-icons'), 'Resetting the feed must restore the full toolbar');
  return 'Feed interaction tests passed: swipe direction, public context, keyboard, focus, and single-video playback.';
}
if (typeof module !== 'undefined' && require.main === module) {
  runFeedHubTests(require('fs').readFileSync(require('path').join(__dirname, '../feed-hub.js'), 'utf8'))
    .then(console.log).catch(error => { console.error(error); process.exitCode = 1; });
}
