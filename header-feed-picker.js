/* Expandable header navigation shared by the landing and app home pages. */
(() => {
  const header = document.querySelector('.nav, .topbar');
  const toggle = document.querySelector('#headerFeedToggle');
  const choices = document.querySelector('#headerFeedChoices');
  if (!header || !toggle || !choices) return;
  if (!choices.querySelector('a[href="map.html"]')) {
    const mapLink = document.createElement('a'); mapLink.href = 'map.html'; mapLink.textContent = 'Map ↗'; choices.append(mapLink);
  }

  function setOpen(open) {
    header.classList.toggle('feed-open', open);
    document.body.classList.toggle('feed-menu-open', open && header.classList.contains('nav'));
    choices.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation choices' : (header.classList.contains('nav') ? 'Open app navigation' : 'Choose a trip'));
    if (open) choices.querySelector('a')?.focus();
  }

  toggle.addEventListener('click', () => setOpen(choices.hidden));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !choices.hidden) { setOpen(false); toggle.focus(); }
  });
  document.addEventListener('pointerdown', event => {
    if (!choices.hidden && !header.contains(event.target)) setOpen(false);
  });
})();
