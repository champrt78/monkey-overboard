#!/usr/bin/env python3
"""Generate Monkey Overboard sprites via Gemini in Mulletdown-style pixel art."""
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


def _load_ref(path: Path):
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def _remove_bg(img: Image.Image) -> Image.Image:
    """Remove gray/checkerboard backgrounds baked into RGB by Gemini.

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
    h, w = labels.shape
    border = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    border_labels = set(np.unique(border))
    border_labels.discard(0)

    if border_labels:
        remove_mask = np.isin(labels, list(border_labels))
        alpha[remove_mask] = 0

    return Image.fromarray(arr, "RGBA")


def generate(name: str, prompt: str, final_wh: tuple, gen_wh: tuple):
    out = OUT_DIR / name
    print(f"Generating {name} ...")
    parts = [prompt, _load_ref(MULLET_REF), _load_ref(JUNGLE_REF)]
    response = client.models.generate_content(model=MODEL, contents=parts)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
            # Resize from generation resolution to final in-game resolution.
            if img.size != gen_wh:
                img = img.resize(gen_wh, Image.LANCZOS)
            if gen_wh != final_wh:
                img = img.resize(final_wh, Image.NEAREST)
            # Remove baked-in gray/checkerboard background, keep sprite art.
            img = _remove_bg(img)
            img.save(out, "PNG")
            print(f"  Saved {out.name} at {img.size}")
            return
    print(f"  WARNING: no image returned for {name}")


# Sprites are generated at 2x final resolution then downscaled with nearest-neighbor.
# The in-game Sprite2D / AnimatedSprite2D nodes use scale (1, 1), so one source pixel
# equals one viewport pixel — no runtime scaling, no fractional pixels.
SPRITES = [
    (
        "monkey_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A heroic cartoon jungle monkey in the same detailed modern-retro pixel art style as the jungle background. "
        "8 frames in one horizontal row, final size 128x16 pixels (each frame 16x16). "
        "PURE SOLID WHITE BACKGROUND #FFFFFF only, no gradients, no checkerboard, no gray, no texture. "
        "Thick black outline, strong cel-shading with 3 tones, warm brown/tan fur, expressive face, clear limbs. "
        "Frame 0-1: idle standing. Frame 2-3: ascending with arms reaching up. "
        "Frame 4-5: descending with arms tucked. Frame 6-7: tumbling spin. "
        "Side-view 2D game sprite, modern retro pixel art, cohesive with the lush jungle plate.",
        (128, 16),
        (256, 32),
    ),
    (
        "gator_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A cartoon alligator in the same detailed modern-retro pixel art style as the jungle background. "
        "5 frames in one horizontal row, final size 160x12 pixels (each frame 32x12). "
        "Completely transparent background, NO mat, NO background color, NO checkerboard, NO gray border, PURE SOLID WHITE BACKGROUND #FFFFFF is also acceptable. "
        "Thick black outline, strong cel-shading, jungle green scales, expressive yellow eyes, white teeth. "
        "Frame 0-1: patrol swimming. Frame 2: alert rearing up. Frame 3-4: chomp with jaws wide. "
        "Side-view 2D game sprite, modern retro pixel art, cohesive with the lush jungle plate.",
        (160, 12),
        (320, 24),
    ),
    (
        "gator_lunge_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A cartoon alligator LUNGING forward in the same detailed modern-retro pixel art style as the jungle background. "
        "2 frames in one horizontal row, final size 64x12 pixels (each frame 32x12). "
        "Completely transparent background, NO mat, NO background color, NO checkerboard, NO gray border, PURE SOLID WHITE BACKGROUND #FFFFFF is also acceptable. "
        "Thick black outline, strong cel-shading, jungle green scales, big yellow eyes, white teeth visible. "
        "Frame 0: body coiled back ready to lunge, mouth open. Frame 1: stretched forward mid-lunge, jaws wide. "
        "Side-view 2D game sprite facing LEFT, modern retro pixel art, cohesive with the lush jungle plate.",
        (64, 12),
        (128, 24),
    ),
    (
        "gator_chomp_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A cartoon alligator CHOMPING in the same detailed modern-retro pixel art style as the jungle background. "
        "2 frames in one horizontal row, final size 64x12 pixels (each frame 32x12). "
        "Completely transparent background, NO mat, NO background color, NO checkerboard, NO gray border, PURE SOLID WHITE BACKGROUND #FFFFFF is also acceptable. "
        "Thick black outline, strong cel-shading, jungle green scales, big yellow eyes, massive white teeth. "
        "Frame 0: jaws wide open waiting for the monkey to fall in. Frame 1: jaws snapping shut. "
        "Side-view 2D game sprite facing LEFT, modern retro pixel art, cohesive with the lush jungle plate.",
        (64, 12),
        (128, 24),
    ),
    (
        "banana_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A bright yellow banana in the same detailed modern-retro pixel art style as the jungle background. "
        "3 frames in one horizontal row, final size 24x8 pixels (each frame 8x8). "
        "PURE SOLID WHITE BACKGROUND #FFFFFF only, no gradients, no checkerboard, no gray, no texture. "
        "Thick black outline, slight wobble/shimmer, small highlight. "
        "Side-view 2D game sprite, modern retro pixel art, cohesive with the lush jungle plate.",
        (24, 8),
        (48, 16),
    ),
    (
        "splash_sheet.png",
        "High quality detailed pixel art sprite sheet matching BOTH reference images. "
        "A water splash in the same detailed modern-retro pixel art style as the jungle background. "
        "5 frames in one horizontal row, final size 80x16 pixels (each frame 16x16). "
        "PURE SOLID WHITE BACKGROUND #FFFFFF only, no gradients, no checkerboard, no gray, no texture. "
        "Blue and white water, impact to peak spray to dissipate. "
        "Side-view 2D game sprite, modern retro pixel art, cohesive with the lush jungle plate.",
        (80, 16),
        (160, 32),
    ),
    (
        "seesaw_plank.png",
        "High quality detailed pixel art wooden seesaw plank matching BOTH reference images. "
        "Single frame, final size 44x6 pixels. "
        "PURE SOLID WHITE BACKGROUND #FFFFFF only, no gradients, no checkerboard, no gray, no texture. "
        "Brown wood grain with darker ends, metal fulcrum hint, strong cel-shading. "
        "Modern retro pixel art, cohesive with the lush jungle plate.",
        (44, 6),
        (88, 12),
    ),
]

_targets = set(sys.argv[1:]) if len(sys.argv) > 1 else set()
for name, prompt, final_size, gen_size in SPRITES:
    if _targets and name not in _targets:
        continue
    generate(name, prompt, final_size, gen_size)

print("Done.")
