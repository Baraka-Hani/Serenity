(() => {
  const grid = document.querySelector('#publishedGrid');
  const status = document.querySelector('#publishedStatus');
  const count = document.querySelector('#publishedCount');

  function empty(message) {
    const card = document.createElement('div');
    card.className = 'published-empty';
    card.textContent = message;
    grid.replaceChildren(card);
  }

  function renderPost(post) {
    const card = document.createElement('article');
    card.className = 'published-card';
    const video = document.createElement('video');
    video.src = window.RoamApp.postVideoUrl(post.id);
    video.controls = true;
    video.playsInline = true;
    video.preload = 'metadata';
    video.setAttribute('aria-label', `${post.destination} published by you`);
    const body = document.createElement('div');
    body.className = 'published-card__body';
    const top = document.createElement('div');
    top.className = 'published-card__top';
    const title = document.createElement('h2');
    title.textContent = post.destination;
    top.append(title);
    if (post.feed_id) {
      const trip = document.createElement('a');
      trip.className = 'published-card__trip';
      trip.href = `feed.html?feed=${encodeURIComponent(post.feed_id)}`;
      trip.textContent = `${post.feed_name || `Trip ${post.feed_id}`} ↗`;
      top.append(trip);
    } else {
      const trip = document.createElement('span');
      trip.className = 'published-card__trip';
      trip.textContent = 'Home feed';
      top.append(trip);
    }
    const caption = document.createElement('p');
    caption.textContent = post.caption;
    const meta = document.createElement('div');
    meta.className = 'published-card__meta';
    const date = document.createElement('span');
    date.textContent = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(post.created_at * 1000));
    const clipName = document.createElement('span');
    clipName.textContent = post.clip_name || 'Published clip';
    meta.append(date, clipName);
    body.append(top, caption, meta);
    if (post.tip) {
      const tip = document.createElement('p');
      tip.textContent = `Tip · ${post.tip}`;
      body.append(tip);
    }
    card.append(video, body);
    return card;
  }

  async function load() {
    grid.replaceChildren();
    count.textContent = 'Loading…';
    try {
      const user = await window.RoamApp.me();
      if (!user) {
        count.textContent = 'Sign in required';
        status.textContent = 'Sign in to see the videos you have published.';
        const emptyCard = document.createElement('div');
        emptyCard.className = 'published-empty';
        emptyCard.append('Your published videos are linked to your account. ', Object.assign(document.createElement('a'), { href: 'auth.html?next=clips', textContent: 'Sign in ↗' }));
        grid.append(emptyCard);
        return;
      }
      const posts = [];
      let offset = 0;
      let hasMore = true;
      while (hasMore) {
        const result = await window.RoamApp.posts({ sort: 'mine', offset });
        posts.push(...result.posts);
        offset += result.posts.length;
        hasMore = result.has_more;
      }
      count.textContent = `${posts.length} ${posts.length === 1 ? 'published clip' : 'published clips'}`;
      if (!posts.length) {
        status.textContent = 'Your published videos will appear here.';
        const emptyCard = document.createElement('div');
        emptyCard.className = 'published-empty';
        emptyCard.append('No videos published yet. Add videos to a trip in Clip Studio, then share them from the Home feed. ', Object.assign(document.createElement('a'), { href: 'app.html#feeds', textContent: 'Open Clip Studio ↗' }));
        grid.append(emptyCard);
        return;
      }
      status.textContent = 'Only videos published to the Home feed are shown here.';
      grid.append(...posts.map(renderPost));
    } catch (error) {
      count.textContent = 'Unavailable';
      status.textContent = `Could not load published clips: ${error.message}`;
      empty('Your published clips could not be loaded. Refresh the page or sign in again.');
    }
  }

  load();
})();
