from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import os
import pathlib
from typing import Union

from pyrex.exceptions import GitError
import pyrex.utils as utils

# TODO allow yaml - nicer to read - by making WorkspaceConfig/ExperimentConfig factory functions

log = logging.getLogger(__name__)


@dataclass
class JSONConfigFile:
    @classmethod
    def load(cls, filepath: Union[str, os.PathLike]) -> JSONConfigFile:
        with open(filepath, "r") as file:
            contents = json.load(file)
        return cls(**contents)

    def dump(self, filepath: Union[str, os.PathLike]) -> None:
        contents = asdict(self)
        try:
            _ = json.dumps(contents)
        except (TypeError, OverflowError) as exc:
            raise exc("Object is not JSON serializable. Abandoning the write!")
        else:
            with open(filepath, "w") as file:
                json.dump(asdict(self), file, indent=6)


class GitRepoSubdir:
    """Base class acting as a container for subdirectory of a git repo."""

    def __init__(self, root: Union[str, os.PathLike] = "."):
        self._root = pathlib.Path(root).resolve()

        if self.get_repo_root() is None:
            log.warning("'%s' is not inside a git repository!" % self._root)

    @property
    def root(self) -> Union[pathlib.Path, None]:
        """Absolute path to the root directory of the workspace."""
        return self._root

    def get_repo_root(self) -> pathlib.Path:
        """Absolute path to the root of the git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--show-toplevel"
            )
        except GitError:
            return None
        else:
            return pathlib.Path(result.strip()).resolve()

    def get_branch(self) -> Union[str, None]:
        """Attempts to extract the name of the current branch of the repo.

        Returns an empty string if the project is not in a git working tree."""
        try:
            result = utils.git_run_command(
                "-C", str(self._root), "rev-parse", "--abbrev-ref", "HEAD"
            )
        except GitError:
            return None
        else:
            return result.strip()

    def get_commit(self) -> Union[str, None]:
        """Get commit SHA-1 associated with current HEAD"""
        try:
            result = utils.git_run_command("-C", str(self._root), "rev-parse", "HEAD")
        except GitError:
            return None
        else:
            return result.strip()
