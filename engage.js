/* Shared games are saved in this browser and launched only when selected. */
(() => {
  const form = document.querySelector('#gameForm');
  const titleInput = form.elements.namedItem('title');
  const urlInput = form.elements.namedItem('url');
  const list = document.querySelector('#gameList');
  const empty = document.querySelector('#gameEmpty');
  const status = document.querySelector('#gameStatus');
  const add = document.querySelector('#addGame');
  let key = null;

  function gameLink(value) {
    try {
      const url = new URL(value);
      if (url.protocol === 'https:' && !url.username && !url.password) return url;
    } catch (_) {
      // The form explains the supported format.
    }
    return null;
  }

  function readGames() {
    const games = JSON.parse(localStorage.getItem(key) || '[]');
    if (!Array.isArray(games)) throw new Error('The saved game list has an invalid format.');
    return games.filter(game => typeof game?.title === 'string' && typeof game.url === 'string' && gameLink(game.url));
  }

  function toggleForm(open, restoreFocus = true) {
    form.hidden = !open;
    add.setAttribute('aria-expanded', String(open));
    if (open) titleInput.focus();
    else if (restoreFocus) add.focus();
  }

  function render(games) {
    list.replaceChildren();
    empty.hidden = games.length > 0;
    for (const game of games) {
      const row = document.createElement('li');
      row.className = 'game-row';
      const details = document.createElement('div');
      const title = document.createElement('strong');
      title.className = 'game-title';
      title.textContent = game.title;
      const host = document.createElement('span');
      host.className = 'game-host';
      host.textContent = gameLink(game.url).hostname;
      details.append(title, host);

      const actions = document.createElement('div');
      actions.className = 'game-actions';
      const play = document.createElement('a');
      play.className = 'app-button app-button--primary';
      play.href = game.url;
      play.target = '_blank';
      play.rel = 'noopener noreferrer';
      play.textContent = 'Open ↗';
      play.setAttribute('aria-label', `Open ${game.title} in a new tab`);
      const remove = document.createElement('button');
      remove.className = 'app-button';
      remove.type = 'button';
      remove.textContent = 'Remove';
      remove.setAttribute('aria-label', `Remove ${game.title} from saved games`);
      remove.addEventListener('click', () => {
        if (save(games => games.filter(item => item.url !== game.url), 'Game removed.')) add.focus();
      });
      actions.append(play, remove);
      row.append(details, actions);
      list.append(row);
    }
  }

  function refresh() {
    try {
      render(readGames());
      status.textContent = '';
    } catch (_) {
      list.replaceChildren();
      empty.hidden = true;
      status.textContent = 'Saved games are unavailable in this browser.';
    }
  }

  function save(update, message) {
    if (!key) return false;
    try {
      const games = update(readGames());
      if (!games) return false;
      localStorage.setItem(key, JSON.stringify(games));
      render(games);
      status.textContent = message;
      return true;
    } catch (_) {
      status.textContent = 'Could not update your saved games. Check your browser storage settings.';
      return false;
    }
  }

  add.addEventListener('click', () => toggleForm(form.hidden));
  document.querySelector('#cancelGame').addEventListener('click', () => toggleForm(false));
  form.addEventListener('submit', event => {
    event.preventDefault();
    const title = titleInput.value.trim();
    const url = gameLink(urlInput.value.trim());
    if (!title || !url) {
      status.textContent = 'Enter a name and an HTTPS game link.';
      (title ? urlInput : titleInput).focus();
      return;
    }
    if (save(games => {
      if (games.some(game => game.url === url.href)) {
        status.textContent = 'This game is already saved.';
        urlInput.focus();
        return null;
      }
      return [{ title, url: url.href }, ...games];
    }, 'Game saved.')) {
      form.reset();
      toggleForm(false);
    }
  });

  async function syncLibrary() {
    try {
      const user = await window.RoamApp.me();
      const nextKey = `serenity-generated-games:${user?.public_id || 'guest'}`;
      if (key !== nextKey) {
        key = nextKey;
        form.reset();
        toggleForm(false, false);
        add.disabled = false;
        refresh();
      }
    } catch (_) {
      key = null;
      form.reset();
      toggleForm(false, false);
      add.disabled = true;
      list.replaceChildren();
      empty.hidden = true;
      status.textContent = 'Connect to Serenity to open your saved games.';
    }
  }

  window.addEventListener('storage', event => {
    if (key && (event.key === key || event.key === null)) refresh();
  });
  window.addEventListener('pageshow', event => { if (event.persisted) syncLibrary(); });
  window.addEventListener('online', syncLibrary);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) syncLibrary(); });
  syncLibrary();
})();
