from __future__ import annotations

import logging
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Union

from slugify import slugify

from pyrepcon.config import WorkspaceConfig
import pyrepcon.git_utils
from pyrepcon.utils import (
    switch_dir,
    timestamp,
    InvalidWorkspaceError,
    InvalidExperimentError,
)

log = logging.getLogger(__name__)


class Workspace:
    """Class acting as a container for pyrex operations."""

    def __init__(self, root: Union[str, os.PathLike] = ".", config: str = "repex.json"):
        self._root = pathlib.Path(root).absolute()
        self._config = self._root / config
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
    def create(cls, path: Union[str, os.PathLike] = ".") -> Workspace:
        # TODO: call function
        pass

    @property
    def root(self) -> pathlib.Path:
        """Path to the root directory of the workspace."""
        return self._root

    @property
    def project_root(self) -> Union[pathlib.Path, None]:
        """Path to the root directory of the entire project.

        This is also the git working tree, and contains the repository."""
        try:
            result = pyrepcon.git_utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--show-toplevel"
            )
        except pyrepcon.git_utils.GitError:
            return None
        else:
            return pathlib.Path(result).absolute()

    @property
    def git_dir(self) -> Union[pathlib.Path, None]:
        """Path to the git repository, usually called '.git/'."""
        try:
            result = pyrepcon.git_utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--git-dir"
            )
        except pyrepcon.git_utils.GitError:
            return None
        else:
            return pathlib.Path(result).absolute()

    @property
    def uses_git(self) -> bool:
        """Returns true if workspace is in a git working tree."""
        return pyrepcon.git_utils.is_inside_work_tree(self._root)

    def load_config(self) -> WorkspaceConfig:
        return WorkspaceConfig.load(self._config)

    def get_branch(self) -> str:
        """Attempts to extract the name of the current branch of the repo.

        Returns an empty string if the project is not in a git working tree."""
        try:
            result = pyrepcon.git_utils.run_command(
                "-C", str(self._root), "rev-parse", "--abbrev-ref", "HEAD"
            )
        except pyrepcon.git_utils.GitError:
            return ""
        else:
            return result.strip()

    def get_version(self) -> str:
        """Get the version."""
        config = self.load_config()
        if config.version_command is not None:
            with switch_dir(self._root):
                result = subprocess.run(
                    config.version_command, capture_output=True, text=True, check=True
                )
            version = result.stdout.strip("\n")
            return version
        else:
            return str(config.version)

    def _get_commit(self) -> str:
        """Get commit SHA-1 associated with current HEAD"""
        result = pyrepcon.git_utils.run_command(
            "-C", str(self._root), "rev-parse", "HEAD"
        )
        return result.strip()

    def _parse_experiment_path(
        self,
        name: str,
        path: list[str],
    ) -> pathlib.Path:
        if "{branch}" in path:
            path = path.replace("{branch}", self.get_branch())
        if "{version}" in path:
            path = path.replace("{version}", self.get_version())
        if "{name}" in path:
            path = path.replace("{name}", name)
        if "{timestamp}" in path:
            path = path.replace("{timestamp}", timestamp())
        return self._root.joinpath(*path.split("/"))

    def _parse_command(self, command: str) -> str:
        if "{commit}" in command:
            command = command.replace("{commit}", self._get_commit())
        return command

    def new_experiment(
        self,
        name: str,
        command: Optional[str] = None,
        files: Optional[list[str]] = None,
        override_path: Union[bool, str, os.PathLike] = False,
    ) -> pathlib.Path:
        """Creates new experiment, returns path to experiment dir."""
        config = self.load_config()

        # Check if referring to existing named experiment, or new one
        if name in config.named_experiments:
            if command is not None or files is not None:
                raise InvalidExperimentError(
                    f"{name} is already a named experiment. 'command' and 'files' should not be given in this case"
                )
            experiment_config = config.named_experiments[name]
        else:
            config.add_named_experiment(name, command, [str(file) for file in files])
            experiment_config = config.named_experiments[name]
            config.dump(self._config)

        # If no path set explicitly by user, construct path from default
        if override_path is not None:
            experiment_path = pathlib.Path(override_path)
        else:
            experiment_path = self._parse_experiment_path(name, config.experiments_path)

        # Create directory for experiment
        if experiment_path.exists():
            raise InvalidExperimentError(
                f"The requested path '{experiment_path}' already exists!"
            )
        experiment_path.mkdir(parents=True, exist_ok=False)

        # Copy files
        for file in experiment_config.files:
            src = (self._root / file).resolve()  # resolves symlinks
            dest = experiment_path / file
            if not src.exists():
                raise InvalidExperimentError(
                    f"Failed to copy '{src}' but it does not exist!"
                )
            if src.is_file():
                shutil.copy(src, dest)
            elif src.is_dir():
                log.debug("Symbolic links are ignored by copytree")
                shutil.copytree(src, dest)

        # Create file with command
        command = self._parse_command(experiment_config.command)
        with (experiment_path / "COMMAND.txt").open("w") as file:
            file.write(command)

        return experiment_path


def run_experiment(path: Union[str, os.PathLike]) -> None:
    path = pathlib.Path(path)
    if not path.exists():
        raise InvalidExperimentError(f"{path} does not exist")
    try:
        with (path / "COMMAND.txt").open("r") as file:
            contents = file.read()
    except FileNotFoundError:
        raise InvalidExperimentError("Didn't find a COMMAND.txt file")

    # TODO: set up logging?
    command = contents.strip().split(" ")
    subprocess.run(command)
