#!/usr/bin/env python3
"""Generate the 135x720 jungle background plate for Monkey Overboard."""
import io
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "godot" / "assets" / "backgrounds"
TARGET_SIZE = (135, 720)
MODEL = "models/gemini-3-pro-image-preview"
REF_IMAGE = Path("C:/Users/Ray/Kimi-Repos/mulletdown/docs/mockups/screens/title_plate.png")


def dark_band_overlay(img: Image.Image, y0: int, y1: int, alpha: int = 180) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, y0, img.width, y1], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def generate_base_image(prompt: str, label: str) -> Image.Image:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    client = genai.Client(api_key=api_key)
    print(f"[gen] {label}: requesting {MODEL} ...")
    parts = [prompt, types.Part.from_bytes(data=REF_IMAGE.read_bytes(), mime_type="image/png")]
    response = client.models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="9:16"),
        ),
    )
    if not response.candidates:
        raise RuntimeError(f"{label}: no candidates in response")
    parts = response.candidates[0].content.parts if response.candidates[0].content else []
    for part in parts:
        if part.inline_data and part.inline_data.data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
    raise RuntimeError(f"{label}: no image data found")


def resize_to_target(img: Image.Image) -> Image.Image:
    tw, th = TARGET_SIZE
    target_aspect = tw / th
    w, h = img.size
    aspect = w / h
    if aspect > target_aspect:
        new_w = int(h * target_aspect)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif aspect < target_aspect:
        new_h = int(w / target_aspect)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = (
        "A detailed modern retro pixel-art jungle background for a vertical mobile game, "
        "exactly matching the style of the reference image. The canvas is tall and narrow (9:16). "
        "ONLY a very small strip of sky at the very top with a few clouds and distant treetops. "
        "The rest is dense tropical jungle: thick tree trunk, hanging vines, big layered canopy leaves, "
        "tropical plants, dappled sunlight, warm greens and browns. "
        "The bottom 8 percent is water with reflections and reeds. "
        "No characters, no UI, no text. Strong black outlines, cel-shading, saturated colors."
    )
    img = generate_base_image(prompt, "jungle_bg")
    img = resize_to_target(img)
    out = OUT_DIR / "jungle_bg.png"
    img.save(out, "PNG")
    print(f"[saved] {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
