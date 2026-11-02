import re

from notes_parser.png import average_color, color_from_data_uri, nearest_color_name


def test_swatches_decode_to_their_colors(raw_text):
    uris = dict(re.findall(r"^\[(image\d+)\]: <(data:[^>]+)>", raw_text, re.M))
    assert color_from_data_uri(uris["image2"]) == "Yellow"
    assert color_from_data_uri(uris["image3"]) == "Green"
    assert color_from_data_uri(uris["image4"]) == "Blue"
    assert color_from_data_uri(uris["image5"]) == "Red"


def test_far_colors_are_not_guessed():
    assert nearest_color_name((0, 0, 0)) is None
    assert nearest_color_name((250, 250, 250)) is None


def test_garbage_input():
    assert average_color(b"not a png") is None
    assert color_from_data_uri("data:image/png;base64,!!!!") is None
    assert color_from_data_uri("nothing here") is None
