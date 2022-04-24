from __future__ import annotations

import logging
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Union

from pyrepcon.config import WorkspaceConfig, ExperimentConfig
import pyrepcon.utils as utils
from pyrepcon.utils import InvalidWorkspaceError, InvalidExperimentError, GitError

log = logging.getLogger(__name__)


_CONFIG_FILE = ".pyrex.json"
_COMMAND_FILE = "COMMAND.txt"


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
        path.mkdir(parents=True, exists_ok=False)
        WorkspaceConfig().dump(path / _CONFIG_FILE)
        return cls(path)

    @property
    def root(self) -> pathlib.Path:
        """Path to the root directory of the workspace."""
        return self._root

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

    def load_config(self) -> WorkspaceConfig:
        return WorkspaceConfig.load(self._config)

    def get_branch(self) -> str:
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

    def get_version(self) -> str:
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

    def _get_commit(self) -> str:
        """Get commit SHA-1 associated with current HEAD"""
        result = utils.git_run_command("-C", str(self._root), "rev-parse", "HEAD")
        return result.strip()

    def _parse_experiment_path(
        self,
        name: str,
        path: list[str],
    ) -> pathlib.Path:
        # NOTE: should I slugify these?
        if "{branch}" in path:
            path = path.replace("{branch}", self.get_branch())
        if "{version}" in path:
            path = path.replace("{version}", self.get_version())
        if "{name}" in path:
            path = path.replace("{name}", name)
        if "{timestamp}" in path:
            path = path.replace("{timestamp}", utils.timestamp())
        return self._root.joinpath(*path.split("/"))

    def _parse_command(self, command: str) -> str:
        if "{commit}" in command:
            command = command.replace("{commit}", self._get_commit())
        return command

    def new_experiment(
        self,
        name: Optional[str] = None,
        command: Optional[str] = None,
        files: Optional[list[Union[str, os.PathLike]]] = None,
        path: Optional[Union[str, os.PathLike]] = None,
    ) -> pathlib.Path:
        """Creates new experiment, returns path to experiment dir."""
        config = self.load_config()

        if name is None:
            experiment_config = ExperimentConfig(command=command, files=files)
        elif name in config.named_experiments:
            if command is not None or files is not None:
                raise InvalidExperimentError(
                    f"An experiment with name '{name}' already exists; 'command' and 'files' should not be given in this case"
                )
            experiment_config = config.named_experiments[name]
        else:
            experiment_config = ExperimentConfig(command=command, files=files or [])
            # Add to our list of named experiments
            config.named_experiments[name] = experiment_config
            config.dump(self._config)

        # If no path set explicitly by user, construct path from default
        if path is not None:
            path = pathlib.Path(path)
        else:
            path = self._parse_experiment_path(name, config.experiments_path)

        # Create directory for experiment (raises exception if already existing)
        path.mkdir(parents=True, exist_ok=False)

        # Copy files
        for file in experiment_config.files:
            src = (self._root / file).resolve()  # resolves symlinks
            dest = path / file
            if not src.exists():
                raise InvalidExperimentError(
                    f"Failed to copy '{src}' - it does not exist!"
                )
            if src.is_file():
                shutil.copy(src, dest)
            elif src.is_dir():
                log.debug("Symbolic links are ignored by copytree")
                shutil.copytree(src, dest)

        # Create file with command
        command = self._parse_command(experiment_config.command)
        with (path / _COMMAND_FILE).open("w") as file:
            file.write(command)

        return path


def run_experiment(path: Union[str, os.PathLike]) -> None:
    path = pathlib.Path(path)
    if not path.exists():
        raise InvalidExperimentError(f"{path} does not exist")
    try:
        with (path / _COMMAND_FILE).open("r") as file:
            contents = file.read()
    except FileNotFoundError:
        raise InvalidExperimentError("Didn't find a command file: '{_COMMAND_FILE}'")

    # TODO: set up logging?
    command = contents.strip().split(" ")
    subprocess.run(command)
