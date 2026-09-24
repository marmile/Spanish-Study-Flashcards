#!/usr/bin/env python3
import argparse
import random
import re
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
    if file_name == "arriba_1_spanish_verb_conjugations.md":
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


def prompt_for_vocab(item):
    target = random.choice(["en", "pl"])
    if target == "en":
        prompt = f"{item['es']} -> English: "
        answer = input(prompt).strip().lower()
        expected = item["en"].lower()
        if answer == expected.lower():
            print("✅ Correct")
            return True
        print(f"❌ Incorrect. The answer was: {item['en']}")
        return False

    prompt = f"{item['es']} -> Polski: "
    answer = input(prompt).strip().lower()
    expected = item["pl"].lower()
    if answer == expected.lower():
        print("✅ Correct")
        return True
    print(f"❌ Incorrect. The answer was: {item['pl']}")
    return False


def prompt_for_verb(item):
    prompt = f"{item['verb']} ({item['person']}) -> "
    answer = input(prompt).strip().lower()
    expected = item["form"].lower()
    if answer == expected:
        print("✅ Correct")
        return True
    print(f"❌ Incorrect. The answer was: {item['form']}")
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


def run_quiz(entries, chapter=None, limit=None, include_vocab=True, include_verbs=True):
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
            score += int(prompt_for_vocab(item))
        else:
            score += int(prompt_for_verb(item))

    print(f"\nFinal score: {score}/{total} ({(score / total * 100) if total else 0:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="Quiz yourself on Spanish vocab and verb conjugations from markdown study files.")
    parser.add_argument("files", nargs="*", default=["arriba_1_spanish_vocabulary.md", "arriba_1_spanish_verb_conjugations.md"], help="Markdown files to study from.")
    parser.add_argument("--chapter", help="Study only one chapter: for example 'Unidad 1' or 'Verb tables'.")
    parser.add_argument("--limit", type=int, help="Number of cards to quiz on.")
    parser.add_argument("--mode", choices=["all", "vocab", "verbs"], default="all", help="Which study set to use.")
    parser.add_argument("--learn", action="store_true", help="Show answers directly instead of testing yourself.")
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
        run_quiz(entries, chapter=args.chapter, limit=args.limit, include_vocab=include_vocab, include_verbs=include_verbs)


if __name__ == "__main__":
    main()
