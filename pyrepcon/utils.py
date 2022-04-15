from __future__ import annotations

import pathlib
import os
import subprocess
from typing import TypeAlias

PathLike: TypeAlias = str | os.PathLike


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
