/* Preview-level publishing controls, independent of video analysis and trip editing. */
(() => {
  function state(clips) {
    const published = clips.filter(clip => Boolean(clip.is_published)).length;
    return { published, private: clips.length - published, total: clips.length,
      key: !clips.length ? 'empty' : !published ? 'private' : published === clips.length ? 'public' : 'mixed' };
  }
  function create({ id, name, clips, location, onLocate, onChanged }) {
    const visibility = state(clips);
    const badge = document.createElement('span'); badge.className = `studio-publication__badge is-${visibility.key}`;
    const labels = { public: '● Public', private: '◒ Private', mixed: '◐ Mixed', empty: '○ No videos' };
    badge.textContent = labels[visibility.key];
    badge.setAttribute('aria-label', `${name}: ${labels[visibility.key].slice(2)}, ${visibility.published} of ${visibility.total} videos on Home feed`);
    const panel = document.createElement('section'); panel.className = 'studio-publication'; panel.setAttribute('aria-label', `Publishing controls for ${name}`);
    const count = document.createElement('p'); count.className = 'studio-publication__count';
    count.textContent = `${visibility.published} public · ${visibility.private} private`;
    const actions = document.createElement('div'); actions.className = 'studio-publication__actions';
    const publish = document.createElement('button'); publish.type = 'button'; publish.textContent = 'Post trip to Home feed';
    publish.hidden = visibility.key === 'public'; publish.disabled = !clips.length;
    const hide = document.createElement('button'); hide.type = 'button'; hide.textContent = 'Make trip private'; hide.hidden = !visibility.published;
    const current = document.createElement('button'); current.type = 'button'; current.className = 'studio-publication__current'; current.hidden = clips.length < 2;
    const message = document.createElement('p'); message.className = 'studio-publication__message'; message.setAttribute('role', 'status');
    let active = clips[0], busy = false;
    function select(clip) {
      active = clip;
      current.textContent = clip?.is_published ? 'Make current video private' : 'Post current video';
      current.setAttribute('aria-label', `${current.textContent}: ${clip?.original_name || name}`);
    }
    async function change(mode, clipIds) {
      if (busy) return;
      busy = true;
      for (const button of [publish, hide, current]) button.disabled = true;
      message.textContent = mode === 'public' ? 'Posting to Home feed…' : 'Making videos private…';
      try {
        await window.RoamApp.setTripVisibility(id, mode, clipIds);
        window.dispatchEvent(new Event('serenity:trip-updated'));
        await onChanged(mode === 'public' ? `${clipIds ? 'Video' : name} is now on Home feed.` : `${clipIds ? 'Video' : name} is private. Saved videos and interactions are kept.`);
      } catch (error) {
        message.textContent = `Visibility was not confirmed: ${error.message} Refresh or retry to check the saved state.`;
      } finally {
        busy = false;
        for (const button of [publish, hide, current]) button.disabled = !clips.length;
      }
    }
    publish.onclick = () => change('public'); hide.onclick = () => change('private');
    current.onclick = () => active && change(active.is_published ? 'private' : 'public', [active.id]);
    select(active); actions.append(publish, hide); panel.append(count, actions, current, message);
    const mapStatus = document.createElement(location && visibility.published ? 'a' : 'button');
    mapStatus.className = 'studio-publication__map';
    if (mapStatus.tagName === 'A') { mapStatus.href = `map.html?trip=${id}`; mapStatus.textContent = 'Pinned on Map ↗'; }
    else { mapStatus.type = 'button'; mapStatus.textContent = location ? 'Destination pin set · private until published' : '＋ Add destination pin for Map'; mapStatus.onclick = onLocate; }
    panel.append(mapStatus);
    return { badge, panel, select };
  }
  window.SerenityPublication = { state, create };
})();
