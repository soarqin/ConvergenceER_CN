from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import os
from pathlib import Path
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from .errors import ToolError
from .translation import TranslationDocument, TranslationEntry


NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:svg",
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}

for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


TABLE = f"{{{NS['table']}}}"
OFFICE = f"{{{NS['office']}}}"
TEXT = f"{{{NS['text']}}}"
CALEXT = f"{{{NS['calcext']}}}"


# Translation.ods is a Convergence-specific workbook.  Category and Type are
# semantic labels, while the FMG file is the actual storage key.  Keeping the
# mapping explicit avoids collisions such as the same ID appearing in several
# FMGs or the same category containing names, summaries, and descriptions.
CONVERGENCE_ODS_MAPPING: dict[tuple[str, str], str] = {
    ("Armor", "Armor Description"): "item/ProtectorCaption.fmg.txt",
    ("Armor", "Armor Description [DLC]"): "item/ProtectorCaption_dlc01.fmg.txt",
    ("Armor", "Armor Name"): "item/ProtectorName.fmg.txt",
    ("Armor", "Armor Name [DLC]"): "item/ProtectorName_dlc01.fmg.txt",
    ("Armor", "Armor Summary"): "item/ProtectorInfo.fmg.txt",
    ("Info", "Tutorial Text"): "menu/TutorialBody.fmg.txt",
    ("Info", "Tutorial Title"): "menu/TutorialTitle.fmg.txt",
    ("Items", "Item Description"): "item/GoodsCaption.fmg.txt",
    ("Items", "Item Description [DLC]"): "item/GoodsCaption_dlc01.fmg.txt",
    ("Items", "Item Name"): "item/GoodsName.fmg.txt",
    ("Items", "Item Name [DLC]"): "item/GoodsName_dlc01.fmg.txt",
    ("Items", "Item Popup"): "item/GoodsDialog.fmg.txt",
    ("Items", "Item Secondary Summary"): "item/GoodsInfo2.fmg.txt",
    ("Items", "Item Secondary Summary [DLC]"): "item/GoodsInfo2_dlc01.fmg.txt",
    ("Items", "Item Summary"): "item/GoodsInfo.fmg.txt",
    ("Items", "Item Summary [DLC]"): "item/GoodsInfo_dlc01.fmg.txt",
    ("Maps", "Action"): "menu/ActionButtonText.fmg.txt",
    ("Maps", "Ground Message"): "menu/BloodMsg.fmg.txt",
    ("Maps", "Location"): "item/PlaceName.fmg.txt",
    ("Maps", "Location [DLC]"): "item/PlaceName_dlc01.fmg.txt",
    ("Maps", "Menu Dialogue"): "menu/GR_Dialogues.fmg.txt",
    ("Menus", "Menu Help"): "menu/GR_LineHelp.fmg.txt",
    ("Menus", "Menu Text"): "menu/GR_MenuText.fmg.txt",
    ("Menus", "Menu Text [DLC]"): "menu/GR_MenuText_dlc01.fmg.txt",
    ("Menus", "Popup Message"): "menu/EventTextForMap.fmg.txt",
    ("Menus", "System Message"): "menu/GR_System_Message_win64.fmg.txt",
    ("NPCs", "Dialogue"): "menu/TalkMsg.fmg.txt",
    ("NPCs", "NPC Menu Item"): "menu/EventTextForTalk.fmg.txt",
    ("NPCs", "NPC Name"): "item/NpcName.fmg.txt",
    ("NPCs", "NPC Name [DLC]"): "item/NpcName_dlc01.fmg.txt",
    ("Skills", "Ash of War Description"): "item/GemCaption.fmg.txt",
    ("Skills", "Ash of War Description [DLC]"): "item/GemCaption_dlc01.fmg.txt",
    ("Skills", "Ash of War Name"): "item/GemName.fmg.txt",
    ("Skills", "Ash of War Name [DLC]"): "item/GemName_dlc01.fmg.txt",
    ("Skills", "Ash of War Summary"): "item/GemInfo.fmg.txt",
    ("Skills", "Ash of War Summary [DLC]"): "item/GemInfo_dlc01.fmg.txt",
    ("Skills", "Weapon Art Name"): "item/ArtsName.fmg.txt",
    ("Skills", "Weapon Art Name [DLC]"): "item/ArtsName_dlc01.fmg.txt",
    ("Skills", "Weapon Art Summary"): "item/ArtsCaption.fmg.txt",
    ("Skills", "Weapon Art Summary [DLC]"): "item/ArtsCaption_dlc01.fmg.txt",
    ("Talismans", "Talisman Description"): "item/AccessoryCaption.fmg.txt",
    ("Talismans", "Talisman Description [DLC]"): "item/AccessoryCaption_dlc01.fmg.txt",
    ("Talismans", "Talisman Name"): "item/AccessoryName.fmg.txt",
    ("Talismans", "Talisman Name [DLC]"): "item/AccessoryName_dlc01.fmg.txt",
    ("Talismans", "Talisman Summary"): "item/AccessoryInfo.fmg.txt",
    ("Talismans", "Talisman Summary [DLC]"): "item/AccessoryInfo_dlc01.fmg.txt",
    ("Weapons", "Infusion"): "item/WeaponEffect.fmg.txt",
    ("Weapons", "Weapon Description"): "item/WeaponCaption.fmg.txt",
    ("Weapons", "Weapon Description [DLC]"): "item/WeaponCaption_dlc01.fmg.txt",
    ("Weapons", "Weapon Effect"): "item/WeaponEffect.fmg.txt",
    ("Weapons", "Weapon Effect [DLC]"): "item/WeaponEffect_dlc01.fmg.txt",
    ("Weapons", "Weapon Name"): "item/WeaponName.fmg.txt",
    ("Weapons", "Weapon Name [DLC]"): "item/WeaponName_dlc01.fmg.txt",
    ("Weapons", "Weapon Summary"): "item/WeaponInfo.fmg.txt",
}


