/* Small API boundary for the landing page. No UI or video analysis lives here. */
(function () {
  async function request(path, options = {}) {
    const response = await fetch(path, { credentials: 'same-origin', ...options });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed.');
    return data;
  }

  window.RoamApp = {
    messageUrl(publicId, postId) {
      const query = new URLSearchParams({ to: publicId });
      if (postId) query.set('post', postId);
      return `search.html?${query}`;
    },
    async findAccounts(q = '', offset = 0) {
      return request(`/api/accounts?${new URLSearchParams({ q, offset })}`, { cache: 'no-store' });
    },
    async me() { return (await request('/api/me')).user; },
    async logout() { return request('/api/logout', { method: 'POST' }); },
    async saveProfile(profile) {
      return (await request('/api/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) })).user;
    },
    async publicProfile(identifier) {
      // Never revive a cached public listing after its owner makes videos private.
      try { localStorage.removeItem(`serenity-profile:${identifier}`); } catch (_) {}
      const profile = (await request(`/api/profiles/${encodeURIComponent(identifier)}`, { cache: 'no-store' })).profile;
      return { profile, cached: false, stale: false };
    },
    invalidateProfileCache() {
      try {
        for (let index = localStorage.length - 1; index >= 0; index--) {
          const key = localStorage.key(index);
          if (key?.startsWith('serenity-profile:')) localStorage.removeItem(key);
        }
      } catch (error) {
        console.warn('Could not invalidate the saved public-profile cache:', error);
      }
    },
    async clips(feed) { return (await request(feed ? `/api/clips?feed=${feed}` : '/api/clips')).clips; },
    async feeds() { return (await request('/api/feeds')).feeds; },
    async createFeed(name) {
      return (await request('/api/feeds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })).feed;
    },
    async publicFeed(id) { return (await request(`/api/public-feeds/${id}`)).feed; },
    async mapTrips(options = {}) {
      const query = new URLSearchParams(options);
      return request(`/api/map/trips?${query}`, { cache: 'no-store' });
    },
    async renameFeed(feed, name) {
      return (await request(`/api/feeds/${feed}/name`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })).name;
    },
    async theme() { return (await request('/api/theme')).theme; },
    async saveTheme(theme) {
      return request('/api/theme', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(theme) });
    },
    async importTrips(batchKey, groups) {
      return request('/api/studio/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ batch_key: batchKey, groups }) });
    },
    async setTripVisibility(feed, visibility, clipIds) {
      const result = await request(`/api/feeds/${encodeURIComponent(feed)}/visibility`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ visibility, ...(clipIds ? { clip_ids: clipIds } : {}) }) });
      window.RoamApp.invalidateProfileCache();
      return result;
    },
    async upload(file, feed, uploadKey) {
      return (await request('/api/clips', {
        method: 'POST', headers: { 'Content-Type': file.type || ({ mp4: 'video/mp4', mov: 'video/quicktime', m4v: 'video/x-m4v', webm: 'video/webm' }[file.name.split('.').pop().toLowerCase()]), 'X-Filename': encodeURIComponent(file.name), 'X-Filename-Encoded': '1', ...(uploadKey ? { 'X-Upload-Key': uploadKey } : {}), ...(feed ? { 'X-Feed': String(feed) } : {}) }, body: file
      })).clip;
    },
    async assignFeed(id, feed) {
      return request(`/api/clips/${encodeURIComponent(id)}/feed`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feed_id: feed }) });
    },
    async notes(feed) { return (await request(`/api/feeds/${feed}/notes`)).notes; },
    async details(feed) { return (await request(`/api/feeds/${feed}/details`)).details; },
    async saveDetails(feed, details) {
      return (await request(`/api/feeds/${feed}/details`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(details) })).details;
    },
    async addNote(feed, body) {
      return (await request(`/api/feeds/${feed}/notes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body }) })).note;
    },
    async posts({ sort = 'recent', q = '', offset = 0, feed } = {}) {
      const params = new URLSearchParams({ sort, q, offset });
      if (feed) params.set('feed', feed);
      return request(`/api/posts?${params}`);
    },
    async publishPost(post) {
      return (await request('/api/posts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(post) })).post;
    },
    async togglePostAction(id, action) {
      return request(`/api/posts/${encodeURIComponent(id)}/${action}`, { method: 'POST' });
    },
    async postComments(id) { return (await request(`/api/posts/${encodeURIComponent(id)}/comments`)).comments; },
    async postContext(id) { return (await request(`/api/posts/${encodeURIComponent(id)}/context`)).context; },
    async addPostComment(id, body) {
      return (await request(`/api/posts/${encodeURIComponent(id)}/comments`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body }) })).comment;
    },
    async removePost(id) { return request(`/api/posts/${encodeURIComponent(id)}`, { method: 'DELETE' }); },
    postVideoUrl(id) { return `/api/posts/${encodeURIComponent(id)}/video`; },
    async remove(id) { return request(`/api/clips/${encodeURIComponent(id)}`, { method: 'DELETE' }); },
    videoUrl(id) { return `/api/clips/${encodeURIComponent(id)}/video`; }
  };

  if (window.RoamTheme) {
    window.RoamApp.me()
      .then(user => user ? window.RoamApp.theme() : null)
      .then(theme => { if (theme?.theme) window.RoamTheme.apply(theme.theme, true); })
      .catch(error => console.warn('Could not restore the account colour scheme:', error));
  }
}());
