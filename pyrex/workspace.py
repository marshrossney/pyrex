from __future__ import annotations

from dataclasses import asdict, replace
import os
import pathlib
import shlex
import shutil
import subprocess
from typing import ClassVar, Optional, Union

from pyrex.exceptions import InvalidWorkspaceError, InvalidPathError, GitError
from pyrex.experiment import Experiment, ExperimentConfig
from pyrex.containers import JSONConfigFile
import pyrex.utils as utils

NAMED_EXPERIMENTS_FILE = ".pyrex/named_experiments.json"
WORKSPACE_CONFIG_FILE = ".pyrex/workspace.json"


class NamedExperimentsFile(JSONConfigFile):
    """Class acting as a container for a PyREx named experiments file."""

    illegal_keys: ClassVar[str] = ["", "new"]
    str_header = "Named experiments:"

    def __getitem__(self, key: str) -> ExperimentConfig:
        return ExperimentConfig(**super().__getitem__(key))

    def __setitem__(self, key: str, value: ExperimentConfig) -> None:
        super().__setitem__(key, asdict(value))


class WorkspaceConfigFile(JSONConfigFile):
    """Class acting as a container for a PyREx workspace config file."""

    str_header = "Workspace config"



class Workspace:
    """Class acting as a container for directory that is a PyREx workspace."""

    named_experiments_file: ClassVar[str] = NAMED_EXPERIMENTS_FILE
    workspace_config_file: ClassVar[str] = WORKSPACE_CONFIG_FILE

    def __init__(
        self,
        root: Union[str, os.PathLike] = ".",
    ):
        if not self.is_workspace(root):
            raise InvalidWorkspaceError(
                "'{root}' is not a PyREx workspace; it does not contain the file '{cls.workspace_file}'"
            )
        self._root = pathlib.Path(root).resolve()
        self._named_experiments = NamedExperimentsFile(
            self._root.joinpath(self.named_experiments_file)
        )
        self._config = WorkspaceConfigFile(
            self._root.joinpath(self.workspace_config_file)
        )

    def __str__(self) -> str:
        return "\n".join(
            [
                "PyREx workspace",
                "===============",
                f"Workspace root: {self._root}",
                f"Workspace version: {self.version or 'not specified'}",
                "",
                str(self._config),
                "",
                str(self._named_experiments),
            ]
        )

    @classmethod
    def is_workspace(cls, path: Union[str, os.PathLike]) -> bool:
        return pathlib.Path(path).resolve().joinpath(cls.workspace_config_file).exists()

    @classmethod
    def init(cls, path: Union[str, os.PathLike] = ".") -> Workspace:
        path = pathlib.Path(path)
        workspace_config_file = path.joinpath(cls.workspace_config_file)
        named_experiments_file = path.joinpath(cls.named_experiments_file)

        path.mkdir(parents=True, exist_ok=True)
        workspace_config_file.parent.mkdir(exist_ok=True, parents=True)
        named_experiments_file.parent.mkdir(exist_ok=True, parents=True)

        WorkspaceConfigFile.touch(workspace_config_file)
        NamedExperimentsFile.touch(named_experiments_file)

        return cls(path)

    @classmethod
    def search_parents(cls, path: Union[str, os.PathLike] = "."):
        path = pathlib.Path(path).resolve()
        search_dir = path
        user = pathlib.Path.home()
        while search_dir.parent.is_relative_to(user):  # don't go past user
            if cls.is_workspace(search_dir):
                return cls(search_dir)
            search_dir = search_dir.parent

        raise InvalidWorkspaceError(
            f"Neither '{path}' nor any of its parents are a PyREx workspace; they do not contain the file '{cls.workspace_config_file}'"
        )

    @property
    def root(self) -> pathlib.Path:
        """Absolute path to the root directory of the workspace."""
        return self._root

    @property
    def config(self) -> WorkspaceConfigFile:
        return self._config

    @property
    def named_experiments(self) -> NamedExperimentsFile:
        return self._named_experiments

    @property
    def version(self) -> str:
        """Get the version."""
        try:
            version_command = self.config["version_command"]
        except KeyError:
            return ""

        version_command = shlex.split(version_command)
        with utils.switch_dir(self._root):
            result = subprocess.run(
                version_command, capture_output=True, text=True, check=True
            )
        version = result.stdout.strip("\n")
        return version

    def git_worktree_root(self) -> pathlib.Path:
        """Absolute path to the root of the git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--show-toplevel"
            )
        except GitError:
            return ""
        else:
            return pathlib.Path(result.strip()).resolve()

    def git_branch(self) -> str:
        """Attempts to extract the name of the current branch of the repo.

        Returns an empty string if the project is not in a git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--abbrev-ref", "HEAD"
            )
        except GitError:
            return ""
        else:
            return result.strip()

    def git_commit(self) -> str:
        """Get commit SHA-1 associated with current HEAD"""
        result = utils.git_run_command("-C", str(self._root), "rev-parse", "HEAD")
        return result.strip()

    def parse_experiment_config(self, config: ExperimentConfig) -> ExperimentConfig:
        if not all([self._root.joinpath(file).exists() for file in config.files]):
            raise FileNotFoundError(
                f"Experiment config contains files which are missing from this workspace"
            )

        path = config.output_path
        if "{repo}" in path:
            path = path.replace("{repo}", str(self.git_worktree_root()))
        if "{workspace}" in path:
            path = path.replace("{workspace}", str(self._root))
        if "{reponame}" in path:
            path = path.replace("{reponame}", self.git_worktree_root().name)
        if "{workspacename}" in path:
            path = path.replace("{workspacename}", self._root.name)
        if "{branch}" in path:
            path = path.replace("{branch}", self.git_branch())
        if "{version}" in path:
            path = path.replace("{version}", self.version)
        if "{timestamp}" in path:
            path = path.replace("{timestamp}", utils.timestamp())
        path = pathlib.Path(path).expanduser()

        if not path.is_absolute():
            raise InvalidPathError(f"Experiment path '{path}' is not absolute")

        config.output_path = str(path)

        if "{commit}" in config.command:
            config.command = config.command.replace("{commit}", self.git_commit())

        return config

    def create_experiment(
        self,
        name_or_config: Union[str, ExperimentConfig],
        override_output_path: Union[bool, str, os.PathLike] = False,
        prompt: bool = True,
    ):
        if type(name_or_config) is ExperimentConfig:
            config = name_or_config
        else:
            config = self.named_experiments[name_or_config]

        if override_output_path:
            output_path = str(pathlib.Path(override_output_path).resolve())
            config = replace(config, output_path=output_path)

        config = self.parse_experiment_config(config)

        experiment = Experiment.create(src=self.root, config=config, prompt=prompt)

        return experiment
