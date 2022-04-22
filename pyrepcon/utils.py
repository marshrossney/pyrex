from __future__ import annotations

from dataclasses import dataclass, asdict
import datetime
import json
import pathlib
import os
from typing import ClassVar, Union


def curr_datetime():
    return datetime.datetime.now().strftime("%G%m%dT%H%M%S")  # ISO 8601 basic

def load_module_from_path(path: Union[str, os.PathLike]):
    assert path.is_file(), f"{path} does not exist"
    spec = importlib.util.spec_from_file_location(path.stem, str(path.resolve()))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class switch_dir:
    """Context manager for changing to *existing* directory."""

    def __init__(self, path: Union[str, os.PathLike]):
        self.new = pathlib.Path(path)
        assert self.new.is_dir()

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.new)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.old)


"""class create_and_enter_dir:

    def __init__(self, path: Union[str, os.PathLike], cleanup_if_exception: bool):
        self.target = pathlib.Path(path)

    def __enter__(self):
        self.current = pathlib.Path.cwd()
        self.target.mkdir(parents=True, exist_ok=False)
        os.chdir(self.target)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            os.chdir(self.current)
"""

def get_version(workspace: pyrepcon.workspace.Workspace):
    """Very hacky way to get version strings. Needs to be more flexible."""
    template = workspace.config.template
    if template == "python-poetry":
        import toml
        with (workspace.root / "pyproject.toml").open("r") as file:
            spec = toml.load(file)
        return spec["tool"]["poetry"]["version"]
    elif template == "julia":
        import toml
        with (workspace.root / "project.toml").open("r") as file:
            spec = toml.load(file)
        return spec["version"]
    elif template == "R":
        with (workspace.root / "DESCRIPTION").open("r") as file:
            spec = file.readlines()
        version_line = [line for line in spec if "Version:" in line]
        version_line = version_line[0]
        return version_ine.strip().split(":")[1]
    else:
        raise NotImplementedError(f"Unknown template: {template}")