ODS_SHEET_NAME = "Translation Data"
OLD_ENGLISH_HEADER = "Old Convergence (English)"
OLD_CHINESE_HEADER = "Old Convergence (Simplified Chinese)"

ODS_CATEGORY_ORDER = (
    "Armor",
    "Info",
    "Items",
    "Maps",
    "Menus",
    "NPCs",
    "Skills",
    "Talismans",
    "Weapons",
)
ODS_TYPE_ORDER: dict[str, tuple[str, ...]] = {
    "Armor": (
        "Armor Description",
        "Armor Name",
        "Armor Summary",
        "Armor Description [DLC]",
        "Armor Name [DLC]",
    ),
    "Info": ("Tutorial Title", "Tutorial Text"),
    "Items": (
        "Item Name",
        "Item Summary",
        "Item Description",
        "Item Secondary Summary",
        "Item Description [DLC]",
        "Item Name [DLC]",
        "Item Summary [DLC]",
        "Item Secondary Summary [DLC]",
        "Item Popup",
    ),
    "Maps": (
        "Action",
        "Ground Message",
        "Location",
        "Location [DLC]",
        "Menu Dialogue",
    ),
    "Menus": (
        "Popup Message",
        "Menu Text",
        "Menu Text [DLC]",
        "Menu Help",
        "System Message",
    ),
    "NPCs": (
        "NPC Name [DLC]",
        "NPC Name",
        "NPC Menu Item",
        "Dialogue",
    ),
    "Skills": (
        "Weapon Art Name",
        "Weapon Art Summary",
        "Weapon Art Summary [DLC]",
        "Weapon Art Name [DLC]",
        "Ash of War Description",
        "Ash of War Name",
        "Ash of War Summary",
        "Ash of War Description [DLC]",
    ),
    "Talismans": (
        "Talisman Summary",
        "Talisman Description",
        "Talisman Name",
        "Talisman Name [DLC]",
        "Talisman Summary [DLC]",
        "Talisman Description [DLC]",
    ),
    "Weapons": (
        "Infusion",
        "Weapon Effect",
        "Weapon Effect [DLC]",
        "Weapon Description",
        "Weapon Name",
        "Weapon Description [DLC]",
        "Weapon Name [DLC]",
        "Weapon Summary",
    ),
}

