# Solution Walkthrough — PDF Population Engine


## 1. The Problem

I'm given scanned PDF forms. A scanned PDF is **just a picture** — no typed text, no fillable boxes. The task: put customer values into the right places automatically, without LLMs, and it must be **accurate** and **repeatable**.

The hard part in one line: **the computer has to write in the right spot on a page that tells it nothing about where anything is.**

## 2. Two Ways to Solve It

| | **A — Coordinate Mapping** | **B — OCR-based** |
|---|---|---|
| Idea | Note each field's position once, save it, reuse it | Let the machine "read" the page, find labels, write next to them |
| Position comes from | Saved coordinates — exact | Detected from document content at run time — can vary |
| Speed | Milliseconds | Heavier — extra image analysis + recognition |
| When it goes wrong | Same error every time (fix once) | Accuracy varies with scan quality |
| Best when | The form layout never changes | Layouts change from doc to doc |

Both are valid — for **different situations**. So the real question is: *which situation am I in?*

## 3. Scope Assumption

Before designing anything, my first decision was to clarify **which problem I was actually solving.** I saw two possible interpretations of the assignment:

### Scenario 1 — Fixed Templates
The organization has a small set of known forms (for example, Axis Bank or Federal Bank). The layout never changes; only the customer data changes. The same template is filled repeatedly for different customers.

### Scenario 2 — Unknown Templates
Every incoming PDF could have a different layout, so the system must first *understand* the document before deciding where to write.

These two scenarios lead to different solutions:

```
                Scanned PDF
                     │
                     ▼
      What problem am I solving?
                     │
        ┌────────────┴────────────┐
        │                         │
 Fixed templates           Unknown templates
        │                         │
 Coordinate Mapping             OCR
```

For this assignment I chose **Scenario 1 — fixed-template document population**, because:

- The requirements emphasize **accuracy** and **repeatability**, which favour deterministic placement.

Based on the supplied samples and requirements, this is the interpretation I committed to. If the scope were instead unknown or changing layouts, I would have taken the OCR branch.

> **Different problem scopes lead to different correct solutions. My first design decision was deciding which problem I was actually solving.**

## 4. Why I Chose Coordinate Mapping

- **Valid for fixed forms** — positions never change, so measuring once is enough.
- **Deterministic placement** — text lands exactly on the calibrated spot (accurate assuming the calibration is correct). Nothing is read, so there's no recognition step to go wrong.
- **Repeatable** — deterministic: identical inputs always produce identical output.
- **Fast and cheap** — measured **~138 ms per form**, ~54 MB memory, no GPU, no internet.
- **Easy to maintain** — a new bank = a new config file, not new code.

## 5. Why Not OCR (Here)

OCR's real strength is **handling layouts that change** — which ours don't. On a fixed form it would only add downsides:

- **Accuracy dependency** — OCR accuracy depends on scan quality, preprocessing, font, and language. Coordinate mapping avoids that dependency entirely, because it doesn't perform text recognition.
- **Higher compute cost** — OCR performs additional image analysis and text recognition, making it computationally more expensive than direct coordinate placement.

OCR is solving a **harder problem than we have** — reading the page — with no benefit for a form whose layout we already know. It isn't "worse"; it's simply built for the *other* branch of the decision tree.

## 6. How It Works — Two Systems

The tool is **two systems joined by one file.** One is a **one-time setup** (a human clicks the field spots). The other is the **automatic engine** (runs for every customer, no human).

