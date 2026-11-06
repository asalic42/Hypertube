// Adds the next page of a list to the items already shown, leaving out those
// the list already has. The pages are fetched one after another and the
// server's order moves between two of them: the catalogue enriches films
// (popularity, rating, a film merged into its twin) while the viewer scrolls,
// and a comment just published shifts the ones below it by one. An item then
// comes back on the next page, and React would get two children with its id.
export function appendPage(current, results) {
    const shown = new Set(current.map((item) => item.id));
    return [...current, ...results.filter((item) => !shown.has(item.id))];
}
