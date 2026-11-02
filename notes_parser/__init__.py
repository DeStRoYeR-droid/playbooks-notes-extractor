"""Turn a Google Play Books notes export (Markdown) into clean, grouped Markdown notes."""

from .clean import clean
from .models import Export, NoHighlights, Note, NotAPlayBooksExport
from .parse import parse
from .render import output_filename, render


def load(markdown: str) -> Export:
    """Parse and clean an export in one step."""
    return clean(parse(markdown))


def convert(markdown: str, group_by: str = "chapter", style: str = "bullet") -> tuple[Export, str]:
    """Parse, clean and render. Returns the cleaned export and the Markdown output."""
    export = load(markdown)
    return export, render(export, group_by, style)  # type: ignore[arg-type]


__all__ = [
    "Export",
    "NoHighlights",
    "Note",
    "NotAPlayBooksExport",
    "clean",
    "convert",
    "load",
    "output_filename",
    "parse",
    "render",
]
