from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import cached_property
import json
import pathlib
import os
from typing import Callable, ClassVar, Union

from slugify import slugify

import pyrepcon.git_utils
from pyrepcon.config import WorkspaceConfig, ExperimentConfig


class InvalidPathError(Exception):
    pass


class Project:
    """Class acting as a container for pyrepcon project operations."""

    def __init__(self, path: Union[str, os.PathLike] = "."):
        path = pathlib.path(str(path)).resolve()
        assert pyrepcon.git_utils.is_inside_work_tree(
            path
        ), f"'{path}' is not inside a git repository"

        self._root = pathlib.Path(
            pyrepcon.git_utils.git_run_command(
                "-C", str(path), "rev-parse", "--show-toplevel"
            )
        ).absolute()
        self._git_dir = pathlib.Path(
            pyrepcon.git_utils.git_run_command(
                "-C", str(path), "rev-parse", "--git-dir"
            )
        )

    @property
    def root(self) -> pathlib.Path:
        """Path to the root directory of the entire project."""
        return self._root

    @property
    def git_dir(self) -> pathlib.Path:
        """Path to the git directory, usually '.git/'."""
        return self._git_dir

    def get_active_workspace(self) -> Union[pathlib.Path, None]:
        """If inside workspace, returns the root of the workspace."""
        search_dir = pathlib.Path.cwd()
        while search_dir.parent.is_relative_to(self.root):
            if self._path_is_workspace(search_dir):
                return search_dir
            search_dir = search_dir.parent

    def get_active_experiment(self) -> Union[pathlib.Path, None]:
        """If inside experiment, returns the root of the experiment."""
        search_dir = pathlib.Path.cwd()
        while search_dir.parent.is_relative_to(self.root):
            if self._path_is_experiment(search_dir):
                return search_dir
            search_dir = search_dir.parent

    def new_workspace(self, path: str, template: str) -> None:
        path = self.root / path
        assert (
            not path.exists()
        ), f"Unable to create workspace at '{path}' - already exists!"
        # TODO: utils cookiecutter / template

    def new_experiment(self, template: str) -> None:
        # TODO cookiecutter
        suggestions = {}

        workspace_path = self._get_workspace_path(workspace)
        workspace_version = self._get_workspace_version(workspace_path)

        default_experiment_parent_path = workspace_path / workspace_version
        default_experiment_name = ...
    
    def _check_valid_path(self, path: pathlib.Path) -> bool:
        """Raises InvalidPathError if path not an existing child of project root."""
        assert type(path) == pathlib.Path
        if not path.exists():
            raise InvalidPathError(f"{path} does not exist!")
        if not path.absolute().is_relative_to(self.root):
            raise InvalidPathError(
                f"{path} is not part of this project (not a child of {self._root})!"
            )

    def _path_is_workspace(self, path: pathlib.Path) -> bool:
        try:
            self._check_valid_path(path / WorkspaceConfig.filename)
        except InvalidPathError as e:
            print(e)
            return False
        else:
            return True

    def _path_is_experiment(self, path: pathlib.Path) -> bool:
        try:
            self._assert_exists_and_in_project(path / ExperimentConfig.filename)
        except InvalidPathError:
            return False
        else:
            return True

    def _get_workspace_version(self, workspace_path: pathlib.Path) -> str:
        commands = WorkspaceConfig.load(workspace_path).get_version
        version = subprocess.run(
            commands, capture_output=True, text=True, check=True
        ).stdout.strip("\n")
        return slugify(version)
