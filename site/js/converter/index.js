/**
 * Play Books notes converter: export Markdown -> clean, grouped Markdown.
 * Runs in the browser (and Node 18+). No dependencies.
 */

import { clean } from "./clean.js";
import { parse } from "./parse.js";
import { outputFilename, render } from "./render.js";

export { NoHighlights, NotAPlayBooksExport } from "./errors.js";
export { GROUPINGS, STYLES, outputFilename, render } from "./render.js";

/** Parse and clean an export. */
export async function load(markdown) {
  return clean(await parse(markdown));
}

/** Counts shown to the reader after upload. */
export function summarize(exp) {
  const colors = {};
  for (const c of exp.colors) colors[c] = 0;
  for (const n of exp.notes) colors[n.color] = (colors[n.color] || 0) + 1;
  for (const c of Object.keys(colors)) if (!colors[c]) delete colors[c];
  const used = new Set(exp.notes.map((n) => n.chapter));
  return {
    title: exp.title,
    notes: exp.notes.length,
    chapters: exp.chapters.filter((c) => used.has(c)).length,
    colors,
    colorsDetected: exp.colorsDetected,
    merged: exp.merged,
    duplicatesRemoved: exp.duplicates,
    comments: exp.notes.filter((n) => n.comment).length,
  };
}

/** Parse, clean and render in one call. */
export async function convert(markdown, groupBy = "chapter", style = "bullet") {
  const exp = await load(markdown);
  return { export: exp, markdown: render(exp, groupBy, style), filename: outputFilename(exp.title) };
}
