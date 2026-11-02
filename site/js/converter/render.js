/** Render cleaned notes as Markdown. Twin of notes_parser/render.py. */

const INLINE = /([\\`*_])/g;
const BLOCK_START = /^(#{1,6}\s|>|[-+*]\s|\d+[.)]\s)/;

export const GROUPINGS = ["chapter", "color", "both"];
export const STYLES = ["bullet", "quote"];

/** Escape characters that would turn plain note text into Markdown formatting. */
export function mdEscape(text) {
  let out = text.replace(INLINE, "\\$1");
  if (BLOCK_START.test(out)) out = "\\" + out;
  return out;
}

function noteLines(note, style) {
  const hl = mdEscape(note.highlight);
  if (style === "bullet") {
    const lines = [`- ${hl}`];
    if (note.comment) lines.push(`    - *${mdEscape(note.comment)}*`);
    return lines;
  }
  const lines = [`> ${hl}`];
  if (note.comment) lines.push("", `**Note:** ${mdEscape(note.comment)}`);
  return lines;
}

function block(notes, style) {
  const out = [];
  notes.forEach((n, i) => {
    if (style === "quote" && i) out.push(""); // separate quote blocks
    out.push(...noteLines(n, style));
  });
  return out;
}

/**
 * Markdown with the book title as the only H1 and one H2 per group.
 * chapter: H2 chapter (book order) · color: H2 color (export order) · both: H2 color, H3 chapter
 */
export function render(exp, groupBy = "chapter", style = "bullet") {
  if (!GROUPINGS.includes(groupBy)) throw new RangeError(`Unknown grouping: ${groupBy}`);
  if (!STYLES.includes(style)) throw new RangeError(`Unknown style: ${style}`);

  const lines = [`# ${mdEscape(exp.title)}`, ""];
  const addGroup = (level, name, notes) => {
    if (!notes.length) return;
    lines.push(`${level} ${mdEscape(name)}`, "", ...block(notes, style), "");
  };

  if (groupBy === "chapter") {
    for (const ch of exp.chapters) addGroup("##", ch, exp.notes.filter((n) => n.chapter === ch));
  } else if (groupBy === "color") {
    for (const c of exp.colors) addGroup("##", c, exp.notes.filter((n) => n.color === c));
  } else {
    for (const c of exp.colors) {
      const inColor = exp.notes.filter((n) => n.color === c);
      if (!inColor.length) continue;
      lines.push(`## ${mdEscape(c)}`, "");
      for (const ch of exp.chapters) addGroup("###", ch, inColor.filter((n) => n.chapter === ch));
    }
  }
  return lines.join("\n").trimEnd() + "\n";
}

export function outputFilename(title) {
  let safe = title.replace(/[\\/:*?"<>|\x00-\x1f]/g, "").trim().replace(/^\.+|\.+$/g, "");
  safe = safe || "Play Books";
  return `${Array.from(safe).slice(0, 120).join("")} - Notes.md`;
}
