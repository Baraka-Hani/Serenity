/* Shared page navigation; swipe horizontally on the toolbar to switch pages. */
(() => {
  const destinations = [
    { key: 'home', label: 'Home feed', icon: '⌂', href: 'app.html#home-feed' },
    { key: 'chat', label: 'Chat', icon: '◌', href: 'search.html' },
    { key: 'map', label: 'Map', icon: '⌖', href: 'map.html' },
    { key: 'trips', label: 'Clip Studio', icon: '◈', href: 'app.html#feeds' },
    { key: 'account', label: 'Account', icon: '◎', href: 'account.html' }
  ];
  document.querySelectorAll('a[href="app.html"]').forEach(link => {
    if (/home feed/i.test(link.textContent)) link.href = 'app.html#home-feed';
  });
  const toolbar = document.createElement('nav');
  toolbar.className = 'liquid-toolbar';
  toolbar.setAttribute('aria-label', 'Page toolbar');
  const meta = document.createElement('div');
  meta.className = 'liquid-toolbar__meta';
  const current = document.createElement('strong');
  current.setAttribute('aria-live', 'polite');
  const hint = document.createElement('span');
  hint.className = 'liquid-toolbar__hint';
  hint.textContent = 'Swipe toolbar to switch pages';
  meta.append(current, hint);
  const track = document.createElement('div');
  track.className = 'liquid-toolbar__track';
  for (const destination of destinations) {
    const link = document.createElement('a');
    link.className = 'liquid-toolbar__link';
    link.href = destination.href;
    link.dataset.route = destination.key;
    link.setAttribute('aria-label', destination.label);
    const icon = document.createElement('span');
    icon.className = 'liquid-toolbar__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = destination.icon;
    const label = document.createElement('span');
    label.textContent = destination.label;
    link.append(icon, label);
    track.append(link);
  }
  toolbar.append(meta, track);
  document.body.append(toolbar);
  document.body.classList.add('has-liquid-toolbar');

  function currentKey() {
    const page = location.pathname.split('/').pop() || 'test.html';
    if (page === 'auth.html') return null;
    if (page === 'account.html') return 'account';
    if (page === 'my-clips.html') return 'account';
    if (page === 'search.html') return 'chat';
    if (page === 'map.html') return 'map';
    if (page === 'feed.html' || /^tile-0[1-5]\.html$/.test(page)) return 'trips';
    if (page === 'app.html') return location.hash === '#feeds' ? 'trips' : 'home';
    return 'home';
  }
  function updateCurrent() {
    const key = currentKey();
    const index = destinations.findIndex(destination => destination.key === key);
    const destination = destinations[index];
    for (const link of track.querySelectorAll('a')) {
      const active = link.dataset.route === key;
      link.classList.toggle('is-current', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    current.textContent = `Now viewing · ${destination?.label || 'Account'}`;
    const active = track.querySelector('.is-current');
    if (active) track.scrollLeft += active.getBoundingClientRect().left - track.getBoundingClientRect().left - (track.clientWidth - active.clientWidth) / 2;
    return index < 0 ? 1 : index;
  }
  updateCurrent();
  window.addEventListener('hashchange', updateCurrent);
  window.addEventListener('pageshow', updateCurrent);

  let touchStart = null;
  let suppressClick = false;
  track.addEventListener('touchstart', event => {
    const touch = event.changedTouches[0];
    touchStart = [touch.clientX, touch.clientY];
  }, { passive: true });
  track.addEventListener('touchend', event => {
    if (!touchStart) return;
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStart[0];
    const deltaY = touch.clientY - touchStart[1];
    touchStart = null;
    if (Math.abs(deltaX) < 55 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.3) return;
    const next = updateCurrent() + (deltaX < 0 ? 1 : -1);
    if (next < 0 || next >= destinations.length) return;
    if (event.cancelable) event.preventDefault();
    suppressClick = true;
    location.assign(destinations[next].href);
  }, { passive: false });
  track.addEventListener('click', event => {
    if (suppressClick) { event.preventDefault(); suppressClick = false; }
  }, true);
  let wheelTotal = 0;
  let wheelReset;
  track.addEventListener('wheel', event => {
    if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return;
    event.preventDefault();
    wheelTotal += event.deltaX;
    clearTimeout(wheelReset);
    wheelReset = setTimeout(() => { wheelTotal = 0; }, 350);
    if (Math.abs(wheelTotal) < 90) return;
    const next = updateCurrent() + (wheelTotal > 0 ? 1 : -1);
    wheelTotal = 0;
    if (next >= 0 && next < destinations.length) location.assign(destinations[next].href);
  }, { passive: false });

})();
