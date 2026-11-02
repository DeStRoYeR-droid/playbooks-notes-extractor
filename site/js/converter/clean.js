/** Cleanup: unescape text, rejoin split highlights, drop contained duplicates. Twin of clean.py. */

import { unescape } from "./parse.js";

const CLOSERS = "\"'”’)]»";
const OPENERS = "\"'“‘([«";
const TERMINAL = ".!?…";
// Words a sentence almost never ends on.
const DANGLING = new Set([
  "a", "an", "the", "of", "and", "or", "but", "nor", "to", "in", "on", "at", "by",
  "for", "from", "with", "without", "into", "onto", "than", "that", "which", "who",
  "whose", "our", "their", "your", "my", "his", "her", "its", "is", "are", "was",
  "were", "be", "as", "if", "so", "because", "when", "while", "this", "these", "those",
]);

const stripEnd = (s, chars) => {
  let i = s.length;
  while (i > 0 && chars.includes(s[i - 1])) i--;
  return s.slice(0, i);
};
const stripStart = (s, chars) => {
  let i = 0;
  while (i < s.length && chars.includes(s[i])) i++;
  return s.slice(i);
};
const squash = (s) => s.replace(/\s+/g, " ").trim();
const norm = (s) => squash(s).toLowerCase();
const isLower = (c) => Boolean(c) && c === c.toLowerCase() && c !== c.toUpperCase();

function endsSentence(text) {
  const t = stripEnd(text.trimEnd(), CLOSERS).trimEnd();
  return Boolean(t) && TERMINAL.includes(t.at(-1));
}

/**
 * True when `b` looks like the second half of a highlight Play Books split in two:
 * same chapter, color and date; the first has no comment and stops mid-sentence;
 * same or next page; and the second continues the sentence.
 */
export function canMerge(a, b) {
  if (a.chapter !== b.chapter || a.color !== b.color) return false;
  if (a.date !== b.date || a.comment) return false;
  if (endsSentence(a.highlight)) return false;
  if (a.page !== null && b.page !== null) {
    if (!(b.page - a.page >= 0 && b.page - a.page <= 1)) return false;
  } else if (a.page !== b.page) {
    return false;
  }
  // A missing period alone is not enough: readers often skip it. The second half must
  // start in lower case, or the first must stop on a word that cannot end a sentence.
  const lastWord = a.highlight.trimEnd().split(" ").at(-1).replace(/[^\p{L}\p{N}\p{M}_']/gu, "").toLowerCase();
  if (DANGLING.has(lastWord)) return true;
  const second = stripStart(b.highlight, OPENERS);
  if (!isLower(second[0])) return false;
  // Across a page turn a lower-case start can be a new highlight that begins
  // mid-sentence; only accept a short tail there (e.g. "anymore.").
  if (a.page !== null && b.page !== null && b.page !== a.page) {
    return second.split(/\s+/).filter(Boolean).length <= 3;
  }
  return true;
}

export function mergeFragments(notes) {
  const out = [];
  let merged = 0;
  for (const n of notes) {
    const prev = out.at(-1);
    if (prev && canMerge(prev, n)) {
      out[out.length - 1] = {
        ...prev,
        highlight: `${prev.highlight.trimEnd()} ${n.highlight.trimStart()}`,
        comment: n.comment,
        page: n.page !== null ? n.page : prev.page,
      };
      merged++;
    } else {
      out.push(n);
    }
  }
  return [out, merged];
}

/** Drop a note whose highlight sits wholly inside its neighbour's (same chapter and color). */
export function dropContained(notes) {
  const out = [];
  let dropped = 0;
  for (const n of notes) {
    const prev = out.at(-1);
    if (prev && prev.chapter === n.chapter && prev.color === n.color) {
      const a = norm(prev.highlight), b = norm(n.highlight);
      if (a.includes(b)) {
        if (n.comment && !prev.comment) out[out.length - 1] = { ...prev, comment: n.comment };
        dropped++;
        continue;
      }
      if (b.includes(a)) {
        out[out.length - 1] = n.comment || !prev.comment ? n : { ...n, comment: prev.comment };
        dropped++;
        continue;
      }
    }
    out.push(n);
  }
  return [out, dropped];
}

/** Unescape, merge split highlights and drop contained duplicates (in that order). */
export function clean(exp) {
  let notes = exp.notes
    .map((n) => ({
      ...n,
      highlight: squash(unescape(n.highlight)),
      comment: n.comment ? squash(unescape(n.comment)) || null : null,
    }))
    .filter((n) => n.highlight);
  let merged, duplicates;
  [notes, merged] = mergeFragments(notes);
  [notes, duplicates] = dropContained(notes);
  return { ...exp, notes, merged, duplicates };
}
