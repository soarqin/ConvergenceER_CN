from pathlib import Path
import shutil
import zipfile
import xml.etree.ElementTree as ET

from souls_translation_tool.ods import (
    OLD_CHINESE_HEADER,
    OLD_ENGLISH_HEADER,
    update_ods,
)


ROOT = Path(__file__).resolve().parents[3]
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
}


def _cell_text(cell: ET.Element) -> str:
    return "\n".join("".join(p.itertext()) for p in cell.findall("./text:p", NS))


def _cells(row: ET.Element) -> list[ET.Element]:
    result = []
    for cell in list(row):
        if cell.tag.rsplit("}", 1)[-1] not in ("table-cell", "covered-table-cell"):
            continue
        result.extend([cell] * int(cell.get("{%s}number-columns-repeated" % NS["table"], "1")))
        if len(result) >= 9:
            break
    return result


def test_update_ods_writes_current_translation_and_version_reference(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "ProtectorCaption.fmg.txt").write_text(
        '> 40000:"new armor text"\n= 40000:"新护甲文本"\n',
        encoding="utf-8",
    )
    output = tmp_path / "updated.ods"

    stats = update_ods(ods, translation_root, output)

    assert stats["updated"] >= 1
    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = sheet.findall("./table:table-row", NS)
    headers = [_cell_text(cell) for cell in _cells(rows[0])]
    assert headers[:7] == [
        "ID",
        "Category",
        "Type",
        "Convergence (Simplified Chinese)",
        "Convergence (English)",
        "Vanilla (English)",
        "Vanilla (Simplified Chinese)",
    ]
    assert headers[7:] == [OLD_ENGLISH_HEADER, OLD_CHINESE_HEADER]

    row = next(row for row in rows[1:] if _cell_text(_cells(row)[0]) == "40000")
    values = [_cell_text(cell) for cell in _cells(row)]
    assert values[3] == "新护甲文本"
    assert values[4] == "new armor text"
    assert values[7].startswith("An iron helmet showing rust")
    assert values[8].startswith("遍布锈痕的铁制头盔")

    conditional = root.find(".//calcext:conditional-formats", NS)
    addresses = [
        condition.get("{%s}target-range-address" % NS["calcext"])
        for condition in conditional
    ]
    assert "'Translation Data'.A2:'Translation Data'.I2" in addresses
    assert "'Translation Data'.D2:'Translation Data'.D2 'Translation Data'.F2:'Translation Data'.I2" in addresses


def test_update_ods_removes_deleted_rows_and_inserts_new_rows_in_type_order(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "ProtectorCaption.fmg.txt").write_text(
        '< 40000:"vanilla 40000"\n'
        '- 40000:"原版40000"\n'
        '> 40000:"mod 40000"\n'
        '= 40000:"模组40000"\n'
        '< 40050:"vanilla 40050"\n'
        '- 40050:"原版40050"\n'
        '> 40050:"mod 40050"\n'
        '= 40050:"模组40050"\n'
        '< 40100:"vanilla 40100"\n'
        '- 40100:"原版40100"\n'
        '> 40100:"mod 40100"\n'
        '= 40100:"模组40100"\n',
        encoding="utf-8",
    )
    output = tmp_path / "updated.ods"

    stats = update_ods(ods, translation_root, output)

    assert stats["final_rows"] == 3
    assert stats["added"] == 1
    assert stats["removed"] > 0
    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = sheet.findall("./table:table-row", NS)
    data_rows = [row for row in rows[1:] if _cell_text(_cells(row)[0]).isdigit()]
    assert [_cell_text(_cells(row)[0]) for row in data_rows] == ["40000", "40050", "40100"]
    assert all(_cell_text(_cells(row)[1]) == "Armor" for row in data_rows)
    assert all(_cell_text(_cells(row)[2]) == "Armor Description" for row in data_rows)

    new_row = data_rows[1]
    new_cells = _cells(new_row)
    assert [_cell_text(cell) for cell in new_cells[:7]] == [
        "40050",
        "Armor",
        "Armor Description",
        "模组40050",
        "mod 40050",
        "vanilla 40050",
        "原版40050",
    ]
    assert _cell_text(new_cells[7:][0]) == ""
    assert _cell_text(new_cells[8:][0]) == ""
    assert new_cells[0].get("{%s}value-type" % NS["office"]) == "float"
    assert [cell.get("{%s}style-name" % NS["table"]) for cell in new_cells[:9]] == [
        "ce7",
        "ce7",
        "ce11",
        "ce12",
        "ce13",
        "ce12",
        "ce12",
        "ce13",
        "ce12",
    ]

    conditional = root.find(".//calcext:conditional-formats", NS)
    addresses = {
        child.find("./calcext:condition", NS).get("{%s}apply-style-name" % NS["calcext"]): child.get(
            "{%s}target-range-address" % NS["calcext"]
        )
        for child in conditional
    }
    assert addresses["ConditionalStyle_1"] == "'Translation Data'.A2:'Translation Data'.I4"
    assert addresses["ConditionalStyle_2"] == "'Translation Data'.D2:'Translation Data'.D4 'Translation Data'.F2:'Translation Data'.I4"
    assert addresses["ConditionalStyle_3"] == "'Translation Data'.A2:'Translation Data'.I4"
    assert addresses["ConditionalStyle_4"] == "'Translation Data'.A2:'Translation Data'.C4"