WEAPON_ITEM_TYPES = frozenset({
    "Weapon Name",
    "Weapon Summary",
    "Weapon Description",
})
ASH_DESCRIPTION_MARKER = "Ashen remains in which spirits yet dwell."
ASH_DESCRIPTION_MARKER_ZH = "寄宿着灵魂的骨灰"
ASH_UPGRADE_SUFFIX = re.compile(r"[+＋]\s*[0-9０-９]{1,2}$")
SEMANTIC_TYPE_ORDER = (
    "Name",
    "Summary",
    "Description",
    "Secondary Summary",
)


def update_ods(
    ods_path: Path,
    translation_root: Path,
    output_path: Path,
) -> dict[str, int]:
    """Update the Convergence translation sheet from local FMG translation files."""

    ods_path = ods_path.resolve()
    translation_root = translation_root.resolve()
    output_path = output_path.resolve()
    if not ods_path.is_file():
        raise ToolError(f"ODS file not found: {ods_path}")
    if not translation_root.is_dir():
        raise ToolError(f"Translation directory not found: {translation_root}")

    translations = _load_translations(translation_root)
    try:
        with zipfile.ZipFile(ods_path, "r") as archive:
            files = {info.filename: (info, archive.read(info.filename)) for info in archive.infolist()}
        content = ET.fromstring(files["content.xml"][1])
        sheet = _find_sheet(content, ODS_SHEET_NAME)
        _ensure_reference_columns(sheet)
        stats = _update_sheet(sheet, translations)
        _extend_conditional_formats(sheet, stats["final_rows"])
        content_bytes = ET.tostring(content, encoding="utf-8", xml_declaration=True)
        _write_ods(files, output_path, content_bytes)
    except KeyError as exc:
        raise ToolError(f"ODS archive is missing {exc.args[0]}") from exc
    except ET.ParseError as exc:
        raise ToolError(f"Invalid ODS XML: {ods_path}: {exc}") from exc

    return stats


def _load_translations(root: Path) -> dict[str, TranslationDocument]:
    result: dict[str, TranslationDocument] = {}
    for relative in sorted(set(CONVERGENCE_ODS_MAPPING.values())):
        path = root / relative
        if path.is_file():
            result[relative] = TranslationDocument.read(path)
    return result


def _find_sheet(content: ET.Element, name: str) -> ET.Element:
    for sheet in content.findall(".//table:table", NS):
        if sheet.get(f"{TABLE}name") == name:
            return sheet
    raise ToolError(f"ODS sheet not found: {name}")


