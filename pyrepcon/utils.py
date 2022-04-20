from __future__ import annotations

from dataclasses import dataclass, asdict
import datetime
import json
import pathlib
import os
from typing import ClassVar, Union  # TypeAlias  Python 3.10


def curr_datetime():
    return datetime.datetime.now().strftime("%G%m%dT%H%M%S")  # ISO 8601 basic


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


class create_and_enter_dir:
    """Create and enter new directory, cleaning up if an exception is raised."""

    def __init__(self, path: Union[str, os.PathLike], cleanup_if_exception: bool):
        self.target = pathlib.Path(path)

    def __enter__(self):
        self.current = pathlib.Path.cwd()
        self.target.mkdir(parents=True, exist_ok=False)
        os.chdir(self.target)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            os.chdir(self.current)


@dataclass
class ConfigBase:
    config_dir: ClassVar[str]
    filename: ClassVar[str] = "config.json"

    @classmethod
    def load(cls, path: Union[str, os.PathLike]):
        """Load config from existing project/workspace/experiment."""
        with (pathlib.Path(path) / cls.config_dir / cls.filename) as file:
            config = json.load(file)
        return cls(**config)

    def dump(self, path: Union[str, os.PathLike]):
        """Dump config to json file."""
        with (pathlib.Path(path) / self.config_dir / self.filename) as file:
            json.dump(asdict(self), file, indent=6)
