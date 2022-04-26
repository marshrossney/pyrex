from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import logging
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Union

from pyrepcon.experiment import COMMAND_FILE, ExperimentConfig, InvalidExperimentError
import pyrepcon.utils as utils
from pyrepcon.utils import GitError

log = logging.getLogger(__name__)


_CONFIG_FILE = ".pyrex.json"


class InvalidWorkspaceError(Exception):
    pass


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


class Workspace:
    """Class acting as a container for pyrex operations."""

    def __init__(self, root: Union[str, os.PathLike] = "."):
        self._root = pathlib.Path(root).resolve()
        self._config = self._root / _CONFIG_FILE
        self._validate()

    def _validate(self):
        if not self._root.exists():
            raise InvalidWorkspaceError(f"{self._root} does not exist!")
        if not self._root.is_dir():
            raise InvalidWorkspaceError(f"{self._root} is not a directory!")
        try:
            _ = self.load_config()
        except FileNotFoundError:
            raise InvalidWorkspaceError(f"{self._config} not found")

    @classmethod
    def init(
        cls,
        path: Union[str, os.PathLike] = ".",
    ) -> Workspace:
        path = pathlib.Path(path)
        path.mkdir(parents=True, exist_ok=True)
        WorkspaceConfig().dump(path / _CONFIG_FILE)
        return cls(path)

    @classmethod
    def search_parents(cls, path: Union[str, os.PathLike] = "."):
        path = pathlib.Path(path).resolve()
        search_dir = path
        user = pathlib.Path.home()
        while search_dir.parent.is_relative_to(user):  # don't go past user
            if (search_dir / _CONFIG_FILE).exists():
                return cls(search_dir)
            search_dir = search_dir.parent

        raise InvalidWorkspaceError(
            "{_CONFIG_FILE} not found in {path} or any of its parents"
        )

    @property
    def root(self) -> pathlib.Path:
        """Path to the root directory of the workspace."""
        return self._root

    @property
    def config_file(self) -> pathlib.Path:
        """Path to the workspace configuration file."""
        return self._config

    @property
    def project_root(self) -> Union[pathlib.Path, None]:
        """Path to the root directory of the entire project.

        This is also the git working tree, and contains the repository."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--show-toplevel"
            )
        except GitError:
            return None
        else:
            return pathlib.Path(result.strip()).resolve()

    @property
    def git_dir(self) -> Union[pathlib.Path, None]:
        """Path to the git repository, usually called '.git/'."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--git-dir"
            )
        except GitError:
            return None
        else:
            return pathlib.Path(result.strip()).resolve()

    @property
    def version(self) -> str:
        return self._get_version()

    def _get_branch(self) -> str:
        """Attempts to extract the name of the current branch of the repo.

        Returns an empty string if the project is not in a git working tree."""
        try:
            result = utils.run_command(
                "-C", str(self._root), "rev-parse", "--abbrev-ref", "HEAD"
            )
        except GitError:
            return ""
        else:
            return result.strip()

    def _get_commit(self) -> str:
        """Get commit SHA-1 associated with current HEAD"""
        result = utils.git_run_command("-C", str(self._root), "rev-parse", "HEAD")
        return result.strip()

    def _get_version(self) -> str:
        """Get the version."""
        config = self.load_config()
        if config.version_command is not None:
            with utils.switch_dir(self._root):
                result = subprocess.run(
                    config.version_command, capture_output=True, text=True, check=True
                )
            version = result.stdout.strip("\n")
            return version
        else:
            return str(config.version)

    def load_config(self) -> WorkspaceConfig:
        return WorkspaceConfig.load(self._config)

    def get_default_experiment_path(
        self, experiment_name: Optional[str] = None
    ) -> pathlib.Path:
        config = self.load_config()
        path = (
            config.named_experiments_path
            if experiment_name
            else config.unnamed_experiments_path
        )
        # NOTE: should I slugify these?
        if "{branch}" in path:
            path = path.replace("{branch}", self._get_branch())
        if "{version}" in path:
            path = path.replace("{version}", self._get_version())
        if "{name}" in path:
            path = path.replace("{name}", experiment_name or "")
        if "{timestamp}" in path:
            path = path.replace("{timestamp}", utils.timestamp())
        return self._root.joinpath(*path.split("/"))

    def parse_command(self, command: str) -> str:
        if "{commit}" in command:
            command = command.replace("{commit}", self._get_commit())
        return command

    def create_experiment(
        self,
        experiment_config: ExperimentConfig,
        path: Union[str, pathlib.Path],
    ) -> None:
        path.mkdir(parents=True, exist_ok=False)

        # Copy files
        for file in experiment_config.working_dir:
            src = (self._root / file).resolve()  # resolves symlinks
            if not src.exists():
                raise InvalidExperimentError(
                    f"Failed to copy '{src}' - it does not exist!"
                )
            dest = path / file
            dest.parent.mkdir(exist_ok=True, parents=True)
            if src.is_file():
                shutil.copy(src, dest)
            elif src.is_dir():
                log.info("Symbolic links are ignored when copying directories!")
                shutil.copytree(src, dest)

        # Create file with command
        command = self.parse_command(experiment_config.command)
        with (path / COMMAND_FILE).open("w") as file:
            file.write(command)

        # Create .gitignore which excludes everything except these files
        gitignore = experiment_config.gitignore()
        with (path / ".gitignore").open("w") as file:
            file.write(gitignore)

    def create_named_experiment(
        self,
        name: str,
        path: Optional[Union[str, pathlib.Path]] = None,
    ) -> pathlib.Path:
        config = self.load_config()
        try:
            experiment_config = config.named_experiments[name]
        except AttributeError:
            raise InvalidExperimentError(
                "'{name}' is not an existing named experiment.\nOptions are {list(config.named_experiments.keys())}"
            )

        # If no path set explicitly by user, construct path from default
        path = (
            pathlib.Path(path)
            if path is None
            else self.get_default_experiment_path(name)
        )
        self.experiment(experiment_config, path)

        return path
