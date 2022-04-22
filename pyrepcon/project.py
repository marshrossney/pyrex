"""Class that acts as Python interface to a git project / repo.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, wraps
import pathlib
import os
from typing import ClassVar, Union

import pyrepcon.base
import pyrepcon.git_utils
from pyrepcon.utils import switch_dir
import pyrepcon.workspace


@dataclass
class ProjectConfig(pyrepcon.base.BaseConfig):
    filename: ClassVar[str] = ".project.json"

    development_branch: str = "dev"
    experiments_branch: str = "exp"
    publication_branch: str = "pub"
    development_dir: str = "workspaces"
    experiments_dir: str = "experiments"
    publication_dir: str = "key_results"


class Project(pyrepcon.base.Base):
    """Class representing version-controlled project."""
    config = ProjectConfig

    def __init__(self, root: Union[str, os.PathLike]):
        super().__init__(root)
        with switch_dir(root):
            self._git_dir = pyrepcon.git_utils.git_dir()

    @classmethod
    def validate(cls, root: pathlib.Path) -> None:
        super().validate(root)
        with switch_dir(root):
            assert (
                pyrepcon.git_utils.root_dir() == root
            ), "'{root} is not the root of the git repository"

    @property
    def development_dir(self) -> pathlib.Path:
        return self.root / self.config.development_dir

    @property
    def experiments_dir(self) -> pathlib.Path:
        return self.root / self.config.experiments_dir

    @property
    def publication_dir(self) -> pathlib.Path:
        return self.root / self.config.publication_dir

    def list_workspaces(self) -> list[str]:
        workspace_config_dirs = self.development_dir.rglob(
            pyrepcon.workspace.WorkspaceConfig.filename
        )
        return [d.parent for d in workspace_config_dirs]

    def list_experiments(self, subdir):
        pass

    def get_workspace(self, workspace_name: str) -> pyrepcon.workspace.Workspace:
        return pyrepcon.workspace.Workspace(self.development_dir / workspace_name)

    def get_experiment(self, experiment_name: str) -> pyrepcon.experiment.Experiment:
        return pyrepcon.experiment.Experiment(self.experiment_dir / experiment_name)

    def new_workspace(
        self, workspace_name: str, template
    ) -> pyrepcon.workspace.Workspace:
        return pyrepcon.workspace.Workspace.new(
            self.development_dir / workspace_name, template
        )

    def new_experiment(self, workspace_name, commit):
        return pyrepcon.experiment.Experiment.new(...)
