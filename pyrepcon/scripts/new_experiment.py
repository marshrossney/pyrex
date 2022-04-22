from __future__ import annotations

import pathlib
import os
import subprocess
from typing import Union

import click
import cookiecutter

import pyrepcon.git_utils
import pyrepcon.project


@click.command()
@click.option("--workspace", type=ExistingDir, default=pathlib.Path.cwd(), help="hi")
@click.option("--reference", type=str, help="name of local branch, tag, or commit hash")
@click.option(
    "--subdir", type=str, default="", help="subdirectory in which to run experiment"
)
@click.option(
    "--command", type=str, nargs="*", default=None, help="commands to run upon creation"
)
def main(
    workspace: Union[str | os.PathLike],
    reference: str,
    command: Optional[list[str]],
    subdir: str = "",
):

    project = pyrepcon.project.Project(pyrepcon.git_utils.root_dir())
    

    commit = git_utils.parse_reference(reference)
    workspace_abs_path = utils.parse_workspace(workspace)
    workspace_rel_path = workspace_abs_path.relative_to(development_dir)
    workspace_version = utils.get_workspace_version(
        workspace_abs_path, commit
    )  # checkout commit

    git_utils.switch_branch(project_config.experiments_branch)
    experiment_path = experiments_dir / workspace_path.relative_to(development_dir)
    experiment_path = experiment_path / workspace_version / subdir / curr_datetime
    experiment_path.mkdir(parents=True, exist_ok=False)
    os.chdir(experiment_path)

    git_utils.checkout_workspace(reference, workspace_path, experiment_path)

    repcon.config.ExperimentConfig(workspace_rel_path, commit, command).dump()

    # TODO: run commands
