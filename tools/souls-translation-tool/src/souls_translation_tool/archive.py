from __future__ import annotations

from pathlib import Path

from .errors import ToolError
from .fmg import FmgDocument


def load_oodle(path: Path) -> None:
    if not path.is_file():
        raise ToolError(f"Oodle DLL not found: {path}")
    try:
        from soulstruct.dcx import oodle

        oodle.LOAD_DLL(str(path))
    except Exception as exc:
        raise ToolError(f"Could not load Oodle DLL {path}: {exc}") from exc


def unpack_dcx(input_path: Path, output_dir: Path, oodle_path: Path) -> dict[str, int]:
    load_oodle(oodle_path)
    try:
        from soulstruct.containers import Binder

        binder = Binder.from_path(input_path)
        binder.write_unpacked_directory(output_dir)
    except Exception as exc:
        raise ToolError(f"Could not unpack {input_path}: {exc}") from exc
    return {"files": len(binder.entries)}


def pack_dcx(input_dir: Path, output_path: Path, oodle_path: Path) -> dict[str, int]:
    load_oodle(oodle_path)
    try:
        from soulstruct.containers import Binder

        binder = Binder.from_unpacked_path(input_dir)
        _write_binder(binder, output_path)
    except Exception as exc:
        raise ToolError(f"Could not pack {input_dir}: {exc}") from exc
    return {"files": len(binder.entries)}


def extract_archive_fmgs(
    archive_path: Path,
    output_dir: Path,
    oodle_path: Path,
) -> dict[str, int]:
    load_oodle(oodle_path)
    try:
        from soulstruct.containers import Binder

        binder = Binder.from_path(archive_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        for stale in output_dir.glob("*.fmg"):
            stale.unlink()
        names: set[str] = set()
        entries = 0
        nulls = 0
        for entry in binder.entries:
            name = Path(entry.name).name
            if not name.casefold().endswith(".fmg"):
                continue
            key = name.casefold()
            if key in names:
                raise ToolError(f"Duplicate FMG name in archive {archive_path}: {name}")
            names.add(key)
            document = FmgDocument.from_bytes(entry.get_uncompressed_data())
            document.write(output_dir / name)
            entries += len(document.entries)
            nulls += sum(value is None for value in document.entries.values())
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Could not extract FMGs from {archive_path}: {exc}") from exc
    return {"files": len(names), "entries": entries, "null": nulls}


def replace_archive_fmgs(
    template_path: Path,
    fmg_dir: Path,
    output_path: Path,
    oodle_path: Path,
) -> dict[str, int]:
    load_oodle(oodle_path)
    try:
        from soulstruct.containers import Binder

        binder = Binder.from_path(template_path)
        replacements = {path.name.casefold(): path for path in fmg_dir.glob("*.fmg")}
        archive_fmgs = {entry.name.casefold(): entry for entry in binder.entries if entry.name.casefold().endswith(".fmg")}
        missing = sorted(set(archive_fmgs) - set(replacements))
        extra = sorted(set(replacements) - set(archive_fmgs))
        if missing or extra:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if extra:
                details.append("extra: " + ", ".join(extra))
            raise ToolError(f"FMG set does not match archive {template_path}: {'; '.join(details)}")
        source_replacements = dict(replacements)
        replaced = 0
        for entry in binder.entries:
            path = replacements.pop(entry.name.casefold(), None)
            if path is None:
                continue
            document = FmgDocument.read(path)
            entry.set_uncompressed_data(document.to_bytes())
            replaced += 1
        _write_binder(binder, output_path)
        restored = Binder.from_path(output_path)
        restored_by_name = {entry.name.casefold(): entry for entry in restored.entries}
        for name, source_path in source_replacements.items():
            source = FmgDocument.read(source_path)
            packed = restored_by_name[name].get_uncompressed_data()
            if FmgDocument.from_bytes(packed).entries != source.entries:
                raise ToolError(f"FMG archive verification failed: {output_path}: {source_path.name}")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Could not build archive {output_path}: {exc}") from exc
    return {"files": replaced}


def _write_binder(binder: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.is_file():
        output_path.unlink()
    backup = output_path.with_name(output_path.name + ".bak")
    if backup.is_file():
        backup.unlink()
    binder.write(output_path, check_hash=False)
    try:
        from soulstruct.containers import Binder

        restored = Binder.from_path(output_path)
        expected_entries = [
            (entry.entry_id, entry.flags, entry.path, entry.data) for entry in binder.entries
        ]
        actual_entries = [
            (entry.entry_id, entry.flags, entry.path, entry.data) for entry in restored.entries
        ]
        if restored.dcx_type != binder.dcx_type or actual_entries != expected_entries:
            raise ToolError(f"Archive write verification failed: {output_path}")
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Archive write verification failed: {output_path}: {exc}") from exc
