from __future__ import annotations

from dataclasses import dataclass
import os
import pathlib
import shlex
import subprocess
from typing import Optional, Union

from pyrex.base import GitRepoSubdir, JSONConfigFile
from pyrex.exceptions import InvalidWorkspaceError, InvalidPathError
from pyrex.experiment import Experiment, ExperimentConfig
import pyrex.utils as utils


@dataclass
class WorkspaceConfig(JSONConfigFile):

    command: str
    experiments_path: str
    version_command: str
    copy_files: list[str]


class Workspace(GitRepoSubdir):
    """Container"""

    workspace_file: str = ".pyrex_workspace"

    workspace_config_file: str = ".pyrex_workspace.json"

    def __init__(
        self,
        root: Union[str, os.PathLike] = ".",
    ):
        if not self.is_workspace(root):
            raise InvalidWorkspaceError(
                "'{root}' is not a PyREx workspace; it does not contain the file '{cls.workspace_file}'"
            )
        self._root = pathlib.Path(root).resolve()
        self._config = WorkspaceConfig.load(
            self._root.joinpath(self.workspace_config_file)
        )

    @classmethod
    def is_workspace(cls, path: Union[str, os.PathLike]) -> bool:
        return pathlib.Path(path).resolve().joinpath(cls.workspace_config_file).exists()

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
    def config(self) -> WorkspaceConfig:
        return self._config

    def get_version(self) -> str:
        """Get the version."""
        version_command = shlex.split(self._config.version_command)
        with utils.switch_dir(self._root):
            result = subprocess.run(
                version_command, capture_output=True, text=True, check=True
            )
        version = result.stdout.strip("\n")
        return version

    def parse_experiment_path(self, experiment_name: str) -> pathlib.Path:
        path = self._config.experiments_path
        if "{name}" in path:
            path = path.replace("{name}", experiment_name)
        if "{repo}" in path:
            path = path.replace("{repo}", str(self.get_repo_root()))
        if "{workspace}" in path:
            path = path.replace("{workspace}", str(self._root))
        if "{reponame}" in path:
            path = path.replace("{reponame}", self.get_worktree_root().name)
        if "{workspacename}" in path:
            path = path.replace("{workspacename}", self._root.name)
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

    def create_experiment(
        self,
        experiment_name: str,
        copy_files: list[str] = [],
        command_posargs: str = "",
        output_path: Optional[str] = None,
        prompt: bool = True,
    ):
        if output_path:
            output_path = pathlib.Path(output_path).resolve()
        else:
            output_path = self.parse_experiment_path(experiment_name)
        if output_path.exists():
            raise FileExistsError(
                "The requested output path '{output_path}' already exists!"
            )

        command = " ".join(
            [self._config.command, f"-e {experiment_name}", command_posargs]
        )
        files = (
            self._config.copy_files
            + copy_files
            + utils.parse_files_from_command(command)
        )

        experiment_config = ExperimentConfig(
            command=command,
            files=files,
            commit=self.get_commit(),
            workspace=str(self._root.relative_to(self.get_repo_root())),
        )

        experiment = Experiment.create(
            src=self._root, dest=output_path, config=experiment_config
        )

        return experiment
