from __future__ import annotations

import datetime
import pathlib
import os
import subprocess
from typing import TypeAlias

import toml # NOTE tomllib part of standard lib as of Python 3.11

import repcon.config
import repcon.git_utils

PathLike: TypeAlias = str | os.PathLike

def now():
    return datetime.datetime.now().strftime("%G%m%dT%H%M%S")  # ISO 8601 basic

def parse_workspace(workspace: str) -> pathlib.Path:
    """..."""
    workspace_as_path = pathlib.Path(workspace)
    if workspace_as_path.is_dir():
        # don't check for .workspace/ dir since may not be necessary
        return workspace_as_path.resolve()

    project_root = repcon.git_utils.root_dir()
    project_config = repcon.config.ProjectConfig.load(project_root)
    rel_path_to_workspace = getattr(project_config.workspaces, workspace)
    abs_path_to_workspace = (
        project_root / project_config.development_dir / rel_path_to_workspace
    )
    return abs_path_to_workspace


def get_workspace_version(workspace: str, reference: str | None = None) -> str:
    """Returns version string associated with workspace."""
    workspace_root = parse_workspace(workspace)
    with repcon.git_utils.checkout(reference):
        workspace_config = repcon.config.WorkspaceConfig.load(workspace_root)
        mode = workspace_config.mode

        if mode == "python-poetry":
            with (workspace_root / "pyproject.toml").open("r") as file:
                conf = toml.load(file)
            version = conf["tool"]["poetry"]["version"]
        elif mode == "julia":
            with (workspace_root / "project.toml").open("r") as file:
                conf = toml.load(file)
            version = conf["version"]
        elif mode == "R":
            with (workspace_root / "DESCRIPTION").open("r") as file:
                conf = file.readlines()
            version_line = [line in conf if "Version:" in line]
            version_line = version_line[0]
            version = version_line.strip().split(":")[1]

    return version

class switch_dir:
    """Context manager for changing to *existing* directory."""

    def __init__(self, path: PathLike):
        self.new = pathlib.Path(path)
        assert self.new.is_dir()

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.new)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.old)

class create_and_enter_dir:
    """Create and enter new directory, cleaning up if an exception is raised."""

    def __init__(self, path: PathLike, cleanup_if_exception):
        self.target = pathlib.Path(path)

    def __enter__(self):
        self.current = pathlib.Path.cwd()
        self.target.mkdir(parents=True, exist_ok=False)
        os.chdir(self.target)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            os.chdir(self.current)
