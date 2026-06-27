#!/usr/bin/env python3
"""Generate Monkey Overboard sprites via Gemini in Mulletdown-style pixel art."""
import os
import sys
from pathlib import Path
from io import BytesIO
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
MODEL = "models/gemini-3-pro-image-preview"
REF_IMAGE = Path("C:/Users/Ray/Kimi-Repos/mulletdown/docs/mockups/screens/title_plate.png")


def _load_ref(path: Path):
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def generate(name: str, prompt: str, final_wh: tuple, gen_wh: tuple):
    out = OUT_DIR / name
    print(f"Generating {name} ...")
    parts = [prompt, _load_ref(REF_IMAGE)]
    response = client.models.generate_content(model=MODEL, contents=parts)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
            # Resize from generation resolution to final in-game resolution.
            if img.size != gen_wh:
                img = img.resize(gen_wh, Image.LANCZOS)
            if gen_wh != final_wh:
                img = img.resize(final_wh, Image.NEAREST)
            # Make sure pure-white backgrounds are transparent.
            datas = img.getdata()
            new_data = []
            for item in datas:
                r, g, b, a = item
                if a > 0 and r > 245 and g > 245 and b > 245:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            img.save(out, "PNG")
            print(f"  Saved {out.name} at {img.size}")
            return
    print(f"  WARNING: no image returned for {name}")


# Frame sizes are kept identical to the current sheets so no scene scaling is needed.
# Each frame is generated at 4x then downscaled with nearest-neighbor.
SPRITES = [
    (
        "monkey_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A cartoon jungle monkey, "
        "8 frames in one horizontal row, final size 112x14 pixels (each frame 14x14). "
        "Transparent background, NO white mat, thick black outline, cel-shaded, warm jungle palette. "
        "Frame 0-1: idle standing. Frame 2-3: ascending with arms reaching up. "
        "Frame 4-5: descending with arms tucked. Frame 6-7: tumbling spin. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (112, 14),
        (448, 56),
    ),
    (
        "gator_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A cartoon alligator, "
        "5 frames in one horizontal row, final size 160x12 pixels (each frame 32x12). "
        "Transparent background, NO white mat, thick black outline, cel-shaded, jungle green palette. "
        "Frame 0-1: patrol swimming. Frame 2: alert rearing up. Frame 3-4: chomp with jaws wide. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (160, 12),
        (640, 48),
    ),
    (
        "banana_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A bright yellow banana, "
        "3 frames in one horizontal row, final size 30x10 pixels (each frame 10x10). "
        "Transparent background, NO white mat, thick black outline, slight wobble/shimmer. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (30, 10),
        (120, 40),
    ),
    (
        "splash_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A water splash, "
        "5 frames in one horizontal row, final size 80x16 pixels (each frame 16x16). "
        "Transparent background, NO white mat, blue and white, impact to dissipate. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (80, 16),
        (320, 64),
    ),
    (
        "seesaw_plank.png",
        "Pixel art wooden seesaw plank in the style of the reference image. "
        "Single frame, final size 44x6 pixels. "
        "Transparent background, NO white mat, brown wood grain with darker ends. "
        "Modern retro pixel art.",
        (44, 6),
        (176, 24),
    ),
]

for name, prompt, final_size, gen_size in SPRITES:
    generate(name, prompt, final_size, gen_size)

print("Done.")
