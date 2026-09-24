# Spanish Study Tool

This project helps you study Spanish vocabulary and verb conjugations from the markdown files in this folder.

## Included files

- `spanish_vocabulary.md`
- `spanish_verb_conjugations.md`
- `otherwords.md`

## Setup

Create and activate the virtual environment from the project folder:

```bash
cd /path/to/Spanish-Study-Flashcards
python3 -m venv .venv
. .venv/bin/activate
```

## Study commands

List the available chapter names:

```bash
python md_flashcards.py --list-chapters
```

Learn a chapter (shows the answer directly):

```bash
python md_flashcards.py --chapter "Unidad 1" --learn
```

Test a chapter:

```bash
python md_flashcards.py --chapter "Unidad 1" --mode vocab
```

Test with image cards and type the Spanish word:

```bash
python md_flashcards.py --chapter "Unidad 1" --mode vocab --image-mode --image-dir images
```

Test verbs only:

```bash
python md_flashcards.py --chapter "Verb tables" --mode verbs
```

Test a chapter with a limit:

```bash
python md_flashcards.py --chapter "Unidad 2" --limit 20
```

## Notes

- The tool reads from the markdown files automatically.
- You can combine the chapter filter with `--mode vocab`, `--mode verbs`, or `--mode all`.
- `otherwords.md` is included as an additional study list.
- TODO: replace the generated placeholder images in the `images/` folder with real photos or better artwork for each word.
