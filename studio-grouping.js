/* Pure collection rules shared by the UI, vision worker, and tests. */
(() => {
  const themes = [
    ['coast', 'Coast & beaches', 'a beach, ocean, surfing or tropical coast'],
    ['mountains', 'Mountain escapes', 'mountains, hiking, rocky peaks or alpine scenery'],
    ['city', 'City discoveries', 'city streets, urban architecture or a city skyline'],
    ['food', 'Food discoveries', 'food, restaurants, street food or cooking'],
    ['nature', 'Gardens & wildlife', 'flowers, gardens, forests, wildlife or green countryside'],
    ['culture', 'Culture & landmarks', 'historic monuments, temples, museums or cultural landmarks'],
    ['night', 'Nights out', 'nightlife, concerts, parties or festivals at night'],
    ['snow', 'Winter adventures', 'snow, skiing, snowboarding or a winter landscape'],
    ['water', 'Lakes & rivers', 'lakes, rivers, waterfalls or boats on inland water'],
    ['road', 'On the road', 'road trips, trains, airports or travelling in a vehicle'],
    ['people', 'People & moments', 'friends, family, people or a social gathering'],
    ['indoors', 'Stays & slow days', 'a hotel, bedroom, indoor space or a relaxing stay']
  ].map(([id, name, prompt]) => ({ id, name, prompt }));
  function classify(scores) {
    const ranked = [...scores].filter(x => Number.isFinite(x.score)).sort((a, b) => b.score - a.score);
    const top = ranked[0], next = ranked[1];
    const theme = themes.find(x => x.prompt === top?.label);
    // Scores rank the candidate themes; they are not calibrated certainty about a trip.
    if (!theme || top.score < .26 || top.score - (next?.score || 0) < .055) return { id: 'review', name: 'Needs a closer look', score: top?.score || 0 };
    return { ...theme, score: top.score };
  }
  function groupsFor(records) {
    const groups = new Map();
    for (const record of records) {
      const theme = record.theme || { id: 'review', name: 'Needs a closer look' };
      // Subfolders keep separate journeys apart; the selected root folder is ignored.
      const path = (record.path || '').split('/').filter(Boolean);
      const folder = path.length > 2 ? path.slice(1, -1).join(' / ') : '';
      const key = `${folder}\u0000${theme.id}`;
      if (!groups.has(key)) groups.set(key, { key: `group-${groups.size + 1}`, name: (folder ? `${folder} · ${theme.name}` : theme.name).slice(0, 60), theme: theme.name, destination: '', location: null, summary: `A collection of ${theme.name.toLowerCase()} moments.`, records: [] });
      groups.get(key).records.push(record);
    }
    return [...groups.values()];
  }
  globalThis.SerenityStudioGrouping = { themes, classify, groupsFor };
})();
