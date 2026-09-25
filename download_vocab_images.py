#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from md_flashcards import load_entries


def normalize_image_key(term: str) -> str:
    cleaned = str(term or "").strip()
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned


def iter_vocab_terms(file_names=None):
    if file_names is None:
        file_names = ["spanish_vocabulary.md", "otherwords.md"]

    seen = set()
    for entry in load_entries(file_names):
        if entry.get("type") != "vocab":
            continue
        term = (entry.get("es") or "").strip()
        if not term:
            continue
        key = normalize_image_key(term)
        if not key or key in seen:
            continue
        seen.add(key)
        yield term, key


def create_card_image(term: str, output_path: Path):
    text = term.strip()
    width, height = 1024, 768
    bg1 = (42, 84, 140)
    bg2 = (84, 144, 204)

    img = Image.new("RGB", (width, height), color=bg1)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(bg1[0] + (bg2[0] - bg1[0]) * ratio)
        g = int(bg1[1] + (bg2[1] - bg1[1]) * ratio)
        b = int(bg1[2] + (bg2[2] - bg1[2]) * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))

    card = Image.new("RGBA", (860, 520), (255, 255, 255, 180))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle((0, 0, 859, 519), radius=36, fill=(255, 255, 255, 180))
    img.paste(card, (82, 124), card)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 120)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 46)
    except OSError:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (width - text_w) / 2
    draw.text((text_x, 290), text, font=font, fill=(18, 27, 52))

    draw.text((80, 640), "Spanish word", font=font_small, fill=(230, 240, 255))
    img.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate local image cards for Spanish vocab terms.")
    parser.add_argument("--image-dir", default="images", help="Folder to store generated images.")
    parser.add_argument("--limit", type=int, help="Optional limit for how many terms to generate.")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)

    index = {}
    items = list(iter_vocab_terms())
    if args.limit is not None:
        items = items[: args.limit]

    for term, key in items:
        target = image_dir / f"{key}.png"
        create_card_image(term, target)
        index[term] = target.name

    manifest_path = image_dir / "word_map.json"
    manifest_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(items)} images in {image_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
