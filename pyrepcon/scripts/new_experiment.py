from __future__ import annotations

import pathlib
import os
import subprocess
from typing import TypeAlias

import click
import cookiecutter
import git

import repcon.config
import repcon.git_utils


ExistingDir: TypeAlias = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path
)


@click.command()
@click.option("--workspace", type=ExistingDir, default=pathlib.Path.cwd(), help="hi")
@click.option("--reference", type=str, help="name of local branch, tag, or commit hash")
@click.option("--subdir", type=str, default="", help="subdirectory in which to run experiment")
@click.option(
    "--command", type=str, nargs="*", default=None, help="commands to run upon creation"
)
def main(workspace: str | os.PathLike, reference: str, command: list[str] | None, subdir: str = ""):
    
    project_root = repcon.git_utils.root_dir()
    project_config = repcon.config.ProjectConfig.load(project_root)
    experiments_dir = project_root / project_config.experiments_dir
    development_dir = project_root / project_config.development_dir
    commit = git_utils.parse_reference(reference)
    workspace_abs_path = utils.parse_workspace(workspace)
    workspace_rel_path = workspace_abs_path.relative_to(development_dir)
    workspace_version = utils.get_workspace_version(workspace_abs_path, commit)  # checkout commit
    curr_datetime = utils.now()

    # NOTE: not necessary - will be checked anyway, but maybe nicer error msg?
    '''assert workspace_path.is_relative_to(
        development_dir
    ), "workspace {workspace_abs_path} is not a subdirectory of {development_dir}"
    assert (
        not git_utils.is_dirty()
    ), "Unable to safely switch branches; repository is in a dirty state."
    '''

    git_utils.switch_branch(project_config.experiments_branch)
    experiment_path = experiments_dir / workspace_path.relative_to(development_dir)
    experiment_path = experiment_path / workspace_version / subdir / curr_datetime
    experiment_path.mkdir(parents=True, exist_ok=False)
    os.chdir(experiment_path)

    git_utils.checkout_workspace(reference, workspace_path, experiment_path)

    repcon.config.ExperimentConfig(
        workspace_rel_path, commit, command
    ).dump()

    # TODO: run commands
