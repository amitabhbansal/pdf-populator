"""Reproducible benchmark for the PDF Population Engine.

Measures render performance and peak memory using the same render() the real
pipeline uses — so the numbers in the docs can be reproduced by anyone, on any
machine, at any time:

    python src/benchmark.py

The numbers naturally vary a little with machine and with the active template
(set INPUT_PDF / DATA_FILE in settings.py). The script prints the template and
field count so every result is self-describing.

The render output is written to the system temp folder (not the project) and
deleted afterwards, so running the benchmark never leaves a PDF behind.
"""

import logging
import os
import resource
import tempfile
import time

import settings
import pdf_renderer

RUNS = 10
TMP_OUTPUT = os.path.join(tempfile.gettempdir(), "_pdf_populator_benchmark.pdf")


def main():
    logging.disable(logging.CRITICAL)  # silence per-field render logs while timing

    mapping = pdf_renderer.load_json(settings.MAPPING_FILE)
    data = pdf_renderer.load_json(settings.DATA_FILE)
    field_count = len(mapping.get("fields", {}))

    # --- Performance: RUNS full renders (open PDF -> place all fields -> save) ---
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        pdf_renderer.render(settings.INPUT_PDF, mapping, data, TMP_OUTPUT)
        times.append(time.perf_counter() - start)
    avg = sum(times) / len(times)

    # --- Peak memory (macOS reports bytes, Linux reports KB) ---
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = rss / (1024 * 1024) if rss > 1_000_000 else rss / 1024

    if os.path.exists(TMP_OUTPUT):
        os.remove(TMP_OUTPUT)

    per_field = f"{avg * 1000 / field_count:.2f} ms" if field_count else "n/a"

    print("PDF Population Engine — benchmark")
    print("---------------------------------")
    print(f"template           : {settings.TEMPLATE_NAME}")
    print(f"fields per render  : {field_count}")
    print(f"runs               : {RUNS}")
    print(f"avg render time    : {avg * 1000:.1f} ms")
    print(f"min / max          : {min(times) * 1000:.1f} / {max(times) * 1000:.1f} ms")
    print(f"time per field     : {per_field}")
    print(f"peak memory        : {peak_mb:.0f} MB")


if __name__ == "__main__":
    main()
