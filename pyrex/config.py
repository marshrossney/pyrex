from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import pathlib
from typing import Callable, Optional, Union

import yaml

import pyrex.data
from pyrex.exceptions import InvalidConfigError, InvalidWorkspaceError

log = logging.getLogger(__name__)

INPUT_CONFIG_FILE = ".pyrex_workspace.yaml"
OUTPUT_CONFIG_FILE = ".pyrex_experiment.yaml"
WORKSPACE_TEMPLATES_FILE = pathlib.Path(__file__).parent.joinpath(
    "templates/workspaces.yaml"
)
EXPERIMENT_TEMPLATES_FILE = pathlib.Path(__file__).parent.joinpath(
    "templates/experiments.yaml"
)


@dataclasses.dataclass
class Config:
    def __str__(self) -> str:
        return yaml.safe_dump(dataclasses.asdict(self), indent=4)

    @staticmethod
    def _get_loader_and_dumper(
        filepath: Union[str, os.PathLike]
    ) -> tuple[Callable, Callable]:
        filepath = pathlib.Path(filepath)
        if filepath.suffix in (".yml", ".yaml"):
            import yaml

            return (yaml.safe_load, lambda x: yaml.safe_dump(x, indent=4))
        elif filepath.suffix == ".json":
            import json

            return (json.load, lambda x: json.dumps(x, indent=4))
        elif filepath.suffix == ".toml":
            import toml

            return (toml.load, toml.dumps)
        else:
            raise InvalidConfigError(f"Invalid file extension: '{filepath.suffix}'")

    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> dict:
        loader, _ = cls._get_loader_and_dumper(filepath)
        try:
            with open(filepath, "r") as file:
                contents = loader(file)
        except Exception as exc:
            raise InvalidConfigError(
                f"Failed to load config from '{filepath}'"
            ) from exc
        else:
            if not contents:
                log.warning("Loaded an empty configuration file from %s" % filepath)
            contents["config_file"] = str(filepath)
            return cls(**contents)

    def dump(self, filepath: Union[str, os.PathLike]) -> None:
        _, dumper = self._get_loader_and_dumper(filepath)
        contents = self.asdict()
        try:
            contents_str = dumper(contents)
        except (TypeError, OverflowError) as exc:
            raise InvalidConfigError(
                "Data serialization failed! Config will *not* be written to file."
            ) from exc
        else:
            if not contents:
                log.warning("Dumping an empty configuration to %s" % filepath)
            with open(filepath, "w") as file:
                file.write(contents_str)

    def asdict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class InputConfig(pyrex.data.Workspace, Config):

    config_file: str
    root: Optional[str] = dataclasses.field(default=None, init=False)
    name: Optional[str] = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        root = pathlib.Path(self.config_file).resolve().parent
        self.root = str(root)
        self.name = root.name

    @classmethod
    def load(cls, workspace_root: Union[str, os.PathLike]) -> InputConfig:
        return super().load(pathlib.Path(workspace_root).joinpath(INPUT_CONFIG_FILE))

    @classmethod
    def search_parents(
        cls, start_path: Union[str, os.PathLike] = "."
    ) -> tuple[InputConfig, pathlib.Path]:

        start_path = pathlib.Path(start_path).resolve()
        search_dir = start_path
        user = pathlib.Path.home()
        while search_dir.parent.is_relative_to(user):  # don't go past user
            if search_dir.joinpath(INPUT_CONFIG_FILE).exists():
                return cls.load(search_dir)
            search_dir = search_dir.parent

        raise InvalidWorkspaceError(
            f"Neither '{start_path}' nor any of its parents contain the file '{INPUT_CONFIG_FILE}'"
        )


@dataclasses.dataclass
class OutputConfig(Config):
    author: pyrex.data.Author
    experiment: pyrex.data.Experiment
    path: pyrex.data.Path
    repository: pyrex.data.Repository
    workspace: pyrex.data.Workspace
    timestamp: str = dataclasses.field(init=False)
    date: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        ts = datetime.datetime.now()
        self.timestamp = ts.strftime("%y%m%dT%H%M%S")
        self.date = ts.strftime("%a %b %m %Y")

    @classmethod
    def load(cls, workspace_root: Union[str, os.PathLike]) -> InputConfig:
        raise NotImplementedError  # TODO reload from existing exp
        # contents = super().load(
        #    pathlib.Path(workspace_root).joinpath(OUTPUT_CONFIG_FILE)
        # )

    def dump(self, experiment_dir: Union[str, os.PathLike]) -> None:
        super().dump(pathlib.Path(experiment_dir).joinpath(OUTPUT_CONFIG_FILE))


class HomogeneousConfigCollection(Config):
    config_class: Config = Config
    illegal_keys: list = []

    def __init__(self, config_file: str, **elements: dict[str, dict]) -> None:
        self._elements = elements

    def __str__(self) -> str:
        return yaml.safe_dump(self._elements, indent=4)

    def __len__(self) -> int:
        return len(self._elements)

    def __contains__(self, key: str) -> bool:
        return key in self._elements

    def __getitem__(self, key: str) -> Config:
        return self.config_class(**self._elements[key])

    def __setitem__(self, key: str, value: Config) -> None:
        if type(key) is not str:
            raise TypeError("Key should be a string")
        if type(value) is not self.config_class:
            raise TypeError(f"Value should be an intance of '{self.config_class}'")

        slug = key.replace(" ", "-")  # really don't want crappy keys
        if slug != key:
            log.info("Simplified %s --> %s" % (key, slug))
            key = slug

        if key in self.illegal_keys:
            raise KeyError(f"Illegal key: '{key}'")
        if key in self:
            raise KeyError(f"An element with key '{key}' already exists!")

        value = dataclasses.asdict(value)
        self._elements.update({key: value})

    def __delitem__(self, key) -> None:
        del self._elements[key]

    def keys(self) -> list:
        return list(self._elements.keys())

    def asdict(self) -> dict:
        return self._elements.copy()


class WorkspaceTemplatesCollection(HomogeneousConfigCollection):
    config_class = pyrex.data.Template

    @classmethod
    def load(cls) -> WorkspaceTemplatesCollection:
        return super().load(WORKSPACE_TEMPLATES_FILE)

    def dump(self) -> None:
        super().dump(WORKSPACE_TEMPLATES_FILE)


class ExperimentTemplatesCollection(HomogeneousConfigCollection):
    config_class = pyrex.data.Template

    @classmethod
    def load(cls) -> TemplatesCollection:
        return super().load(EXPERIMENT_TEMPLATES_FILE)

    def dump(self) -> None:
        super().dump(EXPERIMENT_TEMPLATES_FILE)


class ExperimentsCollection(HomogeneousConfigCollection):
    config_class = pyrex.data.Experiment
