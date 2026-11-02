/**
 * Global error boundary: any uncaught error or rejected promise from this page
 * replaces the working UI with a calm error panel and a reload button.
 * Errors from browser extensions or other origins are ignored.
 */

import { byId, focusAndReveal } from "./dom.js";

let shown = false;

function fromThisPage(filename) {
  return !filename || filename.startsWith(window.location.origin);
}

export function showAppError(error) {
  console.error(error);
  if (shown) return;
  shown = true;
  for (const id of ["result"]) document.getElementById(id)?.setAttribute("hidden", "");
  const panel = byId("app-error");
  panel.hidden = false;
  const heading = byId("app-error-title");
  heading.tabIndex = -1;
  focusAndReveal(heading);
}

export function installErrorBoundary() {
  byId("reload").addEventListener("click", () => window.location.reload());
  window.addEventListener("error", (event) => {
    // Resource load errors (e.g. a blocked font) are not page crashes.
    if (!(event instanceof ErrorEvent)) return;
    if (!fromThisPage(event.filename)) return;
    if (/ResizeObserver loop/.test(event.message)) return;
    showAppError(event.error || new Error(event.message));
  });
  window.addEventListener("unhandledrejection", (event) => showAppError(event.reason));
}
