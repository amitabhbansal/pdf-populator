import cv2
import json
import os
import glob
import re

import settings

# -------------------------
# Configuration (all values come from settings.py — the single source of truth)
# -------------------------

TEMPLATE_NAME = settings.TEMPLATE_NAME
IMAGE_DIR = settings.IMAGE_DIR
OUTPUT_MAPPING = settings.MAPPING_FILE
DATA_PATH = settings.DATA_FILE
DPI = settings.DPI
DEFAULT_FONT = settings.DEFAULT_FONT
DEFAULT_SIZE = settings.DEFAULT_SIZE
DEFAULT_COLOR = settings.DEFAULT_COLOR

# Field names come from the DATA FILE's keys — the user writes that file anyway for
# rendering, so there is no separate field list to author. The page for each field is
# captured from whichever page is on screen when the user clicks ([ / ] to navigate).
# A boolean value marks the field as a CHECKBOX: click the centre of its box.
try:
    with open(DATA_PATH) as f:
        _data = json.load(f)
    FIELDS = list(_data.keys())
    FIELD_TYPES = {k: ("checkbox" if isinstance(v, bool) else "text")
                   for k, v in _data.items()}
except (OSError, json.JSONDecodeError) as e:
    print(f"Could not load field names from {DATA_PATH}: {e}")
    exit()

if not FIELDS:
    print(f"No fields found in {DATA_PATH}.")
    exit()

# -------------------------
# Load Page Images
# -------------------------

# Discover page images named pageN.png and load them in page order.
image_paths = glob.glob(os.path.join(IMAGE_DIR, "page*.png"))


def page_number_of(path):
    match = re.search(r"page(\d+)\.png$", os.path.basename(path))
    return int(match.group(1)) if match else 0


image_paths = sorted(image_paths, key=page_number_of)

if not image_paths:
    print(f"No page images found in {IMAGE_DIR} (run pdf_to_images.py first).")
    exit()

# Each entry: page number, image, and page size in points derived from the image.
# points = pixels * 72 / DPI  (72 points per inch)
pages = {}
for path in image_paths:
    img = cv2.imread(path)
    if img is None:
        continue
    h, w = img.shape[:2]
    num = page_number_of(path)
    pages[num] = {
        "img": img,
        "width_pt": w * 72 / DPI,
        "height_pt": h * 72 / DPI,
    }

# Quick lookup of a page's height in points, needed for the y-flip per field.
page_height_of = {num: p["height_pt"] for num, p in pages.items()}
first_page_num = min(pages)

# -------------------------
# State
# -------------------------

# mapping holds captured PIXEL positions per field; converted to points on save.
# Each value: {"page": <int>, "x": <px>, "y": <px>}.
mapping = {}
current_index = 0                     # which field is active
page_nums = sorted(pages)             # ordered page numbers
current_page_idx = 0                  # index into page_nums (user navigates with [ ])


def to_points(px, py, page_h_pt):
    """Convert an image pixel (top-left origin, y down) to a PDF point
    (bottom-left origin, y up). The clicked point is treated as the text baseline."""
    x_pt = round(px * 72 / DPI, 2)
    y_pt = round(page_h_pt - py * 72 / DPI, 2)
    return x_pt, y_pt


def to_pixels(x_pt, y_pt, page_h_pt):
    """Inverse of to_points: convert a stored PDF point back to an image pixel,
    so an existing mapping can be reloaded and edited."""
    px = round(x_pt * DPI / 72)
    py = round((page_h_pt - y_pt) * DPI / 72)
    return px, py


# Load any existing mapping so a re-run updates fields instead of wiping the file.
# Fields not re-clicked this run are preserved.
if os.path.exists(OUTPUT_MAPPING):
    try:
        with open(OUTPUT_MAPPING) as f:
            existing = json.load(f)
        for name, info in existing.get("fields", {}).items():
            page_num = info.get("page", first_page_num)
            page_h = page_height_of.get(page_num, pages[first_page_num]["height_pt"])
            px, py = to_pixels(info["x"], info["y"], page_h)
            mapping[name] = {"page": page_num, "x": px, "y": py}
        if mapping:
            print(f"Loaded {len(mapping)} existing field(s) from {OUTPUT_MAPPING}")
    except (json.JSONDecodeError, KeyError, OSError) as e:
        print(f"Could not load existing mapping ({e}); starting fresh.")


# -------------------------
# Mouse Callback
# -------------------------


def mouse_callback(event, x, y, flags, param):
    global mapping

    if event == cv2.EVENT_LBUTTONDOWN:
        if current_index >= len(FIELDS):
            return  # "done" state: no active field, ignore clicks
        name = FIELDS[current_index]
        # The page is whatever the user is currently looking at.
        page_num = page_nums[current_page_idx]
        mapping[name] = {"page": page_num, "x": x, "y": y}
        print(f"Set {name} -> page {page_num} ({x}, {y})")


