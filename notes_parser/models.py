from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Note:
    """One highlight from the export.

    Only `chapter`, `color`, `highlight` and `comment` reach the output. `date` and
    `page` are kept internally because the cleanup step uses them to rejoin highlights
    that Play Books split in two.
    """

    chapter: str
    color: str
    highlight: str
    comment: str | None = None
    date: str | None = field(default=None, repr=False, compare=False)
    page: int | None = field(default=None, repr=False, compare=False)


@dataclass
class Export:
    """A parsed Play Books export."""

    title: str
    notes: list[Note]
    chapters: list[str]  # book order
    colors: list[str]  # order of the export's color section
    raw_count: int = 0  # note rows found before cleanup
    merged: int = 0  # split highlights rejoined
    duplicates: int = 0  # contained duplicates dropped
    skipped: int = 0  # bookmarks / rows with no highlighted text
    colors_detected: bool = True  # False when no image could be mapped to a color

    def summary(self) -> dict:
        color_counts = {c: 0 for c in self.colors}
        for n in self.notes:
            color_counts[n.color] = color_counts.get(n.color, 0) + 1
        used_chapters = {n.chapter for n in self.notes}
        return {
            "title": self.title,
            "notes": len(self.notes),
            "chapters": sum(1 for c in self.chapters if c in used_chapters),
            "colors": {c: k for c, k in color_counts.items() if k},
            "colors_detected": self.colors_detected,
            "raw_rows": self.raw_count,
            "merged": self.merged,
            "duplicates_removed": self.duplicates,
            "skipped": self.skipped,
        }


class NotAPlayBooksExport(ValueError):
    """Raised when the input does not look like a Play Books notes export."""

    def __init__(self, message: str = "This doesn't look like a Play Books notes export.") -> None:
        super().__init__(message)


class NoHighlights(NotAPlayBooksExport):
    """Raised when the file is a Play Books export but holds no highlights."""

    def __init__(
        self,
        message: str = "This export has no highlights yet. Highlight something in Play Books, "
        "let it sync, then download the notes again.",
    ) -> None:
        super().__init__(message)
