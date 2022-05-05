from __future__ import annotations

import itertools
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Union

import click

from pyrex.exceptions import GitError


def compute_relative_paths(
    path: Union[str, os.PathLike], reference: Union[str, os.PathLike]
) -> tuple[str, str]:
    path = pathlib.Path(path).resolve()
    reference = pathlib.Path(reference).resolve()

    # NOTE: inner loop is through path.parents
    common_parent = None
    for r, p in itertools.product(
        reference.joinpath("dummy").parents, path.joinpath("dummy").parents
    ):
        if r == p:
            common_parent = r
            break
    assert common_parent is not None

    from_reference = (
        pathlib.Path(".")
        .joinpath(*[".." for _ in reference.relative_to(common_parent).parts])
        .joinpath(path.relative_to(common_parent))
    )
    to_reference = (
        pathlib.Path(".")
        .joinpath(*[".." for _ in path.relative_to(common_parent).parts])
        .joinpath(reference.relative_to(common_parent))
    )

    return str(from_reference), str(to_reference)


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


def git_run_command(
    *args: str,
    where: Union[str, os.PathLike] = ".",
    capture_output=True,
    strip_output=True,
):
    """Runs 'git *args' through subprocess.run, returning the contents of stdout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(where), *args],
            capture_output=capture_output,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(e)

    else:
        if capture_output:
            return result.stdout.strip() if strip_output else result.stdout


def repo_is_dirty(where: Union[str, os.PathLike] = ".") -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(where), "diff-index", "--quiet", "HEAD", "--"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(e)
    else:
        return bool(result.returncode)


def is_valid_remote(url: str) -> bool:
    try:
        _ = git_run_command("ls-remote", url)
    except GitError:
        return False
    else:
        return True


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
        self.tmp = pathlib.Path.cwd().joinpath(".pyrex_tmp")
        self.tmp.mkdir(exist_ok=False)

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.tmp)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.old)
        shutil.rmtree(self.tmp)


def parse_files_from_command(
    command: str, where: Union[str, os.PathLike] = "."
) -> list[str]:
    where = pathlib.Path(where)
    parts = command.split(" ")
    files = []
    for part in parts:
        try:
            part_as_path = where.joinpath(part)
        except SyntaxError:
            pass
        else:
            if part_as_path.is_file():
                files.append(part)
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
