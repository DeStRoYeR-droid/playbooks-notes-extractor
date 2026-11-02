// Runs before first paint (loaded without defer) so a saved theme never flashes.
(function () {
  try {
    var saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
  } catch (e) {
    /* storage blocked: follow the system theme */
  }
})();
