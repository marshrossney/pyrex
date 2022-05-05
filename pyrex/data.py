from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
import shlex
import subprocess
from typing import Optional, Union

import click
from cookiecutter.main import cookiecutter

from pyrex.exceptions import GitError, CookiecutterException, InvalidTemplateError
from pyrex.utils import git_run_command, compute_relative_paths, temp_dir

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Author:
    name: str
    email: str

    @classmethod
    def detect(cls, where: Union[str, os.PathLike] = ".") -> Author:
        try:
            name = git_run_command("config", "user.name", where=where)
            email = git_run_command("config", "user.email", where=where)
        except GitError as exc:
            log.warning("Failed to detect git author information!")
            log.info("The following error was raised: %r" % exc)
            return cls(name="", email="")
        else:
            return cls(name=name, email=email)


@dataclasses.dataclass
class Path:
    from_repo_root: str
    from_workspace_root: str
    to_repo_root: str
    to_workspace_root: str

    @classmethod
    def compute(
        cls,
        experiment_root: Union[str, os.PathLike],
        workspace_root: Union[str, os.PathLike],
        repository_root: Union[str, os.PathLike],
    ) -> Path:

        from_workspace_root, to_workspace_root = compute_relative_paths(
            experiment_root,
            workspace_root,
        )
        from_repo_root, to_repo_root = compute_relative_paths(
            experiment_root,
            repository_root,
        )
        return cls(
            from_workspace_root=str(from_workspace_root),
            to_workspace_root=str(to_workspace_root),
            from_repo_root=str(from_repo_root),
            to_repo_root=str(to_repo_root),
        )


@dataclasses.dataclass
class Repository:
    root: str
    name: str
    branch: str
    commit: str

    @classmethod
    def detect(cls, where: Union[str, os.PathLike] = ".") -> Union[Repository, None]:
        try:
            root = git_run_command("rev-parse", "--show-toplevel", where=where)
        except GitError as exc:
            log.warning("Location '%s' is not inside a git repository!" % where)
            log.info("The following error was raised: %r" % exc)
            return cls(root="", name="", branch="", commit="")
        else:
            name = pathlib.Path(root).name
            branch = git_run_command("rev-parse", "--abbrev-ref", "HEAD", where=where)
            commit = git_run_command("rev-parse", "HEAD", where=where)
            return cls(root=root, name=name, branch=branch, commit=commit)


@dataclasses.dataclass
class Template:
    template: str
    checkout: Optional[str] = None
    directory: Optional[str] = None

    def validate(self) -> None:
        try:
            with temp_dir():
                cookiecutter(
                    **dataclasses.asdict(self), no_input=True, overwrite_if_exists=True
                )
        except CookiecutterException as exc:
            raise InvalidTemplateError(
                "Cookiecutter failed to parse this template"
            ) from exc
        else:
            click.echo("Template seems to work")


@dataclasses.dataclass
class Experiment:
    files: list[str]
    commands: list[str]
    template: Template
    title: str = dataclasses.field(default_factory=str)
    description: str = dataclasses.field(default_factory=str)
    output_path: Optional[str] = None

    def __post_init__(self) -> None:
        # get Template object from named template
        self.template = Template(**self.template)


@dataclasses.dataclass
class Workspace:
    version: str
    experiments_file: str
    experiments_output_path: str

    def __post_init__(self) -> None:
        self.version = subprocess.run(
            shlex.split(self.version),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
