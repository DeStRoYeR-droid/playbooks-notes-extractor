"""Tiny stdlib-only PNG reader, used only to guess a highlight color from its swatch.

Play Books exports each highlight color as a small solid-color PNG swatch embedded
as a base64 data URI. When the "Annotations by color" section is missing, we decode
the swatch and match its average color to the nearest known highlight color.
"""

from __future__ import annotations

import base64
import struct
import zlib

# Average swatch colors as exported by Google Play Books (measured from a real export;
# the export's color headings name them Yellow, Green, Blue and Red).
KNOWN_COLORS: dict[str, tuple[int, int, int]] = {
    "Yellow": (251, 192, 45),
    "Green": (139, 195, 74),
    "Blue": (38, 198, 218),
    "Red": (255, 112, 67),
}

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}  # PNG color type -> samples per pixel


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def average_color(png_bytes: bytes) -> tuple[int, int, int] | None:
    """Return the mean RGB of the opaque pixels, or None if the PNG is unsupported."""
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    pos, idat, palette, trns = 8, b"", None, None
    width = height = depth = ctype = interlace = None
    while pos + 8 <= len(png_bytes):
        length, kind = struct.unpack(">I4s", png_bytes[pos : pos + 8])
        data = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", data)
        elif kind == b"PLTE":
            palette = [tuple(data[i : i + 3]) for i in range(0, len(data), 3)]
        elif kind == b"tRNS":
            trns = data
        elif kind == b"IDAT":
            idat += data
        elif kind == b"IEND":
            break
    if width is None or depth != 8 or interlace or ctype not in _CHANNELS:
        return None
    if ctype == 3 and palette is None:
        return None

    bpp = _CHANNELS[ctype]
    stride = width * bpp
    try:
        raw = zlib.decompress(idat)
    except zlib.error:
        return None
    if len(raw) < height * (stride + 1):
        return None

    prev = bytearray(stride)
    total = [0, 0, 0]
    count = 0
    for y in range(height):
        start = y * (stride + 1)
        ftype = raw[start]
        line = bytearray(raw[start + 1 : start + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                line[i] = (line[i] + _paeth(a, b, c)) & 0xFF
        prev = line
        for x in range(width):
            px = line[x * bpp : (x + 1) * bpp]
            if ctype == 6:
                r, g, b_, alpha = px
            elif ctype == 2:
                (r, g, b_), alpha = px, 255
            elif ctype == 4:
                r = g = b_ = px[0]
                alpha = px[1]
            elif ctype == 0:
                r = g = b_ = px[0]
                alpha = 255
            else:  # palette
                idx = px[0]
                if idx >= len(palette):
                    continue
                r, g, b_ = palette[idx]
                alpha = trns[idx] if trns and idx < len(trns) else 255
            if alpha < 128:
                continue
            total[0] += r
            total[1] += g
            total[2] += b_
            count += 1
    if not count:
        return None
    return tuple(round(t / count) for t in total)  # type: ignore[return-value]


def nearest_color_name(rgb: tuple[int, int, int], max_distance: float = 120.0) -> str | None:
    """Name of the closest known highlight color, or None if nothing is close enough."""
    best, best_dist = None, float("inf")
    for name, ref in KNOWN_COLORS.items():
        dist = sum((p - q) ** 2 for p, q in zip(rgb, ref)) ** 0.5
        if dist < best_dist:
            best, best_dist = name, dist
    return best if best_dist <= max_distance else None


def color_from_data_uri(uri: str) -> str | None:
    """Guess a highlight color name from a `data:image/png;base64,...` URI."""
    if "base64," not in uri:
        return None
    try:
        png = base64.b64decode(uri.split("base64,", 1)[1].strip(), validate=False)
    except (ValueError, base64.binascii.Error):
        return None
    rgb = average_color(png)
    return nearest_color_name(rgb) if rgb else None
