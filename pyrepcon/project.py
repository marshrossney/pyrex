"""Class that acts as Python interface to a git project / repo.
"""
from __future__ import annotations

from functools import wraps
import pathlib
import os
from typing import ClassVar, Union

import pyrepcon.git_utils
from pyrepcon.utils import ConfigBase, switch_dir


PROJECT_CONFIG_DIR = ".project"


class ProjectConfig(ConfigBase):
    config_dir: ClassVar[str] = PROJECT_CONFIG_DIR

    development_branch: str = "dev"
    experiments_branch: str = "exp"
    publication_branch: str = "pub"
    development_dir: str = "workspaces"
    experiments_dir: str = "experiments"
    publication_dir: str = "key_results"


def in_root_dir(meth):
    @wraps(meth)
    def wrapper(self, *args, **kwargs):
        with switch_dir(self.root):
            result = meth(*args, **kwargs)
        return result

    return wrapper


class Project:
    """Class representing version-controlled project."""

    def __init__(self, root: Union[str, os.PathLike]):
        self._root = pathlib.Path(str(root)).resolve()
        self._config = ProjectConfig.load(self._root)
        self._workspaces_list = self._root / PROJECT_CONFIG_DIR / "workspaces.txt"

    @staticmethod
    def is_valid(project_root: Union[str, os.PathLike]) -> bool:
        project_root = pathlib.Path(str(project_root))
        required_dirs = [
            project_root,
            (project_root / ".git"),
            (project_root / PROJECT_CONFIG_DIR),
        ]
        valid = True
        for d in required_dirs:
            if not d.exists():
                print(f"Missing directory: {d}")
                valid = False
        if valid:
            try:
                _ = ProjectConfig.load(project_root)
            except FileNotFoundError:
                print("Unable to load configuration")
                valid = False
        return valid

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @property
    def config(self) -> ProjectConfig:
        return self._config

    @property
    @in_root_dir
    def is_dirty(self) -> bool:
        return pyrepcon.git_utils.is_dirty()

    @property
    def workspaces(self) -> list[str]:
        with self._workspaces_list.open("r") as file:
            lines = file.readlines()
        return [line.strip("\n") for line in lines]

    def add_workspace(self, path: Union[str, os.PathLike]) -> None:
        assert path.is_dir(), "{path} is not a directory!"
        rel_path = pathlib.Path(str(path)).relative_to(self.root)
        with self._workspaces_list.open("r") as file:
            file.write(str(rel_path) + "\n")

    def create_from_template(self, template):
        pass  # TODO
