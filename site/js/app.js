/**
 * Entry point: wires the UI modules together.
 * The converter is a separate chunk loaded on demand (and warmed when the page is
 * idle), so the landing page itself ships only the small UI modules.
 */

import { announce } from "./ui/dom.js";
import { installErrorBoundary } from "./ui/error-boundary.js";
import { initSectionNav } from "./ui/nav.js";
import { initResult } from "./ui/result.js";
import { initThemeToggle } from "./ui/theme.js";
import { initUpload, readExport, UploadError } from "./ui/upload.js";

installErrorBoundary();
initThemeToggle(document.getElementById("theme-toggle"));
initSectionNav(document.getElementById("nav-how"), document.getElementById("how-it-works"));

let converterPromise = null;
const loadConverter = () => (converterPromise ??= import("./converter/index.js"));
let converter = null; // resolved module, set on first use

/** Errors the reader can fix: show them next to the upload area. */
const isReaderError = (err) =>
  err instanceof UploadError || err?.name === "NotAPlayBooksExport" || err?.name === "NoHighlights";

const result = initResult({
  render: (exp, groupBy, style) => converter.render(exp, groupBy, style),
  onReset: () => {
    upload.clearError();
    upload.focus();
  },
  onCopyResult: (ok) =>
    announce(ok ? "Markdown copied to the clipboard." : "Couldn't copy here. Use Download Markdown instead."),
});

const upload = initUpload({
  async onFile(file) {
    upload.clearError();
    upload.setState("busy", `Reading ${file.name}…`);
    try {
      const [text, mod] = await Promise.all([readExport(file), loadConverter()]);
      converter = mod;
      const exp = await mod.load(text);
      result.show(exp, mod.summarize(exp), mod.outputFilename(exp.title));
    } catch (err) {
      result.hide();
      if (!isReaderError(err)) throw err; // unexpected: the error boundary takes over
      upload.showError(err.message);
    } finally {
      upload.setState("ready");
    }
  },
});

const whenIdle = window.requestIdleCallback || ((cb) => setTimeout(cb, 1500));
whenIdle(() => loadConverter().catch(() => { converterPromise = null; /* retried on first use */ }));
