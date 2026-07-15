# 05 - Performance and Limitations

> Measured performance and repeatability of the prototype, accuracy expectations, known limitations, deployment considerations, and future improvements.

## 1. Measured Performance

All figures below are produced by **`src/benchmark.py`**, which runs the real renderer 10 times and reports timing, peak memory, and repeatability. Reproduce them on any machine:

```
python src/benchmark.py
```

Example results (Apple Silicon MacBook Air, Python 3.14):

| Template | Fields | Avg render | Per field | Peak memory |
|---|---|---|---|---|
| Axis (8 pages) | 9 | ~138 ms | ~15 ms | ~54 MB |
| Term Deposit (2 pages) | 59 | ~627 ms | ~11 ms | ~58 MB |

Timing scales mainly with the number of fields; the fixed open/save overhead is amortized across more fields, so per-field cost drops as fields grow. No GPU, no network, no external services. Coordinate mapping does no image analysis or text recognition — a render is just config lookup plus text drawing, far lighter than an OCR pass.

## 2. Measured Repeatability

`benchmark.py` renders the same input twice and compares a **SHA-256 over the rendered pixels** of every page:

- **Rendered content is identical** across runs — the same input always produces the same visual output.
- **Raw file bytes differ slightly** between runs — that's PDF *metadata* (a save timestamp and document ID the format writes), not content. So determinism is checked on rendered pixels, not raw file bytes.

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

- **OCR-assisted anchoring** — detect a few label positions at runtime to auto-correct scan shift/skew, keeping config-driven placement (the OCR upgrade path from `02-Solution-Design.md`).
- **Automatic template detection** — identify which form a PDF is and select its mapping automatically.
- **Batch processing** — fill many data records against one template in a single run.
- **Overflow handling** — warn on, shrink, or wrap values that exceed their field width.
- **REST API / GUI** — expose the renderer as a service or add a simple UI for non-technical users.
- **Searchable output** — optionally add an invisible text layer so filled forms become searchable/archivable.
