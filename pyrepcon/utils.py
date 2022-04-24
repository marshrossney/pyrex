from __future__ import annotations

import datetime
import importlib
import pathlib
import os
from typing import Union


class InvalidWorkspaceError(Exception):
    pass


class InvalidExperimentError(Exception):
    pass


def timestamp():
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
