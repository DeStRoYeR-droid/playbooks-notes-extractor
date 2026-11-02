/**
 * Light/dark toggle. With no saved choice the page follows the system setting;
 * pressing the button saves an explicit choice (see theme-init.js for first paint).
 */

const KEY = "theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");

const current = () => document.documentElement.dataset.theme || (media.matches ? "dark" : "light");

function label(button) {
  const next = current() === "dark" ? "light" : "dark";
  const text = `Switch to ${next} theme`;
  button.setAttribute("aria-label", text);
  button.title = text;
}

function setThemeColor(theme) {
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
    meta.content = theme === "dark" ? "#321E48" : "#EDE9E6";
    meta.removeAttribute("media");
  }
}

export function initThemeToggle(button) {
  label(button);
  button.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* private mode: the choice lasts for this page view only */
    }
    setThemeColor(next);
    label(button);
  });
  media.addEventListener("change", () => label(button));
}