```
   SYSTEM 1 — CALIBRATION  (setup, once per form)
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

> **The renderer is completely stateless. It does not know anything about bank forms or field names — it simply combines a PDF, a mapping, and customer data. All template-specific knowledge lives in configuration, not in code.**

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

## 7. Why These Technologies

- **Python** — the strongest ecosystem for PDF and image work, quick to build, easy to read and hand over. The job is file I/O and simple coordinate maths, not heavy computation.
- **PyMuPDF** — I needed one library that could both render pages for calibration and write vector text back onto PDFs, so I chose PyMuPDF.
- **OpenCV** — used only by the calibration tool, to show the page image and capture mouse clicks. Battle-tested and trivial for this.
- **JSON** (config + data) — human-readable, language-independent, and diff-friendly; config is data, not code.

## 8. Honest Downsides

- **Manual setup per form** — someone clicks each field once in a small tool. But that's a **one-time cost per template** (like writing a config), and every run after that is automatic.
- **Assumes tidy scans** — if a scan is badly shifted or skewed, fixed positions drift.
- **If my assumption is wrong** (unknown or changing layouts, customer photos) — coordinate mapping is the wrong tool and **OCR becomes right**. My design already separates *finding the position* from *drawing the text*, so an OCR step can slot in without a rewrite.

## 9. What's In, and What I Left Out (on purpose)

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

## 10. What Can Be Improved (Roadmap)

- **Support unknown templates via OCR-based field detection** — for the *other* branch of the decision tree (variable or unseen layouts), detect fields at run time instead of relying on a pre-made mapping. This is where OCR earns its place.
- **Modularise the code + add tests** — split each script into smaller, single-purpose modules (e.g. a `geometry` module for the coordinate conversions, an `io` module for loading config/data, a `draw` module for the overlay) and add unit tests for the pure functions (point↔pixel round-trip, hex→RGB, validation) plus an output comparison test. Makes the code easier to extend and safer to change.
- **Better calibration tool** — zoom, drag-to-adjust, undo.
- **Scalable calibration GUI** — with many fields the current window gets cluttered (dots and labels overlap). Improve it with a **side panel listing all fields** (click a field in the list to select it, tick shows which are placed), on-hover highlighting, and show/hide labels — so a form with 50+ fields stays readable.
- **Live preview** — show the real value at the clicked spot while calibrating (what-you-see-is-what-you-get).
- **Per-letter rendering** — for one-box-per-letter fields.
- **Long-text handling** — measure width, then warn/shrink/wrap.
- **Auto-detect the template** — recognise which form a PDF is and pick its mapping.
- **Batch mode** — many customers against one form in a single run.
- **Searchable output** — add an invisible text layer so the filled PDF is searchable.

## 11. Deployment

### Deployment Philosophy

The renderer is designed as a **stateless service**. It takes only three inputs — the **original PDF (template)**, the **mapping configuration**, and the **customer data** — and produces one output: the **filled PDF**.

Because the renderer is stateless, it is simple to deploy and easy to integrate into different environments such as an Automation Anywhere bot, REST API, or desktop application.

### Deployment Options

**1. Automation Anywhere (best fit)** — the renderer is packaged as a Python module or executable and invoked by an AA bot.

```
CRM / Excel  ─▶  Automation Anywhere  ─▶  Renderer  ─▶  Filled PDF
```
Matches the company's domain, drops into existing RPA workflows, and needs no UI.

**2. REST API** — the renderer runs as a lightweight web service.

```
POST /render

{
    "template": "axis_savings",
    "data": { ... }
}

        ↓

filled.pdf
```
For web portals, CRM systems, and internal applications.

**3. Desktop Application** — packaged with PyInstaller: offline, no Python install, suitable for bank branches.

**4. Batch Processing** — a background process monitors an input folder for new JSON files and automatically generates the corresponding PDFs.

```
input/  customer1.json, customer2.json, ...   ─▶   output/  customer1.pdf, customer2.pdf, ...
```
Suitable for overnight processing.

### Template Onboarding

Adding a new form is a one-time setup, not a code change:

```
new template PDF ─▶ render images ─▶ calibrate ─▶ mapping.json ─▶ store in library ─▶ available immediately
```
Supporting a new form requires only a new template and mapping. The rendering engine remains unchanged.

## 12. Product Architecture

How users interact with it, end to end:

```
                 Customer
                     │
                     ▼
              Select Template
                     │
          Existing? ────── No
             │              │
            Yes             ▼
             │      Internal Template
             │         Onboarding
             │              │
             ▼              ▼
        Template Library  (PDF + Mapping)
                     │
                     ▼
         Rendering Engine  ◀── customer data
                     │
                     ▼
                Filled PDF
```

> **The renderer never knows whether it is filling an Axis, Federal, or any other bank form. It simply receives a PDF, a mapping, and customer data. This keeps the engine generic while allowing the template library to grow independently.**

- The **rendering engine is deployed once** and is stateless, so it scales horizontally.
- A **template library** holds each form as *PDF + mapping*; the library grows over time, the code doesn't.
- **Existing template** → the customer submits their data → filled PDF in milliseconds.
- **New template** → triggers a one-time internal onboarding, after which it's available to every customer.


## 13. Numbers (Measured, Not Guessed)

| Metric | Result |
|---|---|
| Full render (8-page form, 9 fields) | ~138 ms average (10 runs) |
| Per field | ~15 ms |
| Peak memory | ~54 MB |
| Fields placed correctly | 9/9, right pages |
| Repeatability | Deterministic visual output for identical inputs |
| Silent failures | None — validation reports every skipped/missing field |

These come from **`src/benchmark.py`** — reproducible on any machine (`python src/benchmark.py`). Timing scales with field count (e.g. the 59-field Term Deposit form takes ~627 ms).

Note: the output **file bytes** differ slightly between runs — that's just PDF save metadata (a timestamp and document ID the format writes on save), not the placed content. The fill itself is fully deterministic: identical inputs always place the same values at the same coordinates.

