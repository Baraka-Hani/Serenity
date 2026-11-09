(() => {
  const $ = selector => document.querySelector(selector);
  const status = $('#accountStatus');
  const identityAuthLink = $('#identityAuthLink');
  const themeForm = $('#themeForm');
  const profileForm = $('#profileForm');
  const drawer = $('#settingsDrawer');
  const backdrop = $('#settingsBackdrop');
  const autoplayToggle = $('#autoplayPreference');
  const preferenceKey = 'serenity-autoplay';
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const viewers = new Map();
  let signedInUser = null;
  let activeViewer = null;
  let returnFocus = null;
  let autoplayOn = true;
  const savedPosts = [];
  let savedOffset = 0;
  let savedHasMore = false;
  let savedLoading = false;

  const themes = {
    serenity: { accent: '#ff6945', soft: '#bcd7b1', paper: '#f2eee4', ink: '#171713', energy: 62 },
    coast: { accent: '#267b83', soft: '#a9d2c5', paper: '#e7f0e8', ink: '#142b30', energy: 58 },
    night: { accent: '#c5a3ff', soft: '#545979', paper: '#181a27', ink: '#f3efff', energy: 70 }
  };

  function showTheme(theme) {
    for (const name of ['accent', 'soft', 'paper', 'ink']) themeForm.elements.namedItem(name).value = theme[name];
  }

  function readThemeForm() {
    return {
      accent: themeForm.elements.namedItem('accent').value,
      soft: themeForm.elements.namedItem('soft').value,
      paper: themeForm.elements.namedItem('paper').value,
      ink: themeForm.elements.namedItem('ink').value,
      energy: window.RoamTheme.read().energy
    };
  }

  function autoplayEnabled() {
    return autoplayOn && !reducedMotion.matches;
  }

  function updatePlayback() {
    for (const viewer of viewers.values()) {
      if (viewer === activeViewer && autoplayEnabled() && !document.hidden) {
        viewer.video.play().catch(() => {
          $('#preferenceStatus').textContent = 'Autoplay was blocked by your browser. Use the video controls to start playback.';
        });
      } else {
        viewer.video.pause();
      }
    }
  }

  function formatDate(timestamp) {
    if (!timestamp) return '';
    return new Intl.DateTimeFormat(undefined, { month: 'short', year: 'numeric' }).format(new Date(timestamp * 1000));
  }

  function renderTrip(trip, onUnsave = null) {
    const article = document.createElement('article');
    article.className = 'account-trip';
    const posts = trip.posts || [];
    let index = 0;
    const media = document.createElement('div');
    media.className = 'account-trip__media';
    const video = document.createElement('video');
    video.controls = true;
    video.muted = true;
    video.playsInline = true;
    video.preload = 'metadata';
    video.setAttribute('aria-label', `${trip.name} video`);
    const previous = document.createElement('button');
    previous.type = 'button';
    previous.className = 'trip-video-nav trip-video-nav--previous';
    previous.textContent = '‹';
    previous.setAttribute('aria-label', `Previous video in ${trip.name}`);
    const next = document.createElement('button');
    next.type = 'button';
    next.className = 'trip-video-nav trip-video-nav--next';
    next.textContent = '›';
    next.setAttribute('aria-label', `Next video in ${trip.name}`);
    const counter = document.createElement('span');
    counter.className = 'trip-video-counter';
    const caption = document.createElement('p');
    caption.className = 'account-trip__caption';
    media.append(video, previous, next, counter);
    const detail = document.createElement('div');
    detail.className = 'account-trip__detail';
    const title = document.createElement('h3');
    title.textContent = trip.name;
    const destination = document.createElement('p');
    destination.className = 'account-trip__destination';
    destination.textContent = trip.destination;
    const date = document.createElement('p');
    date.className = 'account-trip__date';
    date.textContent = `PUBLISHED ${formatDate(trip.published_at)}`;
    detail.append(title, destination, caption, date);
    if (onUnsave) {
      const unsave = document.createElement('button');
      unsave.type = 'button';
      unsave.className = 'account-trip__unsave';
      unsave.textContent = 'Remove from saved';
      unsave.addEventListener('click', () => onUnsave(posts[index], unsave));
      detail.append(unsave);
    }
    article.append(media, detail);

    const viewer = { video, posts };
    viewers.set(article, viewer);
    function selectVideo(nextIndex) {
      if (!posts.length) return;
      index = (nextIndex + posts.length) % posts.length;
      const post = posts[index];
      video.src = window.RoamApp.postVideoUrl(post.id);
      video.setAttribute('aria-label', `${post.clip_name || 'Published video'} from ${trip.name}`);
      caption.textContent = post.caption || '';
      counter.textContent = `${index + 1} / ${posts.length}`;
      previous.disabled = posts.length < 2;
      next.disabled = posts.length < 2;
      video.load();
      updatePlayback();
    }
    previous.addEventListener('click', () => selectVideo(index - 1));
    next.addEventListener('click', () => selectVideo(index + 1));
    video.addEventListener('ended', () => {
      if (posts.length > 1) selectVideo(index + 1);
    });

    let touchStart = null;
    media.addEventListener('touchstart', event => {
      const touch = event.changedTouches[0];
      touchStart = [touch.clientX, touch.clientY];
    }, { passive: true });
    media.addEventListener('touchend', event => {
      if (!touchStart) return;
      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - touchStart[0];
      const deltaY = touch.clientY - touchStart[1];
      touchStart = null;
      if (Math.abs(deltaX) > 55 && Math.abs(deltaX) > Math.abs(deltaY) * 1.3) {
        selectVideo(index + (deltaX < 0 ? 1 : -1));
      }
    }, { passive: true });
    selectVideo(0);
    return article;
  }

  const galleryObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const viewer = viewers.get(entry.target);
      if (entry.isIntersecting && entry.intersectionRatio >= .5) activeViewer = viewer;
      else if (activeViewer === viewer) activeViewer = null;
    }
    updatePlayback();
  }, { threshold: [0, .5] });
  document.addEventListener('visibilitychange', updatePlayback);

  function renderTrips(profile) {
    const gallery = $('#accountTrips');
    clearGallery(gallery);
    gallery.replaceChildren();
    if (!profile.trips.length) {
      const empty = document.createElement('p');
      empty.className = 'account-empty';
      empty.textContent = 'Your public trips will appear here after you publish videos in Clip Studio.';
      gallery.append(empty);
      return;
    }
    const cards = profile.trips.map(renderTrip);
    gallery.append(...cards);
    cards.forEach(card => galleryObserver.observe(card));
  }

  function clearGallery(gallery) {
    for (const card of gallery.children) {
      galleryObserver.unobserve(card);
      const viewer = viewers.get(card);
      viewer?.video.pause();
      viewers.delete(card);
      if (activeViewer === viewer) activeViewer = null;
    }
  }

  function renderSavedTrips() {
    const gallery = $('#savedTrips');
    clearGallery(gallery);
    gallery.replaceChildren();
    $('#savedVideoCount').textContent = String(savedPosts.length);
    const trips = new Map();
    for (const post of savedPosts) {
      const tripId = String(post.feed_id);
      let trip = trips.get(tripId);
      if (!trip) {
        trip = {
          id: tripId,
          name: `${post.feed_name || 'Published trip'} · ${post.author_name}`,
          destination: post.destination,
          published_at: post.created_at,
          posts: []
        };
        trips.set(tripId, trip);
      }
      trip.posts.push(post);
      trip.published_at = Math.max(trip.published_at, post.created_at);
    }
    if (!savedPosts.length) {
      const empty = document.createElement('p');
      empty.className = 'account-empty';
      empty.textContent = signedInUser
        ? 'Videos you save from the Home feed will be collected here.'
        : 'Sign in to save videos and see them here.';
      gallery.append(empty);
      return;
    }
    const cards = [...trips.values()].map(trip => renderTrip(trip, async (post, button) => {
      button.disabled = true;
      try {
        const result = await window.RoamApp.togglePostAction(post.id, 'save');
        if (result.active) {
          $('#savedStatus').textContent = 'This video is still saved.';
          return;
        }
        const index = savedPosts.findIndex(saved => saved.id === post.id);
        if (index >= 0) savedPosts.splice(index, 1);
        $('#savedStatus').textContent = 'Video removed from your saved list.';
        renderSavedTrips();
      } catch (error) {
        $('#savedStatus').textContent = `Could not remove this saved video: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    }));
    gallery.append(...cards);
    cards.forEach(card => galleryObserver.observe(card));
  }

  async function loadSavedVideos(append = false) {
    if (!signedInUser || savedLoading || (append && !savedHasMore)) return;
    savedLoading = true;
    $('#savedMore').disabled = true;
    if (!append) $('#savedStatus').textContent = 'Loading saved videos…';
    try {
      const result = await window.RoamApp.posts({ sort: 'saved', offset: savedOffset });
      savedPosts.push(...result.posts);
      savedOffset += result.posts.length;
      savedHasMore = result.has_more;
      $('#savedMore').hidden = !savedHasMore;
      $('#savedStatus').textContent = '';
      renderSavedTrips();
    } catch (error) {
      $('#savedStatus').textContent = `Could not load saved videos: ${error.message}`;
    } finally {
      savedLoading = false;
      $('#savedMore').disabled = false;
    }
  }

  $('#savedMore').addEventListener('click', () => loadSavedVideos(true));

  function setDrawerOpen(open) {
    if (open) {
      returnFocus = document.activeElement;
      drawer.hidden = false;
      backdrop.hidden = false;
      $('#accountMain').inert = true;
      const toolbar = document.querySelector('.liquid-toolbar');
      if (toolbar) toolbar.inert = true;
      $('#openSettings').setAttribute('aria-expanded', 'true');
      $('#closeSettings').focus();
    } else {
      drawer.hidden = true;
      backdrop.hidden = true;
      $('#accountMain').inert = false;
      const toolbar = document.querySelector('.liquid-toolbar');
      if (toolbar) toolbar.inert = false;
      $('#openSettings').setAttribute('aria-expanded', 'false');
      returnFocus?.focus();
    }
  }

  $('#openSettings').addEventListener('click', () => setDrawerOpen(true));
  $('#closeSettings').addEventListener('click', () => setDrawerOpen(false));
  backdrop.addEventListener('click', () => setDrawerOpen(false));
  drawer.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      setDrawerOpen(false);
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...drawer.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled])')]
      .filter(element => !element.hidden);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  document.querySelectorAll('[data-theme-preset]').forEach(button => {
    const theme = themes[button.dataset.themePreset];
    button.addEventListener('click', () => {
      showTheme(theme);
      window.RoamTheme.apply(theme);
      $('#themeStatus').textContent = `${button.querySelector('span').textContent} palette preview. Save to keep it.`;
    });
  });
  themeForm.addEventListener('input', () => {
    window.RoamTheme.apply(readThemeForm());
    $('#themeStatus').textContent = 'Palette preview. Save to keep these colours.';
  });
  themeForm.addEventListener('submit', async event => {
    event.preventDefault();
    const theme = readThemeForm();
    const save = themeForm.querySelector('.save-theme');
    save.disabled = true;
    try {
      if (signedInUser) {
        await window.RoamApp.saveTheme(theme);
        window.RoamTheme.apply(theme, true);
        $('#themeStatus').textContent = 'Colour scheme saved to your account and applied across Serenity.';
      } else {
        window.RoamTheme.apply(theme, true);
        $('#themeStatus').textContent = 'Colour scheme saved on this device. Sign in to sync it to your account.';
      }
    } catch (error) {
      $('#themeStatus').textContent = `Could not save your account colour scheme: ${error.message}`;
    } finally {
      save.disabled = false;
    }
  });

  try {
    autoplayOn = localStorage.getItem(preferenceKey) !== 'false';
  } catch (error) {
    console.warn('Could not read the video autoplay preference:', error);
    $('#preferenceStatus').textContent = `Could not read this preference: ${error.message}`;
  }
  autoplayToggle.checked = autoplayOn;
  if (autoplayOn && reducedMotion.matches) {
    $('#preferenceStatus').textContent = 'Reduced motion is enabled, so videos will not autoplay.';
  }
  autoplayToggle.addEventListener('change', () => {
    try {
      localStorage.setItem(preferenceKey, String(autoplayToggle.checked));
      autoplayOn = autoplayToggle.checked;
      $('#preferenceStatus').textContent = autoplayToggle.checked
        ? reducedMotion.matches ? 'Reduced motion is enabled, so videos will not autoplay.' : 'Autoplay is on for this device.'
        : 'Autoplay is off. Start videos with their playback controls.';
      updatePlayback();
    } catch (error) {
      autoplayToggle.checked = autoplayOn;
      $('#preferenceStatus').textContent = `Could not save this preference: ${error.message}`;
    }
  });
  reducedMotion.addEventListener('change', () => {
    if (autoplayOn) {
      $('#preferenceStatus').textContent = reducedMotion.matches
        ? 'Reduced motion is enabled, so videos will not autoplay.'
        : 'Autoplay is on for this device.';
      updatePlayback();
    }
  });

  async function loadAccount() {
    try {
      signedInUser = await window.RoamApp.me();
      identityAuthLink.hidden = Boolean(signedInUser);
      $('#signoutButton').hidden = !signedInUser;
      if (!signedInUser) {
        $('#profileName').textContent = 'Your account';
        $('#profileUsername').textContent = 'Sign in to see your profile';
        status.textContent = 'Sign in to view your published trips and manage your profile.';
      } else {
        $('#profileName').textContent = signedInUser.name;
        $('#profileUsername').textContent = `@${signedInUser.username}`;
        $('#profileBio').textContent = signedInUser.bio || 'Sharing the places and moments that made the journey.';
        $('#profileAvatar').textContent = signedInUser.name.trim().charAt(0).toUpperCase();
        $('#profileSettings').hidden = false;
        profileForm.elements.namedItem('name').value = signedInUser.name;
        profileForm.elements.namedItem('username').value = signedInUser.username;
        profileForm.elements.namedItem('bio').value = signedInUser.bio || '';
        $('#accountPublicId').textContent = signedInUser.public_id;
        const profileUrl = `profile.html?id=${encodeURIComponent(signedInUser.public_id)}`;
        $('#publicProfileLink').href = profileUrl;
        $('#publicProfileSettingsLink').href = profileUrl;
        $('#publicProfileLink').hidden = false;
        const result = await window.RoamApp.publicProfile(signedInUser.public_id);
        const profile = result.profile;
        $('#tripCount').textContent = profile.trip_count;
        $('#videoCount').textContent = profile.video_count;
        renderTrips(profile);
        await loadSavedVideos();
        status.textContent = result.stale
          ? 'Showing your saved published trips; Serenity could not refresh them right now.'
          : '';
      }
      if (!signedInUser) renderSavedTrips();
      const savedTheme = signedInUser ? await window.RoamApp.theme() : null;
      const theme = savedTheme?.theme || window.RoamTheme.read();
      window.RoamTheme.apply(theme, true);
      showTheme(theme);
    } catch (error) {
      status.textContent = `Could not load your account: ${error.message}`;
    }
  }

  profileForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!signedInUser) return;
    const save = profileForm.querySelector('[type="submit"]');
    const values = Object.fromEntries(new FormData(profileForm));
    save.disabled = true;
    $('#profileStatus').textContent = 'Saving profile…';
    try {
      signedInUser = await window.RoamApp.saveProfile(values);
      window.RoamApp.invalidateProfileCache();
      $('#profileName').textContent = signedInUser.name;
      $('#profileUsername').textContent = `@${signedInUser.username}`;
      $('#profileBio').textContent = signedInUser.bio || 'Sharing the places and moments that made the journey.';
      $('#profileAvatar').textContent = signedInUser.name.trim().charAt(0).toUpperCase();
      $('#profileStatus').textContent = `Profile saved. Share your @${signedInUser.username} profile using its public profile link.`;
    } catch (error) {
      $('#profileStatus').textContent = `Could not save your profile: ${error.message}`;
    } finally {
      save.disabled = false;
    }
  });

  $('#signoutButton').addEventListener('click', async event => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await window.RoamApp.logout();
      location.assign('auth.html');
    } catch (error) {
      status.textContent = `Could not sign out: ${error.message}`;
      button.disabled = false;
    }
  });

  loadAccount();
})();
