/* Trip creation, trip details, and saved videos share one Clip Studio workspace. */
(() => {
  try {
  const $ = selector => document.querySelector(selector);
  const form = $('#createFeedForm');
  const cards = $('#feedCards');
  const status = $('#studioStatus');
  let user = null;
  let tripPickers = [];
  const createDestination = window.SerenityDestinationPicker.create();
  form.elements.namedItem('destination').closest('label').replaceWith(createDestination.element);

  function setStatus(message) {
    status.textContent = message;
  }

  function makeField(details, key, labelText, maxLength, multiline = false) {
    const label = document.createElement('label');
    label.textContent = labelText;
    const input = multiline ? document.createElement('textarea') : document.createElement('input');
    input.name = key;
    input.maxLength = maxLength;
    input.value = details[key] || '';
    label.append(input);
    return label;
  }

  function makeClipCard(clip) {
    const card = document.createElement('article');
    card.className = 'studio-clip';
    const video = document.createElement('video');
    video.src = window.RoamApp.videoUrl(clip.id);
    video.controls = true;
    video.playsInline = true;
    video.preload = 'none';
    const name = document.createElement('strong');
    name.textContent = clip.original_name;
    const actions = document.createElement('div');
    actions.className = 'studio-clip-actions';
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.onclick = async () => {
      if (!confirm(`Remove "${clip.original_name}" from this trip? Any published post using it will also be removed.`)) return;
      remove.disabled = true;
      try {
        await window.RoamApp.remove(clip.id);
        window.dispatchEvent(new Event('serenity:trip-updated'));
        await loadStudio();
        setStatus(`${clip.original_name} removed.`);
      } catch (error) {
        setStatus(`Could not remove ${clip.original_name}: ${error.message}`);
        remove.disabled = false;
      }
    };
    if (clip.is_published) {
      const published = document.createElement('span');
      published.className = 'studio-published-label';
      published.textContent = 'On Home feed';
      actions.append(published, remove);
    } else {
      const privateClip = document.createElement('span');
      privateClip.className = 'studio-published-label';
      privateClip.textContent = 'Not published';
      actions.append(privateClip, remove);
    }
    const media = document.createElement('div');
    media.className = 'studio-clip-media';
    media.append(video);
    card.append(media, name, actions);
    return card;
  }

  function makeUnassignedClipCard(clip, feeds) {
    const card = document.createElement('article');
    card.className = 'studio-clip';
    const video = document.createElement('video');
    video.src = window.RoamApp.videoUrl(clip.id);
    video.controls = true;
    video.playsInline = true;
    video.preload = 'none';
    const name = document.createElement('strong');
    name.textContent = clip.original_name;
    const actions = document.createElement('div');
    actions.className = 'studio-clip-actions';
    const select = document.createElement('select');
    select.setAttribute('aria-label', `Choose a trip for ${clip.original_name}`);
    select.add(new Option('Choose a trip', ''));
    for (const [id, title] of feeds) select.add(new Option(title, id));
    select.onchange = async () => {
      if (!select.value) return;
      select.disabled = true;
      try {
        await window.RoamApp.assignFeed(clip.id, Number(select.value));
        await loadStudio();
        window.dispatchEvent(new Event('serenity:trip-updated'));
        setStatus(`${clip.original_name} added to ${select.selectedOptions[0].textContent}.`);
      } catch (error) {
        setStatus(`Could not assign ${clip.original_name}: ${error.message}`);
        select.disabled = false;
      }
    };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.onclick = async () => {
      if (!confirm(`Remove "${clip.original_name}" permanently?`)) return;
      remove.disabled = true;
      try {
        await window.RoamApp.remove(clip.id);
        await loadStudio();
        setStatus(`${clip.original_name} removed.`);
      } catch (error) {
        setStatus(`Could not remove ${clip.original_name}: ${error.message}`);
        remove.disabled = false;
      }
    };
    actions.append(select, remove);
    const media = document.createElement('div');
    media.className = 'studio-clip-media';
    media.append(video);
    card.append(media, name, actions);
    return card;
  }

  function makeGalleryPreview(name, clips, index, onSelect = () => {}) {
    const preview = document.createElement('div');
    preview.className = 'studio-gallery-preview';
    const frame = document.createElement('div');
    frame.className = 'studio-gallery-media';
    frame.style.setProperty('--gallery-ratio', ['4 / 5', '3 / 4', '2 / 3'][index % 3]);
    if (!clips.length) {
      const empty = document.createElement('p');
      empty.className = 'studio-gallery-empty';
      empty.textContent = 'Add videos to bring this trip to life';
      frame.append(empty);
    } else {
      const video = document.createElement('video');
      video.controls = true;
      video.playsInline = true;
      video.preload = 'metadata';
      const caption = document.createElement('strong');
      caption.className = 'studio-gallery-caption';
      const counter = document.createElement('span');
      counter.className = 'studio-gallery-counter';
      const setClip = clipIndex => {
        const clip = clips[clipIndex];
        video.pause();
        video.src = window.RoamApp.videoUrl(clip.id);
        video.setAttribute('aria-label', `${clip.original_name} in ${name}`);
        video.load();
        caption.textContent = clip.original_name;
        counter.textContent = `${clipIndex + 1} / ${clips.length}`;
        onSelect(clip);
      };
      const previous = document.createElement('button');
      previous.type = 'button';
      previous.className = 'studio-gallery-arrow studio-gallery-previous';
      previous.setAttribute('aria-label', `Previous video in ${name}`);
      previous.textContent = '‹';
      previous.hidden = clips.length < 2;
      const next = document.createElement('button');
      next.type = 'button';
      next.className = 'studio-gallery-arrow studio-gallery-next';
      next.setAttribute('aria-label', `Next video in ${name}`);
      next.textContent = '›';
      next.hidden = clips.length < 2;
      let activeIndex = 0;
      previous.onclick = () => {
        activeIndex = (activeIndex - 1 + clips.length) % clips.length;
        setClip(activeIndex);
      };
      next.onclick = () => {
        activeIndex = (activeIndex + 1) % clips.length;
        setClip(activeIndex);
      };
      setClip(activeIndex);
      frame.append(video, previous, next, counter);
      preview.append(frame, caption);
      return preview;
    }
    preview.append(frame);
    return preview;
  }

  function publicTripDetails(details) {
    const destination = String(details.destination || '').trim() || 'Location not specified';
    const caption = String(details.summary || '').trim() || 'A place worth experiencing.';
    return { destination, caption, tip: '' };
  }

  async function uploadFiles(feedId, clips, files, details) {
    const videos = [...files];
    if (videos.some(file => !file.type.startsWith('video/'))) {
      throw new Error('Choose video files only.');
    }
    if (videos.some(file => file.size > 50 * 1024 * 1024)) {
      throw new Error('Each video must be 50 MB or smaller.');
    }
    const remaining = 500 - clips.length;
    if (videos.length > remaining) {
      throw new Error(`This trip can hold ${remaining} more ${remaining === 1 ? 'clip' : 'clips'}.`);
    }
    const post = publicTripDetails(details);
    for (const [index, file] of videos.entries()) {
      setStatus(`Saving and publishing ${file.name} (${index + 1} of ${videos.length})…`);
      const clip = await window.RoamApp.upload(file, Number(feedId));
      await window.RoamApp.publishPost({
        clip_id: clip.id,
        destination: post.destination,
        caption: post.caption,
        tip: post.tip
      });
    }
  }

  function makeTripCard(id, name, details, tripClips, galleryIndex) {
    const card = document.createElement('article');
    card.className = 'studio-trip';
    card.dataset.feed = id;
    const head = document.createElement('div');
    head.className = 'studio-trip-heading';
    const titleGroup = document.createElement('div');
    const eyebrow = document.createElement('span');
    eyebrow.className = 'eyebrow';
    eyebrow.textContent = `TRIP ${id}`;
    const title = document.createElement('h3');
    title.textContent = name;
    titleGroup.append(eyebrow, title);
    const open = document.createElement('a');
    open.href = `feed.html?feed=${encodeURIComponent(id)}`;
    open.textContent = 'Open trip page ↗';
    head.append(titleGroup, open);

    const destination = window.SerenityDestinationPicker.create({ value: details.location, text: details.destination });
    tripPickers.push(destination);
    const publication = window.SerenityPublication.create({ id, name, clips: tripClips, location: details.location,
      onLocate: () => { manage.open = true; destination.element.querySelector('input').focus(); },
      onChanged: async message => { await loadStudio(); setStatus(message); } });
    const galleryPreview = makeGalleryPreview(name, tripClips, galleryIndex, publication.select);
    galleryPreview.querySelector('.studio-gallery-media').append(publication.badge);
    const editor = document.createElement('form');
    editor.className = 'studio-trip-details';
    editor.append(
      makeField({ name }, 'name', 'Trip name', 60),
      destination.element,
      makeField(details, 'summary', 'The experience', 1000, true)
    );
    const save = document.createElement('button');
    save.type = 'submit';
    save.className = 'studio-save-details';
    save.textContent = 'Save trip details';
    editor.append(save);
    editor.onsubmit = async event => {
      event.preventDefault();
      save.disabled = true;
      const values = Object.fromEntries(new FormData(editor));
      try {
        await window.RoamApp.renameFeed(id, values.name);
        await window.RoamApp.saveDetails(id, {
          destination: destination.destination,
          location: destination.value,
          summary: values.summary
        });
        setStatus(`${values.name.trim()} saved.`);
        await loadStudio();
        window.dispatchEvent(new Event('serenity:trip-updated'));
      } catch (error) {
        setStatus(`Trip details were not fully saved: ${error.message}`);
      } finally {
        save.disabled = false;
      }
    };

    const media = document.createElement('section');
    media.className = 'studio-trip-media';
    const mediaHead = document.createElement('div');
    mediaHead.className = 'studio-media-heading';
    const mediaTitle = document.createElement('h4');
    mediaTitle.textContent = 'Trip videos';
    const count = document.createElement('span');
    count.textContent = `${tripClips.length} videos`;
    mediaHead.append(mediaTitle, count);
    const uploadLabel = document.createElement('label');
    uploadLabel.className = 'studio-upload';
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'video/mp4,video/webm,video/quicktime,video/x-m4v';
    input.multiple = true;
    input.disabled = tripClips.length >= 500;
    const buttonText = document.createElement('span');
    buttonText.textContent = tripClips.length >= 500 ? 'Trip is full' : '＋ Add videos to this trip';
    const helper = document.createElement('small');
    helper.textContent = 'MP4, WebM, MOV, or M4V · 50 MB max each';
    uploadLabel.append(input, buttonText, helper);
    const publishExisting = document.createElement('button');
    publishExisting.type = 'button';
    publishExisting.className = 'studio-publish-trip';
    publishExisting.textContent = 'Publish saved videos to Home feed';
    publishExisting.hidden = !tripClips.some(clip => !clip.is_published);
    publishExisting.onclick = async () => {
      publishExisting.disabled = true;
      const values = Object.fromEntries(new FormData(editor));
      try {
        await window.RoamApp.renameFeed(id, values.name);
        await window.RoamApp.saveDetails(id, {
          destination: destination.destination,
          location: destination.value,
          summary: values.summary
        });
        const publishedCount = (await window.RoamApp.setTripVisibility(id, 'public')).changed;
        await loadStudio();
        window.dispatchEvent(new Event('serenity:trip-updated'));
        setStatus(`${publishedCount} ${publishedCount === 1 ? 'video' : 'videos'} from ${values.name} published to the Home feed.`);
      } catch (error) {
        await loadStudio();
        setStatus(`Trip was not fully published: ${error.message}`);
        publishExisting.disabled = false;
      }
    };
    input.onchange = async () => {
      if (!input.files?.length) return;
      input.disabled = true;
      try {
        await uploadFiles(id, tripClips, input.files, details);
        await loadStudio();
        window.dispatchEvent(new Event('serenity:trip-updated'));
        setStatus(`${input.files.length} ${input.files.length === 1 ? 'video' : 'videos'} saved to ${name}.`);
      } catch (error) {
        await loadStudio();
        window.dispatchEvent(new Event('serenity:trip-updated'));
        setStatus(`Videos were not fully saved: ${error.message}`);
        input.disabled = false;
      }
    };
    const clipGrid = document.createElement('div');
    clipGrid.className = 'studio-clip-grid';
    if (tripClips.length) {
      clipGrid.append(...tripClips.map(makeClipCard));
    } else {
      const empty = document.createElement('p');
      empty.className = 'studio-empty';
      empty.textContent = 'Your trip videos will appear here. Add clips whenever you are ready.';
      clipGrid.append(empty);
    }
    media.append(mediaHead, uploadLabel, publishExisting, clipGrid);
    const manage = document.createElement('details');
    manage.className = 'studio-trip-manage';
    const manageSummary = document.createElement('summary');
    manageSummary.textContent = 'Manage trip details and videos';
    manage.append(manageSummary, editor, media);
    card.append(galleryPreview, head, publication.panel, manage);
    return card;
  }

  async function loadStudio() {
    if (!user) return;
    try {
      const [names, clips] = await Promise.all([
        window.RoamApp.feeds(),
        window.RoamApp.clips()
      ]);
      const feeds = Object.entries(names);
      const details = await Promise.all(feeds.map(([id]) => window.RoamApp.details(id)));
      tripPickers.forEach(picker => picker.destroy()); tripPickers = [];
      cards.querySelectorAll('video').forEach(video => video.pause());
      cards.replaceChildren();
      const visibleFeeds = feeds.map(([id, name], index) => ({ id, name, details: details[index], clips: clips.filter(clip => String(clip.feed_id) === id), index }))
        .filter(feed => !(/^Feed \d+$/.test(feed.name) && !feed.clips.length && !feed.details.destination && !feed.details.summary));
      if (!visibleFeeds.length) {
        const empty = document.createElement('p');
        empty.className = 'studio-empty';
        empty.textContent = 'Your trips will appear here. Add a collection above to get started.';
        cards.append(empty);
      } else {
        cards.append(...visibleFeeds.map(feed => makeTripCard(feed.id, feed.name, feed.details, feed.clips, feed.index)));
      }
      const unassigned = clips.filter(clip => clip.feed_id == null);
      if (unassigned.length) {
        const section = document.createElement('section');
        section.className = 'studio-unassigned';
        const heading = document.createElement('h3');
        heading.textContent = 'Videos waiting for a trip';
        const grid = document.createElement('div');
        grid.className = 'studio-clip-grid';
        grid.append(...unassigned.map(clip => makeUnassignedClipCard(clip, feeds)));
        section.append(heading, grid);
        cards.append(section);
      }
    } catch (error) {
      setStatus(`Could not load Clip Studio: ${error.message}`);
    }
  }

  form.onsubmit = async event => {
    event.preventDefault();
    if (!user) {
      setStatus('Sign in before creating a trip and saving its videos.');
      return;
    }
    const submit = form.querySelector('[type="submit"]');
    const values = new FormData(form);
    const files = values.getAll('videos').filter(value => value instanceof File && value.size > 0);
    const name = String(values.get('name') || '').trim();
    if (!name) return setStatus('Give your trip a name first.');
    if (files.length > 500) return setStatus('Choose up to 500 videos per trip.');
    const tripDetails = {
      destination: createDestination.destination,
      location: createDestination.value,
      summary: String(values.get('summary') || '')
    };
    if (files.length) {
      try { publicTripDetails(tripDetails); }
      catch (error) { setStatus(error.message); return; }
    }
    submit.disabled = true;
    let createdFeed = null;
    try {
      createdFeed = await window.RoamApp.createFeed(name);
      await window.RoamApp.saveDetails(createdFeed.id, tripDetails);
      if (files.length) await uploadFiles(createdFeed.id, [], files, tripDetails);
      form.reset();
      createDestination.reset();
      await loadStudio();
      window.dispatchEvent(new Event('serenity:trip-updated'));
      setStatus(`${name} created${files.length ? ` and published with ${files.length} ${files.length === 1 ? 'video' : 'videos'}` : ''}.`);
    } catch (error) {
      await loadStudio();
      setStatus(createdFeed
        ? `${name} was created, but its videos may not all have been saved and published: ${error.message}`
        : `Could not create ${name}: ${error.message}`);
    } finally {
      submit.disabled = false;
    }
  };

  $('#accountLink').textContent = 'Sign in ↗';
  window.addEventListener('serenity:studio-imported', loadStudio);
  const storyInput = form.elements.namedItem('summary');
  storyInput.required = false;
  form.querySelector('.trip-create-heading span').textContent = 'Pin the place, describe the experience, and publish the videos that inspire someone to go.';
  form.querySelector('[type="submit"]').textContent = 'Create and publish trip';
  $('.clip-studio > .feed-head p').textContent = 'Create your trip and publish its videos in one step. Published trips appear in the shared Home feed for everyone.';
  const homeFeedLink = document.querySelector('.social-share-link');
  if (homeFeedLink) { homeFeedLink.href = '#feeds'; homeFeedLink.textContent = 'Create a trip ↗'; }
  const heroCopy = document.querySelector('.social-hero p');
  if (heroCopy) heroCopy.textContent = 'Watch a place, find it on the map, and make it your next trip.';
  const feedHeading = document.querySelector('.social-stream-head h2');
  if (feedHeading) feedHeading.textContent = 'Watch it. Go there.';
  const socialRail = document.querySelector('.social-rail');
  if (socialRail) socialRail.hidden = true;
  window.RoamApp.me().then(async account => {
    user = account;
    if (!user) {
      cards.replaceChildren();
      const empty = document.createElement('p');
      empty.className = 'studio-empty';
      empty.textContent = 'Sign in to create trips and upload videos.';
      cards.append(empty);
      setStatus('Sign in to start creating trips.');
      return;
    }
    $('#accountLink').textContent = `${user.name} ↗`;
    $('#accountLink').href = 'account.html';
    setStatus(`Welcome to Clip Studio, ${user.name}. Create a trip and add its videos here.`);
    await loadStudio();
  }).catch(error => setStatus(`Could not connect to Clip Studio: ${error.message}`));
  } catch (error) {
    document.querySelector('#studioStatus').textContent = `Clip Studio could not start: ${error.message}. Refresh to retry.`;
    console.error('Clip Studio initialization failed:', error);
  }
})();
