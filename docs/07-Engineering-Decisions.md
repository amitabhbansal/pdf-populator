# 07 - Engineering Decisions

> A concise decision register: each entry records the decision, the core reason, and the main alternative that was rejected. The full narrative reasoning lives in `02-Solution-Design.md` and `03-Architecture.md`; this is the quick-scan log.

## Decision 1 — Why Coordinate Mapping?

- **Decision:** Place values using pre-measured `(x, y)` coordinates per field.
- **Why:** The forms are fixed templates, so positions never change. This makes placement exact and fully deterministic, directly satisfying the accuracy and repeatability requirements, at minimal complexity and cost.
- **Rejected alternative:** Inferring positions at runtime (OCR), which adds recognition error and non-determinism for a benefit (adapting to layout variation) we don't need here.

## Decision 2 — Why Not OCR?

- **Decision:** Do not use OCR for positioning in this solution.
- **Why:** OCR's value is adapting to variable or unknown layouts. Our layouts are fixed and known, so OCR adds cost (compute, preprocessing) and risk (misreads, run-to-run variability) without adding value. It also works against the repeatability goal.
- **Rejected alternative:** OCR-based positioning — kept as future work for variable/low-quality scans, not for fixed templates.

## Decision 3 — Why JSON?

- **Decision:** Store template coordinates and input data as JSON.
- **Why:** Human-readable, lightweight, language-independent, supports the nested "form → field → {coordinates, font, size, color}" structure, and is easy to maintain and validate.
- **Rejected alternative:** Hardcoding values in source code (couples data to logic, needs a redeploy to change) or a heavier format/database (unnecessary for this scale).

## Decision 4 — Why Configuration-Driven Design?

- **Decision:** Keep positions and styling in external configuration, separate from application logic.
- **Why:** Separates *how to render* (code) from *where to render* (config). A form can be adjusted or a new form added by editing/adding a config file, with no code change, no redeploy, and no risk of breaking program behaviour.
- **Rejected alternative:** Embedding coordinates in code, which makes every template change a code change and re-test.

## Decision 5 — Why Overlay Text Instead of Modifying the Scanned Image?

- **Decision:** Draw the values as a new layer on top of the scanned page rather than editing the image pixels.
- **Why:** The scanned page is an image with no text; "editing" it would mean altering pixels, which is lossy, hard to position precisely, and destroys the original. Overlaying keeps the original scan intact, places crisp vector text at exact coordinates, and is simpler and reversible.
- **Rejected alternative:** Rasterizing new text into the scanned image — lower quality, irreversible, and harder to get pixel-perfect.

## Decision 6 — Why Store Coordinates as PDF Points (not pixels)?

- **Decision:** The calibrator captures clicks in pixels but converts and stores **PDF points** (bottom-left origin) — the canonical, library-agnostic form.
- **Why:** Pixels are meaningless without knowing the render DPI; points are the PDF's native unit and survive re-rendering at any resolution. Consumers convert at their own boundary (PyMuPDF's top-left origin was verified experimentally before adding the y-flip).
- **Rejected alternative:** Storing raw pixels + DPI metadata — couples the config to one specific render and pushes conversion complexity into every consumer.

## Decision 7 — Why a Central settings.py (not .env or per-script constants)?

- **Decision:** One `src/settings.py` imported by all scripts; derived paths computed from the template name.
- **Why:** Native types with no parsing, no extra dependency, and it eliminated a real bug class — DPI was previously duplicated in two scripts that had to match manually. Config here is app parameters, not secrets, so `.env` adds friction without benefit.
- **Rejected alternative:** `.env` (string-typed, needs parsing/dependency; meant for secrets/environment values) or editing constants in each script (drift risk).

## Decision 8 — Why Per-Template Mapping Files?

- **Decision:** Store calibrations at `config/mappings/<template>.json`, derived from the PDF name.
- **Why:** A single shared `mapping.json` meant calibrating a new form silently overwrote the previous form's calibration — the most expensive artifact in the system. Per-template files make that loss impossible and let many forms coexist.
- **Rejected alternative:** One shared mapping file — simpler-looking but destructive on every template switch.

## Decision 9 — Why Pre-Render Validation + Run Summary?

- **Decision:** Before rendering, cross-check `fields.json` ↔ mapping ↔ data and report every mismatch; end each run with an explicit filled/skipped summary.
- **Why:** The worst failure mode isn't a crash — it's a plausible-looking but silently incomplete PDF. Warnings don't block (partial fills can be intentional); an empty mapping is a hard error.
- **Rejected alternative:** Fail-fast on any mismatch (too rigid for legitimate partial fills) or the previous behaviour (silent skips).
