"""Parse a Google Play Books notes export (Google Doc downloaded as Markdown).

The export lists every annotation twice: once grouped by color and once grouped by
chapter. We take the notes from the chapter section and use the color section only to
learn which swatch image stands for which color.

Sections are found by structure (H1 blocks that contain H2 groups and note rows), not
by their English heading words.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .models import Export, NoHighlights, Note, NotAPlayBooksExport
from .png import color_from_data_uri

_IMG = r"!\[[^\]]*\]\[(?P<img>[^\]]+)\]"
# `*![][image3] highlight* comment ...`  (first note of a group)
_ROW_A = re.compile(r"^\*\s*" + _IMG + r"\s*(?P<hl>.*?)(?<!\\)\*(?P<rest>.*)$")
# `![][image3] *highlight* comment ...`
_ROW_B = re.compile(r"^" + _IMG + r"\s*\*(?P<hl>.*?)(?<!\\)\*(?P<rest>.*)$")
# `![][image3] text without italics ...` (defensive)
_ROW_C = re.compile(r"^" + _IMG + r"\s*(?P<rest>.*)$")

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_LINK = r"\[(?P<page>[^\]]*)\]\((?P<url>[^)]*)\)"
_TRAIL_EN = re.compile(r"^(?P<comment>.*?)\s*(?P<date>(?:" + _MONTHS + r") \d{1,2}, \d{4})\s*" + _LINK + r"\s*$")
# Fallback for other date formats: whatever date-like token sits right before the link.
_TRAIL_ANY = re.compile(
    r"^(?P<comment>.*?)\s*(?P<date>\S+ \d{1,2},? \d{4}|\d{1,2}\.? \S+ \d{4}|\d{1,4}[./-]\d{1,2}[./-]\d{1,4})?\s*"
    + _LINK
    + r"\s*$"
)
_IMAGE_DEF = re.compile(r"^\[(?P<img>[^\]]+)\]:\s*<?(?P<uri>data:image/[^>\s]+)>?\s*$", re.M)
_ITALIC = re.compile(r"(?<!\\)\*(.+?)(?<!\\)\*")
_COLOR_WORDS = {"yellow", "green", "blue", "red", "orange", "purple", "pink"}
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$>|~\"'<=&:])")


def unescape(text: str) -> str:
    """Undo the backslash escapes Google Docs adds when exporting Markdown."""
    return _ESCAPE.sub(r"\1", text)


def _clean_heading(line: str) -> str:
    text = line.lstrip("#").strip()
    while len(text) >= 2 and text[0] == text[-1] and text[0] in "*_":
        text = text[1:-1].strip()
    return unescape(text)


def _row_cell(line: str) -> str | None:
    """Inner text of a one-cell table row, or None if the line is not a note row."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or re.fullmatch(r"\|[\s:\-|]*\|", s):
        return None
    inner = s[1:-1].strip()
    if "![" not in inner:
        return None
    return inner


def parse_row(cell: str) -> dict | None:
    """Split one note cell into image id, raw highlight, raw comment, date and page."""
    m = _ROW_A.match(cell) or _ROW_B.match(cell)
    if m:
        img, hl, rest = m.group("img"), m.group("hl").strip(), m.group("rest")
    else:
        m = _ROW_C.match(cell)
        if not m:
            return None
        img, hl, rest = m.group("img"), "", m.group("rest")

    t = _TRAIL_EN.match(rest) or _TRAIL_ANY.match(rest)
    if t:
        comment, date, page_text = t.group("comment"), t.group("date"), t.group("page")
    else:
        comment, date, page_text = rest, None, ""

    if not hl and comment.strip():
        # No italics at all: treat the text as the highlight.
        hl, comment = comment.strip(), ""

    page_digits = re.sub(r"\D", "", page_text or "")
    return {
        "img": img,
        "highlight": hl,
        "comment": comment.strip() or None,
        "date": date,
        "page": int(page_digits) if page_digits else None,
    }


