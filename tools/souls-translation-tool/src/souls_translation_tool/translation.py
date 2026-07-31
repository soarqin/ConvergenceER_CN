from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Iterable

from .errors import ToolError
from .fmg import FmgDocument, FmgValue


PREFIX_ORDER = ("<", "O", ">", "-", "C", "=")
PREFIXES = frozenset(PREFIX_ORDER)
LINE_PATTERN = re.compile(r"^([<>\-=OC])\s+(-?\d+):(.*)$")
MISSING = object()


@dataclass
class TranslationEntry:
    entry_id: int
    values: dict[str, str] = field(default_factory=dict)

    def copy(self) -> "TranslationEntry":
        return TranslationEntry(self.entry_id, dict(self.values))


@dataclass
class TranslationDocument:
    entries: dict[int, TranslationEntry] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path) -> "TranslationDocument":
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            raise ToolError(f"Could not read translation file {path}: {exc}") from exc

        entries: dict[int, TranslationEntry] = {}
        pending: tuple[int, str, int, str] | None = None

        def flush_pending() -> None:
            nonlocal pending
            if pending is None:
                return
            line_number, prefix, entry_id, encoded = pending
            try:
                value = json.loads(encoded)
            except json.JSONDecodeError as exc:
                raise ToolError(f"Invalid quoted text at {path}:{line_number}: {exc.msg}") from exc
            if not isinstance(value, str):
                raise ToolError(f"Translation text is not a string at {path}:{line_number}")
            entry = entries.setdefault(entry_id, TranslationEntry(entry_id))
            if prefix in entry.values:
                raise ToolError(f"Duplicate {prefix} line for ID {entry_id} at {path}:{line_number}")
            entry.values[prefix] = value
            pending = None

        for line_number, line in enumerate(lines, start=1):
            if not line:
                continue
            match = LINE_PATTERN.match(line)
            if match:
                flush_pending()
                prefix, id_text, encoded = match.groups()
                pending = (line_number, prefix, int(id_text), encoded)
            elif pending is not None:
                line_start, prefix, entry_id, encoded = pending
                pending = (line_start, prefix, entry_id, encoded + line)
            else:
                raise ToolError(f"Invalid translation line {path}:{line_number}: {line}")
        flush_pending()
        return cls(entries)

    def write(self, path: Path) -> None:
        lines: list[str] = []
        for entry_id in sorted(self.entries):
            entry = self.entries[entry_id]
            for prefix in PREFIX_ORDER:
                if prefix in entry.values:
                    encoded = json.dumps(entry.values[prefix], ensure_ascii=False)
                    lines.append(f"{prefix} {entry_id}:{encoded}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")

    def copy(self) -> "TranslationDocument":
        return TranslationDocument({entry_id: entry.copy() for entry_id, entry in self.entries.items()})


@dataclass(frozen=True)
class ComparisonResult:
    document: TranslationDocument
    removed_ids: tuple[int, ...]
    null_ids: tuple[int, ...] = ()
    stats: dict[str, int] = field(default_factory=dict)


def generate_three_way(
    game_a: FmgDocument,
    game_b: FmgDocument,
    mod_a: FmgDocument,
) -> ComparisonResult:
    document = TranslationDocument()
    removed: list[int] = []
    null_ids: list[int] = []
    stats = {"total": 0, "unchanged": 0, "changed": 0, "added": 0, "removed": 0, "null": 0}
    all_ids = sorted(set(game_a.entries) | set(game_b.entries) | set(mod_a.entries))
    for entry_id in all_ids:
        stats["total"] += 1
        original_a = game_a.entries.get(entry_id, MISSING)
        current_a = mod_a.entries.get(entry_id, MISSING)
        if _values_equal(current_a, original_a):
            stats["unchanged"] += 1
            continue
        if current_a is MISSING:
            if original_a is not MISSING:
                removed.append(entry_id)
                stats["removed"] += 1
            continue
        if current_a is None:
            null_ids.append(entry_id)
            stats["null"] += 1
            continue

        stats["added" if original_a is MISSING else "changed"] += 1
        values: dict[str, str] = {}
        _add_text(values, "<", original_a)
        _add_text(values, ">", current_a)
        _add_text(values, "-", game_b.entries.get(entry_id, MISSING))
        values["="] = ""
        document.entries[entry_id] = TranslationEntry(entry_id, values)
    return ComparisonResult(document, tuple(removed), tuple(null_ids), stats)


