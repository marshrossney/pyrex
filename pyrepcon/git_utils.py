"""Execute basic git commands as subprocesses.

Relies on the standard subprocess package to execute git commands, rather than requiring
a third-party package such as GitPython. Hence, git must be installed.
"""
from __future__ import annotations

from distutils.util import strtobool
import logging
import pathlib
import os
import subprocess
from typing import Union

log = logging.getLogger(__name__)


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
    """Runs 'git *args' through subprocess.run, returning the contents of stdout with the newline character stripped."""
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
            return result.stdout.strip("\n")


def git_dir() -> pathlib.Path:
    """Returns path to working tree (.git/) directory."""
    result = git_run_command("rev-parse", "--git-dir")
    return pathlib.Path(result)


def root_dir() -> pathlib.Path:
    """Returns absolute path to top-level 'root' directory, containing '.git/'."""
    result = git_run_command("rev-parse", "--show-toplevel")
    return pathlib.Path(result)


def cwd_relative_to_root() -> pathlib.Path:
    """Returns path to current working directory relative to the root of the repo."""
    result = git_run_command(["rev-parse", "--show-prefix"])
    return pathlib.Path(result.strip("\n"))


def root_relative_to_cwd() -> pathlib.Path:
    """Returns path to root of the repo relative to the current working directory."""
    result = git_run_command(["rev-parse", "--show-cdup"])
    return pathlib.Path(result.strip("\n"))


def is_inside_work_tree() -> bool:
    """Returns True if current working directory is inside a git working tree."""
    result = git_run_command("rev-parse", "--is-inside-work-tree")
    return bool(strtobool(result.strip("\n")))


def current_branch() -> str:
    """Returns the name of the current branch."""
    # result = git_run_command(["branch", "--show-current"])  # requires git v2.22
    result = git_run_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.strip("\n")


def is_valid_git_object(obj: str) -> bool:
    """Returns True if obj is a valid branch, tag or reference."""
    try:
        _ = git_run_command(["rev-parse", "--verify", "--quiet", obj])
    except GitError as e:
        if e.returncode == 1:
            # implies command worked as expected, but object is invalid
            return False
        raise e
    return True


def is_local_branch(reference: str) -> bool:
    """Returns True if the provided reference is a local branch."""
    result = git_run_command(["show-ref", "--heads", reference])
    return bool(result)


def is_local_tag(reference: str) -> bool:
    """Returns True if the provided reference is a local tag."""
    result = git_run_command(["show-ref", "--tags", reference])
    return bool(result)


def parse_branch(branch: str) -> str:
    """Returns the full sha1 hash for the most recent (local) commit on a given branch."""
    result = git_run_command(["rev-parse", branch])
    return result.strip("\n")


def parse_head() -> str:
    return parse_branch("HEAD")


def parse_tag(tag: str) -> str:
    """Returns the full sha1 hash for the commit associated with a given tag."""
    result = git_run_command(["rev-parse", tag + "^{}"])
    return result.strip("\n")


def parse_commit(commit: str) -> str:
    """Returns the full sha1 hash for the commit, which may be a shortened hash value."""
    result = git_run_command(["rev-parse", commit])
    return result.strip("\n")


def parse_reference(reference: str | None) -> str:
    """Converts local reference (branch/head, tag, commit) to full-length sha1 hash."""
    if reference is None:
        return parse_head()
    elif is_local_branch(reference):
        return parse_branch(reference)
    elif is_local_tag(reference):
        return parse_tag(reference)
    else:
        return parse_commit(reference)


def is_dirty() -> bool:
    """Returns True if tracked files have been modified but not committed."""
    result = git_run_command(["diff", "HEAD"])  # non-empty string if dirty
    return bool(result)


def local_branches() -> list[str]:
    """Returns list of local branches."""
    result = git_run_command(["branch", "--list"])
    return [b.strip() for b in result.strip().replace("*", "").split("\n")]


def switch_branch(branch: str) -> None:
    """Switches to the head of the given branch. Fails if dirty state."""
    _ = git_run_command(["switch", branch])


def checkout_commit(commit: str) -> None:
    """Switches to a specific commit. Fails if dirty state."""
    _ = git_run_command(["checkout", commit])


def checkout_files(
    source: Union[str, os.PathLike],
    dest: Union[str, os.PathLike],
    commit_or_ref: str,
    git_dir: Union[str, os.PathLike],
) -> None:
    """Checks out a workspace from a given commit at a new location."""
    git_run_command(
        "--git-dir",
        str(git_dir),
        "--work-tree",
        str(dest),
        "checkout",
        commit,
        "--",
        str(source),
        capture_output=False,
    )


class checkout:
    def __init__(self, ref: str | None):
        self.new_ref = ref

    def __enter__(self):
        if self.new_ref is not None:
            self.curr_ref = parse_head()
            _ = git_run_command(["checkout", self.new_ref])

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.new_ref is not None:
            _ = git_run_command(["checkout", self.curr_ref])
