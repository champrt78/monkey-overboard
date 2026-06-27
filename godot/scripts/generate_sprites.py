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


# Sprites are generated at 4x final resolution then downscaled with nearest-neighbor.
# Final frame sizes are doubled from the original 14x14-era sprites; the scene scales
# the AnimatedSprite2D nodes to 0.5 so they keep the same world proportions while
# looking crisp at higher resolution.
SPRITES = [
    (
        "monkey_sheet.png",
        "High quality detailed pixel art sprite sheet in the exact style of the reference image. "
        "A cartoon jungle monkey, 8 frames in one horizontal row, final size 224x28 pixels (each frame 28x28). "
        "Transparent background, NO white mat, NO background, thick black outline, strong cel-shading, warm jungle palette. "
        "Frame 0-1: idle standing. Frame 2-3: ascending with arms reaching up. "
        "Frame 4-5: descending with arms tucked. Frame 6-7: tumbling spin. "
        "Side-view 2D game sprite, modern retro pixel art, expressive face, clear limbs.",
        (224, 28),
        (896, 112),
    ),
    (
        "gator_sheet.png",
        "High quality detailed pixel art sprite sheet in the exact style of the reference image. "
        "A cartoon alligator, 5 frames in one horizontal row, final size 320x24 pixels (each frame 64x24). "
        "Transparent background, NO white mat, NO background, thick black outline, strong cel-shading, jungle green palette. "
        "Frame 0-1: patrol swimming. Frame 2: alert rearing up. Frame 3-4: chomp with jaws wide. "
        "Side-view 2D game sprite, modern retro pixel art, expressive yellow eyes, white teeth.",
        (320, 24),
        (1280, 96),
    ),
    (
        "banana_sheet.png",
        "High quality detailed pixel art sprite sheet in the exact style of the reference image. "
        "A bright yellow banana, 3 frames in one horizontal row, final size 60x20 pixels (each frame 20x20). "
        "Transparent background, NO white mat, NO background, thick black outline, slight wobble/shimmer. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (60, 20),
        (240, 80),
    ),
    (
        "splash_sheet.png",
        "High quality detailed pixel art sprite sheet in the exact style of the reference image. "
        "A water splash, 5 frames in one horizontal row, final size 160x32 pixels (each frame 32x32). "
        "Transparent background, NO white mat, NO background, blue and white, impact to dissipate. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (160, 32),
        (640, 128),
    ),
    (
        "seesaw_plank.png",
        "High quality detailed pixel art wooden seesaw plank in the exact style of the reference image. "
        "Single frame, final size 88x12 pixels. "
        "Transparent background, NO white mat, NO background, brown wood grain with darker ends, metal fulcrum hint. "
        "Modern retro pixel art.",
        (88, 12),
        (352, 48),
    ),
]

for name, prompt, final_size, gen_size in SPRITES:
    generate(name, prompt, final_size, gen_size)

print("Done.")
