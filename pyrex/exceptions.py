from __future__ import annotations

import subprocess


class InvalidConfigError(Exception):
    pass


class InvalidWorkspaceError(Exception):
    pass


class InvalidExperimentError(Exception):
    pass


class InvalidTemplateError(Exception):
    pass


class InvalidPathError(Exception):
    pass


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