# -------------------------
# Window
# -------------------------

cv2.namedWindow("Coordinate Calibrator")
cv2.setMouseCallback("Coordinate Calibrator", mouse_callback)

print("\nCommands")
print("----------------------------")
print("N   -> Next field")
print("P   -> Previous field")
print("]   -> Next page")
print("[   -> Previous page")
print("S   -> Save mapping")
print("R   -> Reset")
print("ESC -> Exit")
print("----------------------------")


def draw_text_bg(img, text, org, scale, fg, thickness):
    """Draw text on a solid black background box so it stays legible over the scan."""
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x, y = org
    cv2.rectangle(img, (x - 3, y - th - 5), (x + tw + 3, y + base + 2), (0, 0, 0), -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, fg, thickness, cv2.LINE_AA)


def jump_to_field_page(index):
    """If the field at `index` is already placed, switch the view to its page.
    Called once when the active field changes (not every frame), so the user can
    still navigate pages freely afterwards."""
    global current_page_idx
    if index < len(FIELDS):
        name = FIELDS[index]
        if name in mapping and mapping[name]["page"] in page_nums:
            current_page_idx = page_nums.index(mapping[name]["page"])


while True:

    done = current_index >= len(FIELDS)
    page_num = page_nums[current_page_idx]
    page = pages[page_num]
    window = page["img"].copy()

    # Draw only the markers that belong to the page currently on screen.
    for name, info in mapping.items():
        if info["page"] != page_num:
            continue
        cv2.circle(window, (info["x"], info["y"]), 5, (0, 0, 255), -1)
        draw_text_bg(window, name, (info["x"] + 10, info["y"] - 8),
                     0.5, (255, 255, 255), 1)

    draw_text_bg(window, f"Page {page_num}/{len(page_nums)}   [ ] to change page",
                 (10, 28), 0.6, (0, 255, 0), 2)

    if done:
        # All fields visited: nothing active, clicks do nothing, prompt to save.
        placed = sum(1 for n in FIELDS if n in mapping)
        draw_text_bg(window, f"All fields visited ({placed}/{len(FIELDS)} set) - press S to save, P to go back",
                     (10, 58), 0.6, (0, 255, 255), 2)
    else:
        active_name = FIELDS[current_index]

        # Ring highlights the active field, but only when it is placed on THIS page.
        if active_name in mapping and mapping[active_name]["page"] == page_num:
            a = mapping[active_name]
            cv2.circle(window, (a["x"], a["y"]), 9, (0, 165, 255), 2)

        status = "SET" if active_name in mapping else "not set"
        kind = FIELD_TYPES.get(active_name, "text")
        label = f"Field {current_index + 1}/{len(FIELDS)} : {active_name} ({kind}) [{status}]"
        draw_text_bg(window, label, (10, 58), 0.6, (0, 255, 255), 2)

    cv2.imshow("Coordinate Calibrator", window)

    key = cv2.waitKey(20) & 0xFF

    # ESC
    if key == 27:
        break

    # Next / previous field. Going past the last field enters the "done" state;
    # the view jumps to the newly active field's page once, if it is already placed.
    elif key == ord("n"):
        current_index = min(current_index + 1, len(FIELDS))
        jump_to_field_page(current_index)
    elif key == ord("p"):
        current_index = max(current_index - 1, 0)
        jump_to_field_page(current_index)

    # Next / previous page
    elif key == ord("]"):
        current_page_idx = min(current_page_idx + 1, len(page_nums) - 1)
    elif key == ord("["):
        current_page_idx = max(current_page_idx - 1, 0)

    # Reset: clear all placements and return to the first field on the first page.
    elif key == ord("r"):
        mapping.clear()
        current_index = 0
        current_page_idx = 0
        print("Reset complete.")

    # Save JSON
    elif key == ord("s"):

        first = pages[first_page_num]
        output = {
            "template": {
                "name": TEMPLATE_NAME,
                "page_width": round(first["width_pt"], 2),
                "page_height": round(first["height_pt"], 2),
            },
            "fields": {},
        }

        # Convert each captured pixel position to PDF points using its own page height.
        for name, info in mapping.items():
            page_h = page_height_of.get(info["page"], first["height_pt"])
            x_pt, y_pt = to_points(info["x"], info["y"], page_h)
            output["fields"][name] = {
                "type": FIELD_TYPES.get(name, "text"),
                "page": info["page"],
                "x": x_pt,
                "y": y_pt,
                "font": DEFAULT_FONT,
                "size": DEFAULT_SIZE,
                "color": DEFAULT_COLOR,
            }

        os.makedirs(os.path.dirname(OUTPUT_MAPPING) or ".", exist_ok=True)
        with open(OUTPUT_MAPPING, "w") as f:
            json.dump(output, f, indent=4)

        print(f"\nSaved {len(output['fields'])} field(s) to {OUTPUT_MAPPING}")
        break

cv2.destroyAllWindows()