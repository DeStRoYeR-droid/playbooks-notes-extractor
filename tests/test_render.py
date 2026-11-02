import re

import pytest

from notes_parser import render
from notes_parser.models import Export, Note
from notes_parser.render import md_escape, output_filename


def headings(md: str, level: int) -> list[str]:
    return re.findall(rf"^{'#' * level} (.+)$", md, re.M)


@pytest.mark.parametrize("group_by", ["chapter", "color", "both"])
@pytest.mark.parametrize("style", ["bullet", "quote"])
def test_single_h1_is_title(export, group_by, style):
    md = render(export, group_by, style)
    assert headings(md, 1) == ["The Art of Thinking Clearly"]
    assert md.startswith("# The Art of Thinking Clearly\n")
    assert md.endswith("\n") and not md.endswith("\n\n")


def test_by_chapter(export):
    md = render(export, "chapter", "bullet")
    assert headings(md, 2) == export.chapters
    assert headings(md, 3) == []


def test_by_color(export):
    md = render(export, "color", "bullet")
    assert headings(md, 2) == ["Yellow", "Green", "Blue", "Red"]
    assert headings(md, 3) == []


def test_both_is_color_then_chapter(export):
    md = render(export, "both", "bullet")
    assert headings(md, 2) == ["Yellow", "Green", "Blue", "Red"]
    h3 = headings(md, 3)
    assert set(h3) <= set(export.chapters)
    # Each color block lists its chapters in book order.
    blocks = re.split(r"^## .+$", md, flags=re.M)[1:]
    for block in blocks:
        chapters = headings(block, 3)
        assert chapters == sorted(chapters, key=export.chapters.index)


@pytest.mark.parametrize("group_by", ["chapter", "color", "both"])
def test_every_note_once(export, group_by):
    md = render(export, group_by, "bullet")
    assert len(re.findall(r"^- ", md, re.M)) == len(export.notes)
    assert len(re.findall(r"^    - \*", md, re.M)) == 12


def test_bullet_comment_is_italic_subbullet(export):
    md = render(export, "chapter", "bullet")
    assert (
        "- The unsuccessful don’t write books or give lectures on their failures.\n"
        "    - *Harsh reality, everybody is interested" in md
    )


def test_quote_style(export):
    md = render(export, "chapter", "quote")
    assert "> The unsuccessful don’t write books or give lectures on their failures.\n\n**Note:** Harsh reality" in md
    assert len(re.findall(r"^> ", md, re.M)) == len(export.notes)
    assert len(re.findall(r"^\*\*Note:\*\* ", md, re.M)) == 12
    # Consecutive quotes are separate blocks.
    assert not re.search(r"^> .*\n> ", md, re.M)


def test_no_page_numbers_dates_or_links(export):
    md = render(export, "chapter", "bullet")
    assert "play.google.com" not in md
    assert not re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}", md)


def test_empty_groups_skipped():
    e = Export(
        title="T",
        notes=[Note("Ch 2", "Blue", "Hi.")],
        chapters=["Ch 1", "Ch 2"],
        colors=["Yellow", "Blue"],
    )
    assert headings(render(e, "chapter"), 2) == ["Ch 2"]
    assert headings(render(e, "color"), 2) == ["Blue"]


def test_md_escape():
    assert md_escape("a *b* c_d") == r"a \*b\* c\_d"
    assert md_escape("# not a heading") == r"\# not a heading"
    assert md_escape("1. not a list") == r"\1. not a list"
    assert md_escape("$10 is fine") == "$10 is fine"


def test_bad_options(export):
    with pytest.raises(ValueError):
        render(export, "page", "bullet")
    with pytest.raises(ValueError):
        render(export, "chapter", "table")


@pytest.mark.parametrize(
    "title, expected",
    [
        ("The Art of Thinking Clearly", "The Art of Thinking Clearly - Notes.md"),
        ('Why? A "Book": Part 1/2', "Why A Book Part 12 - Notes.md"),
        ("", "Play Books - Notes.md"),
    ],
)
def test_output_filename(title, expected):
    assert output_filename(title) == expected
