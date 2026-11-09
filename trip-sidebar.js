/* Published trip navigation, available only in Clip Studio. */
(() => {
  if (!window.RoamApp) return;
  const sidebar = document.createElement('aside');
  sidebar.className = 'trip-sidebar';
  sidebar.id = 'trip-sidebar';
  sidebar.setAttribute('aria-label', 'Your trips');
  const head = document.createElement('div');
  head.className = 'trip-sidebar__head';
  const title = document.createElement('div');
  const eyebrow = document.createElement('span'); eyebrow.textContent = 'Your public stories';
  const heading = document.createElement('h2'); heading.textContent = 'Published trips';
  title.append(eyebrow, heading);
  head.append(title);
  const list = document.createElement('nav');
  list.className = 'trip-sidebar__list';
  list.setAttribute('aria-label', 'Individual trips');
  let rows = [];
  const foot = document.createElement('div'); foot.className = 'trip-sidebar__foot';
  const footLink = document.createElement('a'); footLink.href = 'app.html#feeds'; footLink.textContent = 'Manage trips in Clip Studio ↗';
  foot.append('Trips with published videos appear here. ', footLink);
  sidebar.append(head, list, foot);
  const toggle = document.createElement('button');
  toggle.className = 'trip-sidebar__toggle';
  toggle.type = 'button';
  toggle.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/><path d="M9 7v14"/></svg>';
  toggle.setAttribute('aria-controls', sidebar.id);
  document.body.append(sidebar, toggle);
  document.body.classList.add('has-trip-sidebar');

  const mobile = matchMedia('(max-width: 960px)');
  let isOpen = false;
  function setOpen(open, focusTrip = false) {
    isOpen = open;
    sidebar.classList.toggle('is-open', open);
    document.body.classList.toggle('sidebar-collapsed', !open);
    document.body.classList.toggle('sidebar-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close trip sidebar' : 'Open trip sidebar');
    toggle.title = open ? 'Close trip sidebar' : 'Open trip sidebar';
    sidebar.setAttribute('aria-hidden', String(!open));
    sidebar.inert = !open;
    if (open && focusTrip && mobile.matches) rows[0]?.link.focus();
  }
  toggle.onclick = () => setOpen(!isOpen, true);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && sidebar.classList.contains('is-open')) { setOpen(false); toggle.focus(); } });
  mobile.addEventListener?.('change', () => setOpen(!mobile.matches));
  function isClipStudioPage() {
    return location.pathname.split('/').pop() === 'app.html' && location.hash === '#feeds';
  }
  function updateRoute() {
    const enabled = isClipStudioPage();
    document.body.classList.toggle('has-trip-sidebar', enabled);
    sidebar.hidden = !enabled;
    toggle.hidden = !enabled;
    if (enabled) {
      setOpen(!mobile.matches);
      loadTrips();
    } else {
      setOpen(false);
    }
  }

  async function loadTrips() {
    if (!isClipStudioPage()) return;
    try {
      const user = await window.RoamApp.me();
      if (!user) {
        foot.replaceChildren('Sign in to see your saved trips. ');
        const signIn = document.createElement('a'); signIn.href = 'auth.html'; signIn.textContent = 'Sign in ↗'; foot.append(signIn);
        return;
      }
      const [names, clips] = await Promise.all([window.RoamApp.feeds(), window.RoamApp.clips()]);
      const publishedClips = clips.filter(clip => clip.is_published && clip.feed_id != null);
      const publishedFeedIds = new Set(publishedClips.map(clip => String(clip.feed_id)));
      const feeds = Object.entries(names).filter(([id]) => publishedFeedIds.has(id));
      if (!feeds.length) {
        rows = [];
        list.replaceChildren();
        const empty = document.createElement('p');
        empty.className = 'trip-sidebar__empty';
        empty.textContent = 'Your published trips will appear here.';
        list.append(empty);
        return;
      }
      const details = await Promise.all(feeds.map(([id]) => window.RoamApp.details(id)));
      const activeFeed = new URLSearchParams(location.search).get('feed');
      rows = feeds.map(([id, tripName], index) => {
        const link = document.createElement('a');
        link.className = 'trip-sidebar__trip';
        link.href = `feed.html?feed=${encodeURIComponent(id)}`;
        const badge = document.createElement('span'); badge.className = 'trip-sidebar__number'; badge.textContent = id;
        const copy = document.createElement('span'); copy.className = 'trip-sidebar__copy';
        const name = document.createElement('strong'); name.textContent = tripName;
        const trip = details[index];
        const meta = document.createElement('small'); meta.textContent = trip.location?.label || trip.destination || 'Add a destination pin';
        const count = document.createElement('em');
        const clipCount = publishedClips.filter(clip => String(clip.feed_id) === id).length;
        count.textContent = `${clipCount} published ${clipCount === 1 ? 'clip' : 'clips'}`;
        copy.append(name, meta, count); link.append(badge, copy);
        if (activeFeed === id) { link.classList.add('is-current'); link.setAttribute('aria-current', 'page'); }
        return { link, name, meta, count };
      });
      list.replaceChildren(...rows.map(row => row.link));
    } catch (error) {
      foot.replaceChildren(`Published trips are unavailable: ${error.message}`);
    }
  }
  window.addEventListener('serenity:trip-updated', loadTrips);
  window.addEventListener('pageshow', updateRoute);
  window.addEventListener('hashchange', updateRoute);
  updateRoute();
})();
