from md_flashcards import filter_entries, load_entries


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
