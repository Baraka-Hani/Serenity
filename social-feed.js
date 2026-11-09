/* Public travel feed UI. Trip publishing is handled entirely in Clip Studio. */
(() => {
  if (!window.RoamApp || !document.querySelector('#postList')) return;
  const $ = selector => document.querySelector(selector);
  const list = $('#postList');
  const status = $('#postStatus');
  const more = $('#postMore');
  let user = null;
  let offset = 0;
  let requestNumber = 0;
  let loading = false;
  let hasMore = false;

  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }
  function signInMessage() { status.textContent = 'Sign in to like, save, comment, or share a trip.'; }
  function dateLabel(value) {
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value * 1000));
  }
  function action(label, active = false) {
    const button = element('button', active ? 'is-active' : '', label);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(active));
    return button;
  }
  function renderComment(comment) {
    const row = element('div', 'social-comment');
    const author = element('a', 'social-profile-link', comment.author_name);
    author.href = `profile.html?id=${encodeURIComponent(comment.author_public_id)}`;
    row.append(author, document.createTextNode(comment.body));
    return row;
  }
  function renderPost(post, tripPosts) {
    const card = element('article', 'social-post');
    card.dataset.postId = post.id;
    card.dataset.feedId = String(post.feed_id);
    const videos = tripPosts.length ? tripPosts : [post];
    let selectedPost = videos.find(video => video.id === post.id) || videos[0];
    const header = element('div', 'social-post__header');
    const avatar = element('span', 'social-post__avatar', post.author_name.trim().slice(0, 1).toUpperCase());
    avatar.setAttribute('aria-hidden', 'true');
    const byline = element('div', 'social-post__byline');
    const profileLink = element('a', 'social-profile-link');
    profileLink.href = `profile.html?id=${encodeURIComponent(post.author_public_id)}`;
    profileLink.append(element('strong', '', post.author_name));
    byline.append(profileLink, element('small', '', `@${post.author_username} · ${post.feed_name || 'A travel story'}`));
    header.append(avatar, byline, element('time', 'social-post__date', dateLabel(post.created_at)));
    const media = element('div', 'social-post__media');
    const slides = element('div', 'social-post__slides');
    videos.forEach((tripVideo, index) => {
      const slide = element('div', 'social-post__slide');
      slide.dataset.postId = tripVideo.id;
      const video = element('video');
      video.src = window.RoamApp.postVideoUrl(tripVideo.id);
      video.playsInline = true;
      video.muted = true;
      video.loop = true;
      video.preload = 'none';
      video.setAttribute('aria-label', `Trip video ${index + 1} of ${videos.length} from ${tripVideo.destination} by ${post.author_name}`);
      slide.append(video);
      slides.append(slide);
    });
    const place = element('span', 'social-post__place', `⌁ ${selectedPost.destination}`);
    const clipCount = element('span', 'social-post__clip-count', `${videos.length} ${videos.length === 1 ? 'moment' : 'moments'}`);
    const date = header.querySelector('time');
    media.append(slides, place, clipCount);
    const body = element('div', 'social-post__body');
    const caption = element('p', 'social-post__caption', selectedPost.caption);
    const tip = element('p', 'social-post__tip');
    body.append(caption, tip);
    const actions = element('div', 'social-post__actions');
    const like = action('');
    const save = action('');
    const comment = action('');
    const ask = element('a', 'social-ask-creator', '✉  Ask creator');
    ask.setAttribute('aria-label', `Privately ask ${post.author_name} about this video`);
    comment.setAttribute('aria-expanded', 'false');
    const remove = element('button', 'social-post__delete', 'Delete moment');
    remove.type = 'button';
    remove.hidden = !selectedPost.is_mine;
    function updateSelectedPost(nextPost) {
      selectedPost = nextPost;
      card.dataset.postId = nextPost.id;
      date.textContent = dateLabel(nextPost.created_at);
      place.textContent = `⌁ ${nextPost.destination}`;
      caption.textContent = nextPost.caption;
      tip.replaceChildren();
      tip.hidden = !nextPost.tip;
      if (nextPost.tip) tip.append(element('strong', '', 'Travel tip'), document.createTextNode(nextPost.tip));
      like.textContent = `♡  ${nextPost.likes_count} likes`;
      like.classList.toggle('is-active', Boolean(nextPost.liked));
      like.setAttribute('aria-pressed', String(Boolean(nextPost.liked)));
      like.setAttribute('aria-label', `${nextPost.liked ? 'Unlike' : 'Like'} post by ${post.author_name}`);
      save.textContent = nextPost.saved ? '▣  Saved' : '▢  Save';
      save.classList.toggle('is-active', Boolean(nextPost.saved));
      save.setAttribute('aria-pressed', String(Boolean(nextPost.saved)));
      save.setAttribute('aria-label', `${nextPost.saved ? 'Unsave' : 'Save'} post by ${post.author_name}`);
      comment.textContent = `◌  ${nextPost.comments_count} comments`;
      comments.setAttribute('aria-label', `Comments on ${nextPost.destination}`);
      remove.hidden = !nextPost.is_mine;
      ask.hidden = Boolean(nextPost.is_mine);
      ask.href = window.RoamApp.messageUrl(post.author_public_id, nextPost.id);
      if (!comments.hidden) {
        comments.hidden = true;
        comment.setAttribute('aria-expanded', 'false');
        hub?.setCommentsOpen(false);
        commentsList.replaceChildren();
      }
    }
    like.onclick = () => toggleAction('like', like, (result, target) => {
      target.liked = result.active; target.likes_count = result.count;
      updateSelectedPost(selectedPost);
    });
    save.onclick = () => toggleAction('save', save, (result, target) => {
      target.saved = result.active;
      updateSelectedPost(selectedPost);
    });
    async function toggleAction(kind, button, update) {
      if (!user) return signInMessage();
      button.disabled = true;
      try {
        const target = selectedPost;
        const result = await window.RoamApp.togglePostAction(target.id, kind);
        update(result, target);
      } catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    }
    actions.append(like, save, comment, ask, remove);
    remove.onclick = async () => {
      const target = selectedPost;
      if (!confirm('Remove this public post? Your saved clip will stay in Account.')) return;
      try {
        await window.RoamApp.removePost(target.id);
        const index = videos.indexOf(target);
        videos.splice(index, 1);
        if (!videos.length) {
          card._destroyHub?.();
          card.remove();
          status.textContent = 'Trip removed from the Home feed. Your saved clip is still private in Account.';
          return;
        }
        selectedPost = videos[Math.min(index, videos.length - 1)];
        hub?.updatePosts(videos, videos.indexOf(selectedPost));
        updateSelectedPost(selectedPost);
        clipCount.textContent = `${videos.length} ${videos.length === 1 ? 'moment' : 'moments'}`;
        status.textContent = 'Moment removed from the public trip.';
      } catch (error) { status.textContent = error.message; }
    };
    body.append(actions);
    const comments = element('section', 'social-comments');
    comments.hidden = true;
    comments.setAttribute('aria-label', `Comments on ${post.destination}`);
    const commentsList = element('div', 'social-comments__list');
    const commentForm = element('form', 'social-comment-form');
    const commentInput = element('input');
    commentInput.type = 'text'; commentInput.maxLength = 500;
    commentInput.placeholder = 'Write a public comment';
    commentInput.setAttribute('aria-label', 'Write a comment');
    const send = element('button', '', 'Post'); send.type = 'submit';
    commentForm.append(commentInput, send);
    let hub;
    comment.onclick = async () => {
      comments.hidden = !comments.hidden;
      comment.setAttribute('aria-expanded', String(!comments.hidden));
      hub?.setCommentsOpen(!comments.hidden);
      if (!comments.hidden) {
        const target = selectedPost;
        try {
          const items = await window.RoamApp.postComments(target.id);
          if (selectedPost !== target || comments.hidden) return;
          commentsList.replaceChildren(...items.map(renderComment));
          if (!items.length) commentsList.append(element('p', '', 'No comments yet. Start the conversation.'));
        } catch (error) { status.textContent = error.message; }
      }
    };
    commentForm.onsubmit = async event => {
      event.preventDefault();
      if (!user) return signInMessage();
      try {
        const target = selectedPost;
        const result = await window.RoamApp.addPostComment(target.id, commentInput.value);
        if (selectedPost !== target) return;
        if (commentsList.firstChild?.tagName === 'P') commentsList.replaceChildren();
        commentsList.append(renderComment(result));
        selectedPost.comments_count++;
        comment.textContent = `◌  ${selectedPost.comments_count} comments`;
        commentInput.value = '';
      } catch (error) { status.textContent = error.message; }
    };
    comments.append(commentsList, commentForm);
    updateSelectedPost(selectedPost);
    if (window.SerenityFeedHub) {
      hub = window.SerenityFeedHub.create(post, card, media, header, body, comments, videos, updateSelectedPost);
      card.append(hub.root);
      card._destroyHub = hub.destroy;
    } else {
      body.append(comments);
      card.append(header, media, body);
    }
    return card;
  }

  async function loadPosts(append = false) {
    if (append && (loading || !hasMore)) return;
    const current = ++requestNumber;
    loading = true;
    if (!append) { offset = 0; window.SerenityFeedHub?.reset(); list.replaceChildren(); list.scrollTop = 0; }
    status.textContent = 'Loading community stories…';
    more.hidden = true;
    try {
      const result = await window.RoamApp.posts({ sort: 'recent', offset });
      if (current !== requestNumber) return;
      const seenFeeds = new Set([...list.children].map(card => card.dataset.feedId));
      const added = [];
      for (const post of result.posts) {
        const feedId = String(post.feed_id);
        if (seenFeeds.has(feedId)) continue;
        seenFeeds.add(feedId);
        added.push(renderPost(post, result.trip_posts?.[feedId] || [post]));
      }
      list.append(...added);
      offset += result.posts.length;
      hasMore = result.has_more;
      more.hidden = !result.has_more;
      status.textContent = result.posts.length ? '' : append ? 'You’re all caught up.' : 'No trips have been published yet. Create one in Clip Studio to start the Home feed.';
    } catch (error) {
      if (current !== requestNumber) return;
      status.textContent = error.message;
      if (append) more.hidden = false;
    } finally {
      if (current === requestNumber) loading = false;
    }
  }
  more.onclick = () => loadPosts(true);
  list.addEventListener('scroll', () => {
    if (list.scrollHeight - list.scrollTop - list.clientHeight < list.clientHeight * 1.5) loadPosts(true);
  }, { passive: true });
  window.addEventListener('serenity:trip-updated', () => loadPosts());
  window.RoamApp.me().then(account => { user = account; }).catch(() => {
    status.textContent = 'The local server is unavailable.';
  });
  loadPosts();
})();
