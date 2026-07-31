from __future__ import annotations

import argparse
import json
from pathlib import Path

from .archive import pack_dcx, unpack_dcx
from .config import ProjectConfig
from .errors import ToolError
from .fmg import FmgDocument, dump_fmg_text, load_fmg_text
from .project import build_project, extract_update
from .translation import (
    build_directory,
    compare_directories_five_way,
    compare_directories_three_way,
    merge_directories,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="souls-translation-tool")
    parser.add_argument("--config", type=Path, default=Path("souls-translation.toml"))
    commands = parser.add_subparsers(dest="command", required=True)

    fmg = commands.add_parser("fmg", help="Read and write individual FMG files")
    fmg_commands = fmg.add_subparsers(dest="fmg_command", required=True)
    fmg_unpack = fmg_commands.add_parser("unpack")
    fmg_unpack.add_argument("input", type=Path)
    fmg_unpack.add_argument("output", type=Path)
    fmg_pack = fmg_commands.add_parser("pack")
    fmg_pack.add_argument("input", type=Path)
    fmg_pack.add_argument("output", type=Path)

    dcx = commands.add_parser("dcx", help="Unpack and pack DCX/BND files")
    dcx_commands = dcx.add_subparsers(dest="dcx_command", required=True)
    dcx_unpack = dcx_commands.add_parser("unpack")
    dcx_unpack.add_argument("input", type=Path)
    dcx_unpack.add_argument("output", type=Path, help="Output directory")
    dcx_pack = dcx_commands.add_parser("pack")
    dcx_pack.add_argument("input", type=Path)
    dcx_pack.add_argument("output", type=Path, help="Output DCX file")

    translation = commands.add_parser("translation", help="Compare, merge, and build translations")
    translation_commands = translation.add_subparsers(dest="translation_command", required=True)

    generate = translation_commands.add_parser("generate", help="Generate a three-way translation set")
    _directory_argument(generate, "game-a")
    _directory_argument(generate, "game-b")
    _directory_argument(generate, "mod-a")
    _directory_argument(generate, "output")

    update = translation_commands.add_parser("update", help="Generate a five-way updated translation set")
    _directory_argument(update, "game-a")
    _directory_argument(update, "game-b")
    _directory_argument(update, "previous-mod-a")
    _directory_argument(update, "previous-mod-b")
    _directory_argument(update, "current-mod-a")
    _directory_argument(update, "existing")
    _directory_argument(update, "output")

    merge = translation_commands.add_parser("merge", help="Merge update text into an existing translation set")
    _directory_argument(merge, "original")
    _directory_argument(merge, "update")
    _directory_argument(merge, "output")

    build = translation_commands.add_parser("build", help="Build language B FMGs")
    _directory_argument(build, "game-a")
    _directory_argument(build, "game-b")
    _directory_argument(build, "mod-a")
    _directory_argument(build, "translation")
    _directory_argument(build, "output")

    project = commands.add_parser("project", help="Run project-level workflows")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_commands.add_parser("extract-update", help="Extract update archives and generate translation text")
    project_build = project_commands.add_parser("build", help="Build translated FMGs and DCX archives")
    project_build.add_argument("--output", type=Path)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = _run(args)
    except ToolError as exc:
        parser.exit(1, f"error: {exc}\n")
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _run(args: argparse.Namespace) -> dict[str, object] | None:
    if args.command == "fmg":
        if args.fmg_command == "unpack":
            document = FmgDocument.read(args.input)
            dump_fmg_text(document, args.output)
            return {"entries": len(document.entries)}
        document = load_fmg_text(args.input)
        document.write(args.output)
        return {"entries": len(document.entries)}

    if args.command == "dcx":
        config = ProjectConfig.load(args.config)
        if args.dcx_command == "unpack":
            return unpack_dcx(args.input, args.output, config.oodle)
        return pack_dcx(args.input, args.output, config.oodle)

    if args.command == "translation":
        if args.translation_command == "generate":
            return compare_directories_three_way(args.game_a, args.game_b, args.mod_a, args.output)
        if args.translation_command == "update":
            return compare_directories_five_way(
                args.game_a,
                args.game_b,
                args.previous_mod_a,
                args.previous_mod_b,
                args.current_mod_a,
                args.existing,
                args.output,
            )
        if args.translation_command == "merge":
            return merge_directories(args.original, args.update, args.output)
        return build_directory(args.game_a, args.game_b, args.mod_a, args.translation, args.output)

    if args.command == "project" and args.project_command == "extract-update":
        config = ProjectConfig.load(args.config)
        return extract_update(config)
    if args.command == "project" and args.project_command == "build":
        config = ProjectConfig.load(args.config)
        return build_project(config, args.output)
    return None


def _directory_argument(parser: argparse.ArgumentParser, name: str) -> None:
    parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)


if __name__ == "__main__":
    main()
