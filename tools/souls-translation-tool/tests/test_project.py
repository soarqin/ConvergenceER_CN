from pathlib import Path
import shutil
from dataclasses import replace

import pytest

from souls_translation_tool.config import ProjectConfig
from souls_translation_tool.fmg import FmgDocument
from souls_translation_tool.project import build_project, extract_update
from soulstruct.containers import Binder

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPOSITORY_ROOT / "souls-translation.toml"
HOST_PROJECT_AVAILABLE = CONFIG_PATH.is_file()


@pytest.mark.skipif(not HOST_PROJECT_AVAILABLE, reason="Host project configuration is unavailable")
def test_project_builds_both_archives_with_real_config(tmp_path: Path) -> None:
    config = ProjectConfig.load(CONFIG_PATH)
    result = build_project(config, tmp_path)

    assert result["item"]["fmg"] == 78
    assert result["menu"]["fmg"] == 53
    for stem in config.archives.values():
        archive = tmp_path / f"{stem}.msgbnd.dcx"
        binder = Binder.from_path(archive)
        assert len(binder.entries) > 0


@pytest.mark.skipif(not HOST_PROJECT_AVAILABLE, reason="Host project configuration is unavailable")
def test_project_extracts_update_archives_and_generates_text(tmp_path: Path) -> None:
    config = ProjectConfig.load(CONFIG_PATH)
    update_dir = tmp_path / "update"
    update_dir.mkdir()
    mod_a_dir = tmp_path / "mod-a"
    mod_b_dir = tmp_path / "mod-b"
    shutil.copytree(config.mod_a, mod_a_dir)
    shutil.copytree(config.mod_b, mod_b_dir)
    for stem in config.archives.values():
        shutil.copy2(config.update / f"{stem}.msgbnd.dcx", update_dir / f"{stem}.msgbnd.dcx")
    menu_fmg = mod_a_dir / "menu_dlc02" / "GR_MenuText.fmg"
    document = FmgDocument.read(menu_fmg)
    document.entries[401002] = "old version"
    document.write(menu_fmg)

    result = extract_update(replace(config, update=update_dir, mod_a=mod_a_dir, mod_b=mod_b_dir))

    assert result["item"]["extracted"]["files"] == 78
    assert result["menu"]["extracted"]["files"] == 50
    assert result["menu"]["translation"]["files"] == 1
    assert (update_dir / "menu" / "GR_MenuText.fmg.txt").is_file()
