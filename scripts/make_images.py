"""Regenerate the app icons and the Open Graph image from HTML/SVG templates.

    python3 scripts/make_images.py

Needs the dev dependency `playwright` (and `python -m playwright install chromium`,
or set CHROME_PATH to an installed Chrome).
Run it after changing the palette, the logo mark or the site name. Outputs go to
site/icons/ and site/og-image.png.
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FONTS = "fonts"  # relative to the temporary page written into site/

BARS = """
  <rect x="{x}" y="{y1}" width="{w1}" height="{h}" rx="{r}" fill="#FBC02D"/>
  <rect x="{x}" y="{y2}" width="{w2}" height="{h}" rx="{r}" fill="#8BC34A"/>
  <rect x="{x}" y="{y3}" width="{w3}" height="{h}" rx="{r}" fill="#26C6DA"/>
  <rect x="{x}" y="{y4}" width="{w4}" height="{h}" rx="{r}" fill="#FF7043"/>
"""


def mark(size: int, *, rounded: bool, inset: float) -> str:
    """The four-bar mark on an umber tile. `inset` keeps bars inside a maskable safe zone."""
    s = size
    pad = s * inset
    inner = s - 2 * pad
    h = inner * 0.13
    gap = inner * 0.07
    top = pad + (inner - (4 * h + 3 * gap)) / 2
    x = pad + inner * 0.03
    bars = BARS.format(
        x=x, h=h, r=h * 0.38,
        y1=top, y2=top + h + gap, y3=top + 2 * (h + gap), y4=top + 3 * (h + gap),
        w1=inner * 0.94, w2=inner * 0.68, w3=inner * 0.84, w4=inner * 0.47,
    )
    rx = s * 0.22 if rounded else 0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
        f'<rect width="{s}" height="{s}" rx="{rx}" fill="#5C4F4A"/>{bars}</svg>'
    )


ICONS = {
    "favicon-32.png": (32, dict(rounded=True, inset=0.2)),
    "apple-touch-icon.png": (180, dict(rounded=False, inset=0.2)),
    "icon-192.png": (192, dict(rounded=True, inset=0.2)),
    "icon-512.png": (512, dict(rounded=True, inset=0.2)),
    "icon-maskable-512.png": (512, dict(rounded=False, inset=0.27)),
}

OG = f"""<!doctype html><html><head><style>
@font-face {{ font-family: Belgrano; src: url({FONTS}/belgrano-latin-400.woff2) format("woff2"); }}
@font-face {{ font-family: "Google Sans"; font-weight: 400 700; src: url({FONTS}/google-sans-latin-wght.woff2) format("woff2"); }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 630px; background: #EDE9E6; color: #5C4F4A; font-family: "Google Sans", sans-serif;
  display: grid; grid-template-columns: 1fr 470px; gap: 56px; padding: 72px 72px 0; position: relative; overflow: hidden; }}
.brand {{ display: flex; align-items: center; gap: 14px; font-family: Belgrano; font-size: 30px; }}
h1 {{ font-family: Belgrano; font-weight: 400; font-size: 58px; line-height: 1.1; margin-top: 52px; letter-spacing: -0.5px; }}
p {{ margin-top: 26px; font-size: 25px; line-height: 1.4; color: #4E665E; max-width: 560px; }}
.card {{ margin-top: 8px; background: #F7F4F2; border: 1px solid #D6CCC4; border-radius: 18px; padding: 30px 32px;
  font: 17px/1.75 ui-monospace, "DejaVu Sans Mono", monospace; color: #5C4F4A; white-space: pre-wrap; height: 448px; overflow: hidden; }}
.card .h {{ color: #5C766D; font-weight: 700; }}
.strip {{ position: absolute; left: 0; right: 0; bottom: 0; height: 22px; display: flex; }}
.strip span {{ height: 100%; }}
</style></head><body>
<div>
  <div class="brand">{mark(44, rounded=True, inset=0.2)}<span>Play Books Notes</span></div>
  <h1>Your Play Books highlights, as clean Markdown</h1>
  <p>Group by chapter or color, keep your comments, download a tidy .md file.</p>
</div>
<div class="card"><span class="h"># The Art of Thinking Clearly</span>

<span class="h">## 1: Survivorship Bias</span>

- In daily life, because triumph is made more visible than failure, you overestimate your chances of succeeding
- The unsuccessful don’t write books or give lectures on their failures.
    - *Harsh reality…*

<span class="h">## 5: Sunk Cost Fallacy</span>

- The sunk cost fallacy is most dangerous when we have invested a lot…</div>
<div class="strip"><span style="width:8.5%;background:#FBC02D"></span><span style="width:31.1%;background:#8BC34A"></span><span style="width:38.5%;background:#26C6DA"></span><span style="width:21.9%;background:#FF7043"></span></div>
</body></html>"""


def main() -> None:
    icons = SITE / "icons"
    icons.mkdir(exist_ok=True)
    with sync_playwright() as p:
        # CHROME_PATH lets you use an installed Chrome instead of Playwright's download.
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
        for name, (size, opts) in ICONS.items():
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f'<html><body style="margin:0;background:transparent">{mark(size, **opts)}</body></html>')
            page.screenshot(path=icons / name, omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
            page.close()
        # Written next to site/fonts so the page can load the self-hosted fonts.
        tmp = SITE / "_og-template.html"
        tmp.write_text(OG, encoding="utf-8")
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 630})
            page.goto(tmp.as_uri())
            page.evaluate("document.fonts.ready")
            if page.evaluate("[...document.fonts].some(f => f.family.includes('Belgrano') && f.status !== 'loaded')"):
                raise SystemExit("Fonts did not load; check site/fonts.")
            page.screenshot(path=SITE / "og-image.png")
        finally:
            tmp.unlink(missing_ok=True)
        browser.close()
    print("Wrote", ", ".join(ICONS), "and og-image.png")


if __name__ == "__main__":
    main()
