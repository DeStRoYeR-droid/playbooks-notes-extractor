"""The browser converter (JavaScript) must give byte-identical output to notes_parser."""

import shutil
import subprocess
from pathlib import Path

import pytest

from notes_parser import convert

from .conftest import FIXTURE

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")


def js_convert(path: Path, group_by: str, style: str) -> str:
    out = subprocess.run(
        [NODE, str(ROOT / "scripts" / "convert.mjs"), str(path), group_by, style],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    return out.stdout


@pytest.mark.parametrize("group_by", ["chapter", "color", "both"])
@pytest.mark.parametrize("style", ["bullet", "quote"])
def test_same_output(group_by, style):
    _, expected = convert(FIXTURE.read_text(encoding="utf-8"), group_by, style)
    assert js_convert(FIXTURE, group_by, style) == expected


def test_same_output_without_color_section(raw_text, tmp_path):
    a, b = raw_text.index("# Annotations by color"), raw_text.index("# All your annotations")
    f = tmp_path / "nocolor.md"
    f.write_text(raw_text[:a] + raw_text[b:], encoding="utf-8")
    _, expected = convert(f.read_text(encoding="utf-8"), "both", "bullet")
    assert js_convert(f, "both", "bullet") == expected
