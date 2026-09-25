from pathlib import Path

from md_flashcards import (
    filter_entries,
    find_image_for_term,
    generate_ascii_word_art,
    get_emoji_visual_for_term,
    load_entries,
    open_image_file,
    parse_vocab_rows,
    prompt_for_vocab,
    run_quiz,
)


def test_find_image_for_term_matches_accented_phrase(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_file = image_dir / "que_idiomas_hablas.png"
    image_file.write_bytes(b"fake")

    found = find_image_for_term("¿Qué idiomas hablas?", image_dir)
    assert found == image_file


def test_prompt_for_vocab_shows_word_and_success_message(monkeypatch, capsys):
    captured = {}

    def fake_input(prompt):
        captured["prompt"] = prompt
        return "hello"

    monkeypatch.setattr("builtins.input", fake_input)

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item)

    captured_output = capsys.readouterr().out
    assert result is True
    assert captured["prompt"] == "hola -> English: "
    assert "✅ Correct! Great job!" in captured_output


def test_prompt_for_vocab_shows_correct_answer_when_wrong(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "goodbye")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item)

    captured_output = capsys.readouterr().out
    assert result is False
    assert "❌ Incorrect. The correct answer was: hello" in captured_output


def test_load_entries_includes_vocab_and_conjugations():
    entries = load_entries([
        "spanish_vocabulary.md",
        "spanish_verb_conjugations.md",
    ])

    assert any(item["type"] == "vocab" and item["es"] == "hola" and item["en"] == "hello" for item in entries)
    assert any(
        item["type"] == "verb"
        and item["verb"] == "ser"
        and item["person"] == "yo"
        and item["form"] == "soy"
        for item in entries
    )


def test_chapter_filter_keeps_unit_1_vocab_only():
    entries = load_entries(["spanish_vocabulary.md"])
    unit_1_entries = filter_entries(entries, chapter="Unidad 1", include_vocab=True, include_verbs=False)

    assert unit_1_entries
    assert all(item["chapter"] == "Unidad 1" for item in unit_1_entries)
    assert any(item["es"] == "hola" for item in unit_1_entries)
    assert not any(item["es"] == "la clase" for item in unit_1_entries)


def test_chapter_filter_handles_verb_chapter_name():
    entries = load_entries(["spanish_verb_conjugations.md"])
    verbs = filter_entries(entries, chapter="Verb tables", include_vocab=False, include_verbs=True)

    assert verbs
    assert all(item["chapter"] == "Verb tables" for item in verbs)
    assert any(item["verb"] == "ser" and item["person"] == "yo" and item["form"] == "soy" for item in verbs)


def test_load_entries_includes_otherwords_list():
    entries = load_entries(["otherwords.md"])

    assert any(item["type"] == "vocab" and item["es"] == "apellido" and item["en"] == "last name" for item in entries)
    assert any(item["type"] == "vocab" and item["es"] == "aquí" and item["en"] == "here" for item in entries)


def test_open_image_file_skips_linux_desktop_launch(monkeypatch, tmp_path):
    image_file = tmp_path / "test_linux_skip.png"
    image_file.write_bytes(b"fake")

    monkeypatch.setattr("md_flashcards.sys.platform", "linux")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Linux should not launch a desktop viewer")

    monkeypatch.setattr("md_flashcards.subprocess.run", fail_if_called)

    assert open_image_file(image_file) is False


def test_generate_ascii_word_art_contains_dog_shape():
    art = generate_ascii_word_art("perro")
    assert "🐶" in art
    assert "PERRO" not in art.upper()


def test_generate_ascii_word_art_for_generic_word_has_framed_graphic():
    art = generate_ascii_word_art("nube")
    assert "☁️" in art or "☁" in art
    assert "NUBE" not in art.upper()


