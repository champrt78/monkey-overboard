#!/usr/bin/env python3
"""Generate Monkey Overboard sprites via Gemini."""
import os, sys
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


def generate(name, prompt, size_wh):
	out = OUT_DIR / name
	print(f"Generating {name} ...")
	response = client.models.generate_content(model=MODEL, contents=[prompt])
	for part in response.candidates[0].content.parts:
		if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
			img = Image.open(BytesIO(part.inline_data.data))
			img = img.convert("RGBA")
			# PIL verify dimensions fill the canvas — resize if needed
			if img.size != size_wh:
				img = img.resize(size_wh, Image.NEAREST)
			img.save(out, "PNG")
			print(f"  Saved {out.name} at {img.size}")
			return
	print(f"  WARNING: no image returned for {name}")


SPRITES = [
	("monkey_sheet.png",
	 "Pixel art sprite sheet for a cartoon monkey character, 6 frames in a single horizontal row, "
	 "each frame 14x14 pixels, 84x14 pixels total. Jungle palette. Transparent background. "
	 "Frame 0: sitting idle. Frame 1: arms-up ascending. Frame 2: arms-out descending/alarmed. "
	 "Frame 3: arms-spread happy catch. Frame 4: tumbling scared (miss). Frame 5: thumbs-up celebrate. "
	 "Chunky retro pixel art, NES/Game Boy Color style, clean outline, no anti-aliasing.",
	 (84, 14)),
	("gator_sheet.png",
	 "Pixel art sprite sheet for an alligator, 4 frames horizontal, each 32x12 pixels, 128x12 total. "
	 "Jungle green palette, yellow eyes, white teeth. Transparent background. "
	 "Frame 0: calm patrol eyes-open. Frame 1: leaning forward alert. "
	 "Frame 2: mouth wide open chomp. Frame 3: mouth shut satisfied. "
	 "Chunky retro pixel art, viewed from the side, NES style, clean outline.",
	 (128, 12)),
	("banana_sheet.png",
	 "Pixel art sprite sheet for a banana, 2 frames horizontal, each 10x10 pixels, 20x10 total. "
	 "Bright yellow banana, slight pixel glow/shimmer on frame 2. Transparent background. "
	 "Chunky retro pixel art, NES/Game Boy Color style.",
	 (20, 10)),
	("seesaw_plank.png",
	 "Pixel art wooden plank for a game see-saw, single frame, 44x6 pixels. "
	 "Brown wood grain, slight bevel on top and bottom edges, darker ends. "
	 "Transparent background. Chunky retro pixel art.",
	 (44, 6)),
	("splash_sheet.png",
	 "Pixel art water splash animation, 4 frames horizontal, each 16x16 pixels, 64x16 total. "
	 "Blue/white water eruption: frame 0 impact, frames 1-2 peak spray, frame 3 settling. "
	 "Transparent background. Chunky retro pixel art.",
	 (64, 16)),
]

for name, prompt, size in SPRITES:
	generate(name, prompt, size)

print("Done.")
