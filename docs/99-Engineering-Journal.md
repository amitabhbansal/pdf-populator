# 99 - Engineering Journal

> A running, concise log of what I learned while working on this project.

## 2026-07-15 — Prototype build, hardening, and measurement

- **Verify library behaviour experimentally, don't assume**: tested PyMuPDF's `insert_text` origin by drawing at (50, 50) on a blank page and checking where pixels landed (top → top-left origin, y-flip needed).
- **`insert_text` anchors at the glyph baseline**, so text rises above the click point; a tunable nudge (0.35 × font size) visually centres text on the clicked spot.
- **Store canonical units, convert at boundaries**: clicks captured in pixels → stored as PDF points → flipped to library space only inside the renderer.
- **Byte-identical ≠ content-identical**: outputs differed byte-wise across runs (PDF save timestamp/ID metadata) but were pixel-identical by SHA-256 over rendered pages — measure the thing that matters.
- **Measured, not estimated**: ~138 ms per 8-page form (9 fields), ~15 ms/field, ~54 MB peak, fully deterministic content.
- **A shared mapping file was a data-loss bug**: switching templates overwrote the previous calibration → per-template `config/mappings/<template>.json`.
- **The worst failure is silent**: added pre-render validation (fields ↔ mapping ↔ data) and an explicit filled/skipped summary per run.
- **Mixing terminal `input()` with a GUI event loop is fragile** (macOS especially) — driving the calibrator from a predefined field list was simpler and more reliable.
- **Centralising config killed a bug class**: DPI duplicated across two scripts → single `settings.py` import.

## 2026-07-14 — Problem understanding and design foundations

- A **PDF page is a canvas**; **rendering means drawing objects** (text, lines, images) onto it at explicit positions.
- PDFs come in three kinds: **True (digital)**, **Image-only (scanned)**, and **Searchable** (scanned + invisible OCR text layer). Ours is **Image-only** — pixels, no text.
- Scanned PDFs are hard because the file carries **no positional information** about its content — the computer can't answer "where is the word 'Name'?".
- Editable PDFs (AcroForm/XFA or real text objects) would have been easier because they give position/field access for free.
- **OCR** converts an image into text and returns, per unit, the **text**, a **bounding box** `(x, y, w, h)`, and a **confidence** score. Its pipeline is roughly preprocess → segment → recognize. It's pattern recognition, not understanding.
- **Use OCR** when there's no text layer and layouts vary; **don't use OCR** when a text layer already exists or the layout is fixed and known.
- **Coordinate Mapping is deterministic**: positions are stored, not inferred, so the same input always yields the same output.
- **Fixed templates should prefer Coordinate Mapping** — it's more accurate and repeatable than OCR for this case, with far less cost.
- Good engineering means **choosing the simplest solution that satisfies the requirements** — not the most sophisticated one.
- **Separate configuration from application logic**: code = how to render, config = where to render.
- **JSON is configuration, not business logic** — human-readable, lightweight, language-independent, nestable, easy to maintain.
- Fill forms by **overlaying** text on top of the scan, never by modifying the scanned image itself — keeps the original intact and placement exact.

## Virtual Environment

### What I learned

A virtual environment creates an isolated Python environment for a project.

### Why did I use it?

- Prevent dependency conflicts between projects.
- Keep project libraries isolated.
- Make the project reproducible for other developers.
- Follow Python best practices.

### Interview Answer

A virtual environment isolates project dependencies, preventing version conflicts between different projects. It also makes the project easier to reproduce by allowing other developers to install the exact same dependencies using the project's requirements file.

# PyMuPDF

## Why did I choose it?

I evaluated multiple PDF libraries before implementation.

### Requirements

- Open an existing scanned PDF.
- Read page information.
- Draw text at exact coordinates.
- Save a modified PDF.

PyMuPDF satisfies all of these requirements with a simple API.

### Why not other libraries?

- ReportLab → Better for generating PDFs from scratch.
- PyPDF2 → Good for merging/splitting PDFs but not rendering text.
- pdfplumber → Used for extracting text.
- OpenCV → Image processing, unnecessary for fixed templates.

### Interview Answer

I selected PyMuPDF because it directly supports opening existing PDFs, rendering text at specific coordinates, and saving the modified document. It matched the project requirements while keeping the solution simple and lightweight.