def test_run_quiz_emoji_display_only_uses_emoji_words(monkeypatch):
    entries = [
        {"type": "vocab", "chapter": "Unidad 1", "es": "hola", "en": "hello", "pl": ""},
        {"type": "vocab", "chapter": "Unidad 1", "es": "perro", "en": "dog", "pl": ""},
        {"type": "vocab", "chapter": "Unidad 1", "es": "nube", "en": "cloud", "pl": ""},
        {"type": "vocab", "chapter": "Unidad 1", "es": "el estuche", "en": "pencil case", "pl": ""},
    ]

    calls = []

    def fake_prompt(item, **kwargs):
        calls.append(item["es"])
        return True

    monkeypatch.setattr("md_flashcards.prompt_for_vocab", fake_prompt)
    monkeypatch.setattr("md_flashcards.random.shuffle", lambda items: None)

    run_quiz(entries, chapter="Unidad 1", include_vocab=True, include_verbs=False, display="emoji", image_dir=Path("images"))

    assert calls == ["hola", "perro", "nube"]


def test_run_quiz_picture_display_only_uses_words_with_image_files(monkeypatch, tmp_path):
    (tmp_path / "la_mochila.jpg").write_bytes(b"fake")
    entries = [
        {"type": "vocab", "chapter": "Unidad 1", "es": "la mochila", "en": "backpack", "pl": ""},
        {"type": "vocab", "chapter": "Unidad 1", "es": "el estuche", "en": "pencil case", "pl": ""},
    ]

    calls = []

    def fake_prompt(item, **kwargs):
        calls.append(item["es"])
        return True

    monkeypatch.setattr("md_flashcards.prompt_for_vocab", fake_prompt)
    monkeypatch.setattr("md_flashcards.random.shuffle", lambda items: None)

    run_quiz(entries, chapter="Unidad 1", include_vocab=True, include_verbs=False, display="picture", image_dir=tmp_path)

    assert calls == ["la mochila"]


def test_parse_vocab_rows_merges_wrapped_phrase_lines(tmp_path):
    file_path = tmp_path / "wrapped.md"
    file_path.write_text(
        "## Unidad 1\n\n"
        "  el camarero / la        waiter / waitress       kelner / kelnerka\n"
        "  camarera\n",
        encoding="utf-8",
    )

    entries = parse_vocab_rows(file_path)

    assert entries == [{
        "type": "vocab",
        "chapter": "Unidad 1",
        "es": "el camarero / la camarera",
        "en": "waiter / waitress",
        "pl": "kelner / kelnerka",
    }]


def test_get_emoji_visual_for_term_uses_exact_mapping_for_llamarse():
    assert get_emoji_visual_for_term("llamarse") == "🗣️"
    assert get_emoji_visual_for_term("hablar") == "💬"


def test_prompt_for_vocab_ascii_display_shows_ascii_preview(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.png"))
    monkeypatch.setattr("md_flashcards.open_image_file", lambda *args, **kwargs: False)
    monkeypatch.setattr("md_flashcards.sys.platform", "linux")
    monkeypatch.setattr("md_flashcards.display_image_in_terminal", lambda *args, **kwargs: print("ASCII preview shown"))
    monkeypatch.setattr("builtins.input", lambda prompt: "hola")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item, display="ascii", image_dir=Path("images"))

    captured_output = capsys.readouterr().out
    assert result is True
    assert "ASCII preview shown" in captured_output
    assert "✅ Correct! Great job!" in captured_output


def test_prompt_for_vocab_shows_image_and_accepts_answer(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.png"))
    monkeypatch.setattr("md_flashcards.display_color_image_in_terminal", lambda *args, **kwargs: print("colour preview shown"))
    monkeypatch.setattr("builtins.input", lambda prompt: "hola")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item, display="picture", image_dir=Path("images"))

    captured_output = capsys.readouterr().out
    assert result is True
    assert "colour preview shown" in captured_output
    assert "hola" not in captured_output.lower().split("type the spanish word shown in the image")[-1]
    assert "✅ Correct! Great job!" in captured_output