def _update_sheet(
    sheet: ET.Element,
    translations: dict[str, TranslationDocument],
) -> dict[str, int]:
    rows = sheet.findall("./table:table-row", NS)
    if not rows:
        raise ToolError(f"ODS sheet is empty: {ODS_SHEET_NAME}")

    header_cells = _expanded_cells(rows[0])
    headers = {_cell_text(cell): index for index, cell in enumerate(header_cells)}
    required = {
        "ID",
        "Category",
        "Type",
        "Convergence (Simplified Chinese)",
        "Convergence (English)",
    }
    missing = sorted(required - set(headers))
    if missing:
        raise ToolError(f"ODS sheet is missing columns: {', '.join(missing)}")

    id_col = headers["ID"]
    category_col = headers["Category"]
    type_col = headers["Type"]
    chinese_col = headers["Convergence (Simplified Chinese)"]
    english_col = headers["Convergence (English)"]
    old_english_col = headers.get(OLD_ENGLISH_HEADER)
    old_chinese_col = headers.get(OLD_CHINESE_HEADER)

    local_ash_ids = _find_local_ash_ids(translations)
    data_rows: list[tuple[tuple[str, str, int], ET.Element]] = []
    tail_rows: list[ET.Element] = []
    file_key_types: dict[tuple[str, int], set[tuple[str, str]]] = defaultdict(set)
    for row in rows[1:]:
        key = _row_key(row, id_col, category_col, type_col)
        if key is None:
            tail_rows.append(row)
            continue
        data_rows.append((key, row))
        category, type_name, entry_id = key
        relative = CONVERGENCE_ODS_MAPPING.get((category, type_name))
        if relative is not None:
            file_key_types[(relative, entry_id)].add((category, type_name))

    ash_ids = local_ash_ids | _find_ods_ash_ids(
        data_rows,
        english_col,
        headers.get("Vanilla (English)"),
    )

    local_entries = _build_local_entries(translations, file_key_types, ash_ids)

    stats = Counter(
        rows=len(data_rows),
        final_rows=0,
        updated=0,
        unchanged=0,
        version_changes=0,
        removed=0,
        added=0,
    )
    kept_rows: list[tuple[tuple[str, str, int], ET.Element]] = []
    existing_keys: set[tuple[str, str, int]] = set()
    for key, row in data_rows:
        existing_keys.add(key)
        if not _should_keep_key(key, ash_ids):
            stats["removed"] += 1
            continue
        entry = local_entries.get(key)
        if entry is None:
            stats["removed"] += 1
            continue
        changed, version_changed = _update_existing_row(
            row,
            entry,
            chinese_col,
            english_col,
            old_english_col,
            old_chinese_col,
        )
        stats["updated" if changed else "unchanged"] += 1
        stats["version_changes"] += int(version_changed)
        kept_rows.append((key, row))

    for key, entry in local_entries.items():
        if key in existing_keys:
            continue
        kept_rows.append((key, _make_translation_row(key, entry)))
        stats["added"] += 1

    ordered_rows = [
        row
        for _, row in sorted(
            kept_rows,
            key=lambda item: _row_sort_key(
                item[0],
            ),
        )
    ]
    _replace_data_rows(sheet, rows[1:], ordered_rows, tail_rows)
    stats["final_rows"] = len(ordered_rows)
    return dict(stats)


def _build_local_entries(
    translations: dict[str, TranslationDocument],
    file_key_types: dict[tuple[str, int], set[tuple[str, str]]],
    ash_ids: set[int],
) -> dict[tuple[str, str, int], TranslationEntry]:
    entries: dict[tuple[str, str, int], TranslationEntry] = {}
    file_mappings: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, relative in CONVERGENCE_ODS_MAPPING.items():
        file_mappings[relative].append(key)

    for relative, document in translations.items():
        candidates = file_mappings.get(relative, [])
        if not candidates:
            continue
        for entry_id, entry in document.entries.items():
            if ">" not in entry.values and "=" not in entry.values:
                continue
            if not _should_keep_file_entry(relative, entry_id, ash_ids):
                continue
            known_types = file_key_types.get((relative, entry_id))
            if known_types:
                selected = [key for key in candidates if key in known_types]
            elif len(candidates) == 1:
                selected = candidates
            else:
                formatted = ", ".join(f"{category} / {type_name}" for category, type_name in candidates)
                raise ToolError(
                    f"Cannot classify {relative} ID {entry_id}; "
                    f"the ODS has no existing row and the FMG maps to {formatted}"
                )
            for category, type_name in selected:
                entries[(category, type_name, entry_id)] = entry
    return entries


