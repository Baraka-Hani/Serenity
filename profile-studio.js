/* Clip Studio on the Profile: every trip and video the owner has, as tiles, filterable
   by Live (on Feed), Private (only the owner) or All. Owner-only data; nothing here is
   shown on the public profile page. Creating trips and uploading stay in Clip Studio. */
(() => {
  const FILTERS = [
    { key: 'all', label: 'All', hint: 'Every video you have saved' },
    { key: 'live', label: 'Live', hint: 'On Feed, visible to everyone' },
    { key: 'private', label: 'Private', hint: 'Only you can see these' }
  ];
  const isLive = clip => Boolean(clip.is_published);
  const matches = (clip, filter) => filter === 'all' || (filter === 'live') === isLive(clip);

  // Pure grouping so the filter logic can be tested without a browser.
  function group(feeds, clips, details = {}) {
    const trips = Object.entries(feeds).map(([id, name]) => ({
      id, name, details: details[id] || {}, clips: clips.filter(clip => String(clip.feed_id) === id)
    })).filter(trip => !(/^Feed \d+$/.test(trip.name) && !trip.clips.length && !trip.details.destination && !trip.details.summary));
    const unassigned = clips.filter(clip => clip.feed_id == null);
    const live = clips.filter(isLive).length;
    return { trips, unassigned, counts: { all: clips.length, live, private: clips.length - live, trips: trips.length } };
  }
  function visible(trip, filter) {
    const shown = trip.clips.filter(clip => matches(clip, filter));
    // An empty trip still belongs under All and Private (it has nothing on Feed yet).
    return shown.length || (!trip.clips.length && filter !== 'live') ? shown : null;
  }

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  // Only fetch video metadata once a tile is near the screen; dozens of tiles must not
  // compete for the browser's few connections.
  const lazy = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting) { entry.target.preload = 'metadata'; lazy.unobserve(entry.target); }
  }, { rootMargin: '300px 0px' }) : null;

  function tileMedia(title, clips, onSelect) {
    const frame = el('div', 'profile-studio__media');
    if (!clips.length) {
      frame.append(el('p', 'profile-studio__empty-media', 'No videos yet. Add some in Clip Studio.'));
      return { frame, video: null };
    }
    const video = el('video');
    video.controls = true; video.playsInline = true; video.preload = 'none';
    const chip = el('span', 'profile-studio__clip-state');
    const counter = el('span', 'profile-studio__counter');
    const previous = el('button', 'profile-studio__arrow profile-studio__arrow--previous', '‹');
    const next = el('button', 'profile-studio__arrow profile-studio__arrow--next', '›');
    previous.type = next.type = 'button';
    previous.setAttribute('aria-label', `Previous video in ${title}`);
    next.setAttribute('aria-label', `Next video in ${title}`);
    previous.hidden = next.hidden = clips.length < 2;
    let index = 0;
    const show = nextIndex => {
      index = (nextIndex + clips.length) % clips.length;
      const clip = clips[index];
      video.pause();
      video.src = window.RoamApp.videoUrl(clip.id);
      video.setAttribute('aria-label', `${clip.original_name} in ${title}`);
      chip.textContent = isLive(clip) ? '● Live' : '◒ Private';
      chip.classList.toggle('is-live', isLive(clip));
      counter.textContent = `${index + 1} / ${clips.length}`;
      onSelect(clip);
    };
    previous.onclick = () => show(index - 1);
    next.onclick = () => show(index + 1);
    show(0);
    lazy?.observe(video);
    if (!lazy) video.preload = 'metadata';
    frame.append(video, chip, counter, previous, next);
    return { frame, video };
  }

  function tripTile(trip, shown, refresh) {
    const tile = el('article', 'profile-studio__tile');
    tile.dataset.feed = trip.id;
    const publication = window.SerenityPublication.create({
      id: trip.id, name: trip.name, clips: trip.clips, location: trip.details.location,
      onLocate: () => location.assign('studio.html'),
      onChanged: message => refresh(message)
    });
    const { frame } = tileMedia(trip.name, shown, clip => publication.select(clip));
    frame.append(publication.badge);
    const head = el('div', 'profile-studio__head');
    const titles = el('div');
    titles.append(el('h3', '', trip.name), el('p', 'profile-studio__destination', trip.details.destination || 'No destination yet'));
    const links = el('div', 'profile-studio__links');
    const page = el('a', '', 'Trip page ↗'); page.href = `feed.html?feed=${encodeURIComponent(trip.id)}`;
    const edit = el('a', '', 'Edit in Clip Studio ↗'); edit.href = 'studio.html';
    links.append(page, edit);
    head.append(titles, links);
    tile.append(frame, head, publication.panel);
    return tile;
  }

  function waitingTile(clips) {
    const tile = el('article', 'profile-studio__tile profile-studio__tile--waiting');
    const { frame } = tileMedia('Videos waiting for a trip', clips, () => {});
    const head = el('div', 'profile-studio__head');
    const titles = el('div');
    titles.append(el('h3', '', 'Waiting for a trip'), el('p', 'profile-studio__destination', `${clips.length} ${clips.length === 1 ? 'video' : 'videos'} not in a trip yet`));
    const edit = el('a', '', 'Add to a trip in Clip Studio ↗'); edit.href = 'studio.html';
    const links = el('div', 'profile-studio__links'); links.append(edit);
    head.append(titles, links);
    tile.append(frame, head);
    return tile;
  }

  function mount(root, { onCounts = () => {}, initialFilter } = {}) {
    let filter = FILTERS.some(item => item.key === initialFilter) ? initialFilter : 'all';
    let data = null;
    const tabs = el('div', 'profile-studio__filters');
    tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', 'Show videos by visibility');
    const grid = el('div', 'profile-studio__grid');
    grid.id = 'profileStudioGrid';
    grid.setAttribute('role', 'tabpanel');
    const status = el('p', 'account-status profile-studio__status');
    status.setAttribute('role', 'status');
    const buttons = FILTERS.map(item => {
      const button = el('button', 'profile-studio__filter');
      button.type = 'button';
      button.dataset.filter = item.key;
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', grid.id);
      button.title = item.hint;
      button.onclick = () => select(item.key);
      button.onkeydown = event => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const position = (FILTERS.findIndex(entry => entry.key === filter) + (event.key === 'ArrowRight' ? 1 : -1) + FILTERS.length) % FILTERS.length;
        select(FILTERS[position].key); buttons[position].focus();
      };
      tabs.append(button);
      return button;
    });
    root.replaceChildren(tabs, status, grid);

    function labelTabs() {
      FILTERS.forEach((item, index) => {
        const button = buttons[index];
        button.replaceChildren(el('span', '', item.label), el('strong', '', String(data ? data.counts[item.key] : '–')));
        button.setAttribute('aria-selected', String(item.key === filter));
        button.tabIndex = item.key === filter ? 0 : -1;
        button.setAttribute('aria-label', `${item.label}: ${data ? data.counts[item.key] : 'loading'} videos. ${item.hint}.`);
      });
    }
    function render() {
      labelTabs();
      grid.querySelectorAll('video').forEach(video => { video.pause(); lazy?.unobserve(video); });
      const tiles = [];
      for (const trip of data.trips) {
        const shown = visible(trip, filter);
        if (shown) tiles.push(tripTile(trip, shown, refresh));
      }
      const waiting = data.unassigned.filter(clip => matches(clip, filter));
      if (waiting.length) tiles.push(waitingTile(waiting));
      if (!tiles.length) {
        const empty = el('div', 'account-empty');
        empty.append(!data.counts.all ? 'Your trips and videos will appear here. ' : filter === 'live'
          ? 'Nothing is live yet. Post a trip to Feed from any tile, or '
          : filter === 'private' ? 'Every video you have is live on Feed. ' : 'Your trips and videos will appear here. ');
        const link = el('a', '', 'open Clip Studio ↗'); link.href = 'studio.html';
        empty.append(link);
        tiles.push(empty);
      }
      grid.replaceChildren(...tiles);
    }
    function select(key) {
      filter = key;
      try { sessionStorage.setItem('serenity-profile-studio-filter', key); } catch { /* per-tab convenience only */ }
      if (data) render(); else labelTabs();
    }
    async function refresh(message = '') {
      status.textContent = data ? 'Updating your videos…' : 'Loading your videos…';
      try {
        const [feeds, clips] = await Promise.all([window.RoamApp.feeds(), window.RoamApp.clips()]);
        const ids = Object.keys(feeds);
        const details = await Promise.all(ids.map(id => window.RoamApp.details(id).catch(() => ({}))));
        data = group(feeds, clips, Object.fromEntries(ids.map((id, index) => [id, details[index]])));
        onCounts(data.counts);
        render();
        status.textContent = message;
      } catch (error) {
        status.textContent = `Could not load your videos: ${error.message}`;
      }
    }
    try { filter = sessionStorage.getItem('serenity-profile-studio-filter') || filter; } catch { /* ignore */ }
    if (!FILTERS.some(item => item.key === filter)) filter = 'all';
    labelTabs();
    window.addEventListener('serenity:trip-updated', () => window.RoamApp.invalidateProfileCache?.());
    refresh();
    return { refresh, select, get filter() { return filter; } };
  }

  window.SerenityProfileStudio = { group, visible, matches, mount, FILTERS };
})();
