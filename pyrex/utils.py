from __future__ import annotations

import datetime
import importlib
import pathlib
import os
import shutil
import subprocess
from typing import Union

import click

from pyrex.exceptions import GitError


def prompt_for_name(
        init_name: Optional[str] = None, existing_names: list[str] = [], illegal_names: list[str] = [], attempts: int = 5
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


def parse_files_from_command(command: str) -> list[str]:
    parts = command.split(" ")
    files = []
    for part in parts:
        try:
            part_as_path = pathlib.Path(part)
        except SyntaxError:
            pass
        else:
            if part_as_path.resolve().is_file():
                # Resolve symlinks
                files.append(str(part_as_path))
    return files


def raise_(exc):
    raise exc