def generate_five_way(
    game_a: FmgDocument,
    game_b: FmgDocument,
    previous_mod_a: FmgDocument,
    previous_mod_b: FmgDocument,
    current_mod_a: FmgDocument,
    existing: TranslationDocument | None = None,
) -> ComparisonResult:
    document = TranslationDocument()
    removed: list[int] = []
    null_ids: list[int] = []
    stats = {"total": 0, "unchanged": 0, "changed": 0, "added": 0, "removed": 0, "null": 0}
    all_ids = sorted(
        set(game_a.entries)
        | set(game_b.entries)
        | set(previous_mod_a.entries)
        | set(previous_mod_b.entries)
        | set(current_mod_a.entries)
    )

    for entry_id in all_ids:
        stats["total"] += 1
        original_a = game_a.entries.get(entry_id, MISSING)
        previous_a = previous_mod_a.entries.get(entry_id, MISSING)
        current_a = current_mod_a.entries.get(entry_id, MISSING)

        if _values_equal(current_a, previous_a):
            stats["unchanged"] += 1
            continue
        if current_a is MISSING:
            if previous_a is not MISSING:
                removed.append(entry_id)
                stats["removed"] += 1
            else:
                stats["unchanged"] += 1
            continue
        if current_a is None:
            null_ids.append(entry_id)
            stats["null"] += 1
            continue

        stats["added" if previous_a is MISSING else "changed"] += 1
        values: dict[str, str] = {}
        _add_text(values, "<", original_a)
        _add_text(values, "O", previous_a)
        _add_text(values, ">", current_a)
        _add_text(values, "-", game_b.entries.get(entry_id, MISSING))
        _add_text(values, "C", previous_mod_b.entries.get(entry_id, MISSING))
        values["="] = ""
        document.entries[entry_id] = TranslationEntry(entry_id, values)

    return ComparisonResult(
        document,
        tuple(sorted(set(removed))),
        tuple(sorted(set(null_ids))),
        stats,
    )


def merge_documents(original: TranslationDocument, update: TranslationDocument) -> TranslationDocument:
    result = original.copy()
    for entry_id, incoming in update.entries.items():
        current = result.entries.get(entry_id)
        if current is None:
            result.entries[entry_id] = incoming.copy()
            continue

        values: dict[str, str] = {}
        for prefix in ("<", "-"):
            if prefix in incoming.values:
                values[prefix] = incoming.values[prefix]
            elif prefix in current.values:
                values[prefix] = current.values[prefix]

        if "O" in current.values:
            values["O"] = current.values["O"]
        elif "O" in incoming.values:
            values["O"] = incoming.values["O"]
        elif ">" in current.values:
            values["O"] = current.values[">"]

        if ">" in incoming.values:
            values[">"] = incoming.values[">"]
        elif ">" in current.values:
            values[">"] = current.values[">"]

        if "C" in current.values:
            values["C"] = current.values["C"]
        elif "C" in incoming.values:
            values["C"] = incoming.values["C"]
        elif "=" in current.values:
            values["C"] = current.values["="]

        if "=" in incoming.values:
            values["="] = incoming.values["="]
        elif "=" in current.values:
            values["="] = current.values["="]

        result.entries[entry_id] = TranslationEntry(entry_id, values)
    return result


def build_target_fmg(
    game_a: FmgDocument,
    game_b: FmgDocument,
    mod_a: FmgDocument,
    translation: TranslationDocument | None,
) -> FmgDocument:
    result, _ = _build_target_fmg(game_a, game_b, mod_a, translation)
    return result


def _build_target_fmg(
    game_a: FmgDocument,
    game_b: FmgDocument,
    mod_a: FmgDocument,
    translation: TranslationDocument | None,
) -> tuple[FmgDocument, bool]:
    translation = translation or TranslationDocument()
    result = game_b.copy()
    dirty = len(result.entries) < len(mod_a.entries)
    if dirty:
        result.entries = {
            entry_id: _normalize_fmg_value(value)
            for entry_id, value in result.entries.items()
        }
        result.reuse_offsets = False

    for entry_id, current_value in mod_a.entries.items():
        current_a = _normalize_fmg_value(current_value)
        if entry_id in game_a.entries:
            original_a = _normalize_fmg_value(game_a.entries[entry_id])
            if _is_empty_text(original_a) and _is_empty_text(current_a):
                continue
            if original_a == current_a:
                continue
        if not dirty:
            result.entries = {
                current_id: _normalize_fmg_value(value)
                for current_id, value in result.entries.items()
            }
            result.reuse_offsets = False
            dirty = True
        result.entries[entry_id] = current_a

    for entry_id, entry in translation.entries.items():
        translated = entry.values.get("=", "")
        if translated == "":
            continue
        if not dirty:
            result.entries = {
                current_id: _normalize_fmg_value(value)
                for current_id, value in result.entries.items()
            }
            result.reuse_offsets = False
            dirty = True
        result.entries[entry_id] = translated if entry_id in result.entries else _normalize_text(translated)
    return result, dirty


