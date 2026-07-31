from pathlib import Path

import pytest

from souls_translation_tool.fmg import FmgDocument
from souls_translation_tool.translation import (
    TranslationDocument,
    TranslationEntry,
    build_target_fmg,
    build_directory,
    compare_directories_five_way,
    compare_directories_three_way,
    generate_five_way,
    generate_three_way,
    merge_directories,
    merge_documents,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HOST_TRANSLATION_FIXTURE = REPOSITORY_ROOT / "item/AccessoryCaption.fmg.txt"


def document(entries: dict[int, str | None]) -> FmgDocument:
    return FmgDocument(entries=entries)


def test_translation_text_roundtrip_preserves_all_prefixes(tmp_path: Path) -> None:
    source = TranslationDocument(
        {
            2020: TranslationEntry(
                2020,
                {
                    "<": "game A",
                    "O": "old mod A",
                    ">": "new mod A\nsecond line",
                    "-": "game B",
                    "C": "old mod B",
                    "=": "",
                },
            )
        }
    )
    path = tmp_path / "translation.fmg.txt"

    source.write(path)
    restored = TranslationDocument.read(path)

    assert restored == source
    assert path.read_text(encoding="utf-8").splitlines() == [
        '< 2020:"game A"',
        'O 2020:"old mod A"',
        '> 2020:"new mod A\\nsecond line"',
        '- 2020:"game B"',
        'C 2020:"old mod B"',
        '= 2020:""',
    ]


@pytest.mark.skipif(not HOST_TRANSLATION_FIXTURE.is_file(), reason="Host project fixture is unavailable")
def test_parse_repository_six_prefix_sample() -> None:
    source = TranslationDocument.read(REPOSITORY_ROOT / "item/AccessoryCaption.fmg.txt")
    entry = source.entries[2020]

    assert tuple(entry.values) == ("<", "O", ">", "-", "C", "=")
    assert entry.values["O"] != entry.values[">"]
    assert entry.values["C"] != entry.values["="]


def test_golden_fixture_preserves_six_prefix_format() -> None:
    source = TranslationDocument.read(Path(__file__).parent / "fixtures/six_prefix.fmg.txt")

    assert source.entries[10].values["O"] == "old mod A"
    assert source.entries[10].values["C"] == "old mod B"
    assert source.entries[20].values["="] == ""


def test_three_way_distinguishes_null_empty_and_removed() -> None:
    game_a = document({1: "same", 2: "old", 3: "old", 4: None, 5: "old"})
    game_b = document({1: "same B", 2: "old B", 3: "old B", 4: None, 5: "old B"})
    mod_a = document({1: "same", 2: "new", 3: "", 4: "added"})

    result = generate_three_way(game_a, game_b, mod_a)

    assert set(result.document.entries) == {2, 3, 4}
    assert result.document.entries[3].values[">"] == ""
    assert "<" not in result.document.entries[4].values
    assert result.removed_ids == (5,)


def test_five_way_preserves_unchanged_existing_translation() -> None:
    game_a = document({1: "game", 2: "game 2"})
    game_b = document({1: "游戏", 2: "游戏 2"})
    previous_a = document({1: "old mod", 2: "same mod"})
    previous_b = document({1: "旧译", 2: "保留译文"})
    current_a = document({1: "new mod", 2: "same mod"})
    existing = TranslationDocument(
        {
            2: TranslationEntry(2, {"<": "game 2", ">": "same mod", "-": "游戏 2", "=": "保留译文"})
        }
    )

    result = generate_five_way(game_a, game_b, previous_a, previous_b, current_a, existing)

    assert result.document.entries[1].values == {
        "<": "game",
        "O": "old mod",
        ">": "new mod",
        "-": "游戏",
        "C": "旧译",
        "=": "",
    }
    merged = merge_documents(existing, result.document)
    assert merged.entries[2].values["="] == "保留译文"


def test_merge_preserves_reference_lines_and_promotes_old_values() -> None:
    original = TranslationDocument(
        {1: TranslationEntry(1, {"<": "game", ">": "old A", "-": "游戏", "=": "旧译"})}
    )
    update = TranslationDocument(
        {1: TranslationEntry(1, {"<": "game", ">": "new A", "-": "游戏", "=": ""})}
    )

    merged = merge_documents(original, update)

    assert merged.entries[1].values == {
        "<": "game",
        "-": "游戏",
        "O": "old A",
        ">": "new A",
        "C": "旧译",
        "=": "",
    }


def test_merge_preserves_existing_history_snapshots() -> None:
    original = TranslationDocument(
        {
            1: TranslationEntry(
                1,
                {
                    "<": "game",
                    "O": "older A",
                    ">": "old A",
                    "-": "游戏",
                    "C": "older B",
                    "=": "old B",
                },
            )
        }
    )
    update = TranslationDocument(
        {
            1: TranslationEntry(
                1,
                {
                    "<": "game",
                    "O": "update history A",
                    ">": "new A",
                    "-": "游戏",
                    "C": "update history B",
                    "=": "",
                },
            )
        }
    )

    merged = merge_documents(original, update)

    assert merged.entries[1].values["O"] == "older A"
    assert merged.entries[1].values["C"] == "older B"
    assert merged.entries[1].values[">"] == "new A"


def test_build_uses_translation_or_current_mod_fallback() -> None:
    game_a = document({1: "game", 2: "game 2", 3: "game 3", 4: "game 4"})
    game_b = document({1: "游戏", 2: "游戏 2", 3: "游戏 3", 4: "游戏 4"})
    mod_a = document({1: "mod", 2: "mod 2", 3: "game 3", 4: None})
    translations = TranslationDocument(
        {
            1: TranslationEntry(1, {">": "mod", "=": "翻译"}),
            2: TranslationEntry(2, {">": "mod 2", "=": ""}),
        }
    )

    result = build_target_fmg(game_a, game_b, mod_a, translations)

    assert result.entries[1] == "翻译"
    assert result.entries[2] == "mod 2"
    assert result.entries[3] == "游戏 3"
    assert result.entries[4] is None


def test_build_keeps_current_translation_when_reference_is_stale() -> None:
    translations = TranslationDocument({1: TranslationEntry(1, {">": "old", "=": "译文"})})

    result = build_target_fmg(document({1: "game"}), document({1: "游戏"}), document({1: "new"}), translations)

    assert result.entries[1] == "译文"


def test_error_text_is_preserved_when_mod_text_changes() -> None:
    result = generate_three_way(
        document({1: "normal"}),
        document({1: "游戏"}),
        document({1: "[ERROR]"}),
    )

    assert result.document.entries[1].values[">"] == "[ERROR]"


def test_three_way_distinguishes_every_empty_like_state() -> None:
    cases = [None, "", "[ERROR]"]
    for old_value in cases:
        for new_value in cases:
            result = generate_three_way(
                document({1: old_value}),
                document({1: "语言 B"}),
                document({1: new_value}),
            )
            if old_value == new_value or {old_value, new_value} == {"", "[ERROR]"}:
                assert not result.document.entries
                assert not result.removed_ids
            elif new_value is None:
                assert result.null_ids == (1,)
            else:
                assert result.document.entries[1].values[">"] == new_value


def test_build_distinguishes_every_empty_like_state() -> None:
    game_a = document({1: None, 2: "", 3: "[ERROR]"})
    game_b = document({1: "原文 1", 2: "原文 2", 3: "原文 3"})
    mod_a = document({1: "[ERROR]", 2: None, 3: ""})

    result = build_target_fmg(game_a, game_b, mod_a, None)

    assert result.entries[1] == "[ERROR]"
    assert result.entries[2] is None
    assert result.entries[3] == "原文 3"


def test_build_matches_fmgcarry_merge_semantics() -> None:
    game_a = document(
        {
            1: "same",
            2: "old",
            3: "",
            4: "[ERROR]",
            5: "normal",
            6: None,
            7: "text with trailing space ",
        }
    )
    game_b = document(
        {
            1: "相同",
            2: "旧译",
            3: "保留空文本译文",
            4: "保留错误译文",
            5: "普通译文",
            6: None,
            7: "保留译文",
            20: "仅语言 B 存在",
            21: " \n",
        }
    )
    mod_a = document(
        {
            1: "same",
            2: "new text \n",
            3: "[ERROR]",
            4: " \n",
            5: "[ERROR]",
            6: "",
            7: "text with trailing space",
            8: "added text \n",
        }
    )
    translations = TranslationDocument(
        {
            2: TranslationEntry(2, {"=": "人工译文 "}),
            8: TranslationEntry(8, {"=": "新增译文 "}),
            9: TranslationEntry(9, {"=": "仅翻译文本存在 \n"}),
            10: TranslationEntry(10, {"=": "[ERROR]"}),
            11: TranslationEntry(11, {"=": ""}),
        }
    )

    result = build_target_fmg(game_a, game_b, mod_a, translations)

    assert result.entries == {
        1: "相同",
        2: "人工译文 ",
        3: "保留空文本译文",
        4: "保留错误译文",
        5: "[ERROR]",
        6: "",
        7: "保留译文",
        8: "新增译文 ",
        9: "仅翻译文本存在",
        10: "[ERROR]",
        20: "仅语言 B 存在",
        21: " \n",
    }


def test_directory_build_keeps_b_only_files_and_ignores_mod_only_files(tmp_path: Path) -> None:
    game_a = tmp_path / "a"
    game_b = tmp_path / "b"
    mod_a = tmp_path / "mod"
    translation = tmp_path / "translation"
    output = tmp_path / "output"
    for directory in (game_a, game_b, mod_a):
        directory.mkdir()

    FmgDocument(entries={1: "A"}).write(game_a / "common.fmg")
    FmgDocument(entries={1: "B"}).write(game_b / "common.fmg")
    FmgDocument(entries={1: "MOD"}).write(mod_a / "common.fmg")
    FmgDocument(entries={2: "only B"}).write(game_b / "b-only.fmg")
    FmgDocument(entries={3: "only MOD"}).write(mod_a / "mod-only.fmg")

    stats = build_directory(game_a, game_b, mod_a, translation, output)

    assert stats == {"files": 2, "entries": 2, "null": 0, "empty": 0}
    assert (output / "b-only.fmg").is_file()
    assert not (output / "mod-only.fmg").exists()


def test_directory_build_copies_unchanged_fmg_bytes(tmp_path: Path) -> None:
    game_a = tmp_path / "a"
    game_b = tmp_path / "b"
    mod_a = tmp_path / "mod"
    translation = tmp_path / "translation"
    output = tmp_path / "output"
    for directory in (game_a, game_b, mod_a):
        directory.mkdir()

    FmgDocument(entries={1: "same"}).write(game_a / "sample.fmg")
    FmgDocument(entries={1: "相同", 2: " \n"}).write(game_b / "sample.fmg")
    FmgDocument(entries={1: "same"}).write(mod_a / "sample.fmg")

    build_directory(game_a, game_b, mod_a, translation, output)

    assert (output / "sample.fmg").read_bytes() == (game_b / "sample.fmg").read_bytes()


def test_directory_merge_copies_original_only_files(tmp_path: Path) -> None:
    original = tmp_path / "original"
    update = tmp_path / "update"
    output = tmp_path / "output"
    original.mkdir()
    update.mkdir()
    original_only = original / "old.fmg.txt"
    original_only.write_text('= 1:"old"\n', encoding="utf-8")
    (update / "new.fmg.txt").write_text('> 2:"new"\n= 2:""\n', encoding="utf-8")

    assert merge_directories(original, update, output) == {
        "files": 2,
        "new_files": 1,
        "merged_files": 0,
        "preserved_files": 1,
        "new_entries": 1,
        "merged_entries": 0,
    }
    assert (output / "old.fmg.txt").read_text(encoding="utf-8") == '= 1:"old"\n'
    assert (output / "new.fmg.txt").is_file()


def test_directory_comparisons_report_null_separately(tmp_path: Path) -> None:
    game_a = tmp_path / "a"
    game_b = tmp_path / "b"
    previous_a = tmp_path / "previous-a"
    previous_b = tmp_path / "previous-b"
    current_a = tmp_path / "current-a"
    existing = tmp_path / "existing"
    output = tmp_path / "output"
    for directory in (game_a, game_b, previous_a, previous_b, current_a, existing):
        directory.mkdir()

    FmgDocument(entries={1: "old", 2: "old"}).write(game_a / "sample.fmg")
    FmgDocument(entries={1: "旧", 2: "旧"}).write(game_b / "sample.fmg")
    FmgDocument(entries={1: "old", 2: "previous"}).write(previous_a / "sample.fmg")
    FmgDocument(entries={1: "old", 2: "previous"}).write(previous_b / "sample.fmg")
    FmgDocument(entries={1: None, 2: "current"}).write(current_a / "sample.fmg")
    FmgDocument(entries={1: "旧", 2: "旧"}).write(game_b / "sample.fmg")

    three = compare_directories_three_way(game_a, game_b, current_a, output / "three")
    five = compare_directories_five_way(
        game_a, game_b, previous_a, previous_b, current_a, existing, output / "five"
    )

    assert three["null"] == 1
    assert five["null"] == 1
    assert (output / "three" / "null.json").is_file()
    assert (output / "five" / "null.json").is_file()


def test_directory_generate_removes_stale_output_files(tmp_path: Path) -> None:
    game_a = tmp_path / "a"
    game_b = tmp_path / "b"
    mod_a = tmp_path / "mod"
    output = tmp_path / "output"
    for directory in (game_a, game_b, mod_a, output):
        directory.mkdir()
    FmgDocument(entries={1: "same"}).write(game_a / "sample.fmg")
    FmgDocument(entries={1: "相同"}).write(game_b / "sample.fmg")
    FmgDocument(entries={1: "same"}).write(mod_a / "sample.fmg")
    stale = output / "stale.fmg.txt"
    stale.write_text('= 1:"stale"\n', encoding="utf-8")

    compare_directories_three_way(game_a, game_b, mod_a, output)

    assert not stale.exists()


def test_merge_reports_new_and_merged_entries(tmp_path: Path) -> None:
    original = tmp_path / "original"
    update = tmp_path / "update"
    output = tmp_path / "output"
    original.mkdir()
    update.mkdir()
    (original / "sample.fmg.txt").write_text(
        '< 1:"old"\n> 1:"old mod"\n= 1:"旧译"\n',
        encoding="utf-8",
    )
    (update / "sample.fmg.txt").write_text(
        '< 1:"old"\n> 1:"new mod"\n= 1:""\n> 2:"new"\n= 2:""\n',
        encoding="utf-8",
    )

    assert merge_directories(original, update, output) == {
        "files": 1,
        "new_files": 0,
        "merged_files": 1,
        "preserved_files": 0,
        "new_entries": 1,
        "merged_entries": 1,
    }
