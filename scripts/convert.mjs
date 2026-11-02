#!/usr/bin/env node
// Convert an export with the browser converter, from the command line.
// Usage: node scripts/convert.mjs EXPORT.md [chapter|color|both] [bullet|quote]  (writes to stdout)
import { readFile } from "node:fs/promises";
import { convert, NotAPlayBooksExport } from "../site/js/converter/index.js";

const [file, groupBy = "chapter", style = "bullet"] = process.argv.slice(2);
if (!file) {
  console.error("usage: node scripts/convert.mjs EXPORT.md [chapter|color|both] [bullet|quote]");
  process.exit(2);
}
try {
  const { markdown } = await convert(await readFile(file, "utf8"), groupBy, style);
  process.stdout.write(markdown);
} catch (err) {
  console.error(`error: ${err.message}`);
  process.exit(err instanceof NotAPlayBooksExport ? 1 : 3);
}
