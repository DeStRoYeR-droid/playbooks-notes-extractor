# Play Books Notes

Turn a Google Play Books notes export into clean Markdown: only your highlighted passages and
your own comments, grouped by chapter, by highlight color, or by color then chapter.

**Live site:** https://destroyer-droid.github.io/playbooks-notes-extractor/

Drop the `.md` file that Google Docs downloads for a book's notes, pick a layout, and download
`<Book title> - Notes.md`. Everything runs in the browser; the file is never uploaded.

## Tech stack

| Part | What | Why |
| --- | --- | --- |
| Site | Plain HTML, CSS and JavaScript modules | GitHub Pages serves static files; no framework or build step needed |
| Converter | `site/js/converter/` (JavaScript, no dependencies) | Runs in the browser, about 15 KB, loaded only when needed |
| Reference implementation | `notes_parser/` (Python, standard library only) | Command-line use; a parity test keeps it byte-identical to the JS converter |
| Fonts | Belgrano (headings), Google Sans (text), self-hosted | No third-party requests; SIL Open Font License |
| Tests | `node --test`, pytest, Playwright | Converter, parity, and browser interactions |
| Hosting | GitHub Pages via GitHub Actions | Tests run before every deploy |

The site has **no runtime dependencies**. Dev tools are `pytest` and `playwright` (Python) and
Node 20+ for the JS tests.

## Features

- Drag-and-drop or a "Choose a Markdown file" button (keyboard accessible).
- The first screen holds only the headline and the upload area; the "How it works" section
  (getting the export from Drive, what is kept and dropped, a before/after of the cleanup, and the
  privacy model) starts exactly one screen down. Its nav link is marked current while it is on
  screen.
- Navbar: How it works, a Buy Me a Coffee link (opens in a new tab; icon only on phones), and the
  theme toggle.
- Grouping: by chapter, by color, or color then chapter. Note style: bullet points or quote blocks.
- Output: the book title as the only H1; chapter names (with their numbers) or colors as H2; in
  "color, then chapter", chapters are H3. Your comments appear as italic sub-bullets, or as
  `**Note:**` lines under quote blocks. Page numbers, dates, links and images are dropped.
