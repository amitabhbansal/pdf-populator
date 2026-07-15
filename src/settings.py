"""Central configuration — the single place to change how the tool behaves.

Everything a user normally needs to adjust lives here. The individual scripts
(pdf_to_images, coordinate_calibrator, pdf_renderer) import these values, so there
is one source of truth and, importantly, DPI can never drift out of sync between
the renderer that makes the page images and the calibrator that reads them.

Paths are relative to the project root, so run the scripts from the project root:
    python src/pdf_to_images.py
"""

import os

# =========================================================
# 1. Which form and which data
# =========================================================

# The scanned PDF to fill, and the values to place into it.
INPUT_PDF = "input/Term Deposit Account Opening Form English_Original.pdf"
DATA_FILE = "input/sample_data.json"

# =========================================================
# 2. Rendering knobs
# =========================================================

# Resolution used to render pages for calibration. A single value shared by both
# the image renderer and the calibrator, so their coordinates always line up.
DPI = 120

# The stored coordinate is the text baseline; this fraction of the font size lowers
# it so the clicked point roughly centres the text vertically. Increase to move text
# down, decrease to move it up, 0 = pure baseline.
BASELINE_NUDGE = 0.35

# =========================================================
# 3. Default text style (written for each field during calibration)
# =========================================================

DEFAULT_FONT = "Helvetica"
DEFAULT_SIZE = 11
DEFAULT_COLOR = "#000000"

# =========================================================
# 4. Derived paths (usually no need to edit)
# =========================================================

# Template name is taken from the PDF filename, e.g. "Axis Original".
TEMPLATE_NAME = os.path.splitext(os.path.basename(INPUT_PDF))[0]

# Page images live under output/<template>/, keeping multiple forms separate.
IMAGE_DIR = os.path.join("output", TEMPLATE_NAME)

# The coordinate mapping produced by the calibrator.
# Stored PER TEMPLATE (derived from the PDF name), so calibrating a new form never
# overwrites the calibration of a previous one. Field names come from DATA_FILE's keys.
MAPPING_FILE = os.path.join("config", "mappings", f"{TEMPLATE_NAME}.json")

# Final filled PDF.
OUTPUT_PDF = os.path.join("output", f"filled_{TEMPLATE_NAME}.pdf")
