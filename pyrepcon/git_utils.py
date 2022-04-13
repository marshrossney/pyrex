"""Execute basic git commands as subprocesses.

Relies on the standard subprocess package to execute git commands, rather than requiring
a third-party package such as GitPython. Hence, git must be installed.
"""
from __future__ import annotations

from distutils.util import strtobool
import os
import pathlib
import subprocess
from typing import TypeAlias

Path: TypeAlias = pathlib.Path
PathLike: TypeAlias = str | os.PathLike
CalledProcessError: TypeAlias = subprocess.CalledProcessError


class GitError(Exception):
    """Handles errors from calling git commands using subprocess."""

    def __init__(self, error: CalledProcessError):
        if type(error.cmd) is list:
            error.cmd = " ".join(error.cmd)
        message = f"""The git command '{error.cmd}' returned non-zero exit status {error.returncode}
        {error.stderr}
        """
        super().__init__(message)

        self.error = error


def git_run_command(args: list[str]):
    """Runs 'git *args' through subprocess.run, returning the contents of stdout."""
    try:
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except CalledProcessError as e:
        raise GitError(e)


def git_dir() -> Path:
    """Returns path to working tree (.git/) directory."""
    result = git_run_command(["rev-parse", "--git-dir"])
    return Path(result.strip("\n"))


def root_dir() -> Path:
    """Returns absolute path to top-level 'root' directory, containing '.git/'."""
    result = git_run_command(["rev-parse", "--show-toplevel"])
    return Path(result.strip("\n"))


def cwd_relative_to_root() -> Path:
    """Returns path to current working directory relative to the root of the repo."""
    result = git_run_command(["rev-parse", "--show-prefix"])
    return Path(result.strip("\n"))


def root_relative_to_cwd() -> Path:
    """Returns path to root of the repo relative to the current working directory."""
    result = git_run_command(["rev-parse", "--show-cdup"])
    return Path(result.strip("\n"))


def is_inside_work_tree() -> bool:
    """Returns True if current working directory is inside a git working tree."""
    result = git_run_command(["rev-parse", "--is-inside-work-tree"])
    return bool(strtobool(result))


def current_branch() -> str:
    """Returns the name of the current branch."""
    # result = git_run_command(["branch", "--show-current"])  # requires git v2.22
    result = git_run_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.strip("\n")


def most_recent_commit() -> str:
    """Returns the full sha1 hash for the most recent (local) commit on the current branch."""
    result = git_run_command(["rev-parse", "HEAD"])
    return result.strip("\n")


def is_dirty() -> bool:
    """Returns True if tracked files have been modified but not committed."""
    result = git_run_command(["diff", "HEAD"])  # non-empty string if dirty
    return bool(result)


def is_valid_git_object(obj: str) -> bool:
    """Returns True if obj is a valid branch name or revision reference."""
    try:
        _ = git_run_command(["rev-parse", "--verify", "--quiet", obj])
    except GitError as e:
        if (
            e.returncode == 1
        ):  # implies command worked as expected, but object is invalid
            return False
        raise e
    return True


def local_branches() -> list[str]:
    """Returns list of local branches."""
    result = git_run_command(["branch", "--list"])
    return [b.strip() for b in result.strip().replace("*", "").split("\n")]


def switch_branch(branch: str) -> None:
    """Switches to the head of the given branch. Fails if dirty state."""
    _ = git_run_command(["switch", branch])


def checkout_workspace(commit: str, source: PathLike, dest: PathLike) -> None:
    """Checks out a workspace from a given commit at a new location."""
    _ = git_run_command(
        ["checkout", "--work-tree", str(source), commit, "--", str(dest)]
    )
