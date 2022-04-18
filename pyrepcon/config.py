from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import pathlib
from typing import ClassVar

PROJECT_CONFIG_DIR = ".project"
WORKSPACE_CONFIG_DIR = ".workspace"
EXPERIMENT_CONFIG_DIR = ".experiment"

Path: TypeAlias = pathlib.Path
PathLike: TypeAlias = str | os.PathLike


class _ConfigBase:
    _config_dir: ClassVar[str]

    @classmethod
    def load(cls, path: PathLike):
        """Load config from existing project/workspace/experiment."""
        with (pathlib.Path(path) / self._config_dir / "config.json") as file:
            config = json.load(file)
        return cls(**config)

    def dump(self, path: PathLike):
        """Dump config to json file."""
        with (pathlib.Path(path) / self._config_dir / "config.json") as file:
            json.dump(asdict(self), file, indent=6)


# NOTE: don't validate workspaces since they might exist on different branch
@dataclass(kw_only=True)
class ProjectConfig(_ConfigBase):
    _config_dir: ClassVar[str] = PROJECT_CONFIG_DIR

    development_branch: str = "dev"
    experiments_branch: str = "exp"
    publication_branch: str = "pub"
    development_dir: str = "workspaces"
    experiments_dir: str = "experiments"
    publication_dir: str = "results"

    workspaces: dict[str, str] = {}


@dataclass(kw_only=True)
class WorkspaceConfig(_ConfigBase):
    _config_dir: ClassVar[str] = WORKSPACE_CONFIG_DIR

    mode: str = "python-poetry"


@dataclass(kw_only=True)
class ExperimentConfig(_ConfigBase):
    _config_dir: ClassVar[str] = EXPERIMENT_CONFIG_DIR

    workspace: str
    reference: str
    command: list[str]
