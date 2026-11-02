/** The file is not a Play Books notes export. */
export class NotAPlayBooksExport extends Error {
  constructor(message = "This doesn't look like a Play Books notes export.") {
    super(message);
    this.name = "NotAPlayBooksExport";
  }
}

/** The file is a Play Books export, but it has no highlights in it. */
export class NoHighlights extends NotAPlayBooksExport {
  constructor(message = "This export has no highlights yet. Highlight something in Play Books, let it sync, then download the notes again.") {
    super(message);
    this.name = "NoHighlights";
  }
}