def _find_local_ash_ids(
    translations: dict[str, TranslationDocument],
) -> set[int]:
    ash_ids: set[int] = set()
    for relative, document in translations.items():
        filename = Path(relative).name
        if filename not in {
            "GoodsName.fmg.txt",
            "GoodsName_dlc01.fmg.txt",
            "GoodsCaption.fmg.txt",
            "GoodsCaption_dlc01.fmg.txt",
        }:
            continue
        for entry_id, entry in document.entries.items():
            if filename.startswith("GoodsName") and _has_ash_upgrade_suffix(entry):
                ash_ids.update(_ash_upgrade_group(entry_id))
            elif _is_ash_description(entry):
                ash_ids.update(_ash_upgrade_group(entry_id))
    return ash_ids


def _find_ods_ash_ids(
    data_rows: list[tuple[tuple[str, str, int], ET.Element]],
    english_col: int,
    vanilla_english_col: int | None,
) -> set[int]:
    ash_ids: set[int] = set()
    for (category, type_name, entry_id), row in data_rows:
        if category != "Items":
            continue
        cells = _expanded_cells(row)
        if type_name.removesuffix(" [DLC]") == "Item Name":
            if _has_ash_upgrade_suffix_in_text(_cell_text(cells[english_col])):
                ash_ids.update(_ash_upgrade_group(entry_id))
            continue
        if type_name.removesuffix(" [DLC]") != "Item Description":
            continue
        for column in (english_col, vanilla_english_col):
            if column is not None and column < len(cells) and _is_ash_text(_cell_text(cells[column])):
                ash_ids.update(_ash_upgrade_group(entry_id))
                break
    return ash_ids


def _is_ash_description(entry: TranslationEntry) -> bool:
    return any(_is_ash_text(value) for value in entry.values.values())


def _has_ash_upgrade_suffix(entry: TranslationEntry) -> bool:
    return any(_has_ash_upgrade_suffix_in_text(value) for value in entry.values.values())


def _has_ash_upgrade_suffix_in_text(value: str) -> bool:
    return bool(ASH_UPGRADE_SUFFIX.search(value.rstrip('\\n')))


def _ash_upgrade_group(entry_id: int) -> set[int]:
    base_id = entry_id - entry_id % 1000
    return {base_id + offset for offset in range(11)}


def _is_ash_text(value: str) -> bool:
    return ASH_DESCRIPTION_MARKER in value or ASH_DESCRIPTION_MARKER_ZH in value


def _should_keep_file_entry(relative: str, entry_id: int, ash_ids: set[int]) -> bool:
    if _is_weapon_item_file(relative):
        return entry_id % 10000 == 0
    if _is_item_file(relative) and entry_id in ash_ids:
        return entry_id % 1000 == 0
    return True


def _should_keep_key(key: tuple[str, str, int], ash_ids: set[int]) -> bool:
    category, type_name, entry_id = key
    relative = CONVERGENCE_ODS_MAPPING.get((category, type_name))
    if relative is None:
        return True
    return _should_keep_file_entry(relative, entry_id, ash_ids)


def _is_weapon_item_file(relative: str) -> bool:
    return Path(relative).name in {
        "WeaponName.fmg.txt",
        "WeaponName_dlc01.fmg.txt",
        "WeaponInfo.fmg.txt",
        "WeaponInfo_dlc01.fmg.txt",
        "WeaponCaption.fmg.txt",
        "WeaponCaption_dlc01.fmg.txt",
    }


def _is_item_file(relative: str) -> bool:
    return Path(relative).name in {
        "GoodsName.fmg.txt",
        "GoodsName_dlc01.fmg.txt",
        "GoodsInfo.fmg.txt",
        "GoodsInfo_dlc01.fmg.txt",
        "GoodsInfo2.fmg.txt",
        "GoodsInfo2_dlc01.fmg.txt",
        "GoodsCaption.fmg.txt",
        "GoodsCaption_dlc01.fmg.txt",
    }


def _row_key(
    row: ET.Element,
    id_col: int,
    category_col: int,
    type_col: int,
) -> tuple[str, str, int] | None:
    cells = _expanded_cells(row)
    required_col = max(id_col, category_col, type_col)
    if len(cells) <= required_col:
        return None
    id_text = _cell_text(cells[id_col]).strip()
    category = _cell_text(cells[category_col])
    type_name = _cell_text(cells[type_col])
    if not id_text.isdigit() or not category or not type_name:
        return None
    return category, type_name, int(id_text)


