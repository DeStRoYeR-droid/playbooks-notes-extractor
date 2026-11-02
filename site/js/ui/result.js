/**
 * Result view: book summary, color spectrum, options, download/copy and the
 * read-only preview. Changing an option re-renders from the parsed export already
 * in memory (no re-reading the file), and each layout is rendered at most once.
 */

import { announce, byId, focusAndReveal, plural } from "./dom.js";

const SWATCH = {
  Yellow: "var(--hl-yellow)",
  Green: "var(--hl-green)",
  Blue: "var(--hl-blue)",
  Red: "var(--hl-red)",
};
const GROUP_TEXT = { chapter: "Grouped by chapter", color: "Grouped by color", both: "Grouped by color, then chapter" };
const STYLE_TEXT = { bullet: "as bullet points", quote: "as quote blocks" };

export function initResult({ render, onReset, onCopyResult }) {
  const section = byId("result");
  const heading = byId("book-title");
  const form = byId("options");
  const preview = byId("preview");
  const previewMeta = byId("preview-meta");
  const filenameEl = byId("filename");
  const colorNotice = byId("color-notice");

  let current = null; // { exp, summary, filename, cache: Map }

  const chosen = (name) => form.querySelector(`input[name="${name}"]:checked`).value;

  function markdownFor(groupBy, style) {
    const key = `${groupBy}|${style}`;
    if (!current.cache.has(key)) current.cache.set(key, render(current.exp, groupBy, style));
    return current.cache.get(key);
  }

  function updatePreview() {
    if (!current) return;
    const groupBy = chosen("group_by");
    const style = chosen("style");
    const md = markdownFor(groupBy, style);
    if (preview.textContent !== md) {
      preview.textContent = md;
      preview.scrollTop = 0;
    }
    previewMeta.textContent = `${GROUP_TEXT[groupBy]}, ${STYLE_TEXT[style]}.`;
  }

  function drawSpectrum(colors, total) {
    const bar = byId("spectrum");
    const legend = byId("legend");
    const segments = [];
    const items = [];
    const parts = [];
    for (const [name, count] of Object.entries(colors)) {
      const fill = SWATCH[name] || "var(--hl-unknown)";
      const seg = document.createElement("span");
      seg.style.width = `${(count / total) * 100}%`;
      seg.style.background = fill;
      segments.push(seg);

      const li = document.createElement("li");
      const chip = document.createElement("span");
      chip.className = "swatch";
      chip.style.background = fill;
      chip.setAttribute("aria-hidden", "true");
      const b = document.createElement("b");
      b.textContent = count.toLocaleString();
      li.append(chip, `${name} `, b);
      items.push(li);
      parts.push(`${name} ${count}`);
    }
    bar.replaceChildren(...segments);
    legend.replaceChildren(...items);
    bar.setAttribute("aria-label", `Highlights by color: ${parts.join(", ")}.`);
    bar.classList.remove("is-growing");
    void bar.offsetWidth; // restart the one-time grow animation for a new book
    bar.classList.add("is-growing");
  }

  function show(exp, summary, filename) {
    current = { exp, summary, filename, cache: new Map() };

    heading.textContent = summary.title;
    const comments = summary.comments
      ? `, ${summary.comments.toLocaleString()} with your comment${summary.comments === 1 ? "" : "s"}`
      : "";
    byId("counts").textContent = `${plural(summary.notes, "note")} across ${plural(summary.chapters, "chapter")}${comments}`;
    drawSpectrum(summary.colors, summary.notes);

    const fixes = [];
    if (summary.merged) fixes.push(`rejoined ${plural(summary.merged, "highlight")} that Play Books had split in two`);
    if (summary.duplicatesRemoved) fixes.push(`removed ${plural(summary.duplicatesRemoved, "duplicate")}`);
    byId("cleanup").textContent = fixes.length ? `Tidied up: ${fixes.join(" and ")}.` : "";

    const colorsOk = summary.colorsDetected;
    for (const id of ["g-color", "g-both"]) byId(id).disabled = !colorsOk;
    if (!colorsOk && chosen("group_by") !== "chapter") byId("g-chapter").checked = true;
    colorNotice.hidden = colorsOk;

    filenameEl.textContent = `Saves as “${filename}”`;
    section.hidden = false;
    updatePreview();
    focusAndReveal(heading);
    announce(`Loaded ${summary.title}: ${plural(summary.notes, "note")} across ${plural(summary.chapters, "chapter")}.`);
  }

  function hide() {
    current = null;
    section.hidden = true;
    preview.textContent = "";
  }

  form.addEventListener("change", updatePreview);
  form.addEventListener("submit", (e) => e.preventDefault());

  byId("download").addEventListener("click", () => {
    if (!current) return;
    const md = markdownFor(chosen("group_by"), chosen("style"));
    const url = URL.createObjectURL(new Blob([md], { type: "text/markdown;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: current.filename });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    announce(`Downloaded ${current.filename}.`);
  });

  byId("copy").addEventListener("click", async () => {
    if (!current) return;
    const md = markdownFor(chosen("group_by"), chosen("style"));
    try {
      await navigator.clipboard.writeText(md);
      onCopyResult(true);
    } catch {
      onCopyResult(false);
    }
  });

  byId("reset").addEventListener("click", () => {
    hide();
    onReset();
  });

  return { show, hide };
}
