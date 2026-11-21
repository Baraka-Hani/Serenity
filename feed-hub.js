/* Video navigation and public travel context. No private clip or trip data is read here. */
(() => {
  const list = document.querySelector('#postList');
  if (!list) return;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  function autoplayEnabled() {
    try {
      return !reducedMotion.matches && localStorage.getItem('serenity-autoplay') !== 'false';
    } catch (error) {
      console.warn('Could not read the video autoplay preference:', error);
      return !reducedMotion.matches;
    }
  }
  const viewers = new Map();
  let active = null;
  let soundOn = false;
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (text, className = '') => {
    const node = el('button', className, text); node.type = 'button'; return node;
  };
  // Browsers allow only ~6 connections per host. Fully buffering every card starves
  // the one on screen, which then freezes a few seconds in. Only the visible video
  // buffers fully; its neighbours fetch just enough to show a first frame.
  function preloadFor(viewer, video) {
    if (video !== viewer.video) return 'none';
    if (viewer === active) return 'auto';
    const cards = [...list.children];
    const distance = active ? Math.abs(cards.indexOf(viewer.card) - cards.indexOf(active.card)) : cards.indexOf(viewer.card);
    return distance <= 1 ? 'metadata' : 'none';
  }
  function updatePlayback() {
    for (const viewer of viewers.values()) {
      const play = viewer === active && viewer.panel === 1 && !viewer.commentsOpen && !viewer.paused &&
        !document.hidden && document.body.dataset.appView === 'home';
      viewer.videos.forEach(video => {
        video.muted = !soundOn;
        const preload = preloadFor(viewer, video);
        if (video.preload !== preload) video.preload = preload;
        if (play && video === viewer.video) {
          if (!video.paused) return;
          const attempt = video.play();
          attempt?.catch?.(error => {
            // AbortError only means a newer pause/load superseded this call; it is not a user pause.
            if (error?.name !== 'NotAllowedError' || viewer.video !== video) return;
            if (!video.muted) { soundOn = false; updatePlayback(); return; }
            viewer.paused = true;
            viewer.play.textContent = 'Play';
          });
        } else if (!video.paused) video.pause();
      });
      viewer.sound.textContent = soundOn ? 'Sound on' : 'Sound off';
      viewer.sound.setAttribute('aria-label', soundOn ? 'Mute video' : 'Enable video sound');
      viewer.sound.setAttribute('aria-pressed', String(soundOn));
    }
  }
  function updateToolbarMode() {
    const index = active ? [...list.children].indexOf(active.card) : -1;
    document.body.classList.toggle(
      'home-toolbar-icons',
      document.body.dataset.appView === 'home' && index >= 1
    );
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const viewer = viewers.get(entry.target);
      if (entry.isIntersecting && entry.intersectionRatio >= .6) active = viewer;
      else if (active === viewer) active = null;
    }
    updateToolbarMode();
    updatePlayback();
  }, { root: list, threshold: [0, .6] });
  document.addEventListener('visibilitychange', updatePlayback);

  function create(post, card, media, header, body, comments, tripPosts = [post], onSlideChange = () => {}) {
    let videos = [...media.querySelectorAll('video')];
    let index = 0;
    let video = videos[index] || videos[0];
    const slideTrack = media.querySelector('.social-post__slides');
    videos.forEach(item => { item.controls = false; item.muted = true; item.loop = true; });
    const root = el('div', 'hub-viewer');
    const navigation = el('div', 'hub-navigation');
    const tabs = el('div', 'hub-tabs');
    tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', 'Explore this video');
    const viewport = el('div', 'hub-viewport');
    viewport.tabIndex = 0;
    viewport.setAttribute('aria-label', 'Trip viewer with travel details, video, and creator trips.');
    const creator = el('section', 'hub-pane hub-context hub-creator');
    const center = el('section', 'hub-pane hub-video');
    const travel = el('section', 'hub-pane hub-context hub-travel');
    const panes = [travel, center, creator];
    const labels = ['Travel details', 'Video', 'Creator trips'];
    const tabButtons = labels.map((label, index) => {
      const tab = button(label, 'hub-tab');
      tab.id = `hub-tab-${post.id}-${index}`;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', `hub-pane-${post.id}-${index}`);
      const pane = panes[index];
      pane.id = `hub-pane-${post.id}-${index}`;
      pane.setAttribute('role', 'tabpanel');
      pane.setAttribute('aria-labelledby', tab.id);
      tab.onclick = () => select(index);
      tab.onkeydown = event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : Math.max(0, Math.min(2, viewer.panel + (event.key === 'ArrowRight' ? 1 : -1)));
        select(next); tabButtons[next].focus();
      };
      tabs.append(tab); return tab;
    });
    const search = el('form', 'hub-search');
    search.setAttribute('role', 'search');
    search.onsubmit = event => event.preventDefault();
    const searchInput = el('input', 'hub-search__input');
    searchInput.type = 'search';
    searchInput.placeholder = 'Search this feed';
    searchInput.setAttribute('aria-label', 'Search trips, destinations, and creators in Feed');
    const searchButton = button('', 'hub-search__button');
    searchButton.setAttribute('aria-label', 'Search Feed');
    searchButton.setAttribute('aria-expanded', 'false');
    searchButton.setAttribute('aria-controls', `hub-search-${post.id}`);
    searchInput.id = `hub-search-${post.id}`;
    searchButton.title = 'Search Feed';
    searchButton.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg>';
    search.append(searchInput, searchButton);
    searchButton.onclick = () => {
      const open = navigation.classList.toggle('is-search-open');
      searchButton.setAttribute('aria-expanded', String(open));
      searchButton.setAttribute('aria-label', open ? 'Close Feed search' : 'Search Feed');
      searchInput.hidden = !open;
      if (open) searchInput.focus();
      else {
        searchInput.value = '';
        filterPosts();
      }
    };
    searchInput.hidden = true;
    function filterPosts() {
      const query = searchInput.value.trim().toLocaleLowerCase();
      for (const item of list.children) {
        if (!item.classList.contains('social-post')) continue;
        item.hidden = Boolean(query) && !item.textContent.toLocaleLowerCase().includes(query);
      }
    }
    searchInput.addEventListener('input', filterPosts);
    searchInput.addEventListener('keydown', event => {
      if (event.key === 'Escape') searchButton.click();
    });
    navigation.append(tabs, search);
    const controls = el('div', 'hub-playback');
    const play = button('Play', 'hub-glass');
    const sound = button('Sound off', 'hub-glass');
    sound.setAttribute('aria-label', 'Enable video sound');
    controls.append(play, sound);
    const carouselControls = el('div', 'hub-carousel-controls');
    const previous = button('‹', 'hub-carousel-arrow');
    const counter = el('span', 'hub-carousel-counter');
    const next = button('›', 'hub-carousel-arrow');
    previous.setAttribute('aria-label', 'Previous trip video');
    next.setAttribute('aria-label', 'Next trip video');
    carouselControls.append(previous, counter, next);
    const playCenter = button('▶', 'hub-play-center');
    playCenter.setAttribute('aria-label', 'Play trip video');
    const progress = el('input', 'hub-progress');
    progress.type = 'range'; progress.min = '0'; progress.max = '100'; progress.step = 'any'; progress.value = '0';
    progress.setAttribute('aria-label', 'Video progress');
    const buffering = el('span', 'hub-buffering');
    buffering.setAttribute('aria-hidden', 'true');
    // The bar follows the frame actually on screen (requestVideoFrameCallback), so it
    // stops whenever the picture stops instead of running ahead of a frozen video.
    const frameClock = typeof performance !== 'undefined' ? () => performance.now() : () => Date.now();
    let scrubbing = false, seekTarget = null, lastFrame = { at: 0, media: 0 }, stallRecoveries = 0;
    function showProgress(time = video.currentTime) {
      if (scrubbing) return;
      const duration = video.duration;
      progress.value = Number.isFinite(duration) && duration > 0 ? String(Math.min(100, Math.max(0, time / duration * 100))) : '0';
      progress.setAttribute('aria-valuetext', Number.isFinite(duration) ? `${Math.floor(time)} of ${Math.floor(duration)} seconds` : 'Loading');
    }
    function setBuffering(item, value) { if (item === video) media.classList.toggle('is-buffering', value); }
    function watchFrames(item) {
      if (item._serenityFrameLoop) return;
      item._serenityFrameLoop = true;
      const tick = (now, metadata) => {
        if (item.paused || item.ended) { item._serenityFrameLoop = false; return; }
        if (metadata) lastFrame = { at: frameClock(), media: metadata.mediaTime, item };
        if (item === video) showProgress(metadata ? metadata.mediaTime : item.currentTime);
        if (item.requestVideoFrameCallback) item.requestVideoFrameCallback(tick);
        else requestAnimationFrame(tick);
      };
      if (item.requestVideoFrameCallback) item.requestVideoFrameCallback(tick);
      else requestAnimationFrame(tick);
    }
    function seekTo(fraction, precise) {
      if (!Number.isFinite(video.duration) || !video.duration) return;
      const target = video.duration * fraction;
      // Dragging fires many inputs; queue the latest instead of stacking seeks, which stutters.
      if (video.seeking && !precise) { seekTarget = target; return; }
      seekTarget = null;
      if (!precise && typeof video.fastSeek === 'function') video.fastSeek(target);
      else video.currentTime = target;
    }
    progress.addEventListener('pointerdown', () => { scrubbing = true; });
    progress.oninput = () => { scrubbing = true; seekTo(Number(progress.value) / 100, false); };
    progress.onchange = () => { seekTo(Number(progress.value) / 100, true); scrubbing = false; };
    progress.addEventListener('pointerup', () => { scrubbing = false; });
    function bindVideoEvents(item) {
      item.addEventListener('timeupdate', () => {
        // Fallback for paused/seeking states; while frames render, watchFrames drives the bar.
        if (item === video && (item.paused || !item._serenityFrameLoop)) showProgress();
      });
      for (const type of ['loadedmetadata', 'durationchange', 'emptied']) item.addEventListener(type, () => { if (item === video) showProgress(); });
      item.addEventListener('seeked', () => {
        if (item !== video) return;
        if (seekTarget !== null) { const target = seekTarget; seekTarget = null; item.currentTime = target; return; }
        lastFrame = { at: frameClock(), media: item.currentTime, item };
        showProgress();
      });
      item.addEventListener('waiting', () => setBuffering(item, true));
      item.addEventListener('stalled', () => setBuffering(item, !item.paused && item.readyState < 3));
      for (const type of ['playing', 'canplay', 'pause', 'seeked', 'error']) item.addEventListener(type, () => setBuffering(item, false));
      item.addEventListener('playing', () => { lastFrame = { at: frameClock(), media: item.currentTime, item }; watchFrames(item); });
      item.addEventListener('play', () => {
        if (item === video) { play.textContent = 'Pause'; playCenter.textContent = 'Ⅱ'; playCenter.setAttribute('aria-label', 'Pause trip video'); media.classList.add('is-playing'); }
      });
      item.addEventListener('pause', () => {
        if (item === video) { play.textContent = 'Play'; playCenter.textContent = '▶'; playCenter.setAttribute('aria-label', 'Play trip video'); media.classList.remove('is-playing'); showProgress(); }
      });
      item.addEventListener('error', () => {
        if (item !== video || media.querySelector('.hub-video-error')) return;
        media.append(el('p', 'hub-video-error', 'This video could not play. You can still swipe through this trip.'));
      });
      item.onclick = () => play.click();
    }
    // If the clock keeps running but no new frame has been drawn for a while, the
    // decoder is stuck (the "bar moves, picture frozen" symptom). Re-seeking to the
    // current time flushes it; repeated failures usually mean an unsupported codec.
    const stallWatch = setInterval(() => {
      const item = video;
      if (viewer !== active || !item?.requestVideoFrameCallback || item.paused || item.seeking || item.readyState < 3 || lastFrame.item !== item) return;
      if (frameClock() - lastFrame.at < 2500 || item.currentTime - lastFrame.media < 1.5) return;
      stallRecoveries += 1;
      lastFrame = { at: frameClock(), media: item.currentTime, item };
      if (stallRecoveries <= 2) { item.currentTime = item.currentTime; return; }
      if (!media.querySelector('.hub-video-error')) media.append(el('p', 'hub-video-error', 'This video is not playing smoothly in this browser. Its format may not be supported here.'));
    }, 1000);
    videos.forEach(bindVideoEvents);
    const closeComments = button('Close comments ×', 'hub-comments-close');
    closeComments.onclick = () => { body.querySelector('[aria-expanded]')?.click(); };
    comments.addEventListener('keydown', event => { if (event.key === 'Escape') { event.stopPropagation(); closeComments.click(); } });
    comments.prepend(closeComments);
    const viewer = { card, video, videos, play, sound, panel: 1, index, paused: !autoplayEnabled(), commentsOpen: false };
    function selectVideo(nextIndex, behavior = reducedMotion.matches ? 'auto' : 'smooth') {
      if (!videos.length) return;
      const previousVideo = video;
      index = (nextIndex + videos.length) % videos.length;
      video = videos[index];
      viewer.index = index;
      viewer.video = video;
      const changed = previousVideo !== video;
      slideTrack.style.transition = behavior === 'auto' ? 'none' : '';
      slideTrack.style.transform = `translateX(-${index * 100}%)`;
      counter.textContent = `${String(index + 1).padStart(2, '0')} / ${String(videos.length).padStart(2, '0')}`;
      previous.disabled = videos.length < 2;
      next.disabled = videos.length < 2;
      if (changed) {
        // Never reload the clip that is already selected (a tap, a cancelled swipe or
        // a vertical scroll used to restart it). A new clip starts from the beginning.
        if (previousVideo && !previousVideo.paused) previousVideo.pause();
        if (video.currentTime) video.currentTime = 0;
        stallRecoveries = 0; seekTarget = null;
        media.classList.remove('is-buffering');
        media.querySelector('.hub-video-error')?.remove();
      }
      showProgress();
      onSlideChange(tripPosts[index]);
      requestAnimationFrame(() => { slideTrack.style.transition = ''; });
      media.classList.toggle('is-playing', !video.paused);
      updatePlayback();
    }
    previous.onclick = () => selectVideo(index - 1);
    next.onclick = () => selectVideo(index + 1);
    play.onclick = () => { viewer.paused = !video.paused; active = viewer; updatePlayback(); };
    playCenter.onclick = play.onclick;
    sound.onclick = () => { soundOn = !soundOn; sound.setAttribute('aria-label', soundOn ? 'Mute video' : 'Enable video sound'); updatePlayback(); };
    media.append(header, body, controls, carouselControls, playCenter, buffering, progress, comments);
    // The media box clips its slides. Focusing a button inside it (Like, Save…) must
    // never scroll it: that would leave the clip strip half a slide out of place.
    media.addEventListener('scroll', () => { if (media.scrollLeft || media.scrollTop) media.scrollTo(0, 0); });
    center.append(media);
    viewport.append(...panes);
    root.append(navigation, viewport);

    let gesture = null;
    media.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('button,a,input,textarea,select')) return;
      gesture = { x: event.clientX, y: event.clientY, horizontal: false };
      event.stopPropagation();
    });
    media.addEventListener('pointermove', event => {
      if (!gesture) return;
      const dx = event.clientX - gesture.x;
      const dy = event.clientY - gesture.y;
      if (!gesture.horizontal && Math.abs(dx) > 12 && Math.abs(dx) > Math.abs(dy) * 1.2) {
        gesture.horizontal = true;
        media.setPointerCapture(event.pointerId);
      }
      if (!gesture.horizontal) return;
      event.preventDefault();
      event.stopPropagation();
      slideTrack.style.transition = 'none';
      slideTrack.style.transform = `translateX(calc(-${index * 100}% + ${dx}px))`;
    });
    function finishVideoSwipe(event) {
      if (!gesture) return;
      event.stopPropagation();
      const dx = event.clientX - gesture.x;
      const horizontal = gesture.horizontal;
      gesture = null;
      if (horizontal) selectVideo(index + (dx < -45 ? 1 : dx > 45 ? -1 : 0));
    }
    media.addEventListener('pointerup', finishVideoSwipe);
    media.addEventListener('pointercancel', () => {
      gesture = null;
      selectVideo(index, 'auto');
    });
    media.addEventListener('keydown', event => {
      if (event.target.closest('button,input,textarea,select')) return;
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault();
        event.stopPropagation();
        selectVideo(index + (event.key === 'ArrowRight' ? 1 : -1));
      } else if (event.key === ' ' && event.target.tagName !== 'INPUT') {
        event.preventDefault();
        play.click();
      }
    });
    let contextPromise;
    let loaded = null;
    function loading(pane, text) { pane.replaceChildren(el('p', 'hub-panel-eyebrow', text), el('p', 'hub-panel-status', 'Loading this trip…')); }
    loading(travel, 'Explore the destination'); loading(creator, 'From the same creator');
    async function loadContext() {
      const id = (tripPosts[index] || post).id;
      if (loaded === id) return;
      if (contextPromise?.id === id) return contextPromise.promise;
      loading(travel, 'Explore the destination'); loading(creator, 'From the same creator');
      const promise = window.RoamApp.postContext(id).then(context => {
        if (!root.isConnected || (tripPosts[index] || post).id !== id) return;
        renderTravel(context); renderCreator(context); loaded = id;
      }).catch(error => {
        if ((tripPosts[index] || post).id !== id) return;
        for (const pane of [creator, travel]) {
          const retry = button('Try again', 'hub-primary');
          retry.onclick = () => { contextPromise = null; loadContext(); };
          pane.replaceChildren(el('p', 'hub-panel-status', error.message), retry);
        }
      }).finally(() => { if (contextPromise?.id === id) contextPromise = null; });
      contextPromise = { id, promise };
      return promise;
    }
    function backButton() { const back = button('Back to video', 'hub-back'); back.onclick = () => { select(1); tabButtons[1].focus(); }; return back; }
    function section(title, text) {
      const block = el('section', 'hub-info-card');
      block.append(el('h3', '', title), el('p', '', text)); return block;
    }
    function renderTravel(context) {
      const info = context.travel;
      const location = el('div', 'hub-location');
      location.append(el('span', 'hub-panel-eyebrow', 'Go where this was filmed'), el('h2', '', info.location?.label || info.destination), el('p', 'hub-location-source', !info.location ? 'This trip has no destination pin yet' : info.location.source === 'video' ? 'Approximate spot from the videos’ location data · Check the exact place before travelling' : 'Pin chosen by the creator · Check the exact place before travelling'));
      const summary = section('Their story', info.summary);
      const visit = section('Experience this place', info.location ? 'Start from the creator’s destination pin. Check access, opening hours, and local conditions before you go.' : 'Ask the creator to pin the destination, or explore other published places on the map.');
      const mapLink = el('a', 'hub-profile-link', info.location ? 'Find this trip on Map ↗' : 'Explore the travel map ↗'); mapLink.href = info.location ? `map.html?trip=${info.feed_id}` : 'map.html'; visit.append(mapLink);
      if (info.location) { const directions = el('a', 'hub-profile-link', 'Get directions in Google Maps ↗'); directions.href = window.SerenityMaps.directions(info.location); directions.target = '_blank'; directions.rel = 'noopener'; visit.append(directions); }
      const question = button('Ask the creator a question', 'hub-primary');
      question.hidden = Boolean((tripPosts[index] || post).is_mine);
      question.onclick = () => { location.assign(window.RoamApp.messageUrl(context.creator.public_id, context.post_id)); };
      const games = el('a', 'hub-profile-link', '🎮  Open games in Engage ↗');
      games.href = `engage.html?post=${encodeURIComponent((tripPosts[index] || post).id)}`;
      visit.append(games);
      travel.replaceChildren(backButton(), location, summary, visit, question);
    }
    function renderCreator(context) {
      const profile = context.creator;
      const heading = el('div', 'hub-location');
      heading.append(el('span', 'hub-panel-eyebrow', 'Keep exploring with'), el('h2', '', profile.name), el('p', '', `@${profile.username}`));
      const profileLink = el('a', 'hub-profile-link', 'View public profile ↗');
      profileLink.href = `profile.html?id=${encodeURIComponent(profile.public_id)}`;
      const related = el('div', 'hub-related');
      for (const trip of context.related_trips) {
        const link = el('a', 'hub-related-trip');
        link.href = `feed.html?feed=${encodeURIComponent(trip.id)}`;
        const preview = el('video', 'hub-related-preview');
        preview.src = window.RoamApp.postVideoUrl(trip.preview_post_id);
        preview.muted = true; preview.playsInline = true; preview.preload = 'metadata';
        preview.setAttribute('aria-hidden', 'true'); preview.tabIndex = -1;
        const copy = el('div', 'hub-related-copy');
        copy.append(el('span', 'hub-panel-eyebrow', trip.same_destination ? 'Same destination' : 'More from this creator'), el('h3', '', trip.name), el('p', '', trip.destination), el('small', '', `${trip.video_count} published ${trip.video_count === 1 ? 'video' : 'videos'} · Open trip ↗`));
        link.append(preview, copy); related.append(link);
      }
      if (!context.related_trips.length) related.append(section('The journey starts here', 'This creator hasn’t published any other trips before this video yet. Their future published trips will appear on their profile.'));
      creator.replaceChildren(backButton(), heading, profileLink, el('p', 'hub-panel-status', 'Other published trips, with the same destination shown first.'), related);
    }

    function select(index, behavior = reducedMotion.matches ? 'auto' : 'smooth') {
      viewer.panel = index;
      panes.forEach((pane, i) => { pane.inert = i !== index; pane.setAttribute('aria-hidden', String(i !== index)); });
      tabButtons.forEach((tab, i) => { tab.setAttribute('aria-selected', String(i === index)); tab.tabIndex = i === index ? 0 : -1; });
      viewport.scrollTo({ left: viewport.clientWidth * index, behavior });
      if (index !== 1) loadContext();
      updatePlayback();
    }
    let start = null;
    let dragged = false;
    viewport.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('button,a,input,textarea,select')) return;
      start = { x: event.clientX, y: event.clientY, left: viewer.panel * viewport.clientWidth, id: event.pointerId, horizontal: false };
      dragged = false;
    });
    viewport.addEventListener('pointermove', event => {
      if (!start) return;
      const dx = event.clientX - start.x, dy = event.clientY - start.y;
      if (!start.horizontal) {
        if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) { start = null; return; }
        if (Math.abs(dx) < 12 || Math.abs(dx) < Math.abs(dy) * 1.25) return;
        start.horizontal = true; viewport.classList.add('is-dragging'); viewport.setPointerCapture(event.pointerId);
      }
      event.preventDefault(); dragged = true;
      viewport.scrollLeft = start.left - dx;
    });
    function endGesture(event) {
      if (!start) return;
      const dx = event.clientX - start.x;
      const next = start.horizontal && Math.abs(dx) > Math.min(80, viewport.clientWidth * .18) ? viewer.panel + (dx < 0 ? 1 : -1) : viewer.panel;
      start = null;
      viewport.classList.remove('is-dragging');
      select(Math.max(0, Math.min(2, next)));
    }
    viewport.addEventListener('pointerup', endGesture);
    viewport.addEventListener('pointercancel', () => { start = null; viewport.classList.remove('is-dragging'); select(viewer.panel); });
    viewport.addEventListener('click', event => { if (dragged) { event.preventDefault(); event.stopPropagation(); dragged = false; } }, true);
    viewport.addEventListener('keydown', event => {
      if (event.target.closest('input,textarea,select,button,a')) return;
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'Escape') {
        event.preventDefault(); select(event.key === 'Escape' ? 1 : Math.max(0, Math.min(2, viewer.panel + (event.key === 'ArrowRight' ? 1 : -1))));
      } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault(); const next = event.key === 'ArrowDown' ? card.nextElementSibling : card.previousElementSibling;
        if (next) list.scrollBy({ top: next.getBoundingClientRect().top - list.getBoundingClientRect().top, behavior: reducedMotion.matches ? 'auto' : 'smooth' });
      } else if (event.key === ' ') { event.preventDefault(); play.click(); }
    });
    // Trackpad scrolling uses native scroll snapping; synchronize controls after it settles.
    let settle;
    viewport.addEventListener('scroll', () => {
      if (start) return;
      clearTimeout(settle);
      settle = setTimeout(() => {
        if (viewport.clientWidth) select(Math.max(0, Math.min(2, Math.round(viewport.scrollLeft / viewport.clientWidth))), 'auto');
      }, 120);
    }, { passive: true });
    const resize = new ResizeObserver(() => { if (viewport.clientWidth) select(viewer.panel, 'auto'); });
    resize.observe(viewport);
    viewers.set(card, viewer); observer.observe(card);
    requestAnimationFrame(() => { select(1, 'auto'); selectVideo(index, 'auto'); });
    // Detached <video> elements keep downloading until garbage-collected; release them.
    const release = item => { item.pause(); item.removeAttribute?.('src'); item.load?.(); };
    viewer.destroy = () => { clearTimeout(settle); clearInterval(stallWatch); resize.disconnect(); observer.unobserve(card); videos.forEach(release); if (active === viewer) active = null; viewers.delete(card); updateToolbarMode(); };
    return { root, updatePosts(posts, nextIndex) {
      tripPosts = posts;
      videos.forEach(release);
      slideTrack.replaceChildren(...posts.map((item, itemIndex) => {
        const slide = el('div', 'social-post__slide');
        slide.dataset.postId = item.id;
        const tripVideo = el('video');
        tripVideo.src = window.RoamApp.postVideoUrl(item.id);
        tripVideo.playsInline = true; tripVideo.muted = true; tripVideo.loop = true; tripVideo.preload = 'none';
        tripVideo.setAttribute('aria-label', `Trip video ${itemIndex + 1} of ${posts.length} from ${item.destination} by ${post.author_name}`);
        slide.append(tripVideo);
        return slide;
      }));
      videos = [...slideTrack.querySelectorAll('video')];
      viewer.videos = videos;
      videos.forEach(item => { item.controls = false; item.muted = true; item.loop = true; bindVideoEvents(item); });
      previous.disabled = posts.length < 2;
      next.disabled = posts.length < 2;
      selectVideo(nextIndex, 'auto');
    }, setCommentsOpen(open) {
      viewer.commentsOpen = open;
      for (const child of media.children) if (child !== comments) child.inert = open;
      if (open) comments.querySelector('input')?.focus();
      else body.querySelector('[aria-expanded]')?.focus();
      updatePlayback();
    }, destroy: viewer.destroy };
  }
  function reset() { for (const viewer of [...viewers.values()]) viewer.destroy(); updateToolbarMode(); }
  window.SerenityFeedHub = { create, reset };
})();
