from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
import json
import os
import pathlib
import shlex
import shutil
import subprocess
from typing import Optional, Union

import click

from pyrex.exceptions import InvalidExperimentError
from pyrex.utils import switch_dir

EXPERIMENT_CONFIG_FILE = "pyrex_experiment.json"


@dataclass
class ExperimentConfig:
    command: str
    output_path: str
    files: list[str] = field(default_factory=list)
    exec_dir: str = "."

    def __post_init__(self):
        self.command = self.command.strip()
        if not self.command:  # catches empty string
            raise InvalidExperimentError("'command' must be specified")

        paths = [pathlib.Path(file) for file in self.files]
        paths.append(pathlib.Path(self.exec_dir))
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
                f"Experiment path: {self.output_path}",
                f"Command: {self.command}",
                f"Exec directory: {self.exec_dir}",
                f"Required files: {self.files}",
            ]
        )
        return summary

    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> ExperimentConfig:
        with open(filepath, "r") as file:
            contents = json.load(file)
        assert "output_path" not in contents, "hmmmmm"
        contents["output_path"] = pathlib.Path(filepath).resolve().parent
        return cls(**contents)


class Experiment:
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
    def is_experiment(cls, path: Union[str, os.PathLike]) -> bool:
        """Raises InvalidExperimentError if file exists but is invalid."""
        config_file = pathlib.Path(path).joinpath(cls.config_file)
        try:
            _ = ExperimentConfig.load(config_file)
        except FileNotFoundError:
            return False
        except InvalidExperimentError as e:
            raise InvalidExperimentError(
                f"Experiment file exists at '{config_file}' but is invalid:\n{e}"
            )
        else:
            return True

    @classmethod
    def create(
        cls,
        src: Union[str, os.PathLike],
        config: ExperimentConfig,
        prompt: bool = True,
    ) -> Experiment:
        src = pathlib.Path(src).resolve()
        dest = pathlib.Path(config.output_path).resolve()

        if dest.exists():
            if not dest.is_dir():
                raise NotADirectoryError("Destination path should be a directory")
            if [f for f in dest.iterdir()]:
                raise FileExistsError("Destination path is non-empty")

        for file in config.files:
            src_file = src.joinpath(file)
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

        gitignore = "*\n" + "\n!".join(config.files)
        with dest.joinpath(".gitignore").open("w") as file:
            file.write(gitignore)

        config = asdict(config)
        config["files"].extend([cls.config_file, ".gitignore"])
        del config["output_path"]  # this is irrelevant now

        with dest.joinpath(cls.config_file).open("w") as file:
            json.dump(config, file, indent=6)

        return cls(dest)

    @property
    def root(self) -> pathlib.Path:
        """Absolute path to the root directory of the experiment."""
        return self._root

    @property
    def config(self) -> ExperimentConfig:
        return self._config

    @property
    def command(self) -> list[str]:
        """Run config.command through shlex.split"""
        return shlex.split(self._config.command)

    @property
    def files(self) -> list[pathlib.Path]:
        """List of paths expected to exist in working directory."""
        return [pathlib.Path(path) for path in self.config.files]

    @staticmethod
    def _validate_subdir(remaining, subdir):
        for f in subdir.iterdir():
            if f.is_dir():
                remaining = self._validate_subdir(remaining, f)
            remaining.remove(f)
        return remaining

    def validate_workdir(self) -> None:
        """Returns True if the working directory is as specified in config.

        If config file specifies that an entire directory should be present,
        there is no way to check whether the contents of the directory are
        as expected - e.g. whether it includes output files from a previously
        run experiment. Hence, it is better to specify the working directory
        with files only.
        """
        try:
            remaining = self._validate_subdir(self.files, self._root)
        except ValueError:
            raise InvalidExperimentError("Working directory missing required files.")
        if remaining:
            raise InvalidExperimentError(
                "Working directory contains unexpected files. Has the experiment already been run?"
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
