/**
 * Parse a Google Play Books notes export (Google Doc downloaded as Markdown).
 * JavaScript twin of notes_parser/parse.py; tests check both give identical output.
 *
 * The export lists every annotation twice: grouped by color, then grouped by chapter.
 * Notes come from the chapter section; the color section only tells us which swatch
 * image stands for which color. Sections are found by structure, not heading words.
 */

import { NoHighlights, NotAPlayBooksExport } from "./errors.js";
import { colorFromDataUri } from "./png.js";

const IMG = String.raw`!\[[^\]]*\]\[(?<img>[^\]]+)\]`;
// `*![][image3] highlight* comment ...` (first note of a group)
const ROW_A = new RegExp(String.raw`^\*\s*` + IMG + String.raw`\s*(?<hl>.*?)(?<!\\)\*(?<rest>.*)$`);
// `![][image3] *highlight* comment ...`
const ROW_B = new RegExp("^" + IMG + String.raw`\s*\*(?<hl>.*?)(?<!\\)\*(?<rest>.*)$`);
// `![][image3] text without italics ...` (defensive)
const ROW_C = new RegExp("^" + IMG + String.raw`\s*(?<rest>.*)$`);

const MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December";
const LINK = String.raw`\[(?<page>[^\]]*)\]\((?<url>[^)]*)\)`;
const TRAIL_EN = new RegExp(
  String.raw`^(?<comment>.*?)\s*(?<date>(?:${MONTHS}) \d{1,2}, \d{4})\s*` + LINK + String.raw`\s*$`,
);
// Fallback for other date formats: whatever date-like token sits right before the link.
const TRAIL_ANY = new RegExp(
  String.raw`^(?<comment>.*?)\s*(?<date>\S+ \d{1,2},? \d{4}|\d{1,2}\.? \S+ \d{4}|\d{1,4}[./-]\d{1,2}[./-]\d{1,4})?\s*` +
    LINK +
    String.raw`\s*$`,
);
const IMAGE_DEF = /^\[(?<img>[^\]]+)\]:\s*<?(?<uri>data:image\/[^>\s]+)>?\s*$/gm;
const ITALIC = /(?<!\\)\*(.+?)(?<!\\)\*/;
const ESCAPE = /\\([\\`*_{}\[\]()#+\-.!$>|~"'<=&:])/g;
const H1 = /^#\s/;
const H2 = /^##\s/;
const COLOR_WORDS = new Set(["yellow", "green", "blue", "red", "orange", "purple", "pink"]);

/** Undo the backslash escapes Google Docs adds when exporting Markdown. */
export function unescape(text) {
  return text.replace(ESCAPE, "$1");
}

function cleanHeading(line) {
  let text = line.replace(/^#+/, "").trim();
  while (text.length >= 2 && text[0] === text.at(-1) && "*_".includes(text[0])) {
    text = text.slice(1, -1).trim();
  }
  return unescape(text);
}

/** Inner text of a one-cell table row, or null if the line is not a note row. */
function rowCell(line) {
  const s = line.trim();
  if (!(s.startsWith("|") && s.endsWith("|")) || /^\|[\s:\-|]*\|$/.test(s)) return null;
  const inner = s.slice(1, -1).trim();
  return inner.includes("![") ? inner : null;
}

/** Split one note cell into image id, raw highlight, raw comment, date and page. */
export function parseRow(cell) {
  let img, hl, rest;
  const m = ROW_A.exec(cell) || ROW_B.exec(cell);
  if (m) {
    ({ img, hl, rest } = m.groups);
    hl = hl.trim();
  } else {
    const c = ROW_C.exec(cell);
    if (!c) return null;
    ({ img, rest } = c.groups);
    hl = "";
  }

  let comment, date, pageText;
  const t = TRAIL_EN.exec(rest) || TRAIL_ANY.exec(rest);
  if (t) {
    comment = t.groups.comment;
    date = t.groups.date ?? null;
    pageText = t.groups.page;
  } else {
    comment = rest;
    date = null;
    pageText = "";
  }

  if (!hl && comment.trim()) {
    // No italics at all: treat the text as the highlight.
    hl = comment.trim();
    comment = "";
  }

  const digits = (pageText || "").replace(/\D/g, "");
  return {
    img,
    highlight: hl,
    comment: comment.trim() || null,
    date,
    page: digits ? Number.parseInt(digits, 10) : null,
  };
}

/** Group lines into H1 blocks; keep only blocks that hold H2 groups with note rows. */
function sections(lines) {
  const blocks = [];
  let current = [];
  for (const line of lines) {
    if (H1.test(line)) {
      blocks.push(current);
      current = [];
    } else {
      current.push(line);
    }
  }
  blocks.push(current);
  return blocks.filter((b) => b.some((l) => H2.test(l)) && b.some((l) => rowCell(l) !== null));
}

function groupedRows(block) {
  const out = [];
  let group = "";
  for (const line of block) {
    if (H2.test(line)) {
      group = cleanHeading(line);
      continue;
    }
    const cell = rowCell(line);
    if (cell === null) continue;
    const row = parseRow(cell);
    if (row) out.push([group, row]);
  }
  return out;
}

function findTitle(lines) {
  for (const line of lines) {
    if (H1.test(line)) break;
    if (line.includes("Cover Image") || line.trim().startsWith("| ![")) {
      const cells = line.trim().replace(/^\|+|\|+$/g, "").split("|").map((c) => c.trim());
      for (const c of cells) {
        const m = ITALIC.exec(c);
        if (m && !m[1].includes("![")) return unescape(m[1].trim());
      }
    }
  }
  return "";
}

/**
 * Parse the export into notes with raw (still escaped) text. Run `clean()` next.
 * Async only because the swatch-color fallback uses DecompressionStream.
 */
export async function parse(markdown) {
  const text = markdown.replace(/^\uFEFF+/, "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = text.split("\n");
  const found = sections(lines);
  if (!found.length) throw new NotAPlayBooksExport();

  let colorRows = found.length >= 2 ? groupedRows(found[0]) : [];
  let chapterRows = groupedRows(found.at(-1));

  // A single section might be the color section on its own: every group is named like
  // a color and uses exactly one swatch. Then its groups are colors, chapters unknown.
  if (found.length === 1) {
    const imgsPerGroup = new Map();
    for (const [g, r] of chapterRows) {
      if (!r.highlight) continue;
      if (!imgsPerGroup.has(g)) imgsPerGroup.set(g, new Set());
      imgsPerGroup.get(g).add(r.img);
    }
    if (
      imgsPerGroup.size &&
      [...imgsPerGroup.keys()].every((g) => COLOR_WORDS.has(g.toLowerCase())) &&
      [...imgsPerGroup.values()].every((s) => s.size === 1)
    ) {
      colorRows = chapterRows;
      chapterRows = chapterRows.map(([, r]) => ["Notes", r]);
    }
  }

  // Image id -> color name, learned from the color section (majority vote).
  const votes = new Map();
  const colorOrder = [];
  for (const [group, row] of colorRows) {
    if (!row.highlight) continue;
    if (!votes.has(row.img)) votes.set(row.img, new Map());
    const v = votes.get(row.img);
    v.set(group, (v.get(group) || 0) + 1);
    if (!colorOrder.includes(group)) colorOrder.push(group);
  }
  const colorMap = new Map();
  for (const [img, counts] of votes) {
    let best = null, bestN = -1;
    for (const [group, n] of counts) if (n > bestN) { best = group; bestN = n; }
    colorMap.set(img, best);
  }

  // Fallback: decode the swatch PNG for any image the color section did not cover.
  const dataUris = new Map();
  for (const m of text.matchAll(IMAGE_DEF)) dataUris.set(m.groups.img, m.groups.uri);
  for (const [, row] of chapterRows) {
    const img = row.img;
    if (row.highlight && !colorMap.has(img) && dataUris.has(img)) {
      const name = await colorFromDataUri(dataUris.get(img));
      if (name) {
        colorMap.set(img, name);
        if (!colorOrder.includes(name)) colorOrder.push(name);
      }
    }
  }

  const notes = [];
  const chapters = [];
  let skipped = 0;
  for (const [chapter, row] of chapterRows) {
    if (!row.highlight) {
      skipped++; // bookmark or empty entry
      continue;
    }
    const color = colorMap.get(row.img) ?? "Unknown";
    if (color === "Unknown" && !colorOrder.includes("Unknown")) colorOrder.push("Unknown");
    if (!chapters.includes(chapter)) chapters.push(chapter);
    notes.push({ chapter, color, highlight: row.highlight, comment: row.comment, date: row.date, page: row.page });
  }

  if (!notes.length) throw new NoHighlights();

  return {
    title: findTitle(lines) || "Play Books Notes",
    notes,
    chapters,
    colors: colorOrder,
    rawCount: chapterRows.length,
    merged: 0,
    duplicates: 0,
    skipped,
    colorsDetected: colorMap.size > 0 && [...colorMap.values()].some((c) => c !== "Unknown"),
  };
}
