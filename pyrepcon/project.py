"""Class that acts as Python interface to a git project / repo.
"""
from __future__ import annotations

from distutils.util import strtobool
from functools import wraps
import os
import pathlib
import subprocess
from typing import TypeAlias

from utils import switch_dir
from git_utils import

Path: TypeAlias = pathlib.Path
PathLike: TypeAlias = str | os.PathLike
CalledProcessError: TypeAlias = subprocess.CalledProcessError

def in_root_dir(meth):
    @wraps(meth)
    def wrapper(self, *args, **kwargs):
        with utils.switch_dir(self.root):
            result = meth(*args, **kwargs)
        return result
    return wrapper

class Project:
    """Class representing version-controlled project.
    """
    def __init__(self, root: PathLike):
        self.validate(root)
        self._root = Path(str(root)).resolve()

    @staticmethod
    def validate(root: PathLike) -> None:
        root = Path(str(root)).resolve()
        assert root.exists()
        assert root.is_dir()
        assert (root / ".git").is_dir()

    @property
    def root(self) -> Path:
        return self._root

    @property
    @in_root_dir
    def is_dirty(self) -> bool:
        return git_utils.is_dirty()

    @property
    def local_branches(self) -> list[str]:
        with switch_dir(root):
            branches = git_utils.local_branches()
        return branches
