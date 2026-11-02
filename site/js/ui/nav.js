/** Marks the "How it works" nav link as current while that section is on screen. */

export function initSectionNav(link, section) {
  if (!link || !section || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    },
    { rootMargin: "-30% 0px -50% 0px" },
  );
  observer.observe(section);
}
