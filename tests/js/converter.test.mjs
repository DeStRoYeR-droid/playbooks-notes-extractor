// Unit tests for the browser converter. Run: node --test tests/js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import { canMerge } from "../../site/js/converter/clean.js";
import { load, NoHighlights, NotAPlayBooksExport, render, summarize } from "../../site/js/converter/index.js";
import { parseRow, unescape } from "../../site/js/converter/parse.js";
import { colorFromDataUri } from "../../site/js/converter/png.js";
import { mdEscape, outputFilename } from "../../site/js/converter/render.js";

const FIXTURE = new URL("../fixtures/art_of_thinking_clearly.md", import.meta.url);
const raw = await readFile(FIXTURE, "utf8");
const exp = await load(raw);
const headings = (md, level) => [...md.matchAll(new RegExp(`^${"#".repeat(level)} (.+)$`, "gm"))].map((m) => m[1]);

test("summary matches the sample export", () => {
  const s = summarize(exp);
  assert.equal(s.title, "The Art of Thinking Clearly");
  assert.equal(s.notes, 351);
  assert.equal(s.chapters, 98);
  assert.deepEqual(s.colors, { Yellow: 30, Green: 109, Blue: 135, Red: 77 });
  assert.equal(s.merged, 18);
  assert.equal(s.duplicatesRemoved, 1);
  assert.equal(s.comments, 12);
  assert.equal(exp.rawCount, 371);
  assert.equal(exp.skipped, 1);
});

test("rows: both italic styles, comment, date, page", () => {
  for (const cell of [
    "*![][image2] Hello there.* my note May 1, 2021 [5](http://x)",
    "![][image2] *Hello there.* my note May 1, 2021 [5](http://x)",
  ]) {
    const r = parseRow(cell);
    assert.deepEqual(r, { img: "image2", highlight: "Hello there.", comment: "my note", date: "May 1, 2021", page: 5 });
  }
  assert.equal(parseRow("![][image4] *Text* July 28, 2021 [286](http://x)").comment, null);
});

test("unescape", () => {
  assert.equal(unescape(String.raw`\$10 \- Impossible\! (Part 1\)`), "$10 - Impossible! (Part 1)");
});

test("split highlights rejoined, separate ones kept apart", () => {
  const has = (s) => exp.notes.filter((n) => n.highlight.includes(s)).length;
  assert.equal(has("We require others’ input to overcome the availability bias."), 1);
  assert.equal(has("she will never sit down on a cold one anymore.”"), 1);
  assert.ok(exp.notes.some((n) => n.highlight.startsWith("The media is not interested")));
  assert.ok(exp.notes.some((n) => n.highlight.startsWith("always ask members’ opinions")));
});

test("canMerge needs a continuation", () => {
  const base = { chapter: "c", color: "Blue", comment: null, date: "May 1, 2021", page: 4 };
  assert.ok(canMerge({ ...base, highlight: "we are puppets of our" }, { ...base, highlight: "Emotions." }));
  assert.ok(canMerge({ ...base, highlight: "a long sentence without" }, { ...base, highlight: "a period" }));
  assert.ok(!canMerge({ ...base, highlight: "Ends here." }, { ...base, highlight: "next one" }));
  assert.ok(!canMerge({ ...base, highlight: "no period" }, { ...base, highlight: "Capital start" }));
  assert.ok(!canMerge({ ...base, highlight: "x", comment: "mine" }, { ...base, highlight: "y" }));
});

test("chapter grouping: one H1, chapters as H2 in book order", () => {
  const md = render(exp, "chapter", "bullet");
  assert.deepEqual(headings(md, 1), ["The Art of Thinking Clearly"]);
  assert.deepEqual(headings(md, 2), exp.chapters);
  assert.equal(md.match(/^- /gm).length, 351);
  assert.equal(md.match(/^ {4}- \*/gm).length, 12);
});

test("both grouping is color, then chapter", () => {
  const md = render(exp, "both", "quote");
  assert.deepEqual(headings(md, 2), ["Yellow", "Green", "Blue", "Red"]);
  assert.ok(headings(md, 3).every((h) => exp.chapters.includes(h)));
  assert.equal(md.match(/^\*\*Note:\*\* /gm).length, 12);
  assert.ok(!/^> .*\n> /m.test(md));
});

test("no links, page numbers or dates in the output", () => {
  const md = render(exp, "color", "bullet");
  assert.ok(!md.includes("play.google.com"));
  assert.ok(!/(January|May|July) \d{1,2}, \d{4}/.test(md));
});

test("fallback: swatch colors decode without the color section", async () => {
  const a = raw.indexOf("# Annotations by color"), b = raw.indexOf("# All your annotations");
  const e = await load(raw.slice(0, a) + raw.slice(b));
  assert.deepEqual(e.notes.map((n) => n.color), exp.notes.map((n) => n.color));
  const uri = raw.match(/^\[image3\]: <(data:[^>]+)>/m)[1];
  assert.equal(await colorFromDataUri(uri), "Green");
});

test("errors", async () => {
  await assert.rejects(load("# Hello\n\nJust a document.\n"), NotAPlayBooksExport);
  const onlyBookmark = "# All your annotations\n\n## *Ch*\n\n|  *![][image6]* July 28, 2021 [288](http://x)  |\n| ----- |\n";
  await assert.rejects(load(onlyBookmark), NoHighlights);
  assert.throws(() => render(exp, "page"), RangeError);
});

test("escaping and file names", () => {
  assert.equal(mdEscape("a *b* c_d"), String.raw`a \*b\* c\_d`);
  assert.equal(mdEscape("# not a heading"), String.raw`\# not a heading`);
  assert.equal(outputFilename('Why? A "Book": Part 1/2'), "Why A Book Part 12 - Notes.md");
  assert.equal(outputFilename(""), "Play Books - Notes.md");
});
