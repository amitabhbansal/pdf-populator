"""Fill a scanned PDF by overlaying values at pre-calibrated coordinates.

Reads three inputs and produces a filled PDF:
  - the original scanned PDF (unchanged background)
  - mapping.json  : per-field position (PDF points) + style (font/size/color)
  - data JSON     : the actual values to place, keyed by field name

The scanned pages are never modified; text is drawn on top of them (an overlay).

Coordinate note: mapping.json stores points in the PDF-native bottom-left origin
(y grows up). PyMuPDF's insert_text uses a top-left origin (y grows down), so this
renderer flips y at the boundary: y_top = page_height - y_stored.
"""

import json
import logging

import pymupdf

import settings

# -------------------------
# Configuration (paths and knobs come from settings.py)
# -------------------------

PDF_PATH = settings.INPUT_PDF
MAPPING_PATH = settings.MAPPING_FILE
DATA_PATH = settings.DATA_FILE
OUTPUT_PATH = settings.OUTPUT_PDF
BASELINE_NUDGE = settings.BASELINE_NUDGE

# Map human-readable font names (as stored in config) to PyMuPDF's built-in fonts.
# This is a PyMuPDF-specific detail, so it lives with the renderer, not in settings.
FONT_MAP = {
    "Helvetica": "helv",
    "Helvetica-Bold": "hebo",
    "Helvetica-Oblique": "heit",
    "Times-Roman": "tiro",
    "Times": "tiro",
    "Courier": "cour",
}
DEFAULT_FONT = "helv"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# -------------------------
# Helpers
# -------------------------


def load_json(path):
    """Load and parse a JSON file, raising a clear error if it fails."""
    with open(path) as f:
        return json.load(f)


def hex_to_rgb(value):
    """Convert a '#RRGGBB' hex colour to a 0-1 RGB tuple for PyMuPDF."""
    value = value.lstrip("#")
    try:
        r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return (r, g, b)
    except (ValueError, IndexError):
        logger.warning("Invalid colour '%s'; defaulting to black.", value)
        return (0, 0, 0)


def resolve_font(name):
    """Map a configured font name to a PyMuPDF built-in, defaulting to Helvetica."""
    return FONT_MAP.get(name, DEFAULT_FONT)


# -------------------------
# Validation
# -------------------------


def validate(mapping, data):
    """Cross-check the mapping and the data BEFORE rendering, so nothing is
    silently missing:
      - every calibrated field should have a value (data)
      - every data key should have a calibrated position (mapping)
    Returns True if rendering can proceed (warnings don't block; a completely
    empty mapping does)."""
    mapped = set(mapping.get("fields", {}))
    provided = set(data)

    for name in sorted(mapped - provided):
        logger.warning("Field '%s' is calibrated but has no value in the data file. "
                       "It will NOT be filled.", name)
    for name in sorted(provided - mapped):
        logger.warning("Data key '%s' has no calibrated position (typo, or not yet "
                       "calibrated?). It will be ignored.", name)

    if not mapped:
        logger.error("Mapping contains no fields; nothing to render.")
        return False
    return True


# -------------------------
# Rendering
# -------------------------


def render(pdf_path, mapping, data, output_path):
    """Overlay each field's value onto the correct page and save the filled PDF."""
    document = pymupdf.open(pdf_path)
    filled = 0
    skipped = []
    try:
        for field_name, spec in mapping.get("fields", {}).items():
            value = data.get(field_name)
            if value is None:
                skipped.append(field_name)
                continue

            page_index = spec.get("page", 1) - 1
            if not 0 <= page_index < document.page_count:
                logger.warning("Field '%s' references page %s which does not exist; skipping.",
                               field_name, spec.get("page"))
                skipped.append(field_name)
                continue

            page = document[page_index]

            x = spec["x"]
            y = spec["y"]
            font = resolve_font(spec.get("font", "Helvetica"))
            size = spec.get("size", 11)
            color = hex_to_rgb(spec.get("color", "#000000"))

            # mapping.json stores bottom-left PDF points; insert_text uses a top-left
            # origin (verified experimentally), so flip y at this boundary. The extra
            # nudge lowers the baseline so the clicked point acts as the text's top-left.
            y_top = page.rect.height - y + size * BASELINE_NUDGE
            position = (x, y_top)

            page.insert_text(
                position,
                str(value),
                fontname=font,
                fontsize=size,
                color=color,
            )
            filled += 1
            logger.info("Placed '%s' on page %s.", field_name, spec.get("page", 1))

        document.save(output_path)
    finally:
        document.close()

    # Run summary: one unambiguous line stating exactly what happened.
    if skipped:
        logger.warning("Summary: %d field(s) filled, %d skipped: %s",
                       filled, len(skipped), ", ".join(skipped))
    else:
        logger.info("Summary: all %d field(s) filled.", filled)
    logger.info("Output written to %s", output_path)
    return filled


def main():
    try:
        mapping = load_json(MAPPING_PATH)
        data = load_json(DATA_PATH)
    except FileNotFoundError as e:
        logger.error("Missing input file: %s", e)
        return
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return

    if not validate(mapping, data):
        return

    render(PDF_PATH, mapping, data, OUTPUT_PATH)


if __name__ == "__main__":
    main()