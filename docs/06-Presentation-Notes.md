# Solution Walkthrough — PDF Population Engine


## 1. The Problem

I'm given scanned PDFs: **no text layer, no form fields — the page is just a picture.** The task is to populate values into them automatically, without LLMs, with accuracy and repeatability as the stated priorities.

The core difficulty: the computer must write at the right spot on a page that gives it **no information about where anything is.**

## 2. The Two Ways to Solve This

| | **Approach A — Coordinate Mapping** | **Approach B — OCR-based** |
|---|---|---|
| Idea | Measure each field's position once, store it, reuse it forever | Make the machine "read" the page, find labels like "Name", write next to them |
| Positioning | Stored data — exact | Inferred at runtime — can vary |
| Speed | Milliseconds | Seconds (OCR is heavy) |
| Failure mode | Systematic only (fix once) | Random misreads on low-quality scans |
| Valid when | The form layout is fixed | Layouts vary between documents |

Each approach is right for a different situation — so the real question is: *which situation am I in?*

## 3. My Key Assumption — and Why I Made It

**I assumed the forms are fixed templates**: a given bank's form always has the same layout — the "Name" line on the Axis form is always in the same place. New *data* changes every day; the *form* does not.

Why I assumed this:

- **The constraints told me what matters**: "*Accuracy and repeatability are important.*" Those two properties point directly at deterministic positioning — stored coordinates that never vary — and away from runtime inference. Coordinate Mapping can only deliver that guarantee if templates are fixed, so I checked whether that assumption was reasonable.
- **The supplied forms support it**: these are standardized, printed bank templates — exactly the kind of document whose layout stays constant across thousands of copies.

I state this assumption openly because the whole design stands on it — and if it doesn't hold, the right solution changes (section 7).

## 4. A Concrete Use Case (What This Looks Like in Practice)

Think of an agent whose daily job is opening bank accounts — Federal Bank today, Axis Bank tomorrow. The *forms* are always the same two or three templates; the *customers* change constantly. Give the system a form + customer data (JSON), get back the filled form — automatically, correctly, every time. This is exactly the fixed-template world the assumption describes.

**One workflow point worth being explicit about:** the system fills the **master template** (the scanned blank form) digitally — each customer does *not* bring their own scan. One clean scan per template is calibrated once; per-customer output is generated digitally from it, then printed/submitted or archived. This is why scan variation between customers isn't a factor in the core flow.

## 5. Why I Chose Coordinate Mapping

- **The assumption makes it valid** — positions never change, so measuring once is enough.
- **High accuracy** — the value lands exactly where the stored coordinate says. No recognition step that could misread.
- **Repeatability** — same input → same output, every run. I verified this: output is **pixel-identical across runs** (SHA-256 over rendered pages).
- **Fast and cheap** — measured **~138 ms per form (~15 ms per field, ~54 MB memory)**. No GPU, no network, no external service.
- **Simple to maintain** — adding a bank = adding a config file. Zero code changes.

## 6. Why Not OCR (For This Case)

OCR's one real benefit is **adapting to layout variation** — but our layouts don't vary. So OCR would only add:

- **Recognition errors** — a misread label means a misplaced value (hurts accuracy).
- **Run-to-run variability** — results depend on scan quality (hurts repeatability).
- **Cost** — seconds of compute per page vs. milliseconds, plus preprocessing (deskew, thresholding).

In short: for fixed templates, OCR adds all its costs and none of its benefits. The two things the requirements stress most — **accuracy and repeatability** — are exactly the two things OCR weakens.

## 7. Honest Downsides of My Approach

