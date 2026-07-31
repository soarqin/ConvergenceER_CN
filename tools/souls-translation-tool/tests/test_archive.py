from pathlib import Path

import pytest

from souls_translation_tool.archive import pack_dcx, unpack_dcx

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OODLE_PATH = REPOSITORY_ROOT / "tools/lib/oo2core_6_win64.dll"
ARCHIVE_FIXTURES = all(
    (REPOSITORY_ROOT / "stage" / f"{name}.msgbnd.dcx").is_file()
    for name in ("item_dlc02", "menu_dlc02")
)


@pytest.mark.skipif(
    not OODLE_PATH.is_file() or not ARCHIVE_FIXTURES,
    reason="Host project archive fixtures are unavailable",
)
@pytest.mark.parametrize("archive_name", ["item_dlc02", "menu_dlc02"])
def test_repository_dcx_roundtrip(tmp_path: Path, archive_name: str) -> None:
    from soulstruct.containers import Binder
    from soulstruct.dcx import oodle

    source_path = REPOSITORY_ROOT / "stage" / f"{archive_name}.msgbnd.dcx"
    unpacked = tmp_path / "unpacked"
    output = tmp_path / f"{archive_name}.msgbnd.dcx"
    oodle_path = OODLE_PATH

    unpack_dcx(source_path, unpacked, oodle_path)
    pack_dcx(unpacked, output, oodle_path)

    oodle.LOAD_DLL(str(oodle_path))
    source = Binder.from_path(source_path)
    restored = Binder.from_path(output)
    assert source.dcx_type == restored.dcx_type
    assert [
        (entry.entry_id, entry.flags, entry.path, entry.data) for entry in source.entries
    ] == [
        (entry.entry_id, entry.flags, entry.path, entry.data) for entry in restored.entries
    ]
