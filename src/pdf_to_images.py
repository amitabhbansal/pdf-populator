"""Render every page of a PDF to a PNG image (one file per page).

These images are what the coordinate calibrator uses to place fields. Rendering
here (rather than by hand) keeps the pipeline reproducible: the DPI is fixed and
recorded, so the pixel -> point conversion in the calibrator stays correct.

All configuration comes from settings.py (a single source of truth), so the DPI
here and in the calibrator can never drift apart.
"""

import os

import pymupdf

import settings


def main():
    os.makedirs(settings.IMAGE_DIR, exist_ok=True)

    # PyMuPDF renders at 72 DPI by default; scale by DPI/72 to reach the target DPI.
    zoom = settings.DPI / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    doc = pymupdf.open(settings.INPUT_PDF)
    page_count = doc.page_count
    try:
        for i, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(matrix=matrix)
            out_path = os.path.join(settings.IMAGE_DIR, f"page{i}.png")
            pixmap.save(out_path)
            print(f"Saved {out_path} ({pixmap.width}x{pixmap.height})")
    finally:
        doc.close()

    print(f"\nRendered {page_count} page(s) from {settings.INPUT_PDF} "
          f"into {settings.IMAGE_DIR} at {settings.DPI} DPI.")


if __name__ == "__main__":
    main()
