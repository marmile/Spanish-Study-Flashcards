#!/usr/bin/env python3
import argparse
import random
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


VOCAB_FILE_NAMES = {"spanish_vocabulary.md"}
VERB_FILE_NAMES = {"spanish_verb_conjugations.md"}
OTHER_WORDS_FILE_NAMES = {"otherwords.md"}
CHAPTER_PREFIXES = {"## Unidad ", "### "}


def normalize_text(value: str) -> str:
    value = value.replace("**", "").replace("_", "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_chapter_name(value: str) -> str:
    cleaned = normalize_text(value)
    if " --- " in cleaned:
        cleaned = cleaned.split(" --- ", 1)[0]
    return cleaned


def get_chapter_name(raw_line: str, file_name: str):
    line = raw_line.strip()
    if line.startswith("## "):
        return normalize_chapter_name(line[3:])
    if line.startswith("### "):
        return normalize_chapter_name(line[4:])
    if file_name == "spanish_verb_conjugations.md":
        return "Verb tables"
    return "General"


def parse_vocab_rows(file_path: Path):
    entries = []
    current_chapter = "General"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            current_chapter = normalize_chapter_name(stripped[3:])
            continue
        if stripped.startswith("### "):
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("-") or "---" in stripped:
            continue
        if stripped.startswith("Español") or stripped.startswith("English") or stripped.startswith("Polski"):
            continue

        cells = re.split(r"\s{2,}", stripped)
        if len(cells) < 2:
            continue

        cells = [normalize_text(cell) for cell in cells if cell.strip()]
        if len(cells) < 2 or cells[0].lower() in {"español", "english", "polski"}:
            continue

        if len(cells) >= 3:
            es, en, pl = cells[0], cells[1], cells[2]
            entries.append({
                "type": "vocab",
                "chapter": current_chapter,
                "es": es,
                "en": en,
                "pl": pl,
            })
        else:
            es, en = cells[0], cells[1]
            entries.append({
                "type": "vocab",
                "chapter": current_chapter,
                "es": es,
                "en": en,
                "pl": "",
            })
    return entries


def parse_verb_rows(file_path: Path):
    entries = []
    current_verb = None
    current_chapter = "Verb tables"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("## "):
            current_chapter = normalize_chapter_name(stripped[3:])
            continue

        if stripped.startswith("### "):
            current_verb = normalize_text(stripped[4:])
            continue

        if stripped.startswith("Person") or stripped.startswith("Español"):
            continue

        if "-----" in stripped or "---" in stripped:
            continue

        person_match = re.match(
            r"^(yo|tú|él / ella / usted|nosotros/as|vosotros/as|ellos / ellas / ustedes)\s{2,}\*\*(.+?)\*\*$",
            stripped,
        )
        if not person_match or current_verb is None:
            continue

        person = person_match.group(1)
        form = normalize_text(person_match.group(2))
        entries.append({
            "type": "verb",
            "chapter": current_chapter,
            "verb": current_verb,
            "person": person,
            "form": form,
        })

    return entries


def parse_other_words_rows(file_path: Path):
    entries = []
    current_chapter = "General"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.endswith(":"):
            current_chapter = normalize_chapter_name(stripped[:-1])
            continue

        if stripped.startswith("Lista para estudiar"):
            continue

        if "—" not in stripped and " - " not in stripped:
            if stripped.startswith("Verbos para practicar"):
                current_chapter = normalize_chapter_name(stripped[:-1])
            continue

        separator = "—" if "—" in stripped else " - "
        left, right = stripped.split(separator, 1)
        es = normalize_text(left)
        en = normalize_text(right)
        if not es or not en:
            continue

        entries.append({
            "type": "vocab",
            "chapter": current_chapter,
            "es": es,
            "en": en,
            "pl": "",
        })

    return entries


def load_entries(file_names):
    entries = []
    for name in file_names:
        file_path = Path(name)
        if not file_path.exists():
            continue

        if file_path.name in VERB_FILE_NAMES:
            entries.extend(parse_verb_rows(file_path))
        elif file_path.name in VOCAB_FILE_NAMES:
            entries.extend(parse_vocab_rows(file_path))
        elif file_path.name in OTHER_WORDS_FILE_NAMES:
            entries.extend(parse_other_words_rows(file_path))
    return entries


def filter_entries(entries, chapter=None, include_vocab=True, include_verbs=True):
    filtered = []
    for item in entries:
        if chapter is not None and item.get("chapter") != chapter:
            continue
        if item["type"] == "vocab" and include_vocab:
            filtered.append(item)
        elif item["type"] == "verb" and include_verbs:
            filtered.append(item)
    return filtered


def list_chapters(entries):
    chapters = []
    seen = set()
    for item in entries:
        chapter = item.get("chapter")
        if chapter and chapter not in seen:
            chapters.append(chapter)
            seen.add(chapter)
    return chapters


def find_image_for_term(term: str, image_dir=None):
    if image_dir is None:
        image_dir = Path(__file__).resolve().parent / "images"
    if not isinstance(image_dir, Path):
        image_dir = Path(image_dir)

    cleaned = normalize_text(term).lower()
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")

    candidates = []
    if cleaned:
        candidates.extend([
            image_dir / f"{cleaned}.png",
            image_dir / f"{cleaned}.jpg",
            image_dir / f"{cleaned}.jpeg",
            image_dir / f"{cleaned}.gif",
            image_dir / f"{cleaned}.webp",
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def open_image_file(path):
    if not path:
        return False
    file_path = Path(path)
    if not file_path.exists():
        return False

    try:
        if sys.platform.startswith("darwin"):
            completed = subprocess.run(["open", str(file_path)], check=False)
        elif sys.platform.startswith("win"):
            completed = subprocess.run(["cmd", "/c", "start", "", str(file_path)], check=False)
        else:
            completed = subprocess.run(["xdg-open", str(file_path)], check=False)
    except OSError:
        return False

    return completed.returncode == 0


def prompt_for_vocab(item, image_dir=None):
    if image_dir is not None:
        word = item.get("es", "")
        print(f"\n🖼️ Showing image for: {word}")
        image_path = find_image_for_term(word, image_dir)
        if image_path is not None:
            open_image_file(image_path)
        else:
            print("(No matching image found in the images folder; showing text fallback.)")

        answer = input("Type the Spanish word shown in the image: ").strip().lower()
        expected = word.lower()
        if answer == expected:
            print("✅ Correct! Great job!")
            return True
        print(f"❌ Incorrect. The correct answer was: {word}")
        return False

    if item.get("en"):
        label = "English"
        expected = item["en"]
    elif item.get("pl"):
        label = "Polski"
        expected = item["pl"]
    else:
        return False

    print(f"\nCard: {item['es']}")
    answer = input(f"{item['es']} -> {label}: ").strip().lower()
    expected_text = expected.lower()
    if answer == expected_text:
        print("✅ Correct! Great job!")
        return True

    print(f"❌ Incorrect. The correct answer was: {expected}")
    return False


def prompt_for_verb(item):
    print(f"\nCard: {item['verb']} ({item['person']})")
    answer = input(f"{item['verb']} ({item['person']}) -> ").strip().lower()
    expected = item["form"].lower()
    if answer == expected:
        print("✅ Correct! Great job!")
        return True
    print(f"❌ Incorrect. The correct answer was: {item['form']}")
    return False


def run_learn(entries, chapter=None, include_vocab=True, include_verbs=True):
    filtered = filter_entries(entries, chapter=chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    if not filtered:
        raise SystemExit("No entries available for this chapter and mode.")

    for item in filtered:
        print(f"\n{item['chapter']}")
        if item["type"] == "vocab":
            print(f"Spanish: {item['es']}")
            print(f"English: {item['en']}")
            print(f"Polski: {item['pl']}")
        else:
            print(f"Verb: {item['verb']}")
            print(f"Person: {item['person']}")
            print(f"Form: {item['form']}")
        input("Press Enter to continue... ")


def run_quiz(entries, chapter=None, limit=None, include_vocab=True, include_verbs=True, image_mode=False, image_dir=None):
    filtered = filter_entries(entries, chapter=chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    if not filtered:
        raise SystemExit("No matching entries for the selected chapter and mode.")

    if limit is not None:
        filtered = filtered[:limit]

    random.shuffle(filtered)
    score = 0
    total = 0

    for item in filtered:
        total += 1
        if item["type"] == "vocab":
            score += int(prompt_for_vocab(item, image_dir=image_dir if image_mode else None))
        else:
            score += int(prompt_for_verb(item))

    print(f"\nFinal score: {score}/{total} ({(score / total * 100) if total else 0:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="Quiz yourself on Spanish vocab and verb conjugations from markdown study files.")
    parser.add_argument("files", nargs="*", default=["spanish_vocabulary.md", "spanish_verb_conjugations.md"], help="Markdown files to study from.")
    parser.add_argument("--chapter", help="Study only one chapter: for example 'Unidad 1' or 'Verb tables'.")
    parser.add_argument("--limit", type=int, help="Number of cards to quiz on.")
    parser.add_argument("--mode", choices=["all", "vocab", "verbs"], default="all", help="Which study set to use.")
    parser.add_argument("--learn", action="store_true", help="Show answers directly instead of testing yourself.")
    parser.add_argument("--image-mode", action="store_true", help="Show an image for each vocab card and type the Spanish word.")
    parser.add_argument("--image-dir", default="images", help="Folder containing matching image files for vocab cards.")
    parser.add_argument("--list-chapters", action="store_true", help="Print the available chapter names and exit.")
    args = parser.parse_args()

    entries = load_entries(args.files)
    if args.list_chapters:
        for chapter in list_chapters(entries):
            print(chapter)
        raise SystemExit(0)

    include_vocab = args.mode in {"all", "vocab"}
    include_verbs = args.mode in {"all", "verbs"}

    if args.learn:
        run_learn(entries, chapter=args.chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    else:
        run_quiz(
            entries,
            chapter=args.chapter,
            limit=args.limit,
            include_vocab=include_vocab,
            include_verbs=include_verbs,
            image_mode=args.image_mode,
            image_dir=Path(args.image_dir),
        )


if __name__ == "__main__":
    main()
