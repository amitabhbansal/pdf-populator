# 05 - Performance and Limitations

> Measured performance and repeatability of the prototype, accuracy expectations, known limitations, deployment considerations, and future improvements.

## 1. Measured Performance

Benchmarked on the Axis form (8-page scanned PDF, 9 calibrated fields), Apple Silicon MacBook Air, Python 3.14, 10 consecutive render passes (each pass = open PDF → place all 9 fields → save output):

| Metric | Value |
|---|---|
| Average time per full render | **138 ms** |
| Min / max across 10 runs | 135 ms / 151 ms |
| Time per field | ~15 ms |
| Peak memory | ~54 MB |
| External services / GPU / network | None |

For comparison, a single OCR pass over one page typically takes on the order of seconds — coordinate mapping skips that work entirely, which is why it is 10–100× faster and has no recognition step that could vary between runs.

## 2. Measured Repeatability

Repeatability was tested by rendering the same input 10 times and hashing the results:

- **Rendered content: 100% identical.** A SHA-256 over the raw pixels of every page was identical across all runs — the same input produces the same visual output, every time.
- **File bytes differ slightly between runs** — this is PDF *metadata* (save timestamp and document ID that the PDF format embeds on save), not content. Worth knowing if anyone ever compares outputs with a byte-level diff: compare rendered content, not raw bytes.

## 3. Accuracy Expectations

- **Placement is exact by construction**: values are drawn at stored coordinates, so there is no recognition step that could misread or drift. In the sample run, 9/9 fields were placed on the correct page at the calibrated position.
- Accuracy is therefore bounded by **calibration quality** — a one-time human step. If a click was imprecise, the text is consistently offset by exactly that amount until recalibrated (errors are systematic and fixable, never random).
- The pre-render **validation step** guarantees nothing fails silently: any field that is declared but uncalibrated, missing a value, or mismatched by name is reported, and every run ends with an explicit filled/skipped summary.

## 4. Limitations

- **Fixed layouts only.** Coordinates assume the form layout never changes. A revised form version requires recalibration.
- **Scan consistency assumed.** A significantly shifted, scaled, or skewed scan of a known form would misplace text. For the supplied fixed templates this does not occur; for messy real-world scans, anchor-based alignment (OCR-assisted) would be the upgrade path.
- **No overflow handling.** A value longer than its box is drawn as-is; there is no auto-shrink or wrapping yet.
- **One data record per run.** Batch filling many records is a straightforward extension but not built.
- **Calibration is manual** (deliberately — one-time cost per template, zero cost thereafter).

## 5. Deployment Considerations

- **Runtime footprint**: pure Python + PyMuPDF/OpenCV/NumPy, ~54 MB peak memory, no GPU, no network calls, no external APIs. Runs anywhere Python runs.
- **Form of deployment**: fits naturally as a **headless batch job or CLI in a container** (the calibrator is a developer-side tool and does not ship to production — production only needs the renderer + configs).
- **Template onboarding as an operational process**: adding a form = calibrate once on a workstation → commit `config/mappings/<template>.json` → production picks it up. No code deployment.
- **Determinism helps operations**: identical inputs produce identical output content, so runs are audit-friendly and safe to retry.
- **Automation Anywhere integration**: the renderer is a single Python entry point with JSON in/PDF out — directly wrappable as a Bot task/package, where the bot supplies the data JSON and collects the filled PDF.

## 6. Future Improvements

- **OCR-assisted anchoring** — detect a few label positions at runtime to auto-correct scan shift/skew, keeping config-driven placement (the hybrid approach from `02-Solution-Design.md`).
- **Automatic template detection** — identify which form a PDF is and select its mapping automatically.
- **Batch processing** — fill many data records against one template in a single run.
- **Overflow handling** — warn on, shrink, or wrap values that exceed their field width.
- **REST API / GUI** — expose the renderer as a service or add a simple UI for non-technical users.
- **Searchable output** — optionally add an invisible text layer so filled forms become searchable/archivable.