def _update_existing_row(
    row: ET.Element,
    entry: TranslationEntry,
    chinese_col: int,
    english_col: int,
    old_english_col: int | None,
    old_chinese_col: int | None,
) -> tuple[bool, bool]:
    cells = _expanded_cells(row)
    values = entry.values
    current_english = values.get(">")
    current_chinese = values.get("=")
    old_english = _cell_text(cells[english_col])
    old_chinese = _cell_text(cells[chinese_col])
    version_changed = (
        current_english is not None
        and not _same_text(old_english, current_english)
    )
    if version_changed:
        if old_english_col is not None and not _cell_text(cells[old_english_col]):
            _set_cell_text(cells[old_english_col], old_english, "ce13")
        if old_chinese_col is not None and not _cell_text(cells[old_chinese_col]):
            if old_chinese:
                _set_cell_text(cells[old_chinese_col], old_chinese, "ce12")

    changed = False
    if current_english is not None and not _same_text(old_english, current_english):
        _set_cell_text(cells[english_col], current_english, "ce13")
        changed = True
    if current_chinese is not None and old_chinese != current_chinese:
        _set_cell_text(cells[chinese_col], current_chinese, "ce12")
        changed = True
    return changed, version_changed


def _make_translation_row(
    key: tuple[str, str, int],
    entry: TranslationEntry,
) -> ET.Element:
    category, type_name, entry_id = key
    values = entry.values
    row = ET.Element(f"{TABLE}table-row", {f"{TABLE}style-name": "ro1"})
    row.extend(
        [
            _make_numeric_cell(entry_id),
            _make_cell("ce7", category),
            _make_cell("ce11", type_name),
            _make_cell("ce12", values.get("=")),
            _make_cell("ce13", values.get(">")),
            _make_cell("ce12", values.get("<")),
            _make_cell("ce12", values.get("-")),
            _make_cell("ce13"),
            _make_cell("ce12"),
        ]
    )
    return row


def _make_numeric_cell(value: int) -> ET.Element:
    cell = _make_cell("ce7")
    cell.set(f"{OFFICE}value-type", "float")
    cell.set(f"{OFFICE}value", str(value))
    cell.set(f"{CALEXT}value-type", "float")
    paragraph = ET.SubElement(cell, f"{TEXT}p")
    paragraph.text = str(value)
    return cell


def _replace_data_rows(
    sheet: ET.Element,
    original_rows: list[ET.Element],
    data_rows: list[ET.Element],
    tail_rows: list[ET.Element],
) -> None:
    for row in original_rows:
        sheet.remove(row)
    header = sheet.findall("./table:table-row", NS)[0]
    insert_at = list(sheet).index(header) + 1
    for row in data_rows + tail_rows:
        sheet.insert(insert_at, row)
        insert_at += 1


def _row_sort_key(
    key: tuple[str, str, int],
) -> tuple[int, int, tuple[int, int, str]]:
    category, type_name, entry_id = key
    category_rank = _category_rank(category, list(ODS_CATEGORY_ORDER))
    type_key = _type_sort_key(category, type_name)
    return category_rank, entry_id, type_key


