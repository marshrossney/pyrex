from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
import shlex
import shutil
import subprocess
from typing import Optional, Union

import click

from pyrex.config import ExperimentConfig, WorkspaceConfig, WORKSPACE_CONFIG_FILE
from pyrex.exceptions import (
    InvalidExperimentError,
    InvalidWorkspaceError,
    InvalidPathError,
    GitError,
)
import pyrex.utils as utils

log = logging.getLogger(__name__)


class PyrexWorkspace:
    """Container"""

    def __init__(self, workdir: Union[str, os.PathLike] = "."):
        try:
            loaded_config = WorkspaceConfig.load(
                pathlib.Path(workdir).joinpath(WORKSPACE_CONFIG_FILE)
            )
        except FileNotFoundError as exc:
            raise InvalidWorkspaceError(
                "'{workdir}' does not contain the file '{WORKSPACE_CONFIG_FILE}'"
            ) from exc

        self._workdir = pathlib.Path(workdir).resolve()
        self._config = loaded_config

        workspace_root = pathlib.Path(self._config.workspace_root)
        if workspace_root.is_absolute():
            self._workspace_root = workspace_root
        else:
            self._workspace_root = self._workdir.joinpath(workspace_root)

        if self.get_repo_root() is None:
            log.warning(
                "Workspace '%s' is not inside a git repository!" % self._workspace_root
            )

    @staticmethod
    def has_workspace_file(path: Union[str, os.PathLike]) -> bool:
        return pathlib.Path(path).resolve().joinpath(WORKSPACE_CONFIG_FILE).exists()

    @classmethod
    def search_parents(cls, path: Union[str, os.PathLike] = "."):
        path = pathlib.Path(path).resolve()
        search_dir = path
        user = pathlib.Path.home()
        while search_dir.parent.is_relative_to(user):  # don't go past user
            if cls.has_workspace_file(search_dir):
                return cls(search_dir)
            search_dir = search_dir.parent

        raise InvalidWorkspaceError(
            f"Neither '{path}' nor any of its parents contain the file '{WORKSPACE_CONFIG_FILE}'"
        )

    @property
    def workdir(self) -> pathlib.Path:
        """Absolute path to the working directory"""
        return self._workdir

    @property
    def config(self) -> WorkspaceConfig:
        """Loaded workspace config file"""
        return self._config

    @property
    def workspace_root(self) -> pathlib.Path:
        """Absolute path to the root directory of the workspace."""
        # NOTE: No longer aboslute!
        return self._workspace_root

    def get_repo_root(self) -> pathlib.Path:
        """Absolute path to the root of the git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._workspace_root), "rev-parse", "--show-toplevel"
            )
        except GitError:
            return None
        else:
            return pathlib.Path(result.strip()).resolve()

    def get_branch(self) -> Union[str, None]:
        """Attempts to extract the name of the current branch of the repo.

        Returns an empty string if the project is not in a git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._workspace_root), "rev-parse", "--abbrev-ref", "HEAD"
            )
        except GitError:
            return None
        else:
            return result.strip()

    def get_commit(self) -> Union[str, None]:
        """Get commit SHA-1 associated with current HEAD"""
        try:
            result = utils.git_run_command(
                "-C", str(self._workspace_root), "rev-parse", "HEAD"
            )
        except GitError:
            return None
        else:
            return result.strip()

    def get_version(self) -> str:
        """Get the version."""
        version_command = shlex.split(self._config.version_command)
        with utils.switch_dir(self._workspace_root):
            result = subprocess.run(
                version_command, capture_output=True, text=True, check=True
            )
        version = result.stdout.strip("\n")
        return version

    def parse_experiment_path(self, template: str) -> pathlib.Path:
        path = template
        if "{repo_root}" in path:
            path = path.replace("{repo_root}", str(self.get_repo_root()))
        if "{workspace_root}" in path:
            path = path.replace("{workspace_root}", str(self._workspace_root))
        if "{repo_name}" in path:
            path = path.replace("{repo_name}", self.get_worktree_root().name)
        if "{workspace_name}" in path:
            path = path.replace("{workspace_name}", self._workspace_root.name)
        if "{branch}" in path:
            path = path.replace("{branch}", self.get_branch())
        if "{version}" in path:
            path = path.replace("{version}", self.get_version())
        if "{timestamp}" in path:
            path = path.replace("{timestamp}", utils.timestamp())

        path = pathlib.Path(path)

        if not path.is_absolute():
            raise InvalidPathError(f"Experiment path '{path}' is not absolute")

        return path

    def _workspace_path(self, new_path):
        new_path = new_path.resolve()
        repo_root = self.get_repo_root()
        if not new_path.is_relative_to(repo_root):
            log.warning("New path is outside of the git repository!")
            return self._workspace_root.resolve()  # absolute path

        if new_path.is_relative_to(self._workspace_root):
            path = pathlib.Path(".").joinpath(
                *[".." for _ in new_path.relative_to(self._workspace_root).parts]
            )
        else:
            path = (
                pathlib.Path(".")
                .joinpath(*[".." for _ in new_path.relative_to(repo_root).parts])
                .joinpath(self._workspace_root.relative_to(repo_root))
            )

        assert (
            new_path.joinpath(path).resolve() == self._workspace_root.resolve()
        ), f"{new_path.joinpath(path).resolve()} != {self._workspace_root.resolve()}"
        return str(path)

    def check_files(self, files) -> None:
        """Returns True if the working directory is as specified in config.

        If config file specifies that an entire directory should be present,
        there is no way to check whether the contents of the directory are
        as expected - e.g. whether it includes output files from a previously
        run experiment. Hence, it is better to specify the working directory
        with files only.
        """
        files = [self._root.joinpath(file) for file in files]
        files_not_found, additional_files = utils.check_for_files(self._root, files)
        if files_not_found:  # if non-empty list
            raise InvalidExperimentError(
                f"Experiment directory '{self._root}' is missing required files: {[str(f) for f in files_not_found]}"
            )

        if additional_files:
            click.echo(
                "Working directory contains unexpected files. Perhaps the experiment already been run?"
            )
            # TODO only if prompt
            click.confirm(
                "Continue",
                prompt_suffix="?",
                default="no",
                show_default=True,
                abort=True,
            )

    def create_experiment(
        self,
        experiment_name: str,
        command_posargs: str = "",
        experiment_path: Optional[str] = None,
        prompt: bool = True,
    ) -> PyrexWorkspace:

        try:
            experiment_config = self._config.experiments[experiment_name]
        except KeyError as exc:
            raise InvalidExperimentError(
                f"{experiment_name} is not a known experiment"
            ) from exc

        if experiment_path:
            experiment_path = pathlib.Path(experiment_path).resolve()
        else:
            experiment_path = self.parse_experiment_path(experiment_config.output_path)
        if experiment_path.exists():
            if not experiment_path.is_dir():
                raise NotADirectoryError(
                    "Experiment path '{experiment_path}' should point to a directory"
                )
            if [f for f in experiment_path.iterdir()]:
                raise FileExistsError(
                    f"Experiment path '{experiment_path}' exists as is non-empty!"
                )

        src = self._workdir  # NOTE: not workspace root - allows experiment clone
        dest = experiment_path

        command = shlex.join(
            shlex.split(experiment_config.command) + shlex.split(command_posargs)
        )
        required_files = (
            experiment_config.required_files + utils.parse_files_from_command(command)
        )

        for file in required_files:
            if not src.joinpath(file).is_file():
                raise FileNotFoundError(
                    f"Source directory '{src}' missing file '{file}'"
                )

        # Update experiment and workspace config files, to be saved
        experiment_config = ExperimentConfig(
            command=command,
            required_files=required_files,
            output_path=str(experiment_path),
            commit=self.get_commit(),
        )

        workspace_config = dataclasses.replace(
            self._config,
            workspace_root=self._workspace_path(experiment_path),
            experiments={experiment_name: experiment_config},
        )

        click.echo(str(experiment_config))
        click.echo()
        if prompt:
            click.confirm(
                "Confirm",
                default="yes",
                abort=True,
                prompt_suffix="?",
                show_default=True,
            )

        dest.mkdir(exist_ok=True, parents=True)
        
        for file in experiment_config.required_files:
            dest.joinpath(file).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(src / file, dest / file)

        workspace_config.dump(dest.joinpath(WORKSPACE_CONFIG_FILE))

        with dest.joinpath(".gitignore").open("w") as file:
            file.write(experiment_config.gitignore())
        with dest.joinpath("README.rst").open("w") as file:
            file.write(experiment_config.readme())

        return type(self)(dest)

    def run_experiment(
        self, experiment_name: str, command_posargs: str = ""
    ) -> None:
        # Shouldn't be able to give extra posargs to an existing experiment
        # Only so we can test in the workspace root
        if command_posargs and not experiment_name:
            raise InvalidExperimentError()
        try:
            experiment_config = self._config.experiments[experiment_name]
        except KeyError as exc:
            raise InvalidExperimentError(
                f"{experiment_name} is not a known experiment"
            ) from exc

        # self.check_files(...)

        command = shlex.split(experiment_config.command) + shlex.split(command_posargs)

        with utils.switch_dir(self._workdir):
            subprocess.run(command)
