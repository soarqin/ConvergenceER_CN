from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .errors import ToolError


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    language_a: str
    language_b: str
    game_a: Path
    game_b: Path
    mod_a: Path
    mod_b: Path
    translation: Path
    update: Path
    stage: Path
    output: Path
    oodle: Path
    archives: dict[str, str]

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        path = path.resolve()
        if not path.is_file():
            raise ToolError(f"Config file not found: {path}")

        with path.open("rb") as config_file:
            data = tomllib.load(config_file)

        root = path.parent
        project = data.get("project", {})
        paths = data.get("paths", {})
        archives = data.get("archives", {})
        required_project = ("language_a", "language_b")
        missing_project = [name for name in required_project if name not in project]
        if missing_project:
            raise ToolError(f"Missing project settings: {', '.join(missing_project)}")
        required_paths = (
            "game_a",
            "game_b",
            "mod_a",
            "mod_b",
            "translation",
            "update",
            "stage",
            "output",
            "oodle",
        )
        missing = [name for name in required_paths if name not in paths]
        if missing:
            raise ToolError(f"Missing config paths: {', '.join(missing)}")
        if not archives:
            raise ToolError("No archives are configured")

        def resolve(value: str) -> Path:
            candidate = Path(value)
            return candidate if candidate.is_absolute() else root / candidate

        return cls(
            root=root,
            language_a=str(project["language_a"]),
            language_b=str(project["language_b"]),
            game_a=resolve(paths["game_a"]),
            game_b=resolve(paths["game_b"]),
            mod_a=resolve(paths["mod_a"]),
            mod_b=resolve(paths["mod_b"]),
            translation=resolve(paths["translation"]),
            update=resolve(paths["update"]),
            stage=resolve(paths["stage"]),
            output=resolve(paths["output"]),
            oodle=resolve(paths["oodle"]),
            archives={str(name): str(stem) for name, stem in archives.items()},
        )
