# 06 - Presentation Notes

> Notes for a 10–15 minute presentation to senior Application Engineers, plus expected interview questions.

## 1. Presentation Flow

1. **Problem** (2 min) — Fill scanned bank forms that have no fields, no text layer, no LLMs allowed. The core difficulty in one sentence: *the computer must write at the right place on a page that carries no positional information about its own content.*
2. **Design thinking** (3 min) — Three candidate approaches: Coordinate Mapping, OCR-based detection, Hybrid. Walk the comparison table (determinism, accuracy, complexity, cost).
3. **The decision** (2 min) — The forms are **fixed templates**, so OCR's only benefit (adapting to variation) isn't needed, while its costs (misreads, non-determinism, compute) directly hurt the stated goals. Coordinate Mapping gives the strongest accuracy/repeatability guarantees for the least complexity. OCR/Hybrid documented as the upgrade path.
4. **Architecture walkthrough** (3 min) — pages→images → one-time visual calibration → per-template JSON mapping → validating renderer that overlays text. Key properties: config-driven (zero form knowledge in code), original scan never modified, calibration is dev-side only.
5. **Demo** (3 min) — edit a value in `sample_data.json` → run renderer → show the filled PDF; show validation catching a typo'd field name; show the run summary.
6. **Metrics** (1 min) — measured: ~138 ms per form, ~15 ms per field, ~54 MB peak, output pixel-identical across runs (byte diffs are PDF metadata only — and I verified that).
7. **Future work** (1 min) — OCR anchoring for skewed scans, template auto-detection, batch mode, overflow handling, AA Bot integration.

## 2. Key Engineering Decisions to Highlight

- Stored coordinates in **library-agnostic PDF points**; converted at boundaries (pixel→point at calibration, point→library space at render). Verified PyMuPDF's origin **experimentally** rather than assuming.
- **Per-template mappings** so calibrating a new form can't destroy an existing calibration.
- **Validation before rendering** — the worst failure mode is a silently incomplete fill; every run ends with an explicit filled/skipped summary.
- **settings.py as single config point** — eliminated the duplicated-DPI bug class entirely.

## 3. Expected Interview Questions

**Design & alternatives**
1. *Why not OCR?* — Fixed templates: OCR's benefit (layout adaptation) isn't needed; its costs (misreads, non-determinism, compute) hurt accuracy/repeatability. It's the upgrade path for variable scans, not the baseline.
2. *Why not an LLM (if allowed)?* — Same reasoning amplified: non-deterministic, costly, unexplainable; overkill for locating boxes on a known layout.
3. *When would your approach break?* — Layout revisions, or shifted/skewed/rescaled scans. Mitigation: recalibrate (cheap), or OCR-anchor alignment as future work.
4. *Why is coordinate mapping more repeatable than OCR?* — Positions are stored data, not runtime inference; there is no recognition step whose output can vary.
5. *What's the Hybrid approach?* — OCR finds a few anchor labels to align the page; placement stays config-driven relative to anchors. Best of both when scans vary.
6. *Why JSON for config?* — Human-readable, lightweight, language-independent, nests naturally, diff-friendly.
7. *Why is the calibrator manual? Isn't that against "automatable"?* — Calibration is one-time setup per template (like writing the config); the *fill pipeline* is fully headless. Setup ≠ runtime.

**PDF & coordinates**
8. *How does a PDF store content?* — Canvas of drawing instructions: text objects, vector graphics, raster images, optional form fields. A scanned PDF is one big raster image, nothing else.
9. *Digital vs scanned vs searchable PDF?* — Real text objects / image-only / image + invisible OCR'd text layer.
10. *Explain the coordinate systems you juggled.* — Image pixels (top-left, y down) → PDF points (bottom-left, y up, 72/inch) → PyMuPDF insert space (top-left). One conversion per boundary.
11. *How did you know PyMuPDF's origin?* — Tested it: inserted text at (50, 50) on a blank page and checked which end the pixels landed. Verified, not assumed.
12. *What is a point?* — 1/72 inch; A4 = 595×842 pt.
13. *Why store points instead of pixels?* — Pixels are meaningless without DPI; points are the PDF's native, DPI-independent unit and survive re-rendering at any resolution.
14. *What's the baseline nudge?* — insert_text anchors at the glyph baseline, so text rises above the click. A 0.35×size offset visually centres text on the clicked spot; tunable, single constant.

**Implementation & robustness**
15. *What happens if a field name is misspelled in the data?* — Pre-render validation flags it as "no calibrated position (possible typo?)"; the run summary lists everything skipped.
16. *What if a field was never calibrated?* — Validation warns "declared but never calibrated — will NOT be filled". Nothing fails silently.
17. *How do you handle multi-page forms?* — Every field declares its page in `fields.json`; the calibrator auto-displays the right page; the renderer routes each value to `field["page"]`.
18. *Is the output really identical every run?* — Rendered content is pixel-identical (SHA-256 over page pixels across 10 runs). Raw bytes differ due to PDF save metadata (timestamp/ID) — measured and understood.
19. *Performance?* — ~138 ms per 8-page form (9 fields), ~15 ms/field, ~54 MB peak, no GPU/network.
20. *How do I add a new bank's form?* — Drop PDF in `input/`, point `settings.py` at it, list fields in `fields.json`, calibrate once. No code changes; new mapping file is created per template.
21. *Why did you not modify the scanned image pixels?* — Overlay keeps the original intact, gives crisp vector text, is reversible, and positions exactly. Rasterizing text in would be lossy and irreversible.
22. *What if a value is too long for its box?* — Currently drawn as-is (documented limitation); planned: measure text width, warn/shrink/wrap.

**Operations & scale**
23. *How would you deploy this?* — Headless CLI/batch in a container; production ships renderer + configs only (calibrator is a dev tool). No external dependencies.
24. *How would this integrate with Automation Anywhere?* — Single Python entry point, JSON in → PDF out; wrappable as a Bot task/package where the bot supplies data and collects the filled form.
25. *How would you scale to thousands of forms a day?* — It's CPU-bound and stateless: ~7 forms/sec/core single-threaded; parallelize per document (process pool or horizontal instances). No shared state to coordinate.
26. *How would you test this?* — Unit tests for pure conversions (point↔pixel round-trip, hex→RGB); golden-file test comparing rendered page pixels; validation-path tests with deliberately broken configs.

## 4. Key Learnings

- Verify library behaviour **experimentally** when correctness depends on it (coordinate origin, repeatability hashes).
- The best solution is the **simplest one that satisfies the stated requirements** — resist sophistication for its own sake, but document the upgrade path.
- Separate **what is data** (coordinates, styles, field lists) from **what is logic** (rendering) — everything that changed during this project changed in config, not code.
- Design the failure modes first: the worst outcome isn't a crash, it's a **plausible-looking wrong output**. Validation + summaries eliminate that class.
