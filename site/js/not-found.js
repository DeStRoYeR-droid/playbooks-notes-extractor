import { initThemeToggle } from "./ui/theme.js";

initThemeToggle(document.getElementById("theme-toggle"));

const back = document.getElementById("go-back");
// Only offer "Go back" when there is somewhere to go back to.
if (window.history.length > 1) {
  back.addEventListener("click", () => window.history.back());
} else {
  back.hidden = true;
}
