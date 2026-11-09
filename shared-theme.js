/* Shared visual tokens only. Each feature keeps its own UI and behaviour. */
(function () {
  const key = 'roam-make-theme-v1';
  const fallback = { accent: '#ff6945', soft: '#bcd7b1', paper: '#f2eee4', ink: '#171713', energy: 62 };
  let current;
  const isColour = value => typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value);

  function read() {
    try {
      const saved = JSON.parse(localStorage.getItem(key));
      if (saved && ['accent', 'soft', 'paper', 'ink'].every(name => isColour(saved[name])) && Number.isFinite(saved.energy) && saved.energy >= 0 && saved.energy <= 100) return saved;
    } catch (_) { /* Storage may be unavailable, including some file previews. */ }
    return current ? { ...current } : { ...fallback };
  }

  function apply(theme, persist = false) {
    if (!theme || !['accent', 'soft', 'paper', 'ink'].every(name => isColour(theme[name])) || !Number.isFinite(theme.energy)) return;
    const root = document.documentElement;
    current = { ...theme };
    for (const name of ['accent', 'soft', 'paper', 'ink']) root.style.setProperty(`--${name}`, theme[name]);
    root.style.setProperty('--energy', `${theme.energy}%`);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme.paper);
    if (persist) {
      try { localStorage.setItem(key, JSON.stringify(theme)); } catch (_) { /* Keep in-page theme even if storage is blocked. */ }
    }
  }

  window.RoamTheme = { read, apply, fallback: () => ({ ...fallback }) };
  apply(read());
}());
