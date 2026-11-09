/* Messaging API boundary. No studio or public-comment UI dependencies. */
(() => {
  async function request(path, body) {
    const response = await fetch(`/api/messages/${path}`, {
      credentials: 'same-origin', cache: 'no-store',
      ...(body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {})
    });
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error || 'Messaging is unavailable. Please try again.');
      error.status = response.status;
      throw error;
    }
    return result;
  }
  window.SerenityMessages = {
    users: q => request(`users?${new URLSearchParams({ q })}`),
    inbox: before => request(`inbox?${new URLSearchParams(before ? { before } : {})}`),
    conversation: (id, options = {}) => request(`with/${encodeURIComponent(id)}?${new URLSearchParams(options)}`),
    send: body => request('send', body),
    read: (id, through) => request(`${encodeURIComponent(id)}/read`, { through }),
    block: (id, blocked) => request(`${encodeURIComponent(id)}/block`, { blocked })
  };
})();
