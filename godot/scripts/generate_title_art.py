#!/usr/bin/env python3
"""Generate 135x240 title/gameover plates for Monkey Overboard using Gemini image gen."""

import io
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "godot" / "assets" / "screens"
TARGET_SIZE = (135, 240)
MODEL = "models/gemini-3-pro-image-preview"


def dark_band_overlay(img: Image.Image, y0: int, y1: int, alpha: int = 180) -> Image.Image:
	"""Darken a horizontal band by compositing a translucent black rectangle."""
	overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
	draw = ImageDraw.Draw(overlay)
	draw.rectangle([0, y0, img.width, y1], fill=(0, 0, 0, alpha))
	return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def pil_verify(img: Image.Image, label: str) -> None:
	"""Ensure the image is exactly the target size and not mostly empty/black."""
	if img.size != TARGET_SIZE:
		raise RuntimeError(f"{label} size is {img.size}, expected {TARGET_SIZE}")

	# Convert to grayscale for analysis.
	gray = img.convert("L")
	pixels = list(gray.get_flattened_data())
	total = len(pixels)
	blackish = sum(1 for p in pixels if p < 10)
	avg = sum(pixels) / total

	# Reject if more than 55 % is near-black or overall image is extremely dim.
	if blackish / total > 0.55:
		raise RuntimeError(f"{label} has too many black void pixels ({blackish}/{total})")
	if avg < 12:
		raise RuntimeError(f"{label} average brightness too low ({avg:.2f})")

	# Ensure no entire edge row/column is completely black.
	for y in range(img.height):
		if all(gray.getpixel((x, y)) == 0 for x in range(img.width)):
			raise RuntimeError(f"{label} has a completely black row at y={y}")
	for x in range(img.width):
		if all(gray.getpixel((x, y)) == 0 for y in range(img.height)):
			raise RuntimeError(f"{label} has a completely black column at x={x}")

	print(f"[verify] {label}: size={img.size}, avg_brightness={avg:.1f}, blackish={blackish}/{total}")


def generate_base_image(prompt: str, label: str) -> Image.Image:
	"""Call the Gemini API and return the generated image as a PIL RGB image."""
	api_key = os.environ.get("GEMINI_API_KEY")
	if not api_key:
		raise RuntimeError("GEMINI_API_KEY environment variable is not set")

	client = genai.Client(api_key=api_key)
	print(f"[gen] {label}: requesting {MODEL} ...")
	response = client.models.generate_content(
		model=MODEL,
		contents=[prompt],
		config=types.GenerateContentConfig(
			response_modalities=["TEXT", "IMAGE"],
			image_config=types.ImageConfig(
				aspect_ratio="9:16",
				image_size="1K",
			),
		),
	)

	# Extract the first inline image part from the response.
	if not response.candidates:
		raise RuntimeError(f"{label}: no candidates in response")
	candidate = response.candidates[0]
	parts = candidate.content.parts if candidate.content else []
	for part in parts:
		if part.inline_data and part.inline_data.data:
			img = Image.open(io.BytesIO(part.inline_data.data))
			return img.convert("RGB")

	raise RuntimeError(f"{label}: no image data found in response parts")


def resize_to_target(img: Image.Image) -> Image.Image:
	"""Crop/resize the generated image to the exact 135x240 target, filling canvas."""
	# Ensure we crop to a 9:16 aspect ratio before resizing to avoid distortion.
	tw, th = TARGET_SIZE
	target_aspect = tw / th
	w, h = img.size
	aspect = w / h

	if aspect > target_aspect:
		# Too wide: crop width.
		new_w = int(h * target_aspect)
		left = (w - new_w) // 2
		img = img.crop((left, 0, left + new_w, h))
	elif aspect < target_aspect:
		# Too tall: crop height.
		new_h = int(w / target_aspect)
		top = (h - new_h) // 2
		img = img.crop((0, top, w, top + new_h))

	return img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)


def save_png(img: Image.Image, path: Path) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	img.save(path, "PNG")


def main() -> int:
	OUT_DIR.mkdir(parents=True, exist_ok=True)

	# --- title plate ---
	title_prompt = (
		"A vibrant retro pixel-art jungle title screen for a mobile game. "
		"Lush green tropical foliage, vines, and a distant tiki totem. "
		"Bold stylized text reads 'MONKEY OVERBOARD' near the top in bright yellow/orange. "
		"The bottom 30% of the image is a smooth dark shadowy area with no text, "
		"leaving clear empty space for UI buttons. "
		"Vertical 9:16 composition, colorful, game-art style."
	)
	title_img = generate_base_image(title_prompt, "title_plate")
	title_img = resize_to_target(title_img)
	# Reinforce the bottom 30% dark area for UI clarity.
	band_top = int(TARGET_SIZE[1] * 0.70)
	title_img = dark_band_overlay(title_img, band_top, TARGET_SIZE[1], alpha=190)
	pil_verify(title_img, "title_plate")
	title_path = OUT_DIR / "title_plate.png"
	save_png(title_img, title_path)
	print(f"[saved] {title_path} ({title_path.stat().st_size} bytes)")

	# --- gameover plate ---
	gameover_prompt = (
		"A retro pixel-art game-over screen for a mobile jungle game. "
		"Darkened jungle backdrop with silhouetted palm trees and vines. "
		"Large dramatic text reads 'GAME OVER' in bold red/orange near the top. "
		"A dark horizontal band across the middle for displaying a score, "
		"and another dark band at the bottom for a 'try again' prompt. "
		"CRITICAL: absolutely NO numbers, scores, high-score values, or placeholder text. "
		"No 'SCORE:', no 'HIGH SCORE:', no digits, no mock numbers anywhere. "
		"Vertical 9:16 composition, moody, game-art style."
	)
	gameover_img = generate_base_image(gameover_prompt, "gameover_plate")
	gameover_img = resize_to_target(gameover_img)
	# Reinforce middle and bottom dark bands.
	mid_top = int(TARGET_SIZE[1] * 0.36)
	mid_bot = int(TARGET_SIZE[1] * 0.56)
	bot_top = int(TARGET_SIZE[1] * 0.74)
	gameover_img = dark_band_overlay(gameover_img, mid_top, mid_bot, alpha=215)
	gameover_img = dark_band_overlay(gameover_img, bot_top, TARGET_SIZE[1], alpha=225)
	pil_verify(gameover_img, "gameover_plate")
	gameover_path = OUT_DIR / "gameover_plate.png"
	save_png(gameover_img, gameover_path)
	print(f"[saved] {gameover_path} ({gameover_path.stat().st_size} bytes)")

	return 0


if __name__ == "__main__":
	try:
		sys.exit(main())
	except Exception as exc:
		print(f"ERROR: {exc}", file=sys.stderr)
		sys.exit(1)
