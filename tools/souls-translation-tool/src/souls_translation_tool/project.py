from __future__ import annotations

from pathlib import Path

from .archive import extract_archive_fmgs, replace_archive_fmgs
from .config import ProjectConfig
from .errors import ToolError
from .translation import build_directory
from .translation import compare_directories_three_way


def build_project(config: ProjectConfig, output_dir: Path | None = None) -> dict[str, object]:
    output_dir = (output_dir or config.output).resolve()
    fmg_root = output_dir / "fmg" / config.language_b
    archive_stats: dict[str, object] = {}

    for category, stem in config.archives.items():
        game_a_dir = config.game_a / stem
        game_b_dir = config.game_b / stem
        mod_a_dir = config.mod_a / stem
        translation_dir = config.translation / category
        target_fmg_dir = fmg_root / stem
        fmg_stats = build_directory(
            game_a_dir,
            game_b_dir,
            mod_a_dir,
            translation_dir,
            target_fmg_dir,
        )

        template_path = config.stage / f"{stem}.msgbnd.dcx"
        if not template_path.is_file():
            raise ToolError(f"Archive template not found: {template_path}")
        output_path = output_dir / f"{stem}.msgbnd.dcx"
        packed_stats = replace_archive_fmgs(template_path, target_fmg_dir, output_path, config.oodle)
        archive_stats[category] = {"fmg": fmg_stats["files"], "packed": packed_stats["files"]}

    return archive_stats


def extract_update(config: ProjectConfig) -> dict[str, object]:
    update_stats: dict[str, object] = {}
    for category, stem in config.archives.items():
        archive_path = config.update / f"{stem}.msgbnd.dcx"
        extracted_dir = config.update / config.language_a / stem
        extract_stats = extract_archive_fmgs(archive_path, extracted_dir, config.oodle)
        output_dir = config.update / category
        compare_stats = compare_directories_three_way(
            config.mod_a / stem,
            config.mod_b / stem,
            extracted_dir,
            output_dir,
        )
        update_stats[category] = {
            "extracted": extract_stats,
            "translation": compare_stats,
        }
    return update_stats
