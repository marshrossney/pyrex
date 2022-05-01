from __future__ import annotations

from dataclasses import dataclass, field, replace
import os
import pathlib
import shlex
import shutil
import subprocess
from typing import ClassVar, Union

import click

from pyrex.base import GitRepoSubdir, JSONConfigFile
from pyrex.exceptions import InvalidExperimentError
from pyrex.utils import switch_dir, symlink_dir

EXPERIMENT_CONFIG_FILE = "pyrex_experiment.json"


@dataclass
class ExperimentConfig(JSONConfigFile):
    command: str
    commit: str
    workspace: str
    files: list[str] = field(default_factory=list)

    def __post_init__(self):
        # TODO check workspace path or url
        self.command = self.command.strip()
        if not self.command:  # catches empty string
            raise InvalidExperimentError("'command' must be specified")

        paths = [pathlib.Path(file) for file in self.files]
        if any([path.is_absolute() for path in paths]):
            raise InvalidExperimentError(
                "Experiment config should not contain absolute paths"
            )
        if any([".." in path.parts for path in paths]):
            raise InvalidExperimentError(
                "Paths containing '../' are not allowed in the experiment config"
            )
        # Remove duplicates
        self.files = list(set(self.files))

    def __str__(self) -> str:
        summary = "\n".join(
            [
                "Experiment Summary",
                "==================",
                f"Command: {self.command}",
                f"Required files: {self.files}",
            ]
        )
        return summary

    def dump_readme(self, fmt: str = "rst"):
        pass


class Experiment(GitRepoSubdir):
    """Class acting as a container for directory that is a PyREx experiment."""

    config_file: ClassVar[str] = EXPERIMENT_CONFIG_FILE

    def __init__(self, root: Union[str, os.PathLike] = "."):
        self._root = pathlib.Path(root).resolve()
        try:
            self._config = ExperimentConfig.load(self._root.joinpath(self.config_file))
        except FileNotFoundError:
            raise InvalidExperimentError(
                "'{root}' is not a PyREx experiment; it does not contain the file '{self.config_file}'"
            )

    @classmethod
    def create(
        cls,
        src,
        dest,
        config: ExperimentConfig,
        prompt: bool = True,
    ) -> Experiment:
        src = pathlib.Path(src).resolve()
        dest = pathlib.Path(dest).resolve()

        if dest.exists():
            if not dest.is_dir():
                raise NotADirectoryError("Destination path should be a directory")
            if [f for f in dest.iterdir()]:
                raise FileExistsError("Destination path is non-empty")

        for file in config.files:
            if not src.joinpath(file).is_file():
                raise FileNotFoundError(
                    f"Source directory '{src}' missing file '{file}'"
                )

        click.echo(str(config))
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

        for file in config.files:
            dest.joinpath(file).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(src / file, dest / file)

        # TODO: make config mutable - this is pointlessly expensive
        config = replace(config, files=config.files + [cls.config_file, ".gitignore"])

        config.dump(dest.joinpath(cls.config_file))
        gitignore = "*\n" + "\n!".join(config.files)
        with dest.joinpath(".gitignore").open("w") as file:
            file.write(gitignore)

        return cls(dest)

    @property
    def config(self) -> ExperimentConfig:
        return self._config

    @property
    def command(self) -> list[str]:
        """Run config.command through shlex.split"""
        return shlex.split(self._config.command)

    def get_workspace_root(self) -> pathlib.Path:
        return self.get_repo_root().joinpath(self._config.workspace)

    @staticmethod
    def _validate_subdir(subdir, expected, additional):
        for f in subdir.iterdir():
            if f.is_dir():
                expected, additional = Experiment._validate_subdir(
                    f, expected, additional
                )
            elif f in expected:
                expected.remove(f)
            else:
                additional.append(f)

            # If huge number of files, e.g. from previously run expt
            if len(additional) > 10:
                additional.append("and potentially more...")
                break

        return expected, additional

    def validate_workdir(self) -> None:
        """Returns True if the working directory is as specified in config.

        If config file specifies that an entire directory should be present,
        there is no way to check whether the contents of the directory are
        as expected - e.g. whether it includes output files from a previously
        run experiment. Hence, it is better to specify the working directory
        with files only.
        """
        files = [self._root.joinpath(file) for file in self._config.files]
        files_not_found, additional_files = self._validate_subdir(self._root, files, [])
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

    def run(self, *, skip_validation: bool = False) -> None:
        """Run command as a Python subprocess."""
        if not skip_validation:
            self.validate_workdir()

        with switch_dir(self._root):
                subprocess.run(self.command)

    def clone(self, dest: Union[str, os.PathLike]) -> Experiment:
        """Clone this experiment to another directory 'dest'."""
        dest = str(pathlib.Path(dest).resolve())
        new_config = replace(self.config, output_dir=dest)
        return type(self).create(src=self._root, config=new_config)
