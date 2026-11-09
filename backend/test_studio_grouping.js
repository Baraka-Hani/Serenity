function runStudioGroupingTests(source) {
  const context = {};
  new Function('globalThis', source)(context);
  const { themes, classify, groupsFor } = context.SerenityStudioGrouping;
  const assert = (ok, text) => { if (!ok) throw new Error(text); };
  const coast = themes.find(theme => theme.id === 'coast');
  const nature = themes.find(theme => theme.id === 'nature');
  assert(classify([{ label: coast.prompt, score: .8 }, { label: nature.prompt, score: .1 }]).id === 'coast', 'Clear visual evidence should suggest a theme');
  assert(classify([{ label: coast.prompt, score: .3 }, { label: nature.prompt, score: .29 }]).id === 'review', 'Ambiguous clips must be left for review');
  assert(classify([]).id === 'review', 'Missing scores must never produce a guessed theme');
  const groups = groupsFor([
    { id: 'one', path: 'Camera Roll/Trip A/1.mp4', theme: coast },
    { id: 'two', path: 'Camera Roll/Trip A/2.mp4', theme: coast },
    { id: 'three', path: 'Camera Roll/Trip B/3.mp4', theme: coast },
    { id: 'four', path: 'Camera Roll/4.mp4', theme: nature },
  ]);
  assert(groups.length === 3, 'Themes and nested journey folders must stay separate');
  assert(groups[0].records.length === 2, 'Similar videos in the same journey folder should form a group');
  assert(groups.every(group => group.destination === ''), 'Visual themes must never invent a travel destination');
  assert(groups.every(group => group.name.length <= 60), 'Suggested names must fit persistent trip names');
  return 'Studio grouping tests passed: semantic labels, ambiguity, folder boundaries, and no invented locations.';
}
if (typeof module !== 'undefined' && require.main === module) console.log(runStudioGroupingTests(require('fs').readFileSync(require('path').join(__dirname, '../studio-grouping.js'), 'utf8')));
