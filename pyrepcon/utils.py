from __future__ import annotations

import datetime
import importlib
import pathlib
import os
import subprocess
from typing import Union


class InvalidWorkspaceError(Exception):
    pass


class InvalidExperimentError(Exception):
    pass


def raise_(exc):
    raise exc


class GitError(Exception):
    """Handles errors from calling git commands using subprocess."""

    def __init__(self, error: subprocess.CalledProcessError):
        if type(error.cmd) is list:
            error.cmd = " ".join(error.cmd)
        message = f"""The git command '{error.cmd}' returned non-zero exit status {error.returncode}
        {error.stderr}
        """
        super().__init__(message)

        self.error = error


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


def parse_files_from_command(command: str) -> list[str]:
    parts = command.split(" ")
    files = []
    for part in parts:
        try:
            part_as_path = pathlib.Path(part)
        except SyntaxError:
            pass
        else:
            if part_as_path.exists():
                files.append(str(part_as_path))
    return files
