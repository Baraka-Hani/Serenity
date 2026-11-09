/* Public stories for visitors, plus saved private videos and notes for the trip owner. */
(() => {
  const params = new URLSearchParams(location.search);
  const page = location.pathname.split('/').pop() || '';
  const legacyPage = /^tile-0([1-5])\.html$/.exec(page);
  const feed = Number(params.get('feed') || legacyPage?.[1]);
  const $ = selector => document.querySelector(selector);
  const layout = $('#feedLayout');
  const studioLink = $('#tripDetailsForm').nextElementSibling;
  studioLink.href = 'app.html#feeds';
  studioLink.textContent = 'Edit this trip in Clip Studio ↗';
  $('#chatTitle').textContent = 'Private notes';
  document.querySelector('.panel.chat .panel-head small').textContent = 'ONLY YOU CAN SEE THESE';
  let user = null;
  let touchStart = null;

  function status(text) { $('#feedStatus').textContent = text; }
  function showPanel(panel) {
    layout.dataset.panel = panel;
    document.querySelectorAll('[data-open-panel]').forEach(button => button.classList.toggle('active', button.dataset.openPanel === panel));
  }
  function showClips(posts, privateClips = []) {
    const grid = $('#feedVideos'); grid.replaceChildren();
    $('#emptyVideos').hidden = posts.length + privateClips.length > 0;
    for (const post of posts) {
      const card = document.createElement('article'); card.className = 'video-card published-trip-video';
      const video = document.createElement('video'); video.src = window.RoamApp.postVideoUrl(post.id); video.controls = true; video.playsInline = true; video.preload = 'none';
      const name = document.createElement('a'); name.href = `profile.html?id=${encodeURIComponent(post.author_public_id)}`; name.textContent = `${post.destination} · ${post.author_name}`;
      card.append(video, name); grid.append(card);
      card.id = `moment-${post.id}`;
      if (!post.is_mine) {
        const ask = document.createElement('a'); ask.textContent = 'Ask the creator about this video ↗';
        ask.href = window.RoamApp.messageUrl(post.author_public_id, post.id); card.append(ask);
      }
      if (params.get('post') === post.id) requestAnimationFrame(() => { card.scrollIntoView({ block: 'center' }); video.focus({ preventScroll: true }); });
    }
    for (const clip of privateClips) {
      const card = document.createElement('article'); card.className = 'video-card published-trip-video';
      const video = document.createElement('video'); video.src = window.RoamApp.videoUrl(clip.id); video.controls = true; video.playsInline = true; video.preload = 'none';
      video.setAttribute('aria-label', `Private video: ${clip.original_name}`);
      const name = document.createElement('span'); name.textContent = `${clip.original_name} · Private, only you`;
      card.append(video, name); grid.append(card);
    }
  }
  function showNotes(notes) {
    const list = $('#feedNotes');
    list.replaceChildren();
    if (!notes.length) {
      const prompt = document.createElement('div'); prompt.className = 'bubble prompt';
      prompt.textContent = 'What made this trip yours? Save places, ideas, and details here as you go.';
      list.append(prompt);
    }
    for (const note of notes) {
      const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = note.body;
      list.append(bubble);
    }
    list.scrollTop = list.scrollHeight;
  }
  function showPrivateAccessMessage() {
    const list = $('#feedNotes');
    list.replaceChildren();
    const prompt = document.createElement('div');
    prompt.className = 'bubble prompt';
    prompt.textContent = 'Private trip notes are only visible to the signed-in account that saved them.';
    const link = document.createElement('a');
    link.href = 'auth.html?next=account';
    link.textContent = 'Sign in to your account ↗';
    prompt.append(document.createElement('br'), link);
    list.append(prompt);
    document.querySelectorAll('#noteForm textarea, #noteForm button').forEach(control => { control.disabled = true; });
  }
  function showDetails(details) {
    const form = $('#tripDetailsForm');
    for (const key of ['destination', 'summary']) {
      const field = $(`#trip-${key}`);
      field.value = details[key] || '';
      field.readOnly = true;
    }
    form.querySelector('[type="submit"]').hidden = true;
    const editLink = form.nextElementSibling;
    editLink.href = 'app.html#feeds';
    editLink.textContent = 'Edit this trip in Clip Studio ↗';
  }
  async function refresh() {
    if (!Number.isSafeInteger(feed) || feed < 1) return status('This trip link is invalid.');
    const posts = [];
    let offset = 0;
    let page;
    do {
      page = await window.RoamApp.posts({ feed, offset });
      posts.push(...page.posts);
      offset += page.posts.length;
    } while (page.has_more);
    showClips(posts);
    const publicTitle = `Trip ${feed}`;
    $('#tripName').textContent = publicTitle;
    document.title = `${publicTitle} — Serenity`;
    const names = user ? await window.RoamApp.feeds() : {};
    const isOwner = Object.hasOwn(names, String(feed));
    const publicFeed = await window.RoamApp.publicFeed(feed);
    const pinned = (await window.RoamApp.mapTrips({ trip: feed })).trips[0];
    function showDestination(place) {
      document.querySelector('.trip-visit')?.remove();
      const visit = document.createElement('section'); visit.className = 'trip-visit';
      const title = document.createElement('h3'); title.textContent = place?.label || 'Experience this place';
      const copy = document.createElement('p'); copy.textContent = place ? 'Destination chosen by the creator. Check access and local conditions before travelling.' : 'The creator has not pinned a destination yet. Explore the map to find other places you can visit.';
      const map = document.createElement('a'); map.href = place && posts.length ? `map.html?trip=${feed}` : 'map.html'; map.textContent = place && posts.length ? 'Find this trip on Map ↗' : 'Explore Map ↗';
      visit.append(title, copy, map);
      if (place) { const directions = document.createElement('a'); directions.href = window.SerenityMaps.directions(place); directions.target = '_blank'; directions.rel = 'noopener'; directions.textContent = 'Get directions in Google Maps ↗'; visit.append(directions); }
      document.querySelector('.work-body').prepend(visit);
    }
    showDestination(pinned);
    const name = names[String(feed)] || publicFeed?.name || publicTitle;
    $('#tripName').textContent = name;
    document.title = `${name} — Serenity`;
    document.querySelector('.heading .eyebrow').textContent = `Published journey / ${feed}`;
    document.querySelector('.panel.work .panel-head small').textContent = `PUBLIC STORIES · ${name.toUpperCase()}`;
    if (!user || !isOwner) {
      $('#tripDetailsForm').hidden = true;
      showPrivateAccessMessage();
      return status(!publicFeed && !posts.length
        ? 'This trip has no published videos yet, or it is unavailable.'
        : 'Published videos are public. Private trip details and notes are only available to their owner.');
    }
    document.querySelectorAll('#noteForm textarea, #noteForm button').forEach(control => { control.disabled = false; });
    const [notes, details, clips] = await Promise.all([
      window.RoamApp.notes(feed),
      window.RoamApp.details(feed),
      window.RoamApp.clips(feed)
    ]);
    const privateClips = clips.filter(clip => !clip.is_published);
    showClips(posts, privateClips);
    document.querySelector('.heading .eyebrow').textContent = `Your journey / ${feed}`;
    document.querySelector('.heading p').textContent = 'All your moments, in one trip. Private videos and notes are only visible to you; published stories can be seen by everyone.';
    document.querySelector('[data-open-panel="work"]').textContent = 'Trip videos';
    $('#workTitle').textContent = 'Your trip videos';
    document.querySelector('.panel.work .panel-head small').textContent = `${clips.length} SAVED MOMENTS`;
    document.querySelector('.work-body > p.work-note').textContent = 'Private videos stay private here. Publish selected stories from Clip Studio when you’re ready to share.';
    document.querySelector('.swipe-hint').textContent = 'Swipe to switch between your trip videos and private notes →';
    $('#emptyVideos strong').textContent = 'No videos saved to this trip yet.';
    $('#emptyVideos p').textContent = 'Add a collection in Clip Studio to start this journey.';
    showNotes(notes);
    showDetails(details);
    showDestination(details.location || pinned);
    status(`${posts.length} published · ${privateClips.length} private ${privateClips.length === 1 ? 'video' : 'videos'} in ${name}.`);
  }

  document.querySelectorAll('[data-open-panel]').forEach(button => button.onclick = () => showPanel(button.dataset.openPanel));
  layout.addEventListener('touchstart', event => { touchStart = [event.changedTouches[0].clientX, event.changedTouches[0].clientY]; }, { passive: true });
  layout.addEventListener('touchend', event => {
    if (!touchStart) return;
    const deltaX = event.changedTouches[0].clientX - touchStart[0];
    const deltaY = event.changedTouches[0].clientY - touchStart[1];
    if (Math.abs(deltaX) > 70 && Math.abs(deltaX) > Math.abs(deltaY) * 1.4) showPanel(deltaX < 0 ? 'work' : 'chat');
    touchStart = null;
  }, { passive: true });

  $('#noteForm').onsubmit = async event => {
    event.preventDefault();
    if (!user) return status('Sign in first to save trip notes.');
    const input = $('#noteInput'); const body = input.value.trim();
    if (!body) return;
    try { await window.RoamApp.addNote(feed, body); input.value = ''; showNotes(await window.RoamApp.notes(feed)); status('Note saved to this feed.'); }
    catch (error) { status(error.message); }
  };
  window.RoamApp.me().then(async account => {
    user = account;
    if (user) $('#accountLink').textContent = `${user.name} ↗`;
    await refresh();
  }).catch(() => status('The local server is unavailable. Run python3 backend/server.py.'));
})();