- Cleanup: rejoins highlights Play Books split in two, drops contained duplicates, removes
  Markdown escapes (see [Cleanup rules](#cleanup-rules)).
- Read-only preview, download, and copy to clipboard. Changing an option re-renders from memory
  without re-reading the file.
- Summary with a color bar of your highlights, the note count and the cleanup done.
- States: initial loading, busy, invalid file, wrong type, empty or oversized file, export with no
  highlights, colors unreadable (color grouping turns off), and a global error boundary.
- Light and dark themes (follows the system; a toggle saves your choice), four layouts
  (mobile < 640px, tablet 640–1024px, desktop 1024–1440px, large > 1440px).
- Accessibility: one H1 per page, landmarks, skip link, visible focus, focus moved to new
  results, live announcements, labelled controls, WCAG AA contrast, reduced-motion support.
- Custom 404 page, `robots.txt`, `sitemap.xml`, web app manifest, icons, canonical URL, Open
  Graph and Twitter card metadata, and a Content-Security-Policy.

## Project structure

```
site/                        ← everything GitHub Pages serves
  index.html                 converter page
  404.html                   not-found page (absolute /playbooks-notes/ paths)
  css/styles.css             tokens (light/dark), layout, components, breakpoints
  js/
    app.js                   entry: wires the UI modules, lazy-loads the converter
    theme-init.js            applies a saved theme before first paint
    not-found.js             404 page script
    ui/                      dom.js, upload.js, result.js, theme.js, nav.js, error-boundary.js
    converter/               parse.js, clean.js, render.js, png.js, errors.js, index.js
  fonts/                     Belgrano + Google Sans (woff2) and their licences
  icons/                     favicon.svg/png, apple-touch-icon, 192/512 and maskable icons
  og-image.png               1200×630 social preview
  robots.txt  sitemap.xml  manifest.webmanifest  .nojekyll
notes_parser/                Python reference implementation + CLI
scripts/
  serve.py                   local server that behaves like GitHub Pages
  convert.mjs                command-line converter using the browser code
  make_images.py             regenerates icons and og-image.png
tests/
  js/                        converter unit tests (node --test)
  test_*.py                  Python parser, renderer, PNG fallback, JS/Python parity
  e2e/                       browser tests (Playwright)
  fixtures/                  a real Play Books export
.github/workflows/pages.yml  test, then deploy to GitHub Pages
```

## Run locally

```bash
python3 scripts/serve.py          # http://127.0.0.1:8000/playbooks-notes/
```

`serve.py` serves `site/` under `/playbooks-notes/` and answers unknown paths with `404.html`,
exactly like GitHub Pages. (Opening `index.html` straight from disk won't work: browsers block
JavaScript modules on `file://` URLs.)

Command line, no browser:

```bash
node scripts/convert.mjs "Notes from Book.md" both quote > notes.md
python3 -m notes_parser "Notes from Book.md" --group color --style bullet
```

## Tests

```bash
npm test                                   # JS converter (no install needed)
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium     # once, for the browser tests
python3 -m pytest                          # Python, parity and browser tests
```

To use an installed Chrome instead of Playwright's download, set `CHROME_PATH=/path/to/chrome`.

## Build

There is no build step. `site/` is deployed as it is. When you change the palette, logo or name,
regenerate the images:

```bash
python3 scripts/make_images.py
```

## Deploy (GitHub Pages)

1. Push the repository to GitHub as `playbooks-notes`.
2. In the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Push to `main`. The workflow runs every test, then publishes `site/`.

The site appears at `https://<user>.github.io/playbooks-notes/`.

**Renaming the repository or using a custom domain** changes the site URL. Update it in:
`site/index.html` (canonical, `og:url`, `og:image`), `site/404.html` (the `/playbooks-notes/`
paths), `site/robots.txt`, `site/sitemap.xml`, and `BASE` in `scripts/serve.py`.

`robots.txt` is only read at a domain root. On a project page (`/playbooks-notes/`) it is
advisory; submit `sitemap.xml` in Google Search Console instead. It takes full effect on a user
site or a custom domain.

No environment variables or secrets are used, so there is no `.env.example`.

## Changing the conversion

The JavaScript converter (`site/js/converter/`) and `notes_parser/` mirror each other module by
module. Change both, then run `python3 -m pytest tests/test_parity.py`: it checks that both
produce identical output on the fixture for all six layouts.

### Cleanup rules

| Problem in the export | Rule |
| --- | --- |
| A highlight split into two entries (`…overcome the` / `availability bias.`) | Joined when both halves share chapter, color and date, the first has no comment and doesn't end a sentence, and the second continues it: starts in lower case, or the first ends on a word like *the*, *of*, *our*. Across a page turn, only a short tail (three words or fewer) is joined. |
| The same passage highlighted twice | A highlight wholly inside its neighbour (same chapter and color) is dropped. |
| Markdown escapes (`\$10`, `Impossible\!`) | Removed. |
| No "Annotations by color" section | Each color swatch PNG is decoded and matched to the nearest Play Books color. |

On the sample export: 370 highlights → 18 rejoined, 1 duplicate dropped → 351 notes.

## Security and privacy

- The file is read with the File API and never leaves the device; the site makes no network
  requests after loading.
- Content-Security-Policy (meta tag): scripts, styles and fonts from the site's own origin only;
  no inline scripts, no `eval`, no third parties. Note text is always inserted as text, never HTML.
- No cookies or analytics. `localStorage` holds only the theme choice.

## Licence notes

Belgrano and Google Sans are under the SIL Open Font License 1.1 (see `site/fonts/`).
Not affiliated with Google.
