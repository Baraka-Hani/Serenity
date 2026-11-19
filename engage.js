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

/* Built-in quizzes use only public details attached to published posts. */
(() => {
  const root = document.querySelector('#engageQuiz');
  if (!root || !window.RoamApp) return;

  const picker = document.querySelector('#quizClip');
  const loadMore = document.querySelector('#quizLoadMore');
  const featured = document.querySelector('#quizFeatured');
  const video = document.querySelector('#quizVideo');
  const title = document.querySelector('#quizClipTitle');
  const creator = document.querySelector('#quizClipCreator');
  const story = document.querySelector('#quizClipStory');
  const place = document.querySelector('#quizClipPlace');
  const spoiler = document.querySelector('#quizClipSpoiler');
  const status = document.querySelector('#quizStatus');
  const cards = document.querySelector('#quizCards');
  const modes = [
    {
      field: 'destination',
      title: 'Destination Detective',
      description: 'Read the trip clue and find the destination.',
      prompt: 'Which destination did the creator tag for this clip?',
      missing: 'This clip has no published destination yet.'
    },
    {
      field: 'tip',
      title: 'Creator Tip-Off',
      description: 'Can you spot the creator’s real travel tip?',
      prompt: 'Which tip did the creator attach to this clip?',
      missing: 'This clip has no published travel tip yet.'
    },
    {
      field: 'caption',
      title: 'Trip Story Match',
      description: 'Match the clip to the story shared with it.',
      prompt: 'Which story was published with this clip?',
      missing: 'This clip has no published trip story yet.'
    }
  ];

  let posts = [];
  let selected = null;
  let loadToken = 0;
  let hasMorePosts = false;
  let nextOffset = 0;
  let loadingMore = false;

  function value(text) {
    return typeof text === 'string' ? text.trim() : '';
  }

  function shuffle(items) {
    const shuffled = items.slice();
    for (let index = shuffled.length - 1; index > 0; index--) {
      const other = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[other]] = [shuffled[other], shuffled[index]];
    }
    return shuffled;
  }

  function choicesFor(mode, randomize = false) {
    const answer = value(selected?.[mode.field]);
    if (!answer) return { choices: [], reason: mode.missing };

    const seen = new Set([answer.toLocaleLowerCase()]);
    const choices = [{ text: answer, correct: true }];
    for (const post of posts) {
      if (post.id === selected.id) continue;
      const text = value(post[mode.field]);
      const normalized = text.toLocaleLowerCase();
      if (!text || seen.has(normalized)) continue;
      seen.add(normalized);
      choices.push({ text, correct: false });
      if (choices.length === 4) break;
    }
    if (choices.length < 2) {
      return { choices: [], reason: 'Publish another trip with this detail to unlock answer choices.' };
    }
    return { choices: randomize ? shuffle(choices) : choices, reason: '' };
  }

  function makeButton(text, className) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = className;
    button.textContent = text;
    return button;
  }

  function startChallenge(mode, area) {
    const result = choicesFor(mode, true);
    area.replaceChildren();
    if (!result.choices.length) {
      const unavailable = document.createElement('p');
      unavailable.className = 'engage-quiz__unavailable';
      unavailable.textContent = result.reason;
      area.append(unavailable);
      return;
    }

    const answer = result.choices.find(choice => choice.correct).text;
    const panel = document.createElement('div');
    panel.className = 'engage-quiz__challenge';
    const prompt = document.createElement('p');
    prompt.className = 'engage-quiz__prompt';
    prompt.textContent = mode.prompt;
    const options = document.createElement('div');
    options.className = 'engage-quiz__options';
    options.setAttribute('role', 'group');
    options.setAttribute('aria-label', mode.prompt);
    const answerButtons = result.choices.map((choice, index) => {
      const option = makeButton(choice.text, 'engage-quiz__option');
      option.addEventListener('click', () => {
        for (const [optionIndex, answerButton] of answerButtons.entries()) {
          answerButton.disabled = true;
          if (result.choices[optionIndex].correct) answerButton.classList.add('is-correct');
          else if (optionIndex === index) answerButton.classList.add('is-wrong');
        }
        const feedback = document.createElement('div');
        feedback.className = 'engage-quiz__feedback';
        feedback.setAttribute('role', 'status');
        const heading = document.createElement('strong');
        heading.textContent = result.choices[index].correct ? 'That’s right!' : 'Not quite.';
        const explanation = document.createElement('p');
        explanation.textContent = result.choices[index].correct
          ? `This detail was shared with ${selected.destination || 'the selected trip'}.`
          : `The correct answer is: ${answer}.`;
        const replay = makeButton('Play again', 'app-button');
        replay.addEventListener('click', () => startChallenge(mode, area));
        feedback.append(heading, explanation);
        panel.append(feedback, replay);
        spoiler.open = true;
        replay.focus();
      });
      options.append(option);
      return option;
    });
    panel.append(prompt, options);
    area.append(panel);
    answerButtons[0].focus();
  }

  function renderGames() {
    cards.replaceChildren();
    for (const [index, mode] of modes.entries()) {
      const card = document.createElement('article');
      card.className = 'engage-quiz-card';
      const header = document.createElement('div');
      header.className = 'engage-quiz-card__header';
      const badge = document.createElement('span');
      badge.className = 'engage-quiz__badge';
      badge.textContent = `CHALLENGE 0${index + 1}`;
      const heading = document.createElement('h3');
      heading.textContent = mode.title;
      const description = document.createElement('p');
      description.className = 'engage-quiz-card__description';
      description.textContent = mode.description;
      const area = document.createElement('div');
      area.className = 'engage-quiz-card__play-area';
      const availability = choicesFor(mode);
      const play = makeButton('Play challenge', 'app-button app-button--primary');
      play.disabled = !availability.choices.length;
      play.addEventListener('click', () => startChallenge(mode, area));
      header.append(badge, heading);
      area.append(play);
      if (!availability.choices.length) {
        const unavailable = document.createElement('p');
        unavailable.className = 'engage-quiz__unavailable';
        unavailable.textContent = availability.reason;
        area.append(unavailable);
      }
      card.append(header, description, area);
      cards.append(card);
    }
  }

  function updateFeatured(post, context) {
    const trip = context.travel || {};
    selected = {
      id: post.id,
      destination: value(trip.destination) || value(post.destination),
      caption: value(trip.summary) || value(post.caption),
      tip: value(trip.tip) || value(post.tip),
      creator: value(context.creator?.name) || value(post.author_name) || 'Serenity creator'
    };
    // The destination and story are quiz answers, so they stay folded away until asked for.
    title.textContent = `Where did ${selected.creator} go?`;
    creator.textContent = 'Watch the clip, then play a challenge below.';
    place.textContent = selected.destination ? `⌁ ${selected.destination}` : 'No destination was shared with this video.';
    story.textContent = selected.caption || 'No trip story was added to this video.';
    spoiler.open = false;
    video.pause();
    video.src = window.RoamApp.postVideoUrl(selected.id);
    video.onerror = () => {
      if (selected?.id === post.id) status.textContent = 'The video preview could not load, but its quiz details are still available.';
    };
    video.load();
    featured.hidden = false;
    renderGames();
  }

  // One group per trip, with its clips numbered, instead of a list of identical names.
  function populatePicker() {
    const selectedId = picker.value;
    picker.replaceChildren();
    const trips = new Map();
    for (const post of posts) {
      const key = post.feed_id === undefined || post.feed_id === null ? `post:${post.id}` : `feed:${post.feed_id}`;
      if (!trips.has(key)) trips.set(key, { label: `${value(post.feed_name) || value(post.destination) || 'Travel video'} · ${value(post.author_name) || 'Serenity creator'}`, clips: [] });
      trips.get(key).clips.push(post);
    }
    for (const trip of trips.values()) {
      const group = document.createElement('optgroup');
      group.label = trip.label;
      trip.clips.forEach((post, index) => {
        const option = document.createElement('option');
        option.value = post.id;
        option.textContent = trip.clips.length > 1 ? `Clip ${index + 1} of ${trip.clips.length}` : 'Trip video';
        option.label = `${trip.label} — ${option.textContent}`;
        group.append(option);
      });
      picker.append(group);
    }
    picker.value = selectedId;
    picker.disabled = posts.length === 0;
    loadMore.hidden = !hasMorePosts;
    loadMore.disabled = loadingMore || !hasMorePosts;
  }

  async function loadMorePosts() {
    if (!hasMorePosts || loadingMore) return;
    loadingMore = true;
    loadMore.disabled = true;
    loadMore.textContent = 'Loading videos…';
    try {
      const result = await window.RoamApp.posts({ sort: 'recent', offset: nextOffset });
      if (!Array.isArray(result.posts)) throw new Error('The published video list has an invalid format.');
      const knownIds = new Set(posts.map(post => post.id));
      const additional = result.posts.filter(post => typeof post?.id === 'string' && post.id && !knownIds.has(post.id));
      nextOffset += result.posts.length;
      hasMorePosts = Boolean(result.has_more);
      posts.push(...additional);
      populatePicker();
      status.textContent = additional.length
        ? `Loaded ${additional.length} more published videos.`
        : 'No additional published videos were found.';
    } catch (error) {
      console.error('Could not load more public videos for Engage:', error);
      status.textContent = 'Could not load more published videos. Try again.';
    } finally {
      loadingMore = false;
      loadMore.textContent = 'Load more videos';
      loadMore.disabled = !hasMorePosts;
    }
  }

  async function selectPost(post, context = null, notice = '') {
    const token = ++loadToken;
    status.textContent = 'Loading this published video…';
    cards.replaceChildren();
    featured.hidden = true;
    try {
      const postContext = context || await window.RoamApp.postContext(post.id);
      if (token !== loadToken) return;
      if (!postContext?.travel) throw new Error('Published trip details are unavailable.');
      updateFeatured(post, postContext);
      status.textContent = notice;
    } catch (error) {
      if (token !== loadToken) return;
      console.error('Could not load the selected published video:', error);
      status.textContent = 'This published video is unavailable. Choose another video or reload Engage.';
    }
  }

  picker.addEventListener('change', () => {
    const post = posts.find(item => item.id === picker.value);
    if (post) selectPost(post);
  });
  loadMore.addEventListener('click', loadMorePosts);

  async function initialize() {
    try {
      const result = await window.RoamApp.posts({ sort: 'recent' });
      if (!Array.isArray(result.posts)) throw new Error('The published video list has an invalid format.');
      posts = result.posts.filter(post => typeof post?.id === 'string' && post.id);
      hasMorePosts = Boolean(result.has_more);
      nextOffset = result.posts.length;
      // Wrong answers come from other trips, so gather a few before the first quiz.
      for (let page = 0; page < 3 && hasMorePosts && new Set(posts.map(post => value(post.destination).toLocaleLowerCase())).size < 4; page++) {
        const extra = await window.RoamApp.posts({ sort: 'recent', offset: nextOffset });
        if (!Array.isArray(extra.posts)) break;
        const known = new Set(posts.map(post => post.id));
        posts.push(...extra.posts.filter(post => typeof post?.id === 'string' && post.id && !known.has(post.id)));
        nextOffset += extra.posts.length;
        hasMorePosts = Boolean(extra.has_more);
      }
      if (!posts.length) {
        picker.replaceChildren();
        picker.disabled = true;
        loadMore.hidden = true;
        status.textContent = 'No published videos are available yet. Publish a trip clip to play.';
        return;
      }

      const requestedId = new URLSearchParams(location.search).get('post');
      let initial = posts.find(post => post.id === requestedId);
      let context = null;
      let notice = '';
      if (requestedId && !initial) {
        try {
          context = await window.RoamApp.postContext(requestedId);
          initial = {
            id: requestedId,
            destination: value(context.travel?.destination),
            caption: value(context.travel?.summary),
            tip: value(context.travel?.tip),
            author_name: value(context.creator?.name)
          };
          posts.unshift(initial);
        } catch (error) {
          console.warn('The requested published video is unavailable:', error);
          initial = posts[0];
          notice = 'That video is unavailable; showing the latest published video instead.';
        }
      }
      populatePicker();
      initial ||= posts[0];
      picker.value = initial.id;
      await selectPost(initial, context, notice);
    } catch (error) {
      console.error('Could not load public videos for Engage:', error);
      picker.disabled = true;
      status.textContent = 'Could not load published videos. Please reload Engage and try again.';
    }
  }

  initialize();
})();
