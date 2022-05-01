from __future__ import annotations

import dataclasses
import json
import logging
import os
import pathlib
from typing import Optional, Union

import yaml

from pyrex.exceptions import InvalidExperimentError

# TODO allow yaml - nicer to read - by making WorkspaceConfig/ExperimentConfig factory functions

log = logging.getLogger(__name__)

WORKSPACE_CONFIG_FILE: str = ".pyrex_workspace.json"


@dataclasses.dataclass
class JSONConfigFile:
    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> JSONConfigFile:
        with open(filepath, "r") as file:
            contents = json.load(file)
        return cls(**contents)

    def dump(self, filepath: Union[str, os.PathLike]) -> None:
        contents = dataclasses.asdict(self)
        try:
            _ = json.dumps(contents)
        except (TypeError, OverflowError) as exc:
            raise Exception(
                "Object is not JSON serializable. Abandoning the write!"
            ) from exc
        else:
            with open(filepath, "w") as file:
                json.dump(contents, file, indent=6)


@dataclasses.dataclass
class YAMLConfigFile:
    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> JSONConfigFile:
        with open(filepath, "r") as file:
            contents = yaml.safe_load(file)
        return cls(**contents)

    def dump(self, filepath: Union[str, os.PathLike]) -> None:
        contents = dataclasses.asdict(self)
        try:
            _ = yaml.safe_dump(contents)
        except (TypeError, OverflowError) as exc:
            raise exc("Object is not JSON serializable. Abandoning the write!")
        else:
            with open(filepath, "w") as file:
                yaml.safe_dump(contents, file)


@dataclasses.dataclass
class ExperimentConfig:
    command: str
    output_path: str
    required_files: list[str]
    commit: Optional[str] = None

    def __post_init__(self):
        self.command = self.command.strip()
        if not self.command:  # catches empty string
            raise InvalidExperimentError("'command' must be specified")

        paths = [pathlib.Path(file) for file in self.required_files]
        if any([path.is_absolute() for path in paths]):
            raise InvalidExperimentError(
                "Experiment config should not contain absolute paths"
            )
        if any([".." in path.parts for path in paths]):
            raise InvalidExperimentError(
                "Paths containing '../' are not allowed in the experiment config"
            )
        # Remove duplicates
        self.required_files = list(set(self.required_files))

    def gitignore(self) -> str:
        dont_ignore = [
            ".gitignore",
            "README.*",
            WORKSPACE_CONFIG_FILE,
        ] + self.required_files
        return "*\n" + "\n!".join(dont_ignore)

    def readme(self) -> None:
        return "\n".join(
            [f"Commit: {self.commit or 'not provided!'}" f"Command: {self.command}"]
        )

    def __str__(self) -> str:
        return json.dumps(dataclasses.asdict(self), indent=4)


@dataclasses.dataclass
class WorkspaceConfig(JSONConfigFile):

    workspace_root: str
    version_command: str
    experiments: dict[str, ExperimentConfig]

    def __post_init__(self):
        self.experiments = {
            name: config
            if type(config) is ExperimentConfig
            else ExperimentConfig(**config)
            for name, config in self.experiments.items()
        }
