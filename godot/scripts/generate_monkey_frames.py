#!/usr/bin/env python3
"""Generate Monkey Overboard monkey frames individually and pack them into a sheet."""
import os
import sys
from pathlib import Path
from io import BytesIO
import numpy as np
import scipy.ndimage as ndi
from google import genai
from google.genai import types
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "assets" / "sprites"
OUT_DIR.mkdir(parents=True, exist_ok=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    sys.exit("ERROR: GEMINI_API_KEY not set")
client = genai.Client(api_key=api_key)
MODEL = "models/gemini-3.1-flash-image"
MULLET_REF = Path("C:/Users/Ray/Kimi-Repos/mulletdown/docs/mockups/screens/title_plate.png")
JUNGLE_REF = Path("C:/Users/Ray/kimi-repos/monkey-overboard/godot/assets/backgrounds/jungle_bg.png")

FRAME_W, FRAME_H = 28, 28
FINAL_SHEET = (FRAME_W * 8, FRAME_H)


def _load_ref(path: Path):
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def _remove_bg(img: Image.Image) -> Image.Image:
    """Remove gray/checkerboard/white backgrounds baked into RGB by Gemini.

    Treats desaturated (<40) or very bright/near-white (>245) pixels as
    background, labels connected components, and zeroes out any component
    touching an image border. Keeps interior sprite art intact.
    """
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    desat = maxc - minc

    # Background seed: gray-ish or near-white/bright regions.
    # Threshold 245 preserves bright saturated sprite colors (e.g. yellow banana)
    # while still catching near-white/very-light-gray background mats.
    bg = (desat < 40) | (maxc > 245)

    labels, _ = ndi.label(bg)
    border = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    border_labels = set(np.unique(border))
    border_labels.discard(0)

    if border_labels:
        remove_mask = np.isin(labels, list(border_labels))
        alpha[remove_mask] = 0

    return Image.fromarray(arr, "RGBA")


def _generate_one(prompt: str, out: Path, gen_wh: tuple):
    print(f"Generating {out.name} ...")
    parts = [prompt, _load_ref(MULLET_REF), _load_ref(JUNGLE_REF)]
    response = client.models.generate_content(model=MODEL, contents=parts)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
            if img.size != gen_wh:
                img = img.resize(gen_wh, Image.LANCZOS)
            img = img.resize((FRAME_W, FRAME_H), Image.NEAREST)
            img = _remove_bg(img)
            img.save(out, "PNG")
            print(f"  Saved {out.name} at {img.size}")
            return
    print(f"  WARNING: no image returned for {out.name}")


FRAME_PROMPTS = [
    ("idle_0.png", "Modern-retro pixel-art jungle monkey, standing idle, slight breathing pose, side view facing right. Thick black outline, cel-shaded brown/tan fur, expressive face. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("idle_1.png", "Modern-retro pixel-art jungle monkey, standing idle with a tiny upward lean, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("ascend_0.png", "Modern-retro pixel-art jungle monkey, ascending with arms reaching up, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("ascend_1.png", "Modern-retro pixel-art jungle monkey, ascending higher with arms stretched, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("descend_0.png", "Modern-retro pixel-art jungle monkey, descending with arms tucked, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("descend_1.png", "Modern-retro pixel-art jungle monkey, descending with arms and legs tucked, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("tumble_0.png", "Modern-retro pixel-art jungle monkey, tumbling/spinning in mid-air, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("tumble_1.png", "Modern-retro pixel-art jungle monkey, tumbling/spinning further, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
]


def _verify_sheet(path: Path) -> bool:
    img = Image.open(path).convert("RGBA")
    print(f"Sheet size: {img.size}, mode: {img.mode}")
    w, h = img.size
    expected = (FRAME_W * 8, FRAME_H)
    if img.size != expected:
        print(f"ERROR: expected size {expected}, got {img.size}")
        return False
    if img.mode != "RGBA":
        print(f"ERROR: expected RGBA mode, got {img.mode}")
        return False
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for x, y in corners:
        px = img.getpixel((x, y))
        if px[3] != 0:
            print(f"ERROR: corner ({x}, {y}) is not transparent: {px}")
            return False
    print(f"Corners transparent: {corners}")
    return True


def main():
    tmp_dir = OUT_DIR / "_monkey_tmp"
    tmp_dir.mkdir(exist_ok=True)
    frames = []
    gen_wh = (FRAME_W * 4, FRAME_H * 4)
    for name, prompt in FRAME_PROMPTS:
        out = tmp_dir / name
        _generate_one(prompt, out, gen_wh)
        frames.append(out)

    sheet = Image.new("RGBA", FINAL_SHEET, (255, 255, 255, 0))
    for i, path in enumerate(frames):
        if not path.exists():
            print(f"ERROR: missing frame {path}")
            continue
        frm = Image.open(path).convert("RGBA")
        if frm.size != (FRAME_W, FRAME_H):
            print(f"WARNING: resizing {path.name} from {frm.size} to {(FRAME_W, FRAME_H)}")
            frm = frm.resize((FRAME_W, FRAME_H), Image.NEAREST)
        sheet.paste(frm, (i * FRAME_W, 0), frm)

    out_path = OUT_DIR / "monkey_sheet.png"
    sheet.save(out_path, "PNG")
    print(f"Packed {out_path}")

    if not _verify_sheet(out_path):
        sys.exit("ERROR: sheet verification failed")
    print("Sheet verified.")


if __name__ == "__main__":
    main()
