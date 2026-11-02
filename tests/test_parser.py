"""Parser and cleanup tests against a real Play Books export (PRD test cases)."""

from collections import Counter

import pytest

from notes_parser import NotAPlayBooksExport, load, parse
from notes_parser.parse import parse_row, unescape

from .conftest import find


# --- Structure ------------------------------------------------------------------------

def test_title(export):
    assert export.title == "The Art of Thinking Clearly"


def test_every_highlight_row_is_read(parsed):
    # Header of the chapter section: "370 notes/highlights • 1 bookmark"
    assert parsed.raw_count == 371
    assert len(parsed.notes) == 370
    assert parsed.skipped == 1


def test_color_map_from_color_section(parsed):
    # Header of the color section: "32 yellow • 113 green • 142 blue • 83 red"
    assert parsed.colors == ["Yellow", "Green", "Blue", "Red"]
    assert Counter(n.color for n in parsed.notes) == {"Yellow": 32, "Green": 113, "Blue": 142, "Red": 83}


def test_chapters_in_book_order(export):
    assert export.chapters[0] == "Introduction"
    assert export.chapters[1] == "1: Why You Should Visit Cemeteries: Survivorship Bias"
    assert export.chapters[-1] == "Epilogue"
    assert len(export.chapters) == 98


def test_chapter_heading_unescaped(export):
    assert "7: Beware the “Special Case”: Confirmation Bias (Part 1)" in export.chapters


def test_bookmark_skipped(export):
    assert "A Note on Sources" not in export.chapters


# --- Rows -----------------------------------------------------------------------------

def test_leading_italic_row(export):
    # First note of a chapter is written `*![][image3] text*` instead of `![][image3] *text*`.
    [note] = find(export, "Will he make it big?")
    assert note.color == "Green"
    assert note.comment is None
    assert note.chapter.startswith("1:")


def test_comment_extracted(export):
    [note] = find(export, "If we stop now, it’ll all have been for nothing")
    assert note.highlight.endswith("Another victim of the sunk cost fallacy")
    assert note.comment.startswith("Sunk cos fallacy - When people believe")
    assert "2021" not in note.comment


def test_short_highlight_with_long_comment_left_as_is(export):
    [note] = [n for n in export.notes if n.highlight == "confirmation bias"]
    assert note.comment.startswith("confirmation bias - If something seems")


def test_dates_and_pages_never_leak_into_text(export):
    for n in export.notes:
        for text in (n.highlight, n.comment or ""):
            assert "play.google.com" not in text
            assert "](" not in text


def test_escapes_removed(export):
    assert "and $10 is $10." in find(export, "The contrast effect is at work")[0].highlight
    assert any("Impossible!" in n.highlight for n in export.notes)
    assert not any("\\" in n.highlight or "\\" in (n.comment or "") for n in export.notes)


def test_parse_row_both_italic_styles():
    a = parse_row("*![][image2] Hello there.* my note May 1, 2021 [5](http://x)")
    b = parse_row("![][image2] *Hello there.* my note May 1, 2021 [5](http://x)")
    for row in (a, b):
        assert row["img"] == "image2"
        assert row["highlight"] == "Hello there."
        assert row["comment"] == "my note"
        assert row["date"] == "May 1, 2021"
        assert row["page"] == 5


def test_parse_row_without_comment():
    row = parse_row("![][image4] *Text* July 28, 2021 [286](http://x)")
    assert row["comment"] is None


def test_unescape():
    assert unescape(r"\$10 \- Impossible\! (Part 1\)") == "$10 - Impossible! (Part 1)"


# --- Cleanup --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "joined",
    [
        "We require others’ input to overcome the availability bias.",
        "you systematically overestimate your chances of succeeding",
        "she will never sit down on a cold one anymore.”",  # across a page turn
        "Why invest all of your energy when half will do",
        "we are puppets of our emotions. We make complex decisions",
        "The more recent the information, the better we remember it.",
    ],
)
def test_split_highlights_rejoined(export, joined):
    assert sum(joined in n.highlight for n in export.notes) == 1


@pytest.mark.parametrize(
    "first, second",
    [
        # Both lack a final period but are separate highlights.
        ("you systematically overestimate your chances of succeeding", "The media is not interested"),
        ("If enough scientists examine", "Such (false) studies"),
        # Lower-case start on the next page, but a long, separate highlight.
        ("Your brain pays more attention", "always ask members’ opinions"),
    ],
)
def test_separate_highlights_not_merged(export, first, second):
    a = [n for n in export.notes if first in n.highlight]
    b = [n for n in export.notes if n.highlight.startswith(second)]
    assert a and b and a[0] is not b[0]
    assert second not in a[0].highlight


def test_merge_count(export):
    assert export.merged == 18


def test_contained_duplicate_dropped(export):
    hits = [n for n in export.notes if "We consider things to be more valuable the moment we own them" in n.highlight]
    assert len(hits) == 1
    assert hits[0].highlight.startswith("the endowment effect.")
    assert export.duplicates == 1


def test_final_counts(export):
    assert len(export.notes) == 370 - 18 - 1
    assert sum(1 for n in export.notes if n.comment) == 12


# --- Robustness -----------------------------------------------------------------------

def test_png_fallback_when_color_section_missing(raw_text, parsed):
    start = raw_text.index("# Annotations by color")
    end = raw_text.index("# All your annotations")
    without_colors = raw_text[:start] + raw_text[end:]
    p = parse(without_colors)
    assert [n.color for n in p.notes] == [n.color for n in parsed.notes]


def test_unknown_colors_when_nothing_to_go_on():
    md = "# All your annotations\n\n## *1: A Chapter*\n\n|  ![][image9] *Some text.* May 1, 2021 [5](http://x)  |\n| ----- |\n"
    e = load(md)
    assert e.notes[0].color == "Unknown"
    assert e.colors_detected is False
    assert e.title == "Play Books Notes"


def test_color_section_only(raw_text, parsed):
    """An export holding only the color section still yields every note, under 'Notes'."""
    end = raw_text.index("# All your annotations")
    p = parse(raw_text[:end])
    assert len(p.notes) == 370
    assert p.chapters == ["Notes"]
    assert Counter(n.color for n in p.notes) == {"Yellow": 32, "Green": 113, "Blue": 142, "Red": 83}


def test_crlf_and_bom(raw_text, export):
    e = load("﻿" + raw_text.replace("\n", "\r\n"))
    assert len(e.notes) == len(export.notes)


@pytest.mark.parametrize("text", ["", "# Hello\n\nJust a document.\n", "| a | b |\n| - | - |\n| 1 | 2 |\n"])
def test_not_an_export(text):
    with pytest.raises(NotAPlayBooksExport):
        parse(text)