def compare_directories_three_way(
    game_a_dir: Path,
    game_b_dir: Path,
    mod_a_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    files = _fmg_file_union(game_a_dir, game_b_dir, mod_a_dir)
    removed: dict[str, tuple[int, ...]] = {}
    nulls: dict[str, tuple[int, ...]] = {}
    written = 0
    entry_stats = {"total": 0, "unchanged": 0, "changed": 0, "added": 0, "removed": 0, "null": 0}
    written_files: set[Path] = set()
    for relative in files:
        result = generate_three_way(
            _read_optional_fmg(game_a_dir / relative),
            _read_optional_fmg(game_b_dir / relative),
            _read_optional_fmg(mod_a_dir / relative),
        )
        output_path = output_dir / relative.with_suffix(relative.suffix + ".txt")
        if result.document.entries:
            result.document.write(output_path)
            written_files.add(output_path.relative_to(output_dir))
            written += 1
        if result.removed_ids:
            removed[relative.as_posix()] = result.removed_ids
        if result.null_ids:
            nulls[relative.as_posix()] = result.null_ids
        for name, value in result.stats.items():
            entry_stats[name] += value
    _write_state_report(output_dir / "removed.json", removed)
    _write_state_report(output_dir / "null.json", nulls)
    _remove_stale_translation_files(output_dir, written_files)
    return {
        "files": written,
        "removed": sum(len(ids) for ids in removed.values()),
        "null": sum(len(ids) for ids in nulls.values()),
        "entries": entry_stats,
    }


def compare_directories_five_way(
    game_a_dir: Path,
    game_b_dir: Path,
    previous_mod_a_dir: Path,
    previous_mod_b_dir: Path,
    current_mod_a_dir: Path,
    existing_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    files = _fmg_file_union(
        game_a_dir,
        game_b_dir,
        previous_mod_a_dir,
        previous_mod_b_dir,
        current_mod_a_dir,
    )
    files = sorted(set(files) | _translation_fmg_files(existing_dir))
    removed: dict[str, tuple[int, ...]] = {}
    nulls: dict[str, tuple[int, ...]] = {}
    written = 0
    entry_stats = {"total": 0, "unchanged": 0, "changed": 0, "added": 0, "removed": 0, "null": 0}
    written_files: set[Path] = set()
    for relative in files:
        translation_relative = relative.with_suffix(relative.suffix + ".txt")
        existing_path = existing_dir / translation_relative
        existing = TranslationDocument.read(existing_path) if existing_path.is_file() else TranslationDocument()
        result = generate_five_way(
            _read_optional_fmg(game_a_dir / relative),
            _read_optional_fmg(game_b_dir / relative),
            _read_optional_fmg(previous_mod_a_dir / relative),
            _read_optional_fmg(previous_mod_b_dir / relative),
            _read_optional_fmg(current_mod_a_dir / relative),
            None,
        )
        updated = merge_documents(existing, result.document)
        if updated.entries:
            updated.write(output_dir / translation_relative)
            written_files.add(translation_relative)
            written += 1
        if result.removed_ids:
            removed[relative.as_posix()] = result.removed_ids
        if result.null_ids:
            nulls[relative.as_posix()] = result.null_ids
        for name, value in result.stats.items():
            entry_stats[name] += value
    _write_state_report(output_dir / "removed.json", removed)
    _write_state_report(output_dir / "null.json", nulls)
    _remove_stale_translation_files(output_dir, written_files)
    return {
        "files": written,
        "removed": sum(len(ids) for ids in removed.values()),
        "null": sum(len(ids) for ids in nulls.values()),
        "entries": entry_stats,
    }


def merge_directories(original_dir: Path, update_dir: Path, output_dir: Path) -> dict[str, int]:
    original_files = {path.relative_to(original_dir): path for path in original_dir.rglob("*.fmg.txt")}
    update_files = {path.relative_to(update_dir): path for path in update_dir.rglob("*.fmg.txt")}
    count = 0
    new_files = 0
    merged_files = 0
    preserved_files = 0
    new_entries = 0
    merged_entries = 0
    for relative in sorted(set(original_files) | set(update_files)):
        original_path = original_files.get(relative)
        update_path = update_files.get(relative)
        target_path = output_dir / relative
        if update_path is None:
            if original_path is not None and original_path.resolve() != target_path.resolve():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(original_path.read_bytes())
            count += 1
            preserved_files += 1
            continue
        original = TranslationDocument.read(original_path) if original_path is not None else TranslationDocument()
        update = TranslationDocument.read(update_path)
        merge_documents(original, update).write(target_path)
        count += 1
        if original_path is None:
            new_files += 1
            new_entries += len(update.entries)
        else:
            merged_files += 1
            new_entries += len(set(update.entries) - set(original.entries))
            merged_entries += len(set(update.entries) & set(original.entries))
    return {
        "files": count,
        "new_files": new_files,
        "merged_files": merged_files,
        "preserved_files": preserved_files,
        "new_entries": new_entries,
        "merged_entries": merged_entries,
    }


def build_directory(
    game_a_dir: Path,
    game_b_dir: Path,
    mod_a_dir: Path,
    translation_dir: Path,
    output_dir: Path,
) -> dict[str, int]:
    files = sorted(_fmg_files(game_b_dir))
    count = 0
    entries = 0
    nulls = 0
    empty = 0
    for relative in files:
        game_a_path = game_a_dir / relative
        game_b_path = game_b_dir / relative
        mod_a_path = mod_a_dir / relative
        game_b = FmgDocument.read(game_b_path)
        translation_path = translation_dir / relative.with_suffix(relative.suffix + ".txt")
        translation = TranslationDocument.read(translation_path) if translation_path.is_file() else None
        if game_a_path.is_file() and mod_a_path.is_file():
            target, dirty = _build_target_fmg(
                FmgDocument.read(game_a_path),
                game_b,
                FmgDocument.read(mod_a_path),
                translation,
            )
        else:
            target, dirty = game_b, False
        output_path = output_dir / relative
        if dirty:
            target.write(output_path)
            if FmgDocument.read(output_path).entries != target.entries:
                raise ToolError(f"FMG build verification failed: {output_path}")
        elif game_b_path.resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(game_b_path.read_bytes())
        count += 1
        entries += len(target.entries)
        nulls += sum(value is None for value in target.entries.values())
        empty += sum(value == "" for value in target.entries.values())
    return {"files": count, "entries": entries, "null": nulls, "empty": empty}


def _add_text(values: dict[str, str], prefix: str, value: object) -> None:
    if value is not MISSING and value is not None:
        if not isinstance(value, str):
            raise TypeError(f"Unexpected FMG value: {value!r}")
        values[prefix] = _normalize_text(value)


def _normalize_text(value: str) -> str:
    trimmed = value.rstrip()
    return value if trimmed == "" else trimmed


def _normalize_fmg_value(value: FmgValue) -> FmgValue:
    return _normalize_text(value) if isinstance(value, str) else value


def _is_empty_text(value: object) -> bool:
    return isinstance(value, str) and (value.strip() == "" or value == "[ERROR]")


def _values_equal(left: object, right: object) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        normalized_left = _normalize_text(left)
        normalized_right = _normalize_text(right)
        if _is_empty_text(normalized_left) and _is_empty_text(normalized_right):
            return True
        return normalized_left == normalized_right
    return left == right


def _fmg_files(directory: Path) -> set[Path]:
    if not directory.is_dir():
        raise ToolError(f"FMG directory not found: {directory}")
    return {path.relative_to(directory) for path in directory.rglob("*.fmg")}


def _fmg_file_union(*directories: Path) -> list[Path]:
    return sorted(set().union(*(_fmg_files(directory) for directory in directories)))


def _translation_fmg_files(directory: Path) -> set[Path]:
    if not directory.is_dir():
        raise ToolError(f"Translation directory not found: {directory}")
    return {
        path.relative_to(directory).with_suffix("")
        for path in directory.rglob("*.fmg.txt")
    }


def _read_optional_fmg(path: Path) -> FmgDocument:
    return FmgDocument.read(path) if path.is_file() else FmgDocument()


def _write_state_report(path: Path, entries: dict[str, Iterable[int]]) -> None:
    if not entries:
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {name: list(ids) for name, ids in sorted(entries.items())}
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _remove_stale_translation_files(output_dir: Path, current_files: set[Path]) -> None:
    if not output_dir.is_dir():
        return
    for path in output_dir.rglob("*.fmg.txt"):
        if path.relative_to(output_dir) not in current_files:
            path.unlink()
