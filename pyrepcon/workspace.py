from __future__ import annotations

from dataclasses import dataclass
import json
import pathlib
import os
from typing import ClassVar, Optional, Union

import toml  # tomllib part of std lib in 3.11

import pyrepcon.base
import pyrepcon.git_utils
import pyrepcon.project
from pyrepcon.utils import switch_dir, get_version

with pathlib.Path(__file__).with_name("templates.json").open("r") as file:
    TEMPLATES = json.load(file)


@dataclass
class WorkspaceConfig(pyrepcon.base.BaseConfig):
    filename: ClassVar[str] = ".workspace.json"

    template: str = "python"


class Workspace(pyrepcon.base.Base):
    config = WorkspaceConfig

    @classmethod
    def new(cls, full_path: Union[str, os.PathLike], template: str) -> Workspace:
        full_path = pathlib.Path(str(full_path)).resolve()
        assert not full_path.exists(), f"{full_path} already exists!"
        try:
            template_url = getattr(TEMPLATES, template)
        except AttributeError:
            # TODO try direct url
            pass

    @property
    def experiments_dir(self) -> pathlib.Path:
        # return path to experiments dir
        # self.project.experiments_dir / self.root.relative_to(self.project.workspaces_dir)

    def new_experiment(self, name: Optional[str] = None, path: Optional[Union[str, os.PathLike]] = None) -> pyrepcon.experiment.Experiment:
        pass

    def get_version(self) -> str:
        """Returns version string associated with workspace."""
        return get_version(self)

    def checkout(self, commit: str, dest: Union[str, os.PathLike] = ".") -> None:
        pyrepcon.git_utils.checkout_workspace(commit, self.root, dest)
