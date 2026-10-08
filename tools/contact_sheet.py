"""Contact sheet builder for review cards.

Lays out a set of images in a labelled grid, scaled up by an integer
nearest-neighbour factor so pixel art stays crisp. One PNG out.

Usage:
    python tools/contact_sheet.py --out sheet.png [--scale 6] [--cols N]
        [--bg "#202020"] [--label-from filename|none] <image> [<image> ...]

Exit status:
    0  sheet written
    2  more than 36 images supplied
"""
import argparse
import math
import os
import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont

MAX_IMAGES = 36
PADDING = 8
LABEL_GAP = 6
LABEL_COLOR = (255, 255, 255, 255)


def parse_color(spec):
    """Return an RGB tuple from a CSS/hex colour string such as '#202020'."""
    return ImageColor.getcolor(spec, "RGB")


def scale_nearest(image, factor):
    """Scale an image by an integer factor using NEAREST only.

    Factor must be a positive integer; anything else raises ValueError.
    """
    factor = int(factor)
    if factor < 1:
        raise ValueError("scale factor must be a positive integer")
    return image.resize((image.width * factor, image.height * factor), Image.NEAREST)


def default_cols(count):
    """Default column count: ceil(sqrt(count))."""
    return int(math.ceil(math.sqrt(count)))


def measure_label_heights(font, labels):
    """Return the pixel height of each label, in the same order as labels."""
    heights = []
    for text in labels:
        if text:
            _top, _bottom, _left, _right = font.getbbox(text)
            heights.append(_bottom - _top)
        else:
            heights.append(0)
    return heights


def compute_cell_size(max_scaled_w, max_scaled_h, label_height):
    """Return (cell_w, cell_h) for the largest scaled image plus padding."""
    cell_w = max_scaled_w + PADDING
    label_area = (LABEL_GAP + label_height) if label_height > 0 else 0
    cell_h = max_scaled_h + label_area + PADDING
    return cell_w, cell_h


def build_sheet(image_paths, scale, cols=None, bg="#202020", label_from="filename"):
    """Render a labelled contact sheet for image_paths and return the Image.

    cols defaults to ceil(sqrt(n)); cell size is the largest scaled image plus
    padding. Images are scaled by an integer NEAREST factor and labelled with
    their file stem unless label_from is 'none'.
    """
    if len(image_paths) > MAX_IMAGES:
        raise ValueError("too many images: {} (max {})".format(len(image_paths), MAX_IMAGES))

    n = len(image_paths)
    if cols is None:
        cols = default_cols(n)
    scale = int(scale)

    bg_color = parse_color(bg) + (255,)

    scaled_cells = []
    labels = []
    for path in image_paths:
        with Image.open(path) as im:
            im = im.convert("RGBA")
            scaled_cells.append(scale_nearest(im, scale))
        if label_from == "none":
            labels.append("")
        else:
            labels.append(os.path.splitext(os.path.basename(path))[0])

    max_w = max(cell.width for cell in scaled_cells)
    max_h = max(cell.height for cell in scaled_cells)

    if label_from == "none":
        label_height = 0
        font = None
    else:
        font = ImageFont.load_default()
        label_height = max(measure_label_heights(font, labels))

    cell_w, cell_h = compute_cell_size(max_w, max_h, label_height)
    rows = int(math.ceil(n / cols))
    sheet_w = cols * cell_w
    sheet_h = rows * cell_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), bg_color)
    draw = ImageDraw.Draw(sheet)

    for index in range(n):
        col = index % cols
        row = index // cols
        x0 = col * cell_w
        y0 = row * cell_h
        cell = scaled_cells[index]

        ix = x0 + (cell_w - cell.width) // 2
        iy = y0
        sheet.alpha_composite(cell, (ix, iy))

        text = labels[index]
        if text:
            left, _top, right, _bottom = font.getbbox(text)
            tw = right - left
            tx = x0 + (cell_w - tw) // 2
            ty = y0 + cell.height + LABEL_GAP
            draw.text((tx, ty), text, font=font, fill=LABEL_COLOR)

    return sheet


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a labelled contact sheet PNG from a set of images."
    )
    parser.add_argument("images", nargs="+", help="image files to include")
    parser.add_argument("--out", required=True, help="output PNG path")
    parser.add_argument("--scale", type=int, default=6, help="integer nearest scale factor")
    parser.add_argument("--cols", type=int, default=None, help="columns (default ceil(sqrt(n)))")
    parser.add_argument("--bg", default="#202020", help="background colour, e.g. '#202020'")
    parser.add_argument(
        "--label-from",
        choices=("filename", "none"),
        default="filename",
        help="label source: filename (file stem) or none",
    )
    args = parser.parse_args(argv)

    if len(args.images) > MAX_IMAGES:
        print(
            "error: too many images: {} (max {})".format(len(args.images), MAX_IMAGES),
            file=sys.stderr,
        )
        return 2

    try:
        sheet = build_sheet(
            args.images,
            scale=args.scale,
            cols=args.cols,
            bg=args.bg,
            label_from=args.label_from,
        )
    except ValueError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    sheet.convert("RGB").save(args.out, "PNG")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
