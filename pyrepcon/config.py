from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import pathlib
import os
from typing import ClassVar, Optional, Union

from pyrepcon.utils import InvalidExperimentError


@dataclass
class ExperimentConfig:
    command: str
    files: list[str]

    def __post_init__(self):
        if not self.command:
            raise InvalidExperimentError("'command' must be specified")


@dataclass
class WorkspaceConfig:
    workspace: str
    version: str = ""
    version_command: Optional[str] = None
    experiments_path: list[str] = field(default_factory=list)
    named_experiments: dict[ExperimentConfig] = field(default_factory=dict)

    def __post_init__(self):
        self.named_experiments = {
            name: ExperimentConfig(**vals)
            for name, vals in self.named_experiments.items()
        }
        self.workspace = str(pathlib.Path(self.workspace).absolute())

    @classmethod
    def load(cls, path: Union[str, os.PathLike]):
        """Load config from existing workspace."""
        with open(path, "r") as file:
            config = json.load(file)

        # TODO should probably update workspace path in case it changed
        return cls(**config)

    def dump(self, path: Union[str, os.PathLike]):
        """Dump config to json file."""
        with open(path, "w") as file:
            json.dump(asdict(self), file, indent=6)

    def add_named_experiment(self, name: str, command: str, files: list[str] = []):
        if name in self.named_experiments:
            raise Exception(f"{name} is already a named experiment.")
        self.named_experiments[name] = ExperimentConfig(command=command, files=files)
