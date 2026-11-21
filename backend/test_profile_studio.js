/* Dependency-free tests for the Profile's Clip Studio filters: node backend/test_profile_studio.js */
function runProfileStudioTests(source) {
  const scope = {};
  new Function('window', 'IntersectionObserver', source)(scope, undefined);
  const { group, visible, matches } = scope.SerenityProfileStudio;
  const check = (ok, text) => { if (!ok) throw new Error(text); };
  const feeds = { 1: 'Kyoto', 2: 'Lisbon', 3: 'Feed 3', 4: 'Empty but named' };
  const clips = [
    { id: 'a', feed_id: 1, is_published: 1 }, { id: 'b', feed_id: 1, is_published: 0 },
    { id: 'c', feed_id: 2, is_published: 0 }, { id: 'd', feed_id: null, is_published: 0 }
  ];
  const data = group(feeds, clips, { 4: { destination: '' } });
  check(data.counts.all === 4 && data.counts.live === 1 && data.counts.private === 3, 'Counts must cover every saved video, live and private');
  check(data.trips.map(trip => trip.id).join() === '1,2,4', 'Untouched placeholder trips (Feed N, empty) must be hidden; named empty trips stay');
  check(data.counts.trips === 3, 'Trip count must match the visible trips');
  check(data.unassigned.map(clip => clip.id).join() === 'd', 'Videos without a trip must still be shown to their owner');
  const kyoto = data.trips[0], lisbon = data.trips[1], empty = data.trips[2];
  check(visible(kyoto, 'all').length === 2, 'All must show every video in a trip');
  check(visible(kyoto, 'live').map(clip => clip.id).join() === 'a', 'Live must show only videos on Feed');
  check(visible(kyoto, 'private').map(clip => clip.id).join() === 'b', 'Private must show only unpublished videos');
  check(visible(lisbon, 'live') === null, 'A fully private trip must not appear under Live');
  check(visible(empty, 'live') === null && visible(empty, 'all').length === 0 && visible(empty, 'private') !== null, 'Empty trips appear under All and Private, never Live');
  check(matches({ is_published: true }, 'live') && !matches({ is_published: 0 }, 'live') && matches({}, 'private'), 'Visibility filter must follow is_published');
  return 'Profile studio tests passed: live/private/all counts, filtering, placeholder trips, and unassigned videos.';
}
if (typeof module !== 'undefined' && require.main === module) console.log(runProfileStudioTests(require('fs').readFileSync(require('path').join(__dirname, '../profile-studio.js'), 'utf8')));
