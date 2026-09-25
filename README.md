# Spanish Study Tool

A terminal flashcard tool for studying Spanish (A1) vocabulary and verb conjugations from the markdown files in this folder. Words can be shown as text, emoji, ASCII art or real photos, with English and Polish meanings.

**Design idea:** keep it simple and stay in the terminal as long as possible. The word lists are plain markdown files, the tool is a single Python script with Pillow as its only dependency, and even photos are drawn in the terminal (`--display picture`). Opening a browser tab (`--display window`) is an optional extra, not a requirement.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install pillow pytest

python md_flashcards.py --list-chapters                              # see the chapters
python md_flashcards.py --chapter "Unidad 1" --memorize              # memorize: picture slideshow
python md_flashcards.py --chapter "Unidad 1" --display picture       # quiz: see the photo, type the Spanish word
```

## Three ways to study

| Mode | Command | What happens |
|---|---|---|
| Learn | `--learn` | Shows each card with its answer; press Enter for the next one |
| Memorize | `--memorize` | Slideshow loop: picture, Spanish word, English and Polish meaning; moves on by itself until Ctrl+C |
| Quiz | *(default)* | Shows a card and you type the answer; score at the end |

### Learn

```bash
python md_flashcards.py --chapter "Unidad 1" --learn
```

### Memorize (slideshow)

```bash
python md_flashcards.py --chapter "Unidad 1" --memorize
python md_flashcards.py --chapter "Unidad 1" --memorize --delay 6 --display window
```

- Each card shows the picture, then the Spanish word with its English (and Polish) meaning. No typing.
- The order is shuffled every round, and it keeps looping until you press Ctrl+C.
- `--delay` sets the seconds per card (default 4).
- Uses `--display picture` by default; any other display mode works too (`emoji`, `ascii`, `window`, or `text` for words only).
- Only vocabulary is used, not verb conjugations.

### Quiz

```bash
python md_flashcards.py --chapter "Unidad 1" --mode vocab                  # Spanish word -> type English
python md_flashcards.py --chapter "Unidad 1" --display picture             # photo -> type Spanish
python md_flashcards.py --chapter "Unidad 1" --display emoji --ignore-punctuation --ignore-accents   # 'que tal' = '¿Qué tal?'
python md_flashcards.py --chapter "Verb tables" --mode verbs               # conjugations
python md_flashcards.py --chapter "Unidad 2" --limit 20                    # only 20 cards
```

### Typing without Spanish characters

If your keyboard has no Spanish characters, the quiz can ignore them when checking answers:

| Option | Ignores | Example accepted answer |
|---|---|---|
| `--ignore-accents` | á é í ó ú ü ñ | `adios` for `adiós`, `manana` for `mañana` |
| `--ignore-punctuation` | ¿ ? ¡ ! . , ; : … | `qué tal` for `¿Qué tal?` |
| both together | all of the above | `que tal` for `¿Qué tal?` |

```bash
python md_flashcards.py --chapter "Unidad 1" --display picture --ignore-accents --ignore-punctuation
```

Both options work in every quiz display mode and for verb conjugations. Without them, answers must match exactly (upper/lower case never matters).

## Display modes

Choose how vocab cards are shown with `--display`:

| `--display` | You see | You type (quiz) |
|---|---|---|
| `text` (default, except in `--memorize`) | the Spanish word | English |
| `emoji` | an emoji | Spanish |
| `ascii` | the photo as black-and-white ASCII art | Spanish |
| `picture` | the photo in colour, drawn in the terminal | Spanish |
| `window` | the photo in a browser tab that updates for each card | Spanish |

- In the picture modes (`emoji`, `ascii`, `picture`, `window`) the English meaning is shown above the picture. A wrong answer shows the Spanish word together with the English one.
- Each picture mode only uses words that have a picture: `emoji` covers about 350 of the 473 words (abstract words such as prepositions have no emoji), while `ascii`, `picture` and `window` use words with an image in `--image-dir` (default `images`).
- `picture` needs a terminal with 24-bit colour (the VS Code terminal and most Linux terminals have it).
- `window` opens `viewer/index.html` in your default browser once, at the first card. Click back into the terminal once; after that the page swaps to the next picture by itself, so the terminal keeps keyboard focus. Tip: put the browser and terminal side by side. If the browser cannot be started, the photo is drawn in the terminal instead.
- `--image-mode` is kept as a shortcut for `--display picture`.

## Options

| Option | What it does |
|---|---|
| `files ...` | Markdown files to study (default: `spanish_vocabulary.md spanish_verb_conjugations.md otherwords.md`) |
| `--chapter NAME` | Study only one chapter, e.g. `"Unidad 1"` or `"Verb tables"` |
| `--mode all\|vocab\|verbs` | Which cards to use (default `all`) |
| `--limit N` | Use only the first N cards of the selection |
| `--learn` | Show answers instead of testing |
| `--memorize` | Slideshow loop: picture + Spanish + English, until Ctrl+C |
| `--delay SECONDS` | Seconds per card in `--memorize` (default 4) |
| `--display MODE` | How vocab cards are shown (see above) |
| `--image-dir DIR` | Folder with the pictures (default `images`) |
| `--ignore-punctuation` | Accept answers typed without ¿ ? ¡ ! . , ; : …, e.g. `qué tal` for `¿Qué tal?` (accents still count) |
| `--ignore-accents` | Accept answers typed without accents and ñ, e.g. `adios` for `adiós`, `manana` for `mañana` |
| `--list-chapters` | Print chapter names and exit |

To study only some files, list them at the start:

```bash
python md_flashcards.py otherwords.md --chapter "Más palabras" --memorize
```

## Files

| File | What it is |
|---|---|
| `spanish_vocabulary.md` | A1 vocabulary by unit (Spanish → English → Polish) |
| `spanish_verb_conjugations.md` | Verb conjugation tables |
| `otherwords.md` | Extra word lists (chapters `Vocabulario y expresiones`, `Posición`, `Frases útiles`, `Más palabras`); one word per line: `es — en` or `es — en — pl` |
| `morewords.md` | Source list (Spanish / Polish lines); its new words were added to `otherwords.md` as the chapter `Más palabras` |
| `md_flashcards.py` | The study tool |
| `fetch_vocab_images.py` | Downloads a real photo for every vocab word into `images/` |
| `download_vocab_images.py` | Generates simple placeholder cards (used when no photo is found) |
| `images/` | One picture per word, plus `word_map.json` (word → file) and `CREDITS.json` (sources and licences) |
| `viewer/` | Created by `--display window` for the browser page; not committed |
| `tests/` | Tests (`python -m pytest`) |

## Images

The pictures in `images/` are photos from Wikipedia and Wikimedia Commons, downloaded by `fetch_vocab_images.py`. Sources, authors and licences are listed in `images/CREDITS.json`; keep that file next to the photos when sharing them, because licences such as CC BY-SA require attribution. Words with no photo found keep a generated placeholder card (`.png`).

### Status: work in progress

Replacing the old generated placeholder cards with real photos is **partly done**. Most words already have a photo, but some are still missing (for example the newest words in `Unidad 13` and `Más palabras`), and some automatically chosen photos may not fit the word well. Words without a picture are simply skipped in the picture modes; `text` and `emoji` modes are not affected.

### Contributing pictures

Better or missing pictures are very welcome. You can replace a photo that does not fit or add one for a word that has none:

1. Use only images with an **open licence** that allows reuse, e.g. CC0 / public domain, CC BY or CC BY-SA (Wikimedia Commons, Openverse, Pixabay, Unsplash, or your own photos/drawings). Do not use images from a normal web search unless the licence clearly allows it.
2. Save the picture as `images/<word>.jpg`, where `<word>` is the Spanish word in lowercase, without accents and `¿?¡!`, with spaces replaced by `_` (e.g. `la mañana` → `la_manana.jpg`, `¿Qué tal?` → `que_tal.jpg`). A width of about 500 px is enough. Delete an old `.png` placeholder with the same name, because `.png` is used first.
3. Add an entry to `images/CREDITS.json` for that file with the source, author and licence, for example:

   ```json
   "la_manana.jpg": {
     "term": "la mañana",
     "source": "https://commons.wikimedia.org/wiki/File:Example.jpg",
     "file": "File:Example.jpg",
     "author": "Author Name",
     "license": "CC BY-SA 4.0"
   }
   ```

   For your own photo, write your name as author and the licence you choose (e.g. `CC0`).

### Downloading photos automatically

Download photos for words that do not have one yet (e.g. after adding new words):

```bash
python fetch_vocab_images.py
```

- `--force` re-downloads every photo.
- Wikimedia limits how fast images can be downloaded, so a full run takes about an hour. The script waits and retries by itself and can be stopped and started again at any time: words that already have a `.jpg` are skipped.
- To fix a bad picture, add or change the search query for that word in `QUERY_OVERRIDES` in `fetch_vocab_images.py`, delete its `.jpg` and run the script again. A query starting with a capital letter is treated as a Wikipedia article title (the article's main image is used); a lowercase query is a Commons photo search.

## Running the tests

```bash
python -m pytest
```
