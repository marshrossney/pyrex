from __future__ import annotations

import datetime
import importlib
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Union

import click

from pyrex.exceptions import GitError


def prompt_for_name(
    init_name: Optional[str] = None,
    existing_names: list[str] = [],
    illegal_names: list[str] = [],
    attempts: int = 5,
):
    for attempt in range(attempts):
        if attempt == 0 and init_name is not None:
            name = init_name
        else:
            name = click.prompt("Name", type=click.STRING)

        slug = name.replace(" ", "-")
        if name != slug:
            click.echo(f"Simplifying: '{name}' --> '{slug}'")
            name = slug

        if not name:
            click.echo("Cannot use empty string as name")
        elif name in illegal_names:
            click.echo(f"Cannot use name '{name}'")
        elif name in existing_names:
            click.echo(f"'{name}' already exists!")
        else:
            return name

    raise click.Abort(f"Giving up after {attempts} attempts")


class symlink_dir:
    def __init__(
        self,
        source_dir: Union[str, os.PathLike],
        target_dir: Union[str, os.PathLike] = ".",
        ignore_patterns: list = [],
        unlink_on_exit: bool = True,
    ):
        self.source_dir = pathlib.Path(source_dir)
        self.target_dir = pathlib.Path(target_dir)
        self.ignore_patterns = ignore_patterns
        self.unlink_on_exit = unlink_on_exit
        self.files = []
        self.links = []

        for d in (self.source_dir, self.target_dir):
            if not d.is_dir():  # don't care for symlinked source dirs
                raise NotADirectoryError(f"{d} is not an existing directory")

        self._add_files(self.source_dir)

    def _add_files(self, subdir: pathlib.Path) -> None:
        for path in subdir.iterdir():
            if path.is_dir():
                self._add_files(path)
            elif path.is_file:
                self.files.append(path)
            else:
                pass  # skip symlinks

    def __enter__(self):
        for file in self.files:
            link = self.target_dir.joinpath(file.relative_to(self.source_dir))
            link.parent.mkdir(exist_ok=True, parents=True)
            try:
                link.symlink_to(file)
            except FileExistsError:
                # NOTE: probably unnecessary since we test for symlink in __exit__
                self.files.remove(file)
            else:
                self.links.append(link)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.unlink_on_exit:
            for link in self.links:
                # NOTE: symlink may have been overwritten with regular file
                if link.is_symlink():
                    link.unlink()


def git_run_command(*args: str, capture_output=True):
    """Runs 'git *args' through subprocess.run, returning the contents of stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=capture_output,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(e)

    else:
        if capture_output:
            return result.stdout


class switch_dir:
    """Context manager for changing to *existing* directory."""

    def __init__(self, path: Union[str, os.PathLike]):
        self.new = pathlib.Path(path)
        assert self.new.is_dir()

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.new)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.old)


class temp_dir:
    def __init__(self):
        self.tmp = pathlib.Path.cwd().joinpath(".tmp")
        self.tmp.mkdir(exist_ok=False)

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.tmp)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.old)
        shutil.rmtree(self.tmp)


def is_valid_remote(url: str) -> bool:
    try:
        _ = git_run_command("ls-remote", url)
    except GitError:
        return False
    else:
        return True


def timestamp():
    return datetime.datetime.now().strftime("%G%m%dT%H%M%S")  # ISO 8601 basic


def load_module_from_path(path: Union[str, os.PathLike]):
    assert path.is_file(), f"{path} does not exist"
    spec = importlib.util.spec_from_file_location(path.stem, str(path.resolve()))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_files_from_command(command: str) -> list[str]:
    parts = command.split(" ")
    files = []
    for part in parts:
        try:
            part_as_path = pathlib.Path(part)
        except SyntaxError:
            pass
        else:
            if part_as_path.is_file():
                files.append(str(part_as_path))
    return files


def raise_(exc):
    raise exc


def check_for_files(
    directory: pathlib.Path,
    expected: list[str],
    additional: list[str] = [],
    break_after: int = 10,
):
    for path in directory.iterdir():
        if path.is_dir():
            expected, additional = check_for_files(path, expected, additional)
        elif path in expected:
            expected.remove(path)
        else:
            additional.append(path)

        # If huge number of files, e.g. from previously run expt
        if len(additional) > break_after:
            break

    return expected, additional
