/** Small DOM helpers shared by the UI modules. */

export const byId = (id) => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
};

export const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;

export const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Read a message to screen-reader users without moving focus. */
export function announce(text) {
  const el = document.getElementById("announcer");
  if (!el) return;
  el.textContent = "";
  // A fresh text node on the next frame makes repeated messages announce again.
  requestAnimationFrame(() => { el.textContent = text; });
}

/** Move keyboard focus to `el` and bring it into view, respecting reduced motion. */
export function focusAndReveal(el) {
  el.focus({ preventScroll: true });
  el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
}
