from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import pathlib
import shlex
import subprocess
from typing import Optional, Union

import click
from cookiecutter.main import cookiecutter
import yaml

from pyrex.exceptions import (
    GitError,
    CookiecutterException,
    InvalidTemplateError,
    InvalidWorkspaceError,
)
import pyrex.utils

log = logging.getLogger(__name__)

WORKSPACE_CONFIG_FILE = ".pyrex_workspace.yaml"
EXPERIMENT_CONFIG_FILE = ".pyrex_experiment.yaml"
WORKSPACE_TEMPLATES_FILE = str(
    pathlib.Path(__file__).parent.joinpath("templates/workspaces.yaml")
)
EXPERIMENT_TEMPLATES_FILE = str(
    pathlib.Path(__file__).parent.joinpath("templates/experiments.yaml")
)


@dataclasses.dataclass
class AuthorConfig:
    name: Union[str, None]
    email: Union[str, None]

    @classmethod
    def detect(cls, where: Union[str, os.PathLike] = ".") -> AuthorConfig:
        try:
            name = pyrex.utils.git_run_command("config", "user.name", where=where)
            email = pyrex.utils.git_run_command("config", "user.email", where=where)
        except GitError as exc:
            log.warning("Failed to detect git author information!")
            log.info("The following error was raised: %r" % exc)
            return cls(name=None, email=None)
        else:
            return cls(name=name, email=email)


@dataclasses.dataclass
class RepoConfig:
    root: Union[str, None]
    name: Union[str, None]
    branch: Union[str, None]
    commit: Union[str, None]

    @classmethod
    def detect(cls, where: Union[str, os.PathLike] = ".") -> RepoConfig:
        try:
            root = pyrex.utils.git_run_command(
                "rev-parse", "--show-toplevel", where=where
            )
        except GitError as exc:
            log.warning("Location '%s' is not inside a git repository!" % where)
            log.info("The following error was raised: %r" % exc)
            return cls(root=None, name=None, branch=None, commit=None)
        else:
            name = pathlib.Path(root).name
            branch = pyrex.utils.git_run_command(
                "rev-parse", "--abbrev-ref", "HEAD", where=where
            )
            commit = pyrex.utils.git_run_command("rev-parse", "HEAD", where=where)
            return cls(root=root, name=name, branch=branch, commit=commit)


# ------------------------------------------------------------------------- #
#                              Data classes                                 #
# ------------------------------------------------------------------------- #


@dataclasses.dataclass
class ExperimentConfig:
    files: list[str]
    commands: list[str]
    title: str = dataclasses.field(default_factory=str)
    description: str = dataclasses.field(default_factory=str)
    template: Optional[str, dict] = None
    output_path: Optional[str] = None


@dataclasses.dataclass
class TemplateConfig:
    template: str
    checkout: Optional[str] = None
    directory: Optional[str] = None

    def validate(self) -> None:
        return
        try:
            with pyrex.utils.temp_dir():
                cookiecutter(
                    template=self.template,
                    checkout=self.checkout,
                    directory=self.directory,
                    no_input=True,
                    overwrite_if_exists=True,
                )
        except CookiecutterException as exc:
            raise InvalidTemplateError(
                "Cookiecutter failed to generate this template"
            ) from exc
        else:
            click.echo("Template seems to work!")


