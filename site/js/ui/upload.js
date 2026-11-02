/**
 * Upload area: drag-and-drop plus a "Choose a Markdown file" button.
 * Checks the file (type, size, encoding) and hands its text to `onText`.
 */

import { byId } from "./dom.js";

export const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED = /\.(md|markdown)$/i;

export class UploadError extends Error {}

/** Read a File as UTF-8 text, or throw an UploadError explaining what's wrong. */
export async function readExport(file) {
  if (!ACCEPTED.test(file.name)) {
    throw new UploadError("That isn't a Markdown file. In Google Docs choose File, then Download, then Markdown (.md), and drop that file here.");
  }
  if (file.size === 0) throw new UploadError("This file is empty. Download the notes doc from Google Docs again.");
  if (file.size > MAX_BYTES) {
    throw new UploadError("This file is larger than 10 MB. Play Books exports are usually under 1 MB; check you picked the notes export.");
  }
  const buffer = await file.arrayBuffer();
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
  } catch {
    throw new UploadError("This file isn't readable text. Download the Google Doc again as Markdown (.md).");
  }
}

export function initUpload({ onFile }) {
  const zone = byId("dropzone");
  const button = byId("choose");
  const input = byId("file-input");
  const alert = byId("upload-alert");
  const title = byId("drop-title");
  const idleTitle = title.textContent;
  let depth = 0;

  const api = {
    setState(state, message) {
      zone.dataset.state = state;
      const busy = state !== "ready";
      zone.setAttribute("aria-busy", String(busy));
      button.disabled = busy;
      title.textContent = message || idleTitle;
    },
    showError(message) {
      alert.textContent = message;
      alert.hidden = false;
    },
    clearError() {
      alert.hidden = true;
      alert.textContent = "";
    },
    focus() {
      button.focus();
    },
  };

  const take = (file) => {
    if (!file || zone.dataset.state !== "ready") return;
    onFile(file);
  };

  button.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    take(input.files[0]);
    input.value = ""; // allow choosing the same file again
  });

  // Dropping a file anywhere else must not navigate away from the page.
  for (const type of ["dragover", "drop"]) window.addEventListener(type, (e) => e.preventDefault());

  zone.addEventListener("dragenter", (e) => {
    e.preventDefault();
    depth += 1;
    zone.classList.add("is-dragging");
  });
  zone.addEventListener("dragleave", () => {
    depth = Math.max(0, depth - 1);
    if (!depth) zone.classList.remove("is-dragging");
  });
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    depth = 0;
    zone.classList.remove("is-dragging");
    take(e.dataTransfer?.files?.[0]);
  });

  api.setState("ready");
  return api;
}