def test_update_ods_is_idempotent_after_reordering(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "ProtectorCaption.fmg.txt").write_text(
        '> 40000:"mod 40000"\n= 40000:"模组40000"\n'
        '> 40050:"mod 40050"\n= 40050:"模组40050"\n'
        '> 40100:"mod 40100"\n= 40100:"模组40100"\n',
        encoding="utf-8",
    )
    first = tmp_path / "first.ods"
    second = tmp_path / "second.ods"

    first_stats = update_ods(ods, translation_root, first)
    second_stats = update_ods(first, translation_root, second)

    assert first_stats["added"] == 1
    assert first_stats["removed"] > 0
    assert second_stats["added"] == 0
    assert second_stats["removed"] == 0
    with zipfile.ZipFile(first) as archive:
        first_content = archive.read("content.xml")
    with zipfile.ZipFile(second) as archive:
        second_content = archive.read("content.xml")
    assert first_content == second_content


def test_update_ods_uses_existing_fmg_id_type_for_shared_fmg(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "WeaponEffect.fmg.txt").write_text(
        '> 1050:"weapon effect 1050"\n= 1050:"武器效果1050"\n'
        '> 1051:"weapon effect 1051"\n= 1051:"武器效果1051"\n'
        '> 6800:"weapon effect 6800"\n= 6800:"武器效果6800"\n'
        '> 6801:"weapon effect 6801"\n= 6801:"武器效果6801"\n',
        encoding="utf-8",
    )
    output = tmp_path / "updated.ods"

    stats = update_ods(ods, translation_root, output)

    assert stats["final_rows"] == 4
    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = [row for row in sheet.findall("./table:table-row", NS)[1:] if _cell_text(_cells(row)[0]).isdigit()]
    assert [(int(_cell_text(_cells(row)[0])), _cell_text(_cells(row)[2])) for row in rows] == [
        (1050, "Weapon Effect"),
        (1051, "Weapon Effect"),
        (6800, "Weapon Effect"),
        (6801, "Weapon Effect"),
    ]


def test_update_ods_filters_weapon_variants_and_spirit_ashes(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "WeaponName.fmg.txt").write_text(
        '> 1050000:"base weapon"\n= 1050000:"基础武器"\n'
        '> 1050001:"variant weapon"\n= 1050001:"质变武器"\n',
        encoding="utf-8",
    )
    (item / "WeaponCaption.fmg.txt").write_text(
        '> 1050000:"base description"\n= 1050000:"基础描述"\n'
        '> 1050001:"variant description"\n= 1050001:"质变描述"\n',
        encoding="utf-8",
    )
    (item / "WeaponInfo.fmg.txt").write_text(
        '> 1050000:"base summary"\n= 1050000:"基础概要"\n'
        '> 1050001:"variant summary"\n= 1050001:"质变概要"\n',
        encoding="utf-8",
    )
    (item / "WeaponEffect.fmg.txt").write_text(
        '> 1050:"effect"\n= 1050:"效果"\n',
        encoding="utf-8",
    )
    (item / "GoodsName_dlc01.fmg.txt").write_text(
        '> 2400000:"Cemetery Shade Ashes"\n= 2400000:"墓地影子的骨灰"\n'
        '> 2400001:"Cemetery Shade Ashes +1"\n= 2400001:"墓地影子的骨灰＋１"\n',
        encoding="utf-8",
    )
    (item / "GoodsInfo_dlc01.fmg.txt").write_text(
        '> 2400000:"Summons Cemetery Shade spirit"\n= 2400000:"能召唤墓地影子的灵魂"\n'
        '> 2400001:"Summons Cemetery Shade spirit"\n= 2400001:"能召唤墓地影子的灵魂"\n',
        encoding="utf-8",
    )
    (item / "GoodsInfo2_dlc01.fmg.txt").write_text(
        '> 2400000:"Cemetery Shade"\n= 2400000:"墓地影子"\n'
        '> 2400001:"Cemetery Shade"\n= 2400001:"墓地影子"\n',
        encoding="utf-8",
    )
    (item / "GoodsCaption_dlc01.fmg.txt").write_text(
        '> 2400000:"Ashen remains in which spirits yet dwell."\n= 2400000:"寄宿着灵魂的骨灰。"\n'
        '> 2400001:"Ashen remains in which spirits yet dwell."\n= 2400001:"寄宿着灵魂的骨灰。"\n',
        encoding="utf-8",
    )
    output = tmp_path / "updated.ods"

    stats = update_ods(ods, translation_root, output)

    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = [
        row
        for row in sheet.findall("./table:table-row", NS)[1:]
        if _cell_text(_cells(row)[0]).isdigit()
    ]
    keys = [
        (int(_cell_text(_cells(row)[0])), _cell_text(_cells(row)[1]), _cell_text(_cells(row)[2]))
        for row in rows
    ]
    assert (1050000, "Weapons", "Weapon Name") in keys
    assert (1050001, "Weapons", "Weapon Name") not in keys
    assert (1050001, "Weapons", "Weapon Description") not in keys
    assert (1050001, "Weapons", "Weapon Summary") not in keys
    assert (1050, "Weapons", "Weapon Effect") in keys
    assert (2400000, "Items", "Item Name [DLC]") in keys
    assert (2400001, "Items", "Item Name [DLC]") not in keys
    assert (2400001, "Items", "Item Summary [DLC]") not in keys
    assert (2400001, "Items", "Item Description [DLC]") not in keys
    assert (2400001, "Items", "Item Secondary Summary [DLC]") not in keys
    assert stats["removed"] > 0


