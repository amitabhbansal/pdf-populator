# Solution Walkthrough — PDF Population Engine


## 1. The Problem

I'm given scanned PDF forms. A scanned PDF is **just a picture** — no typed text, no fillable boxes. The task: put customer values into the right places automatically, without LLMs, and it must be **accurate** and **repeatable**.

The hard part in one line: **the computer has to write in the right spot on a page that tells it nothing about where anything is.**

## 2. Two Ways to Solve It

| | **A — Coordinate Mapping** | **B — OCR-based** |
|---|---|---|
| Idea | Note each field's position once, save it, reuse it | Let the machine "read" the page, find labels, write next to them |
| Position comes from | Saved numbers — exact | Guessed at run time — can vary |
| Speed | Milliseconds | Seconds (OCR is heavy) |
| When it goes wrong | Same error every time (fix once) | Random misreads on poor scans |
| Best when | The form layout never changes | Layouts change from doc to doc |

Both are valid — for **different situations**. So the real question is: *which situation am I in?*

## 3. My Assumption — and Why

**I assumed the forms are fixed templates** — a bank's form always looks the same. Only the *customer data* changes; the *form* doesn't.

Why this assumption is reasonable:

- **The requirements point to it.** They stress *"accuracy and repeatability."* That means the position must be exact and never change between runs — which is exactly what saved coordinates give, and exactly what run-time guessing (OCR) does not. Saved coordinates only work if the form is fixed — so I checked that this holds.
- **The given forms fit it.** They are standard printed bank forms — the same layout across thousands of copies.

I say this out loud because the whole design rests on it. If it were false, the right answer would change (see §8).

## 4. A Real Example

An agent opens bank accounts all day — Axis today, Federal tomorrow. The **forms** are the same two or three templates; the **customers** keep changing. Feed the system a form + customer data, get back the filled form — correctly, every time.

**Important detail:** the system fills the **blank master form** digitally. The customer does **not** bring their own scan. We scan each template **once**, calibrate it once, and generate every customer's copy from that. So "scans vary per customer" is simply not part of the flow.

## 5. Why I Chose Coordinate Mapping

- **Valid for fixed forms** — positions never change, so measuring once is enough.
- **Accurate** — text lands exactly on the saved spot. Nothing "reads" the page, so nothing can misread.
- **Repeatable** — same input → same output, every time. I checked: output is **pixel-identical across runs**.
- **Fast and cheap** — measured **~138 ms per form**, ~54 MB memory, no GPU, no internet.
- **Easy to maintain** — a new bank = a new config file, not new code.

## 6. Why Not OCR (Here)

OCR's only real advantage is **handling layouts that change** — which ours don't. So OCR would just add:

- **Misreads** — a wrong label reading puts text in the wrong place (hurts accuracy).
- **Variation** — results depend on scan quality (hurts repeatability).
- **Cost** — seconds per page instead of milliseconds, plus image clean-up.

So for fixed forms, OCR brings all the cost and none of the benefit — and it weakens the two things the task cares about most.

## 7. How It Works — Two Systems

The tool is **two systems joined by one file.** One is a **one-time setup** (a human clicks the field spots). The other is the **automatic engine** (runs for every customer, no human).

```
   SYSTEM 1 — CALIBRATION  (setup, once per form, done by a developer)
   ─────────────────────────────────────────────────────────────────
        scanned PDF ─▶ pdf_to_images ─▶ page images ─▶ [person clicks] ─▶ mapping file
                                                                            │
                                     ── the mapping file is the bridge ──   │
                                                                            ▼
   SYSTEM 2 — RENDERING  (automatic, once per customer, milliseconds)
   ─────────────────────────────────────────────────────────────────
        original PDF + mapping file + customer data ─▶ pdf_renderer ─▶ filled PDF
```

### What each part takes in and gives out

```
┌──────────────────────────────────────────────────────────┐
│  pdf_to_images.py        (make images we can click on)    │
│  ── IN  ─▶ scanned PDF, chosen DPI                         │
│  ── OUT ─▶ one PNG image per page                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  coordinate_calibrator.py   (human clicks each field once)│
│  ── IN  ─▶ the page images + the field names (data keys)  │
│  ── OUT ─▶ mapping file: each field's position + style    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  pdf_renderer.py            (the automatic engine)        │
│  ── IN  ─▶ original PDF + mapping file + customer data     │
│  ── OUT ─▶ filled PDF                                      │
└──────────────────────────────────────────────────────────┘
```

**The bridge — `config/mappings/<template>.json`:** calibration **writes** it, the renderer **reads** it. The two systems never talk directly; they only share this file. That's why the engine has no form-specific logic inside it — all form knowledge lives in the config.

**All the pieces at a glance:**

| Part | System | What it does |
|---|---|---|
| `settings.py` | Both | One place for all settings (which PDF, DPI, style); builds the paths |
| `pdf_to_images.py` | 1 | PDF pages → images to click on |
| `coordinate_calibrator.py` | 1 | Click fields → mapping file (positions in points) |
| `pdf_renderer.py` | 2 | PDF + mapping + data → filled PDF |
| `config/mappings/<template>.json` | Bridge | The saved field positions for one form |

