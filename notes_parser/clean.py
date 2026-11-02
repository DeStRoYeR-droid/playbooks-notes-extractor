"""Cleanup: unescape text, rejoin split highlights, drop contained duplicates."""

from __future__ import annotations

import re
from dataclasses import replace

from .models import Export, Note
from .parse import unescape

_CLOSERS = "\"'”’)]»"
_TERMINAL = ".!?…"
_OPENERS = "\"'“‘([«"
# Words a sentence almost never ends on.
_DANGLING = {
    "a", "an", "the", "of", "and", "or", "but", "nor", "to", "in", "on", "at", "by",
    "for", "from", "with", "without", "into", "onto", "than", "that", "which", "who",
    "whose", "our", "their", "your", "my", "his", "her", "its", "is", "are", "was",
    "were", "be", "as", "if", "so", "because", "when", "while", "this", "these", "those",
}


def _ends_sentence(text: str) -> bool:
    t = text.rstrip().rstrip(_CLOSERS).rstrip()
    return bool(t) and t[-1] in _TERMINAL


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def can_merge(a: Note, b: Note) -> bool:
    """True when `b` looks like the second half of a highlight Play Books split in two.

    Both halves share chapter, color and date; the first has no comment and stops
    mid-sentence; and they sit on the same or the next page.
    """
    if a.chapter != b.chapter or a.color != b.color:
        return False
    if a.date != b.date or a.comment:
        return False
    if _ends_sentence(a.highlight):
        return False
    if a.page is not None and b.page is not None:
        if not 0 <= b.page - a.page <= 1:
            return False
    elif a.page != b.page:
        return False
    # Readers often highlight a full sentence without its final period, so a missing
    # period alone is not enough. The second half must continue the sentence: it starts
    # in lower case, or the first half stops on a word that cannot end a sentence.
    last_word = re.sub(r"[^\w']", "", a.highlight.rstrip().rsplit(" ", 1)[-1]).casefold()
    if last_word in _DANGLING:
        return True
    second = b.highlight.lstrip(_OPENERS)
    if not second[:1].islower():
        return False
    # Across a page turn, a lower-case start can just be a new highlight that begins
    # mid-sentence; only accept a short tail there (e.g. "anymore.").
    if a.page is not None and b.page is not None and b.page != a.page:
        return len(second.split()) <= 3
    return True


def merge_fragments(notes: list[Note]) -> tuple[list[Note], int]:
    out: list[Note] = []
    merged = 0
    for n in notes:
        if out and can_merge(out[-1], n):
            prev = out[-1]
            out[-1] = replace(
                prev,
                highlight=f"{prev.highlight.rstrip()} {n.highlight.lstrip()}",
                comment=n.comment,
                page=n.page if n.page is not None else prev.page,
            )
            merged += 1
        else:
            out.append(n)
    return out, merged


def drop_contained(notes: list[Note]) -> tuple[list[Note], int]:
    """Drop a note whose highlight sits wholly inside its neighbour's (same chapter, color)."""
    out: list[Note] = []
    dropped = 0
    for n in notes:
        if out and out[-1].chapter == n.chapter and out[-1].color == n.color:
            prev = out[-1]
            a, b = _norm(prev.highlight), _norm(n.highlight)
            if b in a:  # new one is inside the previous one
                if n.comment and not prev.comment:
                    out[-1] = replace(prev, comment=n.comment)
                dropped += 1
                continue
            if a in b:  # previous one is inside the new one
                keep = n if n.comment or not prev.comment else replace(n, comment=prev.comment)
                out[-1] = keep
                dropped += 1
                continue
        out.append(n)
    return out, dropped


def clean(export: Export) -> Export:
    """Unescape, merge split highlights and drop contained duplicates (in that order)."""
    notes = [
        replace(
            n,
            highlight=re.sub(r"\s+", " ", unescape(n.highlight)).strip(),
            comment=(re.sub(r"\s+", " ", unescape(n.comment)).strip() or None) if n.comment else None,
        )
        for n in export.notes
    ]
    notes = [n for n in notes if n.highlight]
    notes, merged = merge_fragments(notes)
    notes, duplicates = drop_contained(notes)
    return replace(export, notes=notes, merged=merged, duplicates=duplicates)
