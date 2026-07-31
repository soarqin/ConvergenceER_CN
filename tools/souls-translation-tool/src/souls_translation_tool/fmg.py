from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import struct
from typing import TypeAlias

from .errors import ToolError


FmgValue: TypeAlias = str | None
NULL_MARKER = "%null%"


@dataclass
class FmgDocument:
    """Lossless FMG data. None is an offset-0 null slot; "" is a real empty string."""

    entries: dict[int, FmgValue] = field(default_factory=dict)
    version: int = 2
    big_endian: bool = False
    unicode: bool = True
    md5: bool = False
    reuse_offsets: bool = False

    @classmethod
    def read(cls, path: Path) -> "FmgDocument":
        try:
            return cls.from_bytes(path.read_bytes())
        except OSError as exc:
            raise ToolError(f"Could not read FMG: {path}: {exc}") from exc

    @classmethod
    def from_bytes(cls, source: bytes) -> "FmgDocument":
        base, md5 = _find_header(source)
        data = source[base:]
        big_endian = bool(data[1])
        endian = ">" if big_endian else "<"
        version = data[2]
        wide = version == 2

        if version not in (0, 1, 2):
            raise ToolError(f"Unsupported FMG version: {version}")
        if len(data) < (40 if wide else 28):
            raise ToolError("FMG header is truncated")

        file_size = struct.unpack_from(f"{endian}I", data, 4)[0]
        unicode_text = bool(data[8])
        group_count = struct.unpack_from(f"{endian}I", data, 12)[0]
        string_count = struct.unpack_from(f"{endian}I", data, 16)[0]
        if file_size > len(data):
            raise ToolError(f"FMG file size {file_size} exceeds input size {len(data)}")

        if wide:
            marker = struct.unpack_from(f"{endian}I", data, 20)[0]
            if marker != 0xFF:
                raise ToolError(f"Invalid FMG V2 marker: 0x{marker:X}")
            offsets_offset = struct.unpack_from(f"{endian}Q", data, 24)[0]
            group_offset = 40
            group_size = 16
            offset_size = 8
            offset_format = "Q"
        else:
            offsets_offset = struct.unpack_from(f"{endian}I", data, 20)[0]
            group_offset = 28
            group_size = 12
            offset_size = 4
            offset_format = "I"

        groups: list[tuple[int, int, int]] = []
        for index in range(group_count):
            offset = group_offset + index * group_size
            if offset + group_size > len(data):
                raise ToolError("FMG group table is truncated")
            first_offset, first_id, last_id = struct.unpack_from(f"{endian}Iii", data, offset)
            if last_id < first_id:
                raise ToolError(f"Invalid FMG ID range: {first_id}..{last_id}")
            groups.append((first_offset, first_id, last_id))

        if offsets_offset + string_count * offset_size > len(data):
            raise ToolError("FMG string offset table is truncated")
        offsets = [
            struct.unpack_from(f"{endian}{offset_format}", data, offsets_offset + i * offset_size)[0]
            for i in range(string_count)
        ]

        entries: dict[int, FmgValue] = {}
        used_offsets: set[int] = set()
        reuse_offsets = False
        for first_offset, first_id, last_id in groups:
            for relative, entry_id in enumerate(range(first_id, last_id + 1)):
                offset_index = first_offset + relative
                if offset_index >= len(offsets):
                    raise ToolError(f"FMG offset index is out of range for ID {entry_id}")
                string_offset = offsets[offset_index]
                if string_offset == 0:
                    value = None
                else:
                    if string_offset >= len(data):
                        raise ToolError(f"FMG string offset is out of range for ID {entry_id}")
                    if string_offset in used_offsets:
                        reuse_offsets = True
                    used_offsets.add(string_offset)
                    value = _read_string(data, string_offset, unicode_text, big_endian)
                if entry_id in entries:
                    if entries[entry_id] != value:
                        raise ToolError(f"Duplicate FMG ID {entry_id} has conflicting values")
                    continue
                entries[entry_id] = value

        return cls(
            entries=entries,
            version=version,
            big_endian=big_endian,
            unicode=unicode_text,
            md5=md5,
            reuse_offsets=reuse_offsets,
        )

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_bytes()
        path.write_bytes(payload)
        restored = self.read(path)
        if restored.entries != self.entries:
            raise ToolError(f"FMG write verification failed: {path}")

    def to_bytes(self) -> bytes:
        if self.version not in (0, 1, 2):
            raise ToolError(f"Unsupported FMG version: {self.version}")

        endian = ">" if self.big_endian else "<"
        wide = self.version == 2
        ids = sorted(self.entries)
        groups = _make_groups(ids)
        group_size = 16 if wide else 12
        header_size = 40 if wide else 28
        offset_size = 8 if wide else 4
        offsets_offset = header_size + len(groups) * group_size
        strings_offset = offsets_offset + len(ids) * offset_size

        output = bytearray(strings_offset)
        output[0] = 0
        output[1] = int(self.big_endian)
        output[2] = self.version
        output[3] = 0
        output[8] = int(self.unicode)
        output[9] = 0xFF if self.version == 0 else 0
        struct.pack_into(f"{endian}I", output, 12, len(groups))
        struct.pack_into(f"{endian}I", output, 16, len(ids))

        if wide:
            struct.pack_into(f"{endian}I", output, 20, 0xFF)
            struct.pack_into(f"{endian}Q", output, 24, offsets_offset)
            struct.pack_into(f"{endian}Q", output, 32, 0)
        else:
            struct.pack_into(f"{endian}I", output, 20, offsets_offset)
            struct.pack_into(f"{endian}I", output, 24, 0)

        id_to_index = {entry_id: index for index, entry_id in enumerate(ids)}
        for group_index, (first_id, last_id) in enumerate(groups):
            group_offset = header_size + group_index * group_size
            first_index = id_to_index[first_id]
            struct.pack_into(f"{endian}Iii", output, group_offset, first_index, first_id, last_id)
            if wide:
                struct.pack_into(f"{endian}I", output, group_offset + 12, 0)

        value_offsets: dict[str, int] = {}
        for index, entry_id in enumerate(ids):
            value = self.entries[entry_id]
            if value is None:
                string_offset = 0
            elif self.reuse_offsets and value in value_offsets:
                string_offset = value_offsets[value]
            else:
                string_offset = len(output)
                output.extend(_encode_string(value, self.unicode, self.big_endian))
                if self.reuse_offsets:
                    value_offsets[value] = string_offset

            format_code = "Q" if wide else "I"
            struct.pack_into(
                f"{endian}{format_code}",
                output,
                offsets_offset + index * offset_size,
                string_offset,
            )

        while len(output) % 4:
            output.append(0)
        struct.pack_into(f"{endian}I", output, 4, len(output))
        payload = bytes(output)
        return hashlib.md5(payload).digest() + payload if self.md5 else payload

    def copy(self) -> "FmgDocument":
        return FmgDocument(
            entries=dict(self.entries),
            version=self.version,
            big_endian=self.big_endian,
            unicode=self.unicode,
            md5=self.md5,
            reuse_offsets=self.reuse_offsets,
        )


