"""Command line: python -m notes_parser EXPORT.md [--group chapter|color|both] [--style bullet|quote] [-o OUT.md]"""

import argparse
import sys
from pathlib import Path

from . import NotAPlayBooksExport, convert, output_filename


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="notes_parser", description=__doc__)
    p.add_argument("export", type=Path, help="Play Books notes export (.md)")
    p.add_argument("--group", choices=["chapter", "color", "both"], default="chapter")
    p.add_argument("--style", choices=["bullet", "quote"], default="bullet")
    p.add_argument("-o", "--out", type=Path, help="output file (default: '<title> - Notes.md'; '-' for stdout)")
    args = p.parse_args(argv)

    try:
        export, md = convert(args.export.read_text(encoding="utf-8-sig"), args.group, args.style)
    except NotAPlayBooksExport as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.out and str(args.out) == "-":
        sys.stdout.write(md)
        return 0
    out = args.out or Path(output_filename(export.title))
    out.write_text(md, encoding="utf-8")
    s = export.summary()
    print(f"{out}: {s['notes']} notes, {s['chapters']} chapters, colors {s['colors']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
