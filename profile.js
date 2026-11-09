(() => {
  const $ = selector => document.querySelector(selector);
  const params = new URLSearchParams(location.search);
  const identifier = params.get('id') || params.get('username');
  const status = $('#profileStatus');
  const card = $('#profileCard');

  function showTrip(trip) {
    const article = document.createElement('article');
    article.className = 'profile-trip';
    const heading = document.createElement('h3');
    heading.textContent = trip.name;
    const destination = document.createElement('p');
    destination.className = 'profile-trip-destination';
    destination.textContent = trip.destination;
    const videos = document.createElement('div');
    videos.className = 'profile-trip-videos';
    for (const post of trip.posts) {
      const wrapper = document.createElement('div');
      wrapper.className = 'profile-trip-video';
      const video = document.createElement('video');
      video.src = window.RoamApp.postVideoUrl(post.id);
      video.controls = true;
      video.playsInline = true;
      video.preload = 'metadata';
      video.setAttribute('aria-label', `${post.clip_name} from ${trip.name}`);
      const caption = document.createElement('p');
      caption.textContent = post.caption;
      wrapper.append(video, caption);
      videos.append(wrapper);
    }
    const date = document.createElement('p');
    date.className = 'profile-trip-date';
    date.textContent = `PUBLISHED ${new Intl.DateTimeFormat(undefined, { month: 'short', year: 'numeric' }).format(new Date(trip.published_at * 1000))}`;
    article.append(heading, destination, videos, date);
    return article;
  }

  async function loadProfile() {
    if (!identifier || !/^(?:[a-z0-9_]{3,24}|[0-9a-f]{16})$/i.test(identifier)) {
      status.textContent = 'This profile link is missing a valid username or account ID.';
      return;
    }
    try {
      const result = await window.RoamApp.publicProfile(identifier);
      const profile = result.profile;
      document.title = `${profile.name} (@${profile.username}) — Serenity`;
      $('#profileName').textContent = profile.name;
      $('#profileUsername').textContent = `@${profile.username}`;
      $('#profileBio').textContent = profile.bio || 'Sharing the places and moments that made the journey.';
      $('#profileAvatar').textContent = profile.name.trim().charAt(0).toUpperCase();
      $('#tripCount').textContent = profile.trip_count;
      $('#videoCount').textContent = profile.video_count;
      $('#publicId').textContent = profile.public_id;
      $('#profileDemoBadge').hidden = !profile.is_demo;
      const messageLink = $('#messageProfile');
      messageLink.href = window.RoamApp.messageUrl(profile.public_id);
      messageLink.textContent = `Message @${profile.username} ↗`;
      window.RoamApp.me().then(user => { messageLink.hidden = user?.public_id === profile.public_id; })
        .catch(() => { messageLink.hidden = false; });
      card.hidden = false;
      const grid = $('#tripGrid');
      grid.replaceChildren();
      if (profile.trips.length) {
        grid.append(...profile.trips.map(showTrip));
      } else {
        const empty = document.createElement('p');
        empty.className = 'profile-empty';
        empty.textContent = 'No public trips yet. Published trips will appear here.';
        grid.append(empty);
      }
      $('#profileTrips').hidden = false;
      status.textContent = result.stale
        ? 'Showing the saved profile; Serenity could not refresh it right now.'
        : result.cached ? 'Showing a recently saved public profile.' : '';
      $('#copyProfile').onclick = async () => {
        try {
          await navigator.clipboard.writeText(`${location.origin}/profile.html?id=${encodeURIComponent(profile.public_id)}`);
          $('#copyProfile').textContent = 'Profile link copied';
        } catch (error) {
          status.textContent = `Could not copy the profile link: ${error.message}`;
        }
      };
    } catch (error) {
      status.textContent = `Could not load this profile: ${error.message}`;
    }
  }

  loadProfile();
})();
