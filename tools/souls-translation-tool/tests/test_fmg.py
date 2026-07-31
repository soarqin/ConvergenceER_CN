from pathlib import Path

import pytest

from souls_translation_tool.fmg import FmgDocument, dump_fmg_text, load_fmg_text

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HOST_FMG_FIXTURES = (REPOSITORY_ROOT / "mod/engUS/item_dlc02/WeaponName.fmg").is_file()


def test_fmg_roundtrip_preserves_null_empty_and_error_text(tmp_path: Path) -> None:
    original = FmgDocument(
        entries={
            10: None,
            11: "",
            12: "[ERROR]",
            20: "Line one\nLine two",
            21: 'Quoted "text" and \\ slash',
        },
        version=2,
        unicode=True,
    )

    packed = original.to_bytes()
    restored = FmgDocument.from_bytes(packed)

    assert restored.entries == original.entries
    assert restored.entries[10] is None
    assert restored.entries[11] == ""
    assert restored.entries[12] == "[ERROR]"


def test_fmg_text_roundtrip_preserves_null_state(tmp_path: Path) -> None:
    original = FmgDocument(entries={1: None, 2: "", 3: "text"})
    text_path = tmp_path / "sample.fmg.txt"

    dump_fmg_text(original, text_path)
    restored = load_fmg_text(text_path)

    assert restored.entries == original.entries
    assert "%null%" in text_path.read_text(encoding="utf-8")


@pytest.mark.skipif(not HOST_FMG_FIXTURES, reason="Host project FMG fixtures are unavailable")
def test_fmg_reader_accepts_identical_duplicate_ids() -> None:
    source = FmgDocument.read(REPOSITORY_ROOT / "mod/engUS/item_dlc02/WeaponName.fmg")

    assert source.entries[7090000] == "Zephyr Blades"


@pytest.mark.parametrize(
    "relative_path",
    [
        "origin/engUS/item_dlc02/WeaponName.fmg",
        "mod/zhoCN/item_dlc02/GoodsCaption.fmg",
    ],
)
@pytest.mark.skipif(not HOST_FMG_FIXTURES, reason="Host project FMG fixtures are unavailable")
def test_repository_fmg_roundtrip(relative_path: str) -> None:
    document = FmgDocument.read(REPOSITORY_ROOT / relative_path)
    restored = FmgDocument.from_bytes(document.to_bytes())

    assert restored.entries == document.entries
    assert restored.version == document.version
    assert restored.big_endian == document.big_endian
    assert restored.unicode == document.unicode
