from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import logging
import os
import pathlib
from typing import Optional, Union

from pyrepcon.utils import InvalidExperimentError, InvalidWorkspaceError

log = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    command: str
    working_dir: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.command:
            raise InvalidExperimentError("'command' must be specified")

        working_dir = [pathlib.Path(file) for file in self.working_dir]
        if any([path.is_absolute() for path in working_dir]):
            raise InvalidExperimentError(
                "Working directory should not contain absolute paths"
            )
        if any([".." in path.parts for path in working_dir]):
            raise InvalidExperimentError(
                "Paths containing '../' are not allowed in the working directory"
            )
        if not len(self.working_dir) == len(set(self.working_dir)):
            raise InvalidExperimentError(
                "Working directory should not contain duplicates"
            )


@dataclass
class WorkspaceConfig:
    version: str = field(default_factory=str)
    version_command: Optional[str] = None
    named_experiments_path: str = field(default_factory=str)
    unnamed_experiments_path: str = field(default_factory=str)
    named_experiments: dict[ExperimentConfig] = field(default_factory=dict)

    def __post_init__(self):
        if "" in self.named_experiments.keys():
            raise InvalidExperimentError(
                "Empty string cannot be used to name an experiment"
            )
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
            log.error("config: %s" % obj)
            raise InvalidWorkspaceError(
                "Config file is not JSON serializable. Abandoning!"
            )
        else:
            with open(path, "w") as file:
                json.dump(obj, file, indent=6)

    def add_named_experiment(self, name: str, experiment_config) -> None:
        # NOTE: should slugify this
        name = str(name)  # really don't want non-string keys
        if name == "":
            raise InvalidExperimentError("Cannot name experiment with an empty string")
        if name in self.named_experiments:
            raise InvalidExperimentError(
                f"An experiment with name '{name}' already exists! Please pick a different name."
            )
        self.named_experiments[name] = experiment_config
