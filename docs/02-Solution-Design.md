# 02 - Solution Design

> The approaches I evaluated for placing values onto a scanned form, how they compare, and why I selected **Coordinate Mapping** for this assignment. OCR is documented here as the alternative considered, not as the chosen path.

## 1. Design Goals

The solution should be:

- **Accurate** — values land exactly where they belong on the form.
- **Repeatable** — the same input always produces the same output (deterministic).
- **Automatable** — runs headless, with no manual steps.
- **Simple and maintainable** — easy to reason about, debug, and extend.
- **Low-cost** — no heavy compute, no external model dependencies.
- **LLM-free** — no language models at any stage (a hard constraint).

## 2. Possible Solution Approaches

### Approach 1 — Coordinate Mapping

**How it works:** Measure each field's position on the form once and store those `(x, y)` coordinates in a configuration file. At runtime, the engine reads the input data, looks up each field's coordinate, and stamps the value at that position on the page.

- **Advantages:** Fully deterministic; exact placement; no recognition step to go wrong; very fast; trivial to debug and explain; no external model or GPU.
- **Disadvantages:** Coordinates must be measured once per form template; assumes scans of a given form are consistent in size/orientation; not self-adapting to layout changes.
- **Complexity:** Low.
- **Accuracy:** High (placement is exact by construction).
- **Performance:** High (just reads config and writes text).
- **Maintainability:** High — adding/adjusting a form is a config change, not a code change.
- **Automation suitability:** Excellent at **runtime** — the render engine is fully automated and deterministic (no interactive or random steps). The **one-time calibration** per template is interactive (a human clicks field positions), but it is setup, not part of the automated run.

### Approach 2 — OCR-Based Detection

**How it works:** Run OCR on the scanned image to read the printed labels ("Name", "Account No"), get each label's bounding box, and write the value at a position computed relative to the detected label.

- **Advantages:** Adapts to shifted or rescaled scans; can support layouts that vary between documents; no manual coordinate measuring.
- **Disadvantages:** OCR can misread labels, especially on low-quality scans; depends on labels being present and legible; introduces non-determinism risk and recognition error; needs image preprocessing (deskew, threshold).
- **Complexity:** High.
- **Accuracy:** Medium — bounded by OCR quality and label detection.
- **Performance:** Lower — OCR is compute-heavy relative to a config lookup.
- **Maintainability:** Medium — more moving parts (preprocessing, OCR, label matching).
- **Automation suitability:** Good, but harder to guarantee identical output across runs.

## 3. Comparison

| Criterion | Coordinate Mapping | OCR-Based |
|---|---|---|
| Determinism / repeatability | High | Medium |
| Placement accuracy | High | Medium |
| Robustness to scan variation | Low | High |
| Implementation complexity | Low | High |
| Performance | High | Low |
| Maintainability | High | Medium |
| Computational cost | Very low | High |
| Automation suitability | Excellent | Good |
| No-LLM constraint | Satisfied | Satisfied |

## 4. Selected Approach — Coordinate Mapping

For **this** assignment, I selected **Coordinate Mapping**. The justification:

- **Fixed templates:** The supplied bank forms (Federal Bank, Axis Bank) have a fixed, known layout. Positions don't change between documents of the same form, so measuring them once is valid and reusable.
- **Deterministic positioning:** Coordinates are stored, not inferred — the same input always yields the same output, satisfying the repeatability requirement directly.
- **Accuracy:** Placement is exact by construction; there's no recognition step that could misread and misplace a value.
- **Simplicity:** The engine is small and easy to reason about, debug, and hand over.
- **Lower computational cost:** No OCR, no model, no GPU — just config lookup and text drawing.
- **Easier maintenance:** Supporting a new form means adding a config file, not changing application logic.

In short, when the layout is fixed, OCR's main benefit (adapting to variation) isn't needed, while its costs (recognition error, non-determinism, compute) directly work against the assignment's accuracy and repeatability goals. Coordinate Mapping gives the strongest guarantees for the least complexity.

## 5. Storing the Coordinates — Configuration-Driven Design

Coordinate Mapping only works well if the coordinates live in the right place. I keep them in **external configuration files**, separate from the application logic, rather than embedding them in source code.

- **Separation of concerns:** the code knows *how* to render; the config knows *where* to render. Neither needs to know about the other's details.
- **Change without code changes:** adjusting a field position or supporting a new form is a config edit — no touching, re-testing, or re-deploying the application logic.
- **Maintainability and scale:** many templates can be supported by adding many config files, while the engine stays the same size.
- **Safer to edit:** a coordinate tweak can't accidentally break program behaviour, because it isn't program code.

## 6. Why JSON for Configuration

I chose **JSON** as the configuration format because it is:

- **Human readable** — coordinates and fields can be inspected and edited by eye.
- **Lightweight** — minimal syntax, no heavy tooling required.
- **Language independent** — not tied to Python; any tool or language can read it.
- **Supports nested structures** — a natural fit for "form → field → { coordinates, font, size, color }".
- **Easy to maintain** — small, diff-friendly, and simple to validate.

This keeps configuration as *data*, cleanly separated from business logic.

## 7. Trade-offs and Limitations

- **Per-template setup:** Each new form layout requires measuring its coordinates once.
- **Sensitivity to scan consistency:** If a scan of a known form is significantly shifted, scaled, or skewed relative to the reference, fixed coordinates can drift. (For provided fixed-template samples this is a non-issue; for messy real-world scans it would matter.)
- **No layout adaptation:** The approach does not self-adjust to unseen or changed layouts.

These limitations are acceptable given the fixed-template nature of the inputs. Where they would matter (variable or low-quality scans), the **OCR** approach above becomes the natural upgrade path — captured as future work in `05-Performance-And-Limitations.md`.