def dump_fmg_text(document: FmgDocument, path: Path) -> None:
    metadata = {
        "version": document.version,
        "big_endian": document.big_endian,
        "unicode": document.unicode,
        "md5": document.md5,
        "reuse_offsets": document.reuse_offsets,
    }
    lines = [f"# souls-translation-fmg {json.dumps(metadata, separators=(',', ':'))}"]
    for entry_id in sorted(document.entries):
        value = document.entries[entry_id]
        encoded = NULL_MARKER if value is None else json.dumps(value, ensure_ascii=False)
        lines.append(f"{entry_id}\t{encoded}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def load_fmg_text(path: Path) -> FmgDocument:
    metadata: dict[str, object] = {}
    entries: dict[int, FmgValue] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line:
            continue
        if raw_line.startswith("# souls-translation-fmg "):
            metadata = json.loads(raw_line.removeprefix("# souls-translation-fmg "))
            continue
        try:
            id_text, encoded = raw_line.split("\t", 1)
            entry_id = int(id_text)
        except ValueError as exc:
            raise ToolError(f"Invalid FMG text line {path}:{line_number}") from exc
        if encoded == NULL_MARKER:
            value = None
        elif encoded.startswith('"'):
            value = json.loads(encoded)
            if not isinstance(value, str):
                raise ToolError(f"FMG text is not a string at {path}:{line_number}")
        else:
            value = encoded
        if entry_id in entries:
            raise ToolError(f"Duplicate FMG ID {entry_id} at {path}:{line_number}")
        entries[entry_id] = value

    return FmgDocument(
        entries=entries,
        version=int(metadata.get("version", 2)),
        big_endian=bool(metadata.get("big_endian", False)),
        unicode=bool(metadata.get("unicode", True)),
        md5=bool(metadata.get("md5", False)),
        reuse_offsets=bool(metadata.get("reuse_offsets", False)),
    )


def _find_header(source: bytes) -> tuple[int, bool]:
    def looks_like_header(offset: int) -> bool:
        return (
            len(source) >= offset + 4
            and source[offset] == 0
            and source[offset + 1] in (0, 1)
            and source[offset + 2] in (0, 1, 2)
            and source[offset + 3] == 0
        )

    if looks_like_header(0):
        return 0, False
    if looks_like_header(16):
        payload = source[16:]
        if source[:16] != hashlib.md5(payload).digest():
            raise ToolError("FMG MD5 prefix does not match the payload")
        return 16, True
    raise ToolError("Input does not contain a recognized FMG header")


def _read_string(data: bytes, offset: int, unicode_text: bool, big_endian: bool) -> str:
    if unicode_text:
        end = offset
        while end + 1 < len(data) and data[end : end + 2] != b"\0\0":
            end += 2
        if end + 1 >= len(data):
            raise ToolError(f"Unterminated UTF-16 FMG string at offset {offset}")
        encoding = "utf-16-be" if big_endian else "utf-16-le"
        return data[offset:end].decode(encoding)

    end = data.find(b"\0", offset)
    if end < 0:
        raise ToolError(f"Unterminated Shift-JIS FMG string at offset {offset}")
    return data[offset:end].decode("shift_jis")


def _encode_string(value: str, unicode_text: bool, big_endian: bool) -> bytes:
    if unicode_text:
        encoding = "utf-16-be" if big_endian else "utf-16-le"
        return value.encode(encoding) + b"\0\0"
    return value.encode("shift_jis") + b"\0"


def _make_groups(ids: list[int]) -> list[tuple[int, int]]:
    if not ids:
        return []
    groups: list[tuple[int, int]] = []
    first = last = ids[0]
    for entry_id in ids[1:]:
        if entry_id == last + 1:
            last = entry_id
        else:
            groups.append((first, last))
            first = last = entry_id
    groups.append((first, last))
    return groups
