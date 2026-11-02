"""Render cleaned notes as Markdown."""

from __future__ import annotations

import re
from typing import Literal

from .models import Export, Note

GroupBy = Literal["chapter", "color", "both"]
Style = Literal["bullet", "quote"]

_INLINE = re.compile(r"([\\`*_])")
_BLOCK_START = re.compile(r"^(#{1,6}\s|>|[-+*]\s|\d+[.)]\s)")


def md_escape(text: str) -> str:
    """Escape characters that would turn plain note text into Markdown formatting."""
    text = _INLINE.sub(r"\\\1", text)
    if _BLOCK_START.match(text):
        text = "\\" + text
    return text


def _note_lines(note: Note, style: Style) -> list[str]:
    hl = md_escape(note.highlight)
    if style == "bullet":
        lines = [f"- {hl}"]
        if note.comment:
            lines.append(f"    - *{md_escape(note.comment)}*")
        return lines
    lines = [f"> {hl}"]
    if note.comment:
        lines += ["", f"**Note:** {md_escape(note.comment)}"]
    return lines


def _block(notes: list[Note], style: Style) -> list[str]:
    out: list[str] = []
    for i, n in enumerate(notes):
        if style == "quote" and i:
            out.append("")  # separate quote blocks
        out += _note_lines(n, style)
    return out


def render(export: Export, group_by: GroupBy = "chapter", style: Style = "bullet") -> str:
    """Markdown with the book title as the only H1 and one H2 per group.

    - chapter: H2 chapter (book order)
    - color:   H2 color (export order)
    - both:    H2 color, H3 chapter
    """
    if group_by not in ("chapter", "color", "both"):
        raise ValueError(f"Unknown grouping: {group_by}")
    if style not in ("bullet", "quote"):
        raise ValueError(f"Unknown style: {style}")

    lines = [f"# {md_escape(export.title)}", ""]

    def add_group(level: str, name: str, notes: list[Note]) -> None:
        if not notes:
            return
        lines.extend([f"{level} {md_escape(name)}", ""])
        lines.extend(_block(notes, style))
        lines.append("")

    if group_by == "chapter":
        for ch in export.chapters:
            add_group("##", ch, [n for n in export.notes if n.chapter == ch])
    elif group_by == "color":
        for color in export.colors:
            add_group("##", color, [n for n in export.notes if n.color == color])
    else:
        for color in export.colors:
            in_color = [n for n in export.notes if n.color == color]
            if not in_color:
                continue
            lines.extend([f"## {md_escape(color)}", ""])
            for ch in export.chapters:
                add_group("###", ch, [n for n in in_color if n.chapter == ch])

    return "\n".join(lines).rstrip() + "\n"


def output_filename(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", title).strip().strip(".") or "Play Books"
    return f"{safe[:120]} - Notes.md"