def test_update_ods_sorts_each_item_by_semantic_type(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "GoodsName.fmg.txt").write_text(
        '> 11032:"name"\n= 11032:"名称"\n', encoding="utf-8"
    )
    (item / "GoodsInfo.fmg.txt").write_text(
        '> 11032:"summary"\n= 11032:"概要"\n', encoding="utf-8"
    )
    (item / "GoodsCaption.fmg.txt").write_text(
        '> 11032:"description"\n= 11032:"描述"\n', encoding="utf-8"
    )
    (item / "GoodsInfo2.fmg.txt").write_text(
        '> 11032:"secondary"\n= 11032:"次要概要"\n', encoding="utf-8"
    )
    output = tmp_path / "updated.ods"

    update_ods(ods, translation_root, output)

    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = [
        row
        for row in sheet.findall("./table:table-row", NS)[1:]
        if _cell_text(_cells(row)[0]).isdigit()
    ]
    item_rows = [
        _cell_text(_cells(row)[2])
        for row in rows
        if _cell_text(_cells(row)[0]) == "11032"
        and _cell_text(_cells(row)[1]) == "Items"
    ]
    assert item_rows == [
        "Item Name",
        "Item Summary",
        "Item Description",
        "Item Secondary Summary",
    ]


def test_update_ods_recognizes_ash_upgrade_group_from_name_suffix(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    item = translation_root / "item"
    item.mkdir(parents=True)
    (item / "GoodsName_dlc01.fmg.txt").write_text(
        '> 2400000:"Cemetery Shade Ashes"\n= 2400000:"墓地影子的骨灰"\n'
        '> 2400001:"Cemetery Shade Ashes +1"\n= 2400001:"墓地影子的骨灰＋１"\n',
        encoding="utf-8",
    )
    (item / "GoodsInfo_dlc01.fmg.txt").write_text(
        '> 2400000:"base summary"\n= 2400000:"基础概要"\n'
        '> 2400001:"upgraded summary"\n= 2400001:"强化概要"\n',
        encoding="utf-8",
    )
    output = tmp_path / "updated.ods"

    update_ods(ods, translation_root, output)

    with zipfile.ZipFile(output) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.get("{%s}name" % NS["table"]) == "Translation Data"
    )
    rows = [
        row
        for row in sheet.findall("./table:table-row", NS)[1:]
        if _cell_text(_cells(row)[0]).isdigit()
    ]
    keys = [
        (int(_cell_text(_cells(row)[0])), _cell_text(_cells(row)[2]))
        for row in rows
        if _cell_text(_cells(row)[1]) == "Items" and _cell_text(_cells(row)[0]) in {"2400000", "2400001"}
    ]
    assert (2400000, "Item Name [DLC]") in keys
    assert (2400000, "Item Summary [DLC]") in keys
    assert (2400001, "Item Name [DLC]") not in keys
    assert (2400001, "Item Summary [DLC]") not in keys


def test_update_ods_is_idempotent_when_new_type_precedes_existing_type(tmp_path: Path) -> None:
    ods = tmp_path / "Translation.ods"
    shutil.copy2(ROOT / "Translation.ods", ods)
    translation_root = tmp_path / "translation"
    menu = translation_root / "menu"
    menu.mkdir(parents=True)
    (menu / "TutorialBody.fmg.txt").write_text(
        '> 301500:"new tutorial text"\n= 301500:"新增教程正文"\n',
        encoding="utf-8",
    )
    first = tmp_path / "first.ods"
    second = tmp_path / "second.ods"

    first_stats = update_ods(ods, translation_root, first)
    second_stats = update_ods(first, translation_root, second)

    assert first_stats["added"] == 1
    assert second_stats["added"] == 0
    assert second_stats["removed"] == 0
    with zipfile.ZipFile(first) as archive:
        first_content = archive.read("content.xml")
    with zipfile.ZipFile(second) as archive:
        second_content = archive.read("content.xml")
    assert first_content == second_content
