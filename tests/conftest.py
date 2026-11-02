from pathlib import Path

import pytest

from notes_parser import load, parse

FIXTURE = Path(__file__).parent / "fixtures" / "art_of_thinking_clearly.md"


@pytest.fixture(scope="session")
def raw_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def parsed(raw_text):
    return parse(raw_text)


@pytest.fixture(scope="session")
def export(raw_text):
    return load(raw_text)


def find(export, start: str):
    """Notes whose highlight starts with `start`."""
    return [n for n in export.notes if n.highlight.startswith(start)]
