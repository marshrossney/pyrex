from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import cached_property
import json
import pathlib
import os
from typing import ClassVar, Union

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


@dataclass
class WorkspaceConfig(BaseConfig):
    filename: ClassVar[str] = ".workspace.json"

    get_version: str

@dataclass
class ExperimentConfig(BaseConfig):
    filename: ClassVar[str] = "experiment.json"

    workspace: str
    commit: str
    commands: list[str]