This also answers *"isn't manual clicking against 'automatable'?"* → **System 1 is setup, System 2 is runtime.** You set up once; the daily run is fully automatic.

## 8. Why These Technologies

- **Python** — the strongest ecosystem for PDF and image work, quick to build, easy to read and hand over. The job is file I/O and simple coordinate maths, not heavy computation, so language speed is a non-issue.
- **PyMuPDF** — one library covers everything I need: open the scanned PDF, read page sizes, render pages to images (for calibration), and draw text/lines at exact coordinates, then save. Fast, with a simple API. *(It's AGPL-licensed — fine for this; a commercial product would need a commercial licence or an alternative.)*
- **OpenCV** — used only by the calibration tool, to show the page image and capture mouse clicks. Battle-tested and trivial for this.
- **JSON** (config + data) — human-readable, language-independent, and diff-friendly; config is data, not code.

## 9. Honest Downsides

- **Manual setup per form** — someone clicks each field once in a small tool. But that's a **one-time cost per template** (like writing a config), and every run after that is automatic.
- **Assumes tidy scans** — if a scan is badly shifted or skewed, fixed positions drift.
- **If my assumption is wrong** (unknown or changing layouts, customer photos) — coordinate mapping is the wrong tool and **OCR becomes right**. My design already separates *finding the position* from *drawing the text*, so an OCR step can slot in without a rewrite.

## 10. What's In, and What I Left Out (on purpose)

**In:**

- **Text fields** — value drawn at the saved spot, with font/size/colour from config.
- **Checkboxes** — a **true/false in the data** makes a field a checkbox (`true` → a tick, `false` → blank). No new config format — the type is read from the value. The tick is drawn as lines, so it needs no special font.

**Left out (known, not missed):**

- **Signatures / photos** — same overlay idea, but with `insert_image`; a config addition, not a redesign.
- **Non-Latin scripts** — the default font is Latin-only; Hindi/regional names need a Unicode font (supported via a `font_file` option).
- **Radio groups (pick one)** — today each option is its own checkbox; a small `radio` type would enforce "only one."
- **One-box-per-letter fields** — need per-character spacing (roadmap).
- **Right-aligned / wrapping text** — amounts and long addresses aren't handled yet (roadmap).
- **Text too long for a box** — no width check yet (roadmap).

## 11. What Can Be Improved (Roadmap)

- **OCR-assisted anchoring** — OCR finds a few labels at run time, works out the scan's shift, and the saved positions self-correct. Handles messy scans while staying config-driven.
- **Better calibration tool** — zoom, drag-to-adjust, undo.
- **Live preview** — show the real value at the clicked spot while calibrating (what-you-see-is-what-you-get).
- **Per-letter rendering** — for one-box-per-letter fields.
- **Long-text handling** — measure width, then warn/shrink/wrap.
- **Auto-detect the template** — recognise which form a PDF is and pick its mapping.
- **Batch mode** — many customers against one form in a single run.
- **Searchable output** — add an invisible text layer so the filled PDF is searchable.

## 12. Deployment

- **Small footprint** — pure Python + PyMuPDF/OpenCV, ~54 MB, no GPU/internet.
- **How it runs** — a headless CLI or batch job in a container. Production ships only the **renderer + config files**; the calibration tool stays with developers.
- **Adding a bank in production** — calibrate once, commit its mapping file, done. No code deploy.
- **Safe to operate** — identical output every run, so it's easy to audit and safe to retry.

## 13. Automation / AI Integration

- **Automation Anywhere Bot** — the renderer is one entry point: JSON in, PDF out. A bot can gather the customer data (CRM, email, sheet), call the engine, and send the filled PDF onward.
- **Where AI fits later** (still no LLM at run time) — OCR for anchor alignment and template auto-detection; or "assisted calibration," where OCR *suggests* positions and a human just confirms — shrinking the manual step.

## 14. Numbers (Measured, Not Guessed)

| Metric | Result |
|---|---|
| Full render (8-page form, 9 fields) | ~138 ms average (10 runs) |
| Per field | ~15 ms |
| Peak memory | ~54 MB |
| Fields placed correctly | 9/9, right pages |
| Repeatability | Pixel-identical output across runs |
| Silent failures | None — validation reports every skipped/missing field |

Worth mentioning: the output **file bytes** differ slightly between runs. I checked — that's just PDF save metadata (timestamp/ID), not the content. The rendered pixels are identical. Measure the thing that matters.


## 15. Solution Highlights (Recap)

- **Fills scanned, field-less PDFs** — no editable fields, no text layer, and **no OCR, no LLM**.
- **Accurate by construction** — values land on exact saved coordinates; there's no "reading" step that can misread.
- **Repeatable** — same input → **pixel-identical output every run** (verified, not claimed).
- **Fast and light** — ~138 ms per form, ~54 MB memory, no GPU, no network.
- **Config-driven** — a new bank = a new config file, **zero code changes**.
- **Two clean systems** — one-time human calibration, then a fully automated fill engine.
- **Fails loudly, never silently** — validation + a filled/skipped summary on every run.
- **Original scan untouched** — values are drawn on top (overlay); supports text **and** checkboxes.

