from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import logging
import pathlib
import os
from typing import ClassVar, Optional, Union

from pyrepcon.utils import InvalidExperimentError, InvalidWorkspaceError

log = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    command: str
    files: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.command:
            raise InvalidExperimentError("'command' must be specified")


@dataclass
class WorkspaceConfig:
    version: str = field(default_factory=str)
    version_command: Optional[str] = None
    experiments_path: list[str] = field(default_factory=list)
    named_experiments: dict[ExperimentConfig] = field(default_factory=dict)

    def __post_init__(self):
        self.named_experiments = {
            name: ExperimentConfig(**vals)
            for name, vals in self.named_experiments.items()
        }

    @classmethod
    def load(cls, path: Union[str, os.PathLike]):
        """Load config from existing workspace."""
        with open(path, "r") as file:
            config = json.load(file)
        return cls(**config)

    def dump(self, path: Union[str, os.PathLike]):
        """Dump config to json file."""
        log.info("Saving workspace config to file: {path}")
        obj = asdict(self)
        # Check object is json serializable so we don't overwrite
        # existing config file unless it actually works
        try:
            _ = json.dumps(obj)
        except (TypeError, OverflowError):
            raise InvalidWorkspaceError(
                "Config file is not JSON serializable. Abandoning!"
            )
        else:
            with open(path, "w") as file:
                json.dump(asdict(self), file, indent=6)

    def add_named_experiment(self, name: str, command: str, files: list[str] = []):
        if name in self.named_experiments:
            raise Exception(f"{name} is already a named experiment.")
        self.named_experiments[name] = ExperimentConfig(command=command, files=files)
