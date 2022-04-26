from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
import pathlib
import shlex
import subprocess
from typing import Optional, Union

log = logging.getLogger(__name__)

COMMAND_FILE = "COMMAND.txt"


class InvalidExperimentError(Exception):
    pass


@dataclass
class ExperimentConfig:
    command: str
    working_dir: Optional[list[str]] = field(default_factory=list)

    def __post_init__(self):
        if not self.command:
            raise InvalidExperimentError("'command' must be specified")

        working_dir = [pathlib.Path(file) for file in self.working_dir]
        if any([path.is_absolute() for path in working_dir]):
            raise InvalidExperimentError(
                "Working directory should not contain absolute paths"
            )
        if any([".." in path.parts for path in working_dir]):
            raise InvalidExperimentError(
                "Paths containing '../' are not allowed in the working directory"
            )
        if not len(self.working_dir) == len(set(self.working_dir)):
            raise InvalidExperimentError(
                "Working directory should not contain duplicates"
            )

    def gitignore(self) -> str:
        contents = f"""
        *
        !README.*
        !{COMMAND_FILE}
        """
        for file in self.working_dir:
            contents += f"\n!{pathlib.Path(file).name}"
        return contents


def run_experiment(path: Union[str, os.PathLike]) -> None:
    path = pathlib.Path(path)
    if not path.exists():
        raise InvalidExperimentError(f"{path} does not exist")
    try:
        with (path / COMMAND_FILE).open("r") as file:
            contents = file.read()
    except FileNotFoundError:
        raise InvalidExperimentError("Didn't find a command file: '{_COMMAND_FILE}'")

    # TODO: set up logging?
    command = shlex.split(contents.strip())
    subprocess.run(command)