def _type_sort_key(
    category: str,
    type_name: str,
) -> tuple[int, int, str]:
    base_type = type_name.removesuffix(" [DLC]")
    for rank, suffix in sorted(
        enumerate(SEMANTIC_TYPE_ORDER),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        if base_type.endswith(f" {suffix}"):
            return 0, rank, type_name
    known_types = ODS_TYPE_ORDER.get(category, ())
    try:
        return 1, known_types.index(type_name), type_name
    except ValueError:
        return 1, _mapping_type_rank(category, type_name), type_name


def _category_rank(category: str, category_order: list[str]) -> int:
    if category in category_order:
        return category_order.index(category)
    known = list(dict.fromkeys(category_name for category_name, _ in CONVERGENCE_ODS_MAPPING))
    try:
        return len(category_order) + known.index(category)
    except ValueError:
        return len(category_order) + len(known)


def _mapping_type_rank(category: str, type_name: str) -> int:
    candidates = [
        current_type
        for current_category, current_type in CONVERGENCE_ODS_MAPPING
        if current_category == category
    ]
    try:
        return candidates.index(type_name)
    except ValueError:
        return len(candidates)


def _ensure_reference_columns(sheet: ET.Element) -> None:
    rows = sheet.findall("./table:table-row", NS)
    header_cells = _expanded_cells(rows[0])
    headers = [_cell_text(cell) for cell in header_cells]
    has_old_columns = OLD_ENGLISH_HEADER in headers and OLD_CHINESE_HEADER in headers
    if not has_old_columns:
        _insert_table_columns(sheet)
        for row_index, row in enumerate(rows):
            _insert_reference_cells(
                row,
                (OLD_ENGLISH_HEADER, OLD_CHINESE_HEADER)
                if row_index == 0
                else (None, None),
            )

    for row in rows:
        _materialize_prefix(row, 9)


def _insert_table_columns(sheet: ET.Element) -> None:
    columns = sheet.findall("./table:table-column", NS)
    logical_column = 1
    insert_at = len(columns)
    for index, column in enumerate(columns):
        repeat = int(column.get(f"{TABLE}number-columns-repeated", "1"))
        if logical_column + repeat > 8:
            insert_at = index
            break
        logical_column += repeat

    new_columns = [
        ET.Element(f"{TABLE}table-column", {
            f"{TABLE}style-name": "co6",
            f"{TABLE}default-cell-style-name": "Default",
        }),
        ET.Element(f"{TABLE}table-column", {
            f"{TABLE}style-name": "co6",
            f"{TABLE}default-cell-style-name": "Default",
        }),
    ]
    if insert_at < len(columns):
        column_index = list(sheet).index(columns[insert_at])
        for column in reversed(new_columns):
            sheet.insert(column_index, column)
    else:
        for column in new_columns:
            sheet.append(column)
    if insert_at < len(columns):
        tail = columns[insert_at]
        repeated = int(tail.get(f"{TABLE}number-columns-repeated", "1"))
        if repeated > 2:
            tail.set(f"{TABLE}number-columns-repeated", str(repeated - 2))
        else:
            tail.attrib.pop(f"{TABLE}number-columns-repeated", None)


def _expanded_cells(row: ET.Element) -> list[ET.Element]:
    cells: list[ET.Element] = []
    for cell in list(row):
        if cell.tag not in (f"{TABLE}table-cell", f"{TABLE}covered-table-cell"):
            continue
        repeat = int(cell.get(f"{TABLE}number-columns-repeated", "1"))
        cells.extend([cell] * min(repeat, 9 - len(cells)))
        if len(cells) >= 9:
            break
    return cells


def _materialize_prefix(row: ET.Element, column_count: int) -> None:
    """Split a repeated cell when the first columns need independent values."""

    logical_column = 0
    for child in list(row):
        if child.tag not in (f"{TABLE}table-cell", f"{TABLE}covered-table-cell"):
            continue
        repeat = int(child.get(f"{TABLE}number-columns-repeated", "1"))
        if logical_column + repeat <= column_count:
            logical_column += repeat
            continue
        needed = column_count - logical_column
        if needed <= 0:
            return

        child_index = list(row).index(child)
        for offset in range(needed):
            clone = deepcopy(child)
            clone.attrib.pop(f"{TABLE}number-columns-repeated", None)
            row.insert(child_index + offset, clone)
        remaining = repeat - needed
        if remaining <= 1:
            child.attrib.pop(f"{TABLE}number-columns-repeated", None)
        else:
            child.set(f"{TABLE}number-columns-repeated", str(remaining))
        return
    


def _trailing_blank_cell_index(row: ET.Element) -> int:
    children = list(row)
    for index in range(len(children) - 1, -1, -1):
        child = children[index]
        if child.tag not in (f"{TABLE}table-cell", f"{TABLE}covered-table-cell"):
            continue
        if not _cell_text(child) and not child.get(f"{OFFICE}value-type"):
            return index
    return len(children)


def _insert_reference_cells(
    row: ET.Element,
    values: tuple[str | None, str | None],
) -> None:
    children = list(row)
    insert_at = _trailing_blank_cell_index(row)
    if insert_at < len(children):
        tail = children[insert_at]
        repeated = int(tail.get(f"{TABLE}number-columns-repeated", "1"))
        if repeated > 2:
            tail.set(f"{TABLE}number-columns-repeated", str(repeated - 2))
        else:
            row.remove(tail)

    english, chinese = values
    row.insert(insert_at, _make_cell("ce10", english) if english is not None else _make_cell("ce13"))
    row.insert(insert_at + 1, _make_cell("ce10", chinese) if chinese is not None else _make_cell("ce12"))


def _make_cell(style_name: str, value: str | None = None) -> ET.Element:
    cell = ET.Element(f"{TABLE}table-cell", {f"{TABLE}style-name": style_name})
    if value:
        _set_cell_text(cell, value, style_name)
    return cell


def _cell_text(cell: ET.Element) -> str:
    paragraphs = cell.findall("./text:p", NS)
    return "\n".join("".join(paragraph.itertext()) for paragraph in paragraphs)


def _set_cell_text(cell: ET.Element, value: str, style_name: str) -> None:
    cell.set(f"{TABLE}style-name", style_name)
    for key in (f"{OFFICE}value", f"{OFFICE}date-value", f"{OFFICE}time-value"):
        cell.attrib.pop(key, None)
    cell.set(f"{OFFICE}value-type", "string")
    cell.set(f"{CALEXT}value-type", "string")
    for child in list(cell):
        cell.remove(child)
    for line in value.split("\n"):
        paragraph = ET.SubElement(cell, f"{TEXT}p")
        paragraph.text = line


def _same_text(left: str, right: str) -> bool:
    return left == right or left.rstrip() == right.rstrip()


def _extend_conditional_formats(sheet: ET.Element, final_rows: int) -> None:
    conditional_formats = sheet.find("./calcext:conditional-formats", NS)
    if conditional_formats is None:
        return
    last_row = max(2, final_rows + 1)
    ranges = {
        "ConditionalStyle_1": f"'{ODS_SHEET_NAME}'.A2:'{ODS_SHEET_NAME}'.I{last_row}",
        "ConditionalStyle_2": (
            f"'{ODS_SHEET_NAME}'.D2:'{ODS_SHEET_NAME}'.D{last_row} "
            f"'{ODS_SHEET_NAME}'.F2:'{ODS_SHEET_NAME}'.I{last_row}"
        ),
        "ConditionalStyle_3": f"'{ODS_SHEET_NAME}'.A2:'{ODS_SHEET_NAME}'.I{last_row}",
        "ConditionalStyle_4": f"'{ODS_SHEET_NAME}'.A2:'{ODS_SHEET_NAME}'.C{last_row}",
    }
    for conditional in conditional_formats:
        condition = conditional.find("./calcext:condition", NS)
        if condition is None:
            continue
        style_name = condition.get(f"{CALEXT}apply-style-name")
        address = ranges.get(style_name)
        if address is not None:
            conditional.set(f"{CALEXT}target-range-address", address)


def _write_ods(
    files: dict[str, tuple[zipfile.ZipInfo, bytes]],
    output_path: Path,
    content_bytes: bytes,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f"{output_path.stem}-", suffix=".ods", dir=output_path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w") as target:
            for filename, (info, original_data) in files.items():
                data = content_bytes if filename == "content.xml" else original_data
                target.writestr(info, data)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