def test_prompt_for_vocab_shows_image_when_answer_is_wrong(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.png"))
    monkeypatch.setattr("md_flashcards.display_color_image_in_terminal", lambda *args, **kwargs: print("colour preview shown"))
    monkeypatch.setattr("builtins.input", lambda prompt: "adios")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item, display="picture", image_dir=Path("images"))

    captured_output = capsys.readouterr().out
    assert result is False
    assert "❌ Incorrect. The correct answer was: hola (English: hello)" in captured_output


def test_prompt_for_vocab_emoji_display_shows_emoji(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "hablar")

    item = {"es": "hablar", "en": "to speak", "pl": ""}
    result = prompt_for_vocab(item, display="emoji")

    captured_output = capsys.readouterr().out
    assert result is True
    assert captured_output.index("English: to speak") < captured_output.index("💬")


def test_display_color_image_in_terminal_prints_truecolor_blocks(tmp_path, capsys):
    from PIL import Image

    from md_flashcards import display_color_image_in_terminal

    image_file = tmp_path / "red.png"
    Image.new("RGB", (4, 4), (255, 0, 0)).save(image_file)

    display_color_image_in_terminal(image_file, max_width=4)

    captured_output = capsys.readouterr().out
    assert "\x1b[38;2;255;0;0m" in captured_output
    assert captured_output.count("▀") == 8


def test_answers_match_ignores_spanish_punctuation_only_when_enabled():
    from md_flashcards import answers_match

    assert answers_match("qué tal", "¿Qué tal?", ignore_punctuation=True)
    assert answers_match("la cuenta por favor", "La cuenta, por favor.", ignore_punctuation=True)
    assert not answers_match("qué tal", "¿Qué tal?")
    assert not answers_match("que tal", "¿Qué tal?", ignore_punctuation=True)


def test_prompt_for_vocab_accepts_answer_without_punctuation(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "qué tal")

    item = {"es": "¿Qué tal?", "en": "How are things?", "pl": ""}
    result = prompt_for_vocab(item, display="emoji", ignore_punctuation=True)

    assert result is True