- **Manual onboarding** — each new template needs one calibration pass (a person clicks each field's position in a small UI tool). But this is a **one-time setup cost per template** — like writing a config — and the fill pipeline itself is 100% automated after that.
- **Assumes consistent scans** — if a scan of a known form is heavily shifted, skewed, or rescaled, fixed coordinates will drift.
- **If the use case is different from my assumption** — unknown forms, varying layouts, photos instead of clean scans — then coordinate mapping is the wrong tool, and **OCR (or a hybrid) becomes the right one**. The architecture already separates "how positions are found" from "how text is drawn", so an OCR positioning step can slot in without redesigning the rest.

## 8. Scope — What I Deliberately Left Out (and Know About)

I kept the prototype focused on the core problem: placing text values accurately. These are out of scope **by choice, not by oversight**:

- **Checkboxes, signatures, photos** — real bank forms need tick marks, a signature image, a passport photo. The same overlay mechanism extends to images (`insert_image` at a stored coordinate); it's an extension of the config schema, not a redesign.
- **Non-Latin scripts** — the built-in Helvetica font covers Latin text only. Hindi/regional names need embedding a Unicode font (PyMuPDF supports this); a config-level `font_file` option is the fix.
- **Comb fields / boxed characters** — one letter per box needs per-character spacing (roadmap).
- **Multiple versions of the same form** — if a bank revises its layout, that's a new template config (and automatic template detection is the long-term answer).
- **Long values overflowing boxes** — no width check yet (roadmap).

## 9. What Can Be Improved (Roadmap)

- **OCR anchoring (hybrid)** — OCR finds 2–3 label positions at runtime, computes the scan's shift/scale, and the stored coordinates self-correct. Best of both worlds for imperfect scans.
- **Better calibration UI** — zoom for precise clicks, drag-to-adjust, undo.
- **Live text preview** — show the actual value rendered at the clicked spot during calibration, so placement is WYSIWYG.
- **Character-by-character rendering** — many bank forms have one box per letter; render values with per-character spacing to fit comb fields.
- **Long text handling** — measure text width; warn, shrink, or wrap values that would overflow their box.
- **Automatic template detection** — recognize which form a PDF is and pick its mapping automatically.
- **Batch mode** — many customer records against one template in a single run.
- **Searchable output** — add an invisible text layer so the filled PDF becomes searchable/archivable.

## 10. Deployment

- **Footprint**: pure Python + PyMuPDF/OpenCV, ~54 MB peak, no GPU/network/external APIs. Runs anywhere.
- **Shape**: headless CLI or batch job in a container. Production ships only the **renderer + config files** — the calibration tool stays with developers.
- **Onboarding a bank in production**: calibrate once on a workstation → commit `config/mappings/<template>.json` → done. No code deployment.
- **Safe operations**: deterministic output means runs are audit-friendly and retry-safe.

## 11. Automation / AI Integration Scope

- **Automation Anywhere Bot**: the renderer is a single entry point — JSON in, PDF out — directly wrappable as a Bot task/package. A bot collects customer data (from a CRM, email, spreadsheet), calls the engine, and routes the filled PDF onward.
- **Where AI fits later (without breaking the no-LLM constraint at runtime)**: OCR for anchor alignment and template auto-detection; assisted calibration where OCR *suggests* field positions and a human just confirms — cutting manual onboarding down further.

## 12. Numbers I Can Show (Measured, Not Estimated)

| Metric | Result |
|---|---|
| Full render (8-page form, 9 fields) | ~138 ms average (10 runs) |
| Per field | ~15 ms |
| Peak memory | ~54 MB |
| Fields filled correctly | 9/9, correct pages |
| Repeatability | Pixel-identical output across all runs |
| Silent failures | None possible — validation reports every skipped/missing field |

One finding worth sharing: raw output **bytes** differ between runs — I investigated and it's PDF save metadata (timestamp/ID), not content. I verified content-identity by hashing the rendered pixels. Measure the thing that matters.

## 13. Demo Flow

1. Show the scanned form — try selecting text (nothing selects: it's just an image).
2. Show `sample_data.json` → run the renderer → open the filled PDF.
3. Change a value, rerun — new PDF in milliseconds.
4. Break a field name on purpose → validation catches it and the summary reports it.
5. Show the calibrator briefly — "this is the one-time setup per template."

---

## Appendix — Likely Questions & Short Answers

1. *Why not OCR?* — Covered in §6: for fixed templates it adds cost and risk, no benefit.
2. *Isn't manual calibration against "automatable"?* — Setup ≠ runtime. Calibration is one-time per template; the fill pipeline is fully headless (§7).
3. *What breaks your approach?* — Layout changes or heavily skewed scans → recalibrate (cheap), or move to OCR anchoring (§9).
4. *How do you know the output is repeatable?* — Measured: pixel-identical across runs (§12).
5. *Coordinate systems?* — Clicks are pixels (top-left origin) → stored as PDF points (bottom-left, 1/72 inch) → converted to the render library's space at the boundary. I verified the library's origin experimentally instead of assuming.
6. *Long values / comb fields?* — Known limitation today; overflow handling and per-character rendering are on the roadmap (§9).
7. *How do I add a new bank?* — Drop the PDF in `input/`, point `settings.py` at it, calibrate once. No code changes; a separate mapping file is created per template.
8. *Scale?* — Stateless and CPU-bound: ~7 forms/sec/core; parallelize per document.
9. *Testing?* — Unit tests for coordinate conversions, golden-file pixel comparison, validation tests with broken configs.
10. *Why JSON configs?* — Human-readable, language-independent, diff-friendly; config is data, not code.
11. *Why overlay instead of editing the scanned image?* — Overlay keeps the original intact, gives crisp vector text, and is reversible; painting pixels into the scan would be lossy and irreversible.
12. *Why not an LLM (if it were allowed)?* — Non-deterministic, costly, unexplainable — overkill for locating boxes on a known layout. Same logic as OCR, amplified.
