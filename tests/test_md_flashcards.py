from pathlib import Path

from md_flashcards import filter_entries, find_image_for_term, load_entries, open_image_file, prompt_for_vocab


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


def test_open_image_file_handles_viewer_failure_gracefully(monkeypatch, tmp_path):
    image_file = tmp_path / "test_viewer_failure.png"
    image_file.write_bytes(b"fake")

    def fake_run(*args, **kwargs):
        return type("Completed", (), {"returncode": 1})()

    monkeypatch.setattr("md_flashcards.subprocess.run", fake_run)

    assert open_image_file(image_file) is False


def test_prompt_for_vocab_shows_image_and_accepts_answer(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.png"))
    monkeypatch.setattr("md_flashcards.open_image_file", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "hola")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item, image_dir=Path("images"))

    captured_output = capsys.readouterr().out
    assert result is True
    assert "🖼️ Showing image for: hola" in captured_output
    assert "✅ Correct! Great job!" in captured_output


def test_prompt_for_vocab_shows_image_when_answer_is_wrong(monkeypatch, capsys):
    monkeypatch.setattr("md_flashcards.find_image_for_term", lambda *args, **kwargs: Path("images/hola.png"))
    monkeypatch.setattr("md_flashcards.open_image_file", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "adios")

    item = {"es": "hola", "en": "hello", "pl": "cześć"}
    result = prompt_for_vocab(item, image_dir=Path("images"))

    captured_output = capsys.readouterr().out
    assert result is False
    assert "🖼️ Showing image for: hola" in captured_output
    assert "❌ Incorrect. The correct answer was: hola" in captured_output
