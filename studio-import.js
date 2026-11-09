/* A collection-first studio: analyse locally, review groups, then persist private trips. */
(() => {
  const manual = document.querySelector('#createFeedForm');
  if (!manual || !window.SerenityVideoAnalysis) return;
  const A = window.SerenityVideoAnalysis;
  const G = window.SerenityStudioGrouping;
  const shell = document.createElement('section'); shell.className = 'auto-studio';
  shell.setAttribute('aria-label', 'Make trips from your videos');
  shell.innerHTML = `<div class="auto-intro"><span class="eyebrow">Your videos. Already a story.</span><h3>Add the moments.<br>We’ll find the connections.</h3><p>Drop a collection or choose a folder. We’ll look for similar scenes and suggest trips you can make your own.</p></div>
    <div class="auto-drop" id="autoDrop"><span class="auto-drop-icon" aria-hidden="true">↥</span><strong>A whole camera roll. A few new journeys.</strong><div class="auto-pickers"><button type="button" id="autoPick">Choose videos</button><button type="button" id="autoFolder">Choose a folder</button></div><input type="file" id="autoFiles" accept="video/mp4,video/quicktime,video/webm,video/x-m4v" multiple hidden><input type="file" id="autoDirectory" webkitdirectory directory multiple hidden><small>Up to 500 videos per collection · 50 MB each · MP4, MOV, WebM, M4V</small></div>
    <div class="auto-steps" aria-label="How it works"><span>01 / Add videos</span><span>02 / Review suggested trips</span><span>03 / Save or publish</span></div>
    <p class="auto-privacy">Vision runs on this device. The first use downloads a large model; video frames aren’t sent to an AI service. Videos upload to your account only when you save.</p>
    <p id="autoStatus" class="auto-status" role="status" aria-live="polite">Your collection will be grouped by visual themes, not guessed cities or travel dates.</p><progress id="autoProgress" max="1" value="0" hidden aria-label="Collection progress"></progress>
    <div class="auto-collection-actions" id="autoActions" hidden><button type="button" id="autoAnalyse">Find my trips</button><button type="button" id="autoManual" hidden>Group without vision</button><button type="button" id="autoCancel" hidden>Stop</button><button type="button" id="autoClear">Clear collection</button></div>
    <section id="autoReview" class="auto-review" hidden aria-label="Review suggested trips"><div class="auto-review-heading"><div><span class="eyebrow">Your suggested trips</span><h3>A little order. All your moments.</h3><p>Review the groups, rename trips, and move any clip. Similar-looking places may be different journeys.</p></div><button type="button" id="autoNewGroup">＋ New group</button></div><div id="autoGroups"></div><details class="auto-clip-editor"><summary>Review and move individual videos</summary><div id="autoClipRows"></div></details><p class="auto-save-note">Ready to share? Post these videos and their trip stories directly to the public Home feed, or save privately for later. A missing destination is labelled “Location not specified.” You can change visibility from any trip preview. Keep this tab open until saving finishes.</p><div class="auto-save-actions"><button type="button" id="autoPublishSave">Post trips to Home feed</button><button type="button" id="autoSave">Save privately</button></div></section>`;
  manual.before(shell);
  const manualWrap = document.createElement('details'); manualWrap.className = 'auto-manual-create';
  const summary = document.createElement('summary'); summary.textContent = 'Prefer to build a trip yourself?';
  manual.before(manualWrap); manualWrap.append(summary, manual);
  document.querySelector('.clip-studio>.feed-head p').textContent = 'Add your videos. Discover their connections. Turn them into trips.';
  const $ = id => shell.querySelector(`#${id}`);
  let records = [], groups = [], batchKey = crypto.randomUUID(), feedMap = null;
  let busy = false, savingStarted = false, done = false, stopRequested = false;
  let publicationChoice = null;
  let vision, controller;
  let destinationPickers = [];
  const status = text => { $('autoStatus').textContent = text; };
  function progress(value, max = 1) { $('autoProgress').hidden = false; $('autoProgress').max = Math.max(1, max); $('autoProgress').value = value; }
  function buttonState() {
    for (const id of ['autoPick', 'autoFolder', 'autoClear', 'autoAnalyse', 'autoManual']) $(id).disabled = busy || (savingStarted && !done && id !== 'autoClear');
    $('autoSave').disabled = busy || done;
    $('autoPublishSave').disabled = busy || done;
    $('autoSave').hidden = savingStarted && publicationChoice === true;
    $('autoPublishSave').hidden = savingStarted && publicationChoice === false;
    $('autoCancel').hidden = !busy;
    $('autoNewGroup').disabled = busy || savingStarted;
    for (const input of $('autoReview').querySelectorAll('input,select,textarea')) input.disabled = busy || savingStarted || input.dataset.blocked === 'true';
    destinationPickers.forEach(picker => { picker.element.inert = busy || savingStarted; });
    $('autoAnalyse').hidden = savingStarted || !records.some(record => !record.theme && !record.duplicate || record.error);
    $('autoAnalyse').textContent = groups.length ? 'Retry analysis' : 'Find my trips';
  }
  function reset() {
    records = []; groups = []; feedMap = null; batchKey = crypto.randomUUID(); savingStarted = false; done = false;
    $('autoReview').hidden = true; $('autoActions').hidden = true; $('autoProgress').hidden = true;
    publicationChoice = null; $('autoManual').hidden = true; $('autoSave').textContent = 'Save privately'; $('autoPublishSave').textContent = 'Post trips to Home feed';
    $('autoGroups').replaceChildren(); $('autoClipRows').replaceChildren(); buttonState();
    destinationPickers.forEach(picker => picker.destroy()); destinationPickers = [];
  }
  function selectFiles(files) {
    if (busy) return;
    reset();
    const videos = [...files].filter(A.isVideo);
    if (videos.length > 500) return status('Choose up to 500 videos at a time. Split this folder into smaller collections.');
    let oversize = 0;
    for (const file of videos) {
      if (file.size > A.MAX_SIZE || !file.size) { oversize++; continue; }
      records.push({ file, path: file.webkitRelativePath || file._collectionPath || file.name, id: crypto.randomUUID(), selected: true });
    }
    if (!records.length) return status('No supported videos found. Choose MP4, MOV, WebM, or M4V videos up to 50 MB each.');
    $('autoActions').hidden = false;
    status(`${records.length} ${records.length === 1 ? 'video' : 'videos'} ready.${oversize ? ` ${oversize} empty or oversized videos were skipped.` : ''} Find my trips will analyse three frames from each video on this device.`);
    buttonState();
  }
  $('autoPick').onclick = () => $('autoFiles').click();
  $('autoFolder').onclick = () => $('autoDirectory').click();
  for (const id of ['autoFiles', 'autoDirectory']) $(id).onchange = event => { selectFiles(event.target.files); event.target.value = ''; };
  $('autoClear').onclick = () => { reset(); status('Add a new collection whenever you’re ready. Any trips already saved remain in your account.'); };
  async function readEntry(entry, output) {
    if (output.length > 500) throw new Error('This folder contains more than 500 videos. Choose a smaller folder.');
    if (entry.isFile) {
      const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
      if (A.isVideo(file)) { file._collectionPath = entry.fullPath.replace(/^\//, ''); output.push(file); }
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      while (true) {
        const entries = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
        if (!entries.length) break;
        for (const child of entries) await readEntry(child, output);
      }
    }
  }
  $('autoDrop').ondragover = event => { event.preventDefault(); if (!busy) $('autoDrop').classList.add('is-dragging'); };
  $('autoDrop').ondragleave = () => $('autoDrop').classList.remove('is-dragging');
  $('autoDrop').ondrop = async event => {
    event.preventDefault(); $('autoDrop').classList.remove('is-dragging'); if (busy) return;
    const entries = [...(event.dataTransfer.items || [])].map(item => item.webkitGetAsEntry?.()).filter(Boolean);
    try {
      const files = [];
      if (entries.length) { for (const entry of entries) await readEntry(entry, files); } else files.push(...event.dataTransfer.files);
      selectFiles(files);
    } catch (error) { status(error.message); }
  };
  function buildGroups() {
    groups = G.groupsFor(records.filter(record => record.theme));
    for (const group of groups) for (const record of group.records) record.groupKey = group.key;
    renderReview();
  }
  async function analyse(manualOnly = false) {
    if (busy) return;
    busy = true; stopRequested = false; controller = new AbortController(); buttonState();
    const hashes = new Set(); let duplicates = 0;
    try {
      if (!manualOnly) {
        status('Preparing local vision. The first model download can take several minutes.');
        vision = new A.Vision(item => { if (item.status === 'progress' && Number.isFinite(item.progress)) status(`Downloading vision model: ${Math.round(item.progress)}%. Your videos stay on this device.`); });
        await vision.request('init');
      }
      for (const [index, record] of records.entries()) {
        if (stopRequested) break;
        status(`${manualOnly ? 'Preparing' : 'Finding themes in'} ${index + 1} of ${records.length}: ${record.file.name}`);
        progress(index, records.length);
        record.hash ||= await A.fingerprint(record.file);
        if (hashes.has(record.hash)) { record.selected = false; record.duplicate = true; duplicates++; continue; }
        hashes.add(record.hash); record.duplicate = false;
        if (record.theme && !record.error) continue;
        try {
          if (manualOnly) { record.theme = { id: 'review', name: 'Needs a closer look' }; record.error = null; record.selected = true; }
          else {
            const sample = await A.sample(record.file, controller.signal);
            record.thumbnail = sample.thumbnail;
            const result = await vision.request('analyse', sample.frames);
            record.theme = result.theme; record.error = null; record.selected = true;
          }
        } catch (error) {
          if (error.name === 'AbortError') throw error;
          record.error = error.message; record.selected = false;
        }
      }
      buildGroups(); progress(records.length, records.length);
      const failed = records.filter(record => record.error).length;
      status(`${stopRequested ? 'Analysis stopped. ' : ''}${groups.length} suggested ${groups.length === 1 ? 'trip' : 'trips'}.${duplicates ? ` ${duplicates} exact ${duplicates === 1 ? 'duplicate' : 'duplicates'} excluded.` : ''}${failed ? ` ${failed} videos could not be analysed; their errors are listed below.` : ''}${manualOnly ? ' Grouping is manual; no visual themes were inferred.' : ' Review the suggestions before saving.'}`);
      $('autoManual').hidden = !failed;
    } catch (error) {
      buildGroups();
      status(error.name === 'AbortError' ? 'Analysis stopped. Completed suggestions are kept; you can retry or group the rest manually.' : `Vision could not finish: ${error.message} Retry, or choose Group without vision.`);
      $('autoManual').hidden = false;
    } finally { vision?.stop(); vision = null; busy = false; buttonState(); }
  }
  $('autoAnalyse').onclick = () => analyse();
  $('autoManual').onclick = () => analyse(true);
  $('autoCancel').onclick = () => { stopRequested = true; if (!savingStarted) { controller?.abort(); vision?.stop(); } status(savingStarted ? 'Stopping after the current upload. Saved videos will be kept.' : 'Stopping analysis…'); };
  function node(tag, className, text) { const element = document.createElement(tag); element.className = className || ''; if (text !== undefined) element.textContent = text; return element; }
  function renderReview() {
    $('autoReview').hidden = !records.length;
    destinationPickers.forEach(picker => picker.destroy()); destinationPickers = [];
    const grid = $('autoGroups'); grid.replaceChildren();
    for (const group of groups) {
      const members = records.filter(record => record.groupKey === group.key && record.selected && !record.duplicate);
      const card = node('article', 'auto-group');
      const header = node('div', 'auto-group-head'); header.append(node('span', 'eyebrow', group.theme || 'Your group'), node('span', 'auto-group-count', `${members.length} ${members.length === 1 ? 'video' : 'videos'}`));
      const thumbs = node('div', 'auto-thumbnails');
      for (const record of members.slice(0, 4)) if (record.thumbnail) { const image = node('img'); image.src = record.thumbnail; image.alt = ''; thumbs.append(image); }
      card.append(header, thumbs);
      for (const [key, label, length] of [['name', 'Trip name', 60]]) {
        const field = node('label', '', label), input = node('input'); input.value = group[key]; input.maxLength = length;
        input.oninput = () => { group[key] = input.value; }; input.onchange = () => renderReview();
        field.append(input); card.append(field);
      }
      const destination = window.SerenityDestinationPicker.create({ value: group.location, text: group.destination,
        onChange: value => { group.location = value; if (value) group.destination = value.label.slice(0, 120); else group.destination = ''; } });
      destinationPickers.push(destination); card.append(destination.element);
      const storyLabel = node('label', '', 'Story'), story = node('textarea'); story.rows = 2; story.maxLength = 1000; story.value = group.summary;
      story.oninput = () => { group.summary = story.value; }; storyLabel.append(story); card.append(storyLabel);
      const mergeLabel = node('label', '', 'Merge this group into'), merge = node('select'); merge.add(new Option('Keep as its own trip', ''));
      for (const other of groups) if (other !== group) merge.add(new Option(other.name, other.key));
      merge.onchange = () => { for (const record of records) if (record.groupKey === group.key) record.groupKey = merge.value; groups = groups.filter(item => item !== group); renderReview(); };
      mergeLabel.append(merge); card.append(mergeLabel); grid.append(card);
    }
    const rows = $('autoClipRows'); rows.replaceChildren();
    for (const record of records) {
      const row = node('div', 'auto-clip-row'), label = node('label'), check = node('input'); check.type = 'checkbox'; check.checked = record.selected; check.dataset.blocked = String(Boolean(record.duplicate || !record.theme));
      check.onchange = () => { record.selected = check.checked; renderReview(); };
      label.append(check, node('span', '', record.file.name));
      const note = node('small', '', record.duplicate ? 'Exact duplicate · excluded' : record.error || record.theme?.name || 'Not analysed yet');
      const assignment = node('select'); assignment.setAttribute('aria-label', `Trip for ${record.file.name}`);
      for (const group of groups) assignment.add(new Option(group.name, group.key)); assignment.value = record.groupKey || '';
      assignment.dataset.blocked = String(Boolean(!record.theme || record.duplicate));
      assignment.onchange = () => { record.groupKey = assignment.value; renderReview(); };
      row.append(label, note, assignment); rows.append(row);
    }
    buttonState();
    // Preserve intrinsically disabled checkboxes/selectors after the general busy-state pass.
    rows.querySelectorAll('.auto-clip-row').forEach((row, index) => {
      if (!records[index].theme || records[index].duplicate) for (const input of row.querySelectorAll('input,select')) input.disabled = true;
    });
  }
  $('autoNewGroup').onclick = () => { groups.push({ key: `group-${crypto.randomUUID()}`, name: 'New trip', theme: 'Your group', destination: '', location: null, summary: 'Moments from this journey.' }); renderReview(); };
  async function saveCollection(publish) {
    if (busy || done) return;
    if (publicationChoice !== null) publish = publicationChoice;
    const selected = records.filter(record => record.selected && record.theme && !record.duplicate);
    const activeGroups = groups.filter(group => selected.some(record => record.groupKey === group.key));
    if (!selected.length) return status('Choose at least one analysed video to save.');
    if (activeGroups.length > 100) return status('This collection has more than 100 groups. Merge some groups before saving.');
    if (activeGroups.some(group => !group.name.trim())) return status('Give each trip a name before saving.');
    busy = true; buttonState();
    const account = await window.RoamApp.me().catch(() => null);
    if (!account) {
      busy = false; buttonState(); status('Sign in in a new tab, then return here and save. Your collection will stay in this tab. ');
      const signIn = node('a', '', 'Open sign in ↗'); signIn.href = 'auth.html'; signIn.target = '_blank'; signIn.rel = 'noopener'; $('autoStatus').append(signIn);
      return;
    }
    busy = true; savingStarted = true; publicationChoice = publish; stopRequested = false; buttonState();
    const actionButton = $(publish ? 'autoPublishSave' : 'autoSave');
    try {
      feedMap ||= (await window.RoamApp.importTrips(batchKey, activeGroups.map(({ key, name, destination, summary, location }) => ({ key, name, destination, summary, location })))).groups;
      for (const [index, record] of selected.entries()) {
        if (stopRequested) break;
        const feed = feedMap.find(feed => feed.key === record.groupKey);
        status(`Saving ${index + 1} of ${selected.length}: ${record.file.name}`); progress(index, selected.length);
        if (!record.savedId) record.savedId = (await window.RoamApp.upload(record.file, feed.id, `${batchKey}-${record.hash}`)).id;
      }
      if (publish && !stopRequested) for (const group of activeGroups) {
        if (stopRequested) break;
        const feed = feedMap.find(feed => feed.key === group.key);
        const members = selected.filter(record => record.groupKey === group.key);
        status(`Posting ${group.name} to Home feed…`);
        await window.RoamApp.setTripVisibility(feed.id, 'public', members.map(record => record.savedId));
      }
      done = !stopRequested; const count = selected.filter(record => record.savedId).length;
      status(done ? `${count} ${count === 1 ? 'video' : 'videos'} saved across ${activeGroups.length} ${activeGroups.length === 1 ? 'trip' : 'trips'}${publish ? ' and published to Home feed' : ', privately'}. Your journeys are ready below.` : `Paused. ${count} ${count === 1 ? 'video' : 'videos'} saved. Resume to finish the collection.`);
      progress(count, selected.length); actionButton.textContent = done ? publish ? '✓ Posted to Home feed' : '✓ Trips saved privately' : publish ? 'Resume posting' : 'Resume saving';
    } catch (error) { status(`Saving or posting stopped: ${error.message} Saved videos are safe. Retry to finish; check the preview badges for their current visibility.`); actionButton.textContent = publish ? 'Retry saving and posting' : 'Retry unfinished uploads'; }
    finally { busy = false; buttonState(); window.dispatchEvent(new Event('serenity:studio-imported')); window.dispatchEvent(new Event('serenity:trip-updated')); }
  }
  $('autoSave').onclick = () => saveCollection(false);
  $('autoPublishSave').onclick = () => saveCollection(true);
  window.addEventListener('beforeunload', event => { if (busy || records.length && !done) { event.preventDefault(); event.returnValue = ''; } });
})();