def test_prompt_for_vocab_window_display_opens_viewer(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.jpg"))
    monkeypatch.setattr("md_flashcards.open_image_window", lambda path: opened.append(path) or True)
    monkeypatch.setattr("builtins.input", lambda prompt: "hola")

    item = {"es": "hola", "en": "hello", "pl": ""}
    result = prompt_for_vocab(item, display="window", image_dir=Path("images"))

    assert result is True
    assert opened == [Path("images/hola.jpg")]


def test_prompt_for_vocab_window_display_falls_back_to_terminal(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.jpg"))
    monkeypatch.setattr("md_flashcards.open_image_window", lambda path: False)
    monkeypatch.setattr("md_flashcards.display_color_image_in_terminal", lambda *args, **kwargs: print("colour preview shown"))
    monkeypatch.setattr("builtins.input", lambda prompt: "hola")

    prompt_for_vocab({"es": "hola", "en": "hello", "pl": ""}, display="window", image_dir=Path("images"))

    assert "colour preview shown" in capsys.readouterr().out


def test_gui_environment_restores_original_vars_and_drops_snap_paths(monkeypatch):
    from md_flashcards import gui_environment

    monkeypatch.setenv("XDG_DATA_DIRS", "/snap/code/1/usr/share:/usr/share")
    monkeypatch.setenv("XDG_DATA_DIRS_VSCODE_SNAP_ORIG", "/usr/share")
    monkeypatch.setenv("GTK_PATH", "/snap/code/1/usr/lib/gtk-3.0")
    monkeypatch.setenv("SNAP", "/snap/code/1")

    env = gui_environment()

    assert env["XDG_DATA_DIRS"] == "/usr/share"
    assert "GTK_PATH" not in env
    assert "SNAP" not in env


def test_open_image_window_launches_browser_once_and_updates_card(monkeypatch, tmp_path):
    import md_flashcards

    launches = []
    monkeypatch.setattr(md_flashcards, "VIEWER_DIR", tmp_path / "viewer")
    monkeypatch.setattr(md_flashcards, "launch_in_desktop", lambda page: launches.append(page) or True)
    monkeypatch.setattr(md_flashcards, "_viewer_opened", False)
    first = tmp_path / "hola.jpg"
    second = tmp_path / "adios.jpg"
    first.write_bytes(b"fake")
    second.write_bytes(b"fake")

    assert md_flashcards.open_image_window(first) is True
    assert md_flashcards.open_image_window(second) is True

    card_js = (tmp_path / "viewer" / "card.js").read_text(encoding="utf-8")
    assert launches == [tmp_path / "viewer" / "index.html"]
    assert second.resolve().as_uri() in card_js

    md_flashcards.close_image_window()
    assert (tmp_path / "viewer" / "card.js").read_text(encoding="utf-8") == "showCard(null);\n"


def test_get_emoji_visual_for_term_ignores_articles_but_prefers_exact_match():
    assert get_emoji_visual_for_term("la mesa") == get_emoji_visual_for_term("mesa")
    assert get_emoji_visual_for_term("los zapatos") == "👞"
    assert get_emoji_visual_for_term("la naranja") == "🍊"
    assert get_emoji_visual_for_term("naranja") == "🟠"
    assert "ADI" not in (get_emoji_visual_for_term("adiós") or "")


def test_run_memorize_loops_through_cards_with_english(monkeypatch, capsys):
    from md_flashcards import run_memorize

    entries = [
        {"type": "vocab", "chapter": "Unidad 1", "es": "hola", "en": "hello", "pl": "cześć"},
        {"type": "vocab", "chapter": "Unidad 1", "es": "nube", "en": "cloud", "pl": ""},
        {"type": "verb", "chapter": "Unidad 1", "verb": "ser", "person": "yo", "form": "soy"},
    ]
    monkeypatch.setattr("md_flashcards.time.sleep", lambda seconds: None)
    monkeypatch.setattr("md_flashcards.random.shuffle", lambda items: None)

    shown = run_memorize(entries, chapter="Unidad 1", display="emoji", delay=0, rounds=2)

    output = capsys.readouterr().out
    assert shown == 4
    assert "English: hello" in output
    assert "Polski: cześć" in output
    assert "👋" in output
    assert "Round 2" in output
    assert "soy" not in output


def test_run_memorize_stops_cleanly_on_ctrl_c(monkeypatch, capsys):
    from md_flashcards import run_memorize

    def interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("md_flashcards.time.sleep", interrupt)
    entries = [{"type": "vocab", "chapter": "Unidad 1", "es": "hola", "en": "hello", "pl": ""}]

    shown = run_memorize(entries, display="text", delay=1)

    assert shown == 1
    assert "Shown 1 cards." in capsys.readouterr().out


def test_answers_match_ignores_accents_only_when_enabled():
    from md_flashcards import answers_match

    assert answers_match("adios", "adiós", ignore_accents=True)
    assert answers_match("hasta manana", "hasta mañana", ignore_accents=True)
    assert not answers_match("adios", "adiós")
    assert answers_match("que tal", "¿Qué tal?", ignore_punctuation=True, ignore_accents=True)


def test_parse_other_words_rows_reads_optional_polish_column(tmp_path):
    from md_flashcards import parse_other_words_rows

    file_path = tmp_path / "otherwords.md"
    file_path.write_text(
        "Más palabras:\n"
        "el gato — cat — kot\n"
        "pared — wall\n",
        encoding="utf-8",
    )

    entries = parse_other_words_rows(file_path)

    assert entries == [
        {"type": "vocab", "chapter": "Más palabras", "es": "el gato", "en": "cat", "pl": "kot"},
        {"type": "vocab", "chapter": "Más palabras", "es": "pared", "en": "wall", "pl": ""},
    ]
