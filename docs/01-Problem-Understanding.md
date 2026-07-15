# 01 - Problem Understanding

> The purpose of this document is **not** to explain the solution. It is to understand the problem from first principles — what is being asked, why it is hard, and the background concepts (PDF internals, OCR) needed before any solution can be designed. No approach is chosen here.

## 1. Problem Statement

Automatically populate customer data into scanned bank forms (Federal Bank, Axis Bank) that have no editable or searchable fields — without using any LLMs. The solution must be fully automated, accurate, and repeatable: same form + same data → same correctly filled output, every time.

## 2. Assignment Constraints

- **Input is a scanned, image-based PDF** — the page is a picture, not text.
- **No AcroForm / XFA fields** — there are no interactive widgets to set values on.
- **No LLMs** — no GPT/Claude-style models may be used to read or interpret the document.
- **Must be automatable** — runs headless (batch job, CLI, or service); no manual clicking.
- **Accuracy and repeatability matter** — output must be correct and identical across runs.

## 3. Requirement Analysis

Every sentence in the assignment hides a design constraint, so I'm breaking down the core requirement phrase by phrase.

> "Automatically populate values into a scanned PDF that contains no editable or searchable form fields."

| Phrase | What it really means | Design implication |
|---|---|---|
| **"automatically populate"** | No human clicks. Given data + a form, out comes a filled form. | Needs a repeatable pipeline, not a manual tool. |
| **"scanned PDF"** | The PDF is essentially a **photograph** of paper. | The hardest constraint — there is no text, only pixels. |
| **"no editable form fields"** | Cannot just "set field value = X" like a web form. | Rules out the easiest solution (AcroForm filling). |
| **"no LLMs"** | No GPT/Claude-style models to "read and understand" the doc. | Forces deterministic, explainable techniques. |
| **"fully automatable"** | Must run headless — batch job, CLI, or service. | No GUI, no manual steps. |
| **"accuracy and repeatability"** | Same input → same output, every time; values land in the right place. | Points toward **deterministic positioning**, not guessing. |

> The core challenge in one sentence: **I need to place text at the correct pixel location on a document where the computer has no idea where anything is, because to it the whole page is just a picture.**

## 4. Types of PDFs

PDFs fall into three categories, based on how they were created:

| Type | What it is | Searchable / Selectable? |
|---|---|---|
| **True PDF** (digital) | Created directly by software (Word, LaTeX, etc.) — text is stored as real characters | Yes |
| **Image-only PDF** (scanned) | A scanned/photographed document with no text layer — just a picture | No |
| **Searchable PDF** | A scanned image with an invisible OCR'd text layer added on top (e.g., via Adobe "Recognize Text") | Yes, but visually still looks like the scan |

**Identifying which type I have** — rather than assuming from the assignment description, I verify the input directly:

1. **Text selection test** — try to select text with the mouse. Nothing highlights → no text layer.
2. **Search test** — Ctrl+F for a word clearly visible on the page. No results → confirms Image-only.
3. **Form field test** — check for AcroForm/XFA fields (via a PDF library, or "Highlight Existing Fields" in a viewer). None present → confirms "no editable fields."



## 5. How PDFs Are Internally Structured

A PDF page is best thought of as a **canvas with drawing instructions**, not a flowing document like a Word file. Every element on the page — text, lines, images — has an exact position on this canvas.

- **Coordinate system**: measured in *points* (1 point = 1/72 inch). The origin `(0, 0)` is the **bottom-left** corner, and the y-axis grows **upward** — the opposite of image/screen coordinates, where `(0, 0)` is top-left and y grows downward. This mismatch matters whenever image (pixel) coordinates are mapped back onto the PDF.
- **What a page can contain**:
  - *Text objects* — real characters with a font and an `(x, y)` position (only in True/Searchable PDFs)
  - *Vector graphics* — lines, boxes, table borders
  - *Raster images* — an embedded picture (this is the *entire* page content for a scanned PDF)
  - *Form fields (AcroForm/XFA)* — interactive widgets like text boxes and checkboxes

## 6. Why Scanned PDFs Are Difficult to Process

Suppose I want to write a value into the form:

```
Name

Amitabh
```

Normally I would do:

```
PDF  →  Field  →  Set Value
```

But there are no fields — it's just an image. So, where should I write? The computer has no idea. For an Image-only PDF there are no text objects at all: the whole page is one raster image, so asking "where is the word 'Name'?" has no answer from the file itself.

This is the core difficulty the whole solution has to solve: **establishing *where* to write on a page that carries no positional information about its own content.**


## 7. What OCR Is

**OCR (Optical Character Recognition)** is the process of taking an image containing text and converting it into machine-readable characters, along with **where** each character/word was found on the image. It is one way to give the computer the positional knowledge a scanned page lacks.

## 8. How OCR Works (High Level)

At a high level, an OCR engine:

1. **Preprocesses** the image (deskew, threshold to black-and-white, remove noise).
2. **Detects** regions likely to contain text.
3. **Segments** those regions into lines, then words, then characters.
4. **Recognizes** each character shape by matching it against learned patterns and picks the most likely text.

It is pattern recognition, not "understanding" — the engine does not comprehend meaning, it guesses characters from shapes.

## 9. Where OCR Is Useful

- **Needed** whenever the file has no text layer at all — i.e., Image-only PDFs — because there is no other way to read the content.
- **Not needed** for True PDFs or Searchable PDFs, where a text layer already exists and can be read directly and reliably. Running OCR there is redundant and can even introduce recognition errors where perfect data already exists.

## 10. What Information OCR Returns

For each recognized unit (character / word / line), OCR typically returns:

- **Text** — the recognized string.
- **Bounding box** — the `(x, y, width, height)` of that text on the image, in pixel coordinates.
- **Confidence** — a score (e.g., 0–100) indicating how sure the engine is about the recognition, useful for filtering out unreliable reads.

## 11. Assumptions

- The supplied forms are **fixed templates** — a given bank form always has the same layout.
- The customer data to populate is **provided separately** (structured input), not extracted from the scan.
- The set of fields to fill is **known in advance** for each form.
- Scans are of **reasonable, consistent quality** (comparable size and orientation).