def _sections(lines: list[str]) -> list[list[str]]:
    """Group lines into H1 blocks; keep only blocks that hold H2 groups with note rows."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^#\s", line):
            blocks.append(current)
            current = []
        else:
            current.append(line)
    blocks.append(current)
    return [
        b
        for b in blocks
        if any(re.match(r"^##\s", l) for l in b) and any(_row_cell(l) for l in b)
    ]


def _grouped_rows(block: list[str]) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    group = ""
    for line in block:
        if re.match(r"^##\s", line):
            group = _clean_heading(line)
            continue
        cell = _row_cell(line)
        if cell is None:
            continue
        row = parse_row(cell)
        if row is not None:
            out.append((group, row))
    return out


def _title(lines: list[str]) -> str:
    for line in lines:
        if re.match(r"^#\s", line):
            break
        if "Cover Image" in line or line.strip().startswith("| !["):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            for c in cells:
                m = _ITALIC.search(c)
                if m and "![" not in m.group(1):
                    return unescape(m.group(1).strip())
    return ""


def parse(markdown: str) -> Export:
    """Parse the export into notes with raw (still escaped) text. Run `clean()` next."""
    text = markdown.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    sections = _sections(lines)
    if not sections:
        raise NotAPlayBooksExport()

    color_rows = _grouped_rows(sections[0]) if len(sections) >= 2 else []
    chapter_rows = _grouped_rows(sections[-1])

    # A single section might be the color section on its own: every group is named like a
    # color and uses exactly one swatch. Then its groups are colors and chapters are unknown.
    if len(sections) == 1:
        imgs_per_group: dict[str, set] = defaultdict(set)
        for g, r in chapter_rows:
            if r["highlight"]:
                imgs_per_group[g].add(r["img"])
        if (
            imgs_per_group
            and all(g.casefold() in _COLOR_WORDS for g in imgs_per_group)
            and all(len(v) == 1 for v in imgs_per_group.values())
        ):
            color_rows = chapter_rows
            chapter_rows = [("Notes", r) for _, r in chapter_rows]

    # Image id -> color name, learned from the color section.
    votes: dict[str, Counter] = defaultdict(Counter)
    color_order: list[str] = []
    for group, row in color_rows:
        if row["highlight"]:
            votes[row["img"]][group] += 1
            if group not in color_order:
                color_order.append(group)
    color_map = {img: c.most_common(1)[0][0] for img, c in votes.items()}

    # Fallback: decode the swatch PNG for any image the color section did not cover.
    data_uris = {m.group("img"): m.group("uri") for m in _IMAGE_DEF.finditer(text)}
    for _, row in chapter_rows:
        img = row["img"]
        if row["highlight"] and img not in color_map and img in data_uris:
            name = color_from_data_uri(data_uris[img])
            if name:
                color_map[img] = name
                if name not in color_order:
                    color_order.append(name)

    notes: list[Note] = []
    chapters: list[str] = []
    skipped = 0
    for chapter, row in chapter_rows:
        if not row["highlight"]:
            skipped += 1  # bookmark or empty entry
            continue
        color = color_map.get(row["img"], "Unknown")
        if color == "Unknown" and "Unknown" not in color_order:
            color_order.append("Unknown")
        if chapter not in chapters:
            chapters.append(chapter)
        notes.append(
            Note(
                chapter=chapter,
                color=color,
                highlight=row["highlight"],
                comment=row["comment"],
                date=row["date"],
                page=row["page"],
            )
        )

    if not notes:
        raise NoHighlights()

    return Export(
        title=_title(lines) or "Play Books Notes",
        notes=notes,
        chapters=chapters,
        colors=color_order,
        raw_count=len(chapter_rows),
        skipped=skipped,
        colors_detected=any(c != "Unknown" for c in color_map.values()) and bool(color_map),
    )
