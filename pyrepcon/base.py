from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import cached_property
import json
import pathlib
import os
from typing import ClassVar, Union

import pyrepcon.git_utils


@dataclass
class BaseConfig:
    filename: ClassVar[str]

    @classmethod
    def load(cls, path: Union[str, os.PathLike]):
        """Load config from existing project/workspace/experiment."""
        with (pathlib.Path(path) / cls.filename).open("r") as file:
            config = json.load(file)
        return cls(**config)

    def dump(self, path: Union[str, os.PathLike]):
        """Dump config to json file."""
        with (pathlib.Path(path) / self.filename).open("w") as file:
            json.dump(asdict(self), file, indent=6)


class Base:
    config: BaseConfig

    def __init__(self, root: Union[str, os.PathLike]):
        root = pathlib.Path(str(root)).resolve()
        self.validate(root)

        self._root = root
        self._config = type(self).config.load(root)
        self._project_root = pathlib.Path(
            pyrepcon.git_utils.git_run_command("-C", str(self.root), "rev-parse", "--show-toplevel")
        ).absolute()
        self._git_dir = pathlib.Path(
            pyrepcon.git_utils.git_run_command("-C", str(self.root), "rev-parse", "--git-dir")
        )

    @classmethod
    def validate(cls, root: pathlib.Path) -> None:
        assert root.exists(), f"'{root}' does not exist!"
        assert root.resolve().is_dir(), f"'{root}' is not a directory"
        assert (
            root / cls.config.filename
        ).exists(), f"Expected to find configuration file '{cls.config.filename}' inside '{root}', but it does not exist!"
        with pyrepcon.utils.switch_dir(root):
            assert (
                pyrepcon.git_utils.is_inside_work_tree()
            ), f"'{root}' is not inside a git repository"

    @classmethod
    def is_valid(cls, root: Union[str, os.PathLike]) -> bool:
        """Returns True if basic validation checks passed."""
        root = pathlib.Path(str(root)).resolve()
        try:
            cls.validate(root)
        except AssertionError as e:
            print(e)
            return False
        else:
            return True

    @property
    def root(self) -> pathlib.Path:
        """Path to the root directory."""
        return self._root

    @property
    def config(self) -> BaseConfig:
        """DataClass containing configuration information used by pyrepcon."""
        return self._config

    @property
    def project_root(self) -> pathlib.Path:
        """Path to the root directory of the entire project."""
        return self._project_root

    @property
    def git_dir(self) -> pathlib.Path:
        """Path to the git directory, usually '.git/'."""
        return self._git_dir