@dataclasses.dataclass
class WorkspaceConfig:
    version: str
    experiments_file: str
    experiments_output_path: str
    experiments_template: Union[str, dict]

    def __post_init__(self) -> None:
        try:
            _ = float(self.version)
        except ValueError:
            self.version = subprocess.run(
                shlex.split(self.version),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        else:
            self.version = str(self.version)


# ------------------------------------------------------------------------- #
#                           Config Collections                              #
# ------------------------------------------------------------------------- #


class HomogeneousConfigCollection:
    config_class: dataclasses.dataclass
    illegal_keys: list = []

    def __init__(
        self, config_file: Union[str, os.PathLike], **elements: dict[str, dict]
    ) -> None:
        self._config_file = config_file
        self._elements = elements

    def __str__(self) -> str:
        return yaml.safe_dump(self._elements, indent=4)

    def __len__(self) -> int:
        return len(self._elements)

    def __contains__(self, key: str) -> bool:
        return key in self._elements

    def __getitem__(self, key: str) -> dataclasses.dataclass:
        return self.config_class(**self._elements[key])

    def __setitem__(self, key: str, value: dataclasses.dataclass) -> None:
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

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    @property
    def keys(self) -> list:
        return list(self._elements.keys())

    @property
    def filepath(self) -> pathlib.Path:
        return pathlib.Path(self._filepath).resolve()

    def asdict(self) -> dict:
        return self._elements.copy()

    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> ExperimentConfigCollection:
        contents = pyrex.utils.load_config(filepath, loader=yaml.safe_load)
        return cls(config_file=filepath, **contents)

    def dump(self) -> None:
        pyrex.utils.dump_config(
            self.asdict(),
            self._config_file,
            dumper=lambda c: yaml.safe_dump(c, indent=4),
        )


class ExperimentConfigCollection(HomogeneousConfigCollection):
    config_class = ExperimentConfig


class WorkspaceTemplateConfigCollection(HomogeneousConfigCollection):
    config_class = TemplateConfig

    @classmethod
    def load(cls) -> WorkspaceTemplateConfigCollection:
        return super().load(WORKSPACE_TEMPLATES_FILE)


class ExperimentTemplateConfigCollection(HomogeneousConfigCollection):
    config_class = TemplateConfig

    @classmethod
    def load(cls) -> ExperimentTemplateConfigCollection:
        return super().load(EXPERIMENT_TEMPLATES_FILE)


# ------------------------------------------------------------------------- #
#                           Input/Output Files                              #
# ------------------------------------------------------------------------- #


@dataclasses.dataclass
class ExperimentSummary:
    author: AuthorConfig
    experiment: ExperimentConfig
    repo: RepoConfig
    workspace: WorkspaceConfig  # NOTE: actually WorkspaceInput!!!
    path_to_workspace_root: str
    path_to_repo_root: str
    timestamp: str = dataclasses.field(init=False)
    date: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        for field, cls in zip(
            ("author", "experiment", "repo", "workspace"),
            (AuthorConfig, ExperimentConfig, RepoConfig, WorkspaceConfig),
        ):
            if not isinstance(getattr(self, field), cls):
                setattr(self, field, cls(**field))
                # NOTE: this is a bit unsatisfactory

        ts = datetime.datetime.now()
        self.timestamp = ts.strftime("%y%m%dT%H%M%S")
        self.date = ts.strftime("%a %b %m %Y")

    def __str__(self) -> str:
        return "\n".join(
            [
                "Experiment Summary",
                "==================",
                yaml.safe_dump(dataclasses.asdict(self), indent=4),
            ]
        )

    @classmethod
    def load(cls, experiment_root: Union[str, os.PathLike]) -> ExperimentConfig:
        return cls(
            **pyrex.utils.load_config(
                pathlib.Path(experiment_root.joinpath(EXPERIMENT_CONFIG_FILE))
            )
        )

    def dump(self, experiment_root: Union[str, os.PathLike]) -> None:
        pyrex.utils.dump_config(
            dataclasses.asdict(self),
            pathlib.Path(experiment_root).joinpath(EXPERIMENT_CONFIG_FILE),
            dumper=lambda c: yaml.safe_dump(c, indent=4),
        )


@dataclasses.dataclass
class WorkspaceInput(WorkspaceConfig):
    config_file: str
    root: str = dataclasses.field(init=False)
    name: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        root = pathlib.Path(self.config_file).resolve().parent
        self.root = str(root)
        self.name = root.name

    def __str__(self) -> str:
        return yaml.safe_dump(dataclasses.asdict(self), indent=4)

    @classmethod
    def load(cls, workspace_root: Union[str, os.PathLike]) -> WorkspaceInput:
        root = pathlib.Path(workspace_root).resolve()
        config_file = root.joinpath(WORKSPACE_CONFIG_FILE)
        return cls(config_file=str(config_file), **pyrex.utils.load_config(config_file))

    @classmethod
    def load_from_pyproject(
        cls, workspace_root: Union[str, os.PathLike]
    ) -> WorkspaceInput:
        raise NotImplementedError

    @classmethod
    def search_parents(
        cls,
        start_path: Union[str, os.PathLike] = ".",
        filename: str = WORKSPACE_CONFIG_FILE,
    ) -> WorkspaceInput:

        start_path = pathlib.Path(start_path).resolve()
        search_dir = start_path
        user = pathlib.Path.home()
        while search_dir.parent.is_relative_to(user):  # don't go past user
            if search_dir.joinpath(WORKSPACE_CONFIG_FILE).exists():
                return cls.load(search_dir)
            elif search_dir.joinpath("pyproject.toml").exists():
                try:
                    return cls.load_from_pyproject(search_dir)
                except Exception:
                    pass
            search_dir = search_dir.parent

        raise InvalidWorkspaceError(
            f"Neither '{start_path}' nor any of its parents contain a PyREx workspace configuration file"
        )

    def get_experiments(self) -> ExperimentConfigCollection:
        return ExperimentConfigCollection.load(
            pathlib.Path(self.root).joinpath(self.experiments_file)
        )
