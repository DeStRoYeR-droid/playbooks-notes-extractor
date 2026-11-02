/**
 * Guess a highlight color from its swatch PNG (fallback when the export has no
 * "Annotations by color" section). Mirrors notes_parser/png.py.
 * Uses the browser's (and Node's) built-in DecompressionStream, so no library is needed.
 */

export const KNOWN_COLORS = {
  Yellow: [251, 192, 45],
  Green: [139, 195, 74],
  Blue: [38, 198, 218],
  Red: [255, 112, 67],
};

const CHANNELS = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 };
const SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

function paeth(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  return pb <= pc ? b : c;
}

async function inflate(bytes) {
  if (typeof DecompressionStream === "undefined") return null;
  try {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  } catch {
    return null;
  }
}

/** Mean RGB of the opaque pixels, or null when the PNG is unsupported. */
export async function averageColor(png) {
  if (png.length < 8 || SIGNATURE.some((b, i) => png[i] !== b)) return null;
  const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
  let pos = 8;
  let width, height, depth, ctype, interlace, palette = null, trns = null;
  const idat = [];
  while (pos + 8 <= png.length) {
    const length = view.getUint32(pos);
    const kind = String.fromCharCode(...png.subarray(pos + 4, pos + 8));
    const data = png.subarray(pos + 8, pos + 8 + length);
    pos += 12 + length;
    if (kind === "IHDR") {
      const d = new DataView(data.buffer, data.byteOffset, data.byteLength);
      width = d.getUint32(0); height = d.getUint32(4);
      depth = data[8]; ctype = data[9]; interlace = data[12];
    } else if (kind === "PLTE") {
      palette = [];
      for (let i = 0; i + 2 < data.length; i += 3) palette.push([data[i], data[i + 1], data[i + 2]]);
    } else if (kind === "tRNS") {
      trns = data;
    } else if (kind === "IDAT") {
      idat.push(data);
    } else if (kind === "IEND") {
      break;
    }
  }
  if (width === undefined || depth !== 8 || interlace || !(ctype in CHANNELS)) return null;
  if (ctype === 3 && !palette) return null;

  const bpp = CHANNELS[ctype];
  const stride = width * bpp;
  const compressed = new Uint8Array(idat.reduce((n, c) => n + c.length, 0));
  let off = 0;
  for (const c of idat) { compressed.set(c, off); off += c.length; }
  const raw = await inflate(compressed);
  if (!raw || raw.length < height * (stride + 1)) return null;

  let prev = new Uint8Array(stride);
  const total = [0, 0, 0];
  let count = 0;
  for (let y = 0; y < height; y++) {
    const start = y * (stride + 1);
    const ftype = raw[start];
    const line = raw.slice(start + 1, start + 1 + stride);
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? line[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      if (ftype === 1) line[i] = (line[i] + a) & 0xff;
      else if (ftype === 2) line[i] = (line[i] + b) & 0xff;
      else if (ftype === 3) line[i] = (line[i] + ((a + b) >> 1)) & 0xff;
      else if (ftype === 4) line[i] = (line[i] + paeth(a, b, c)) & 0xff;
    }
    prev = line;
    for (let x = 0; x < width; x++) {
      const px = line.subarray(x * bpp, (x + 1) * bpp);
      let r, g, b, alpha;
      if (ctype === 6) [r, g, b, alpha] = px;
      else if (ctype === 2) { [r, g, b] = px; alpha = 255; }
      else if (ctype === 4) { r = g = b = px[0]; alpha = px[1]; }
      else if (ctype === 0) { r = g = b = px[0]; alpha = 255; }
      else {
        const idx = px[0];
        if (idx >= palette.length) continue;
        [r, g, b] = palette[idx];
        alpha = trns && idx < trns.length ? trns[idx] : 255;
      }
      if (alpha < 128) continue;
      total[0] += r; total[1] += g; total[2] += b;
      count++;
    }
  }
  if (!count) return null;
  return total.map((t) => Math.round(t / count));
}

/** Closest known highlight color name, or null if nothing is close enough. */
export function nearestColorName(rgb, maxDistance = 120) {
  let best = null, bestDist = Infinity;
  for (const [name, ref] of Object.entries(KNOWN_COLORS)) {
    const dist = Math.hypot(rgb[0] - ref[0], rgb[1] - ref[1], rgb[2] - ref[2]);
    if (dist < bestDist) { best = name; bestDist = dist; }
  }
  return bestDist <= maxDistance ? best : null;
}

/** Guess a highlight color name from a `data:image/png;base64,...` URI. */
export async function colorFromDataUri(uri) {
  const i = uri.indexOf("base64,");
  if (i < 0) return null;
  let bytes;
  try {
    const bin = atob(uri.slice(i + 7).trim());
    bytes = Uint8Array.from(bin, (ch) => ch.charCodeAt(0));
  } catch {
    return null;
  }
  const rgb = await averageColor(bytes);
  return rgb ? nearestColorName(rgb) : null;
}
