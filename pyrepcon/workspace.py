from __future__ import annotations

import pathlib
import os
from typing import ClassVar, Optional, Union

import toml  # tomllib part of std lib in 3.11

import pyrepcon.git_utils
from pyrepcon.project import Project, ProjectConfig
from pyrepcon.utils import ConfigBase, switch_dir


class WorkspaceConfig(ConfigBase):
    config_dir: ClassVar[str] = ".workspace"

    mode: str = "python-poetry"


class Workspace:
    def __init__(self, root: Union[str, os.PathLike]):
        self._root = pathlib.Path(str(root)).resolve()
        self._config = WorkspaceConfig.load(self._root)
        with switch_dir(self._root):
            self._project_root = pyrepcon.git_utils.root_dir()

    @staticmethod
    def ref_to_path(
        workspace_ref: str, project_path: Optional[Union[str, os.PathLike]] = None
    ) -> pathlib.Path:
        if project_path is None:
            project_path = pyrepcon.git_utils.root_dir()
        else:
            project_path = pathlib.Path(project_path)
        project_config = ProjectConfig.load(project_path)
        rel_path_to_workspace = getattr(project_config.workspaces, workspace_ref)
        abs_path_to_workspace = (
            project_path / project_config.development_dir / rel_path_to_workspace
        )
        return abs_path_to_workspace

    @classmethod
    def from_reference(
        cls, workspace_ref: str, project_path: Optional[Union[str, os.PathLike]] = None
    ) -> Workspace:
        workspace_path = cls.ref_to_path(workspace_ref, project_path)
        return cls(workspace_path)

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @property
    def project_root(self) -> pathlib.Path:
        return self._project_root

    @property
    def loc_in_project(self) -> pathlib.Path:
        return self.root.relative_to(self.project_root)

    @property
    def config(self) -> WorkspaceConfig:
        return self._config

    def exists(self) -> bool:
        return self.root.is_dir()

    def create_from_template(self, template):
        pass  # TODO

    def get_version(self, git_ref: Optional[str] = None) -> str:
        """Returns version string associated with workspace."""
        with pyrepcon.git_utils.checkout(git_ref):

            if self.config.mode == "python-poetry":
                with (self.root / "pyproject.toml").open("r") as file:
                    conf = toml.load(file)
                return conf["tool"]["poetry"]["version"]
            elif self.config.mode == "julia":
                with (self.root / "project.toml").open("r") as file:
                    conf = toml.load(file)
                return conf["version"]
            elif self.config.mode == "R":
                with (self.root / "DESCRIPTION").open("r") as file:
                    conf = file.readlines()
                version_line = [line for line in conf if "Version:" in line]
                version_line = version_line[0]
                return version_line.strip().split(":")[1]
            else:
                raise NotImplementedError(f"Unknown mode: {self.config.mode}")

    def checkout(self, commit: str, dest: Union[str, os.PathLike] = ".") -> None:
        pyrepcon.git_utils.checkout_workspace(commit, self.root, dest)
