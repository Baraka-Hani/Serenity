function runStudioPublicationTests(source) {
  const scope = {};
  new Function('window', source)(scope);
  const state = scope.SerenityPublication.state;
  const check = (ok, text) => { if (!ok) throw new Error(text); };
  check(state([]).key === 'empty', 'Empty trips must not claim to be public');
  check(state([{ is_published: 0 }]).key === 'private', 'Unpublished clips must show Private');
  check(state([{ is_published: 1 }, { is_published: true }]).key === 'public', 'Every published clip must show Public');
  const mixed = state([{ is_published: 1 }, { is_published: 0 }, {}]);
  check(mixed.key === 'mixed' && mixed.published === 1 && mixed.private === 2, 'Partial publication must show Mixed with accurate counts');
  return 'Studio publication tests passed: empty, private, public, and mixed states.';
}
if (typeof module !== 'undefined' && require.main === module) console.log(runStudioPublicationTests(require('fs').readFileSync(require('path').join(__dirname, '../studio-publication.js'), 'utf8')));
