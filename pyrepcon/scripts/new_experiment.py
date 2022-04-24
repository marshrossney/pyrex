from __future__ import annotations

import pathlib
from typing import Optional

import click

import pyrepcon.api as api


@click.command()
@click.option("--name", type=click.STRING, help="name of experiment")
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path.cwd(),
    help="hi",
)
@click.option(
    "--files",
    type=click.Path(exists=True, path_type=pathlib.Path),
    nargs=2,
    default=None,
    help="files or directories to copy",
)
@click.option(
    "--command", type=click.STRING, default=None, help="commands to run upon creation"
)
@click.option(
    "--override-path",
    type=click.Path(path_type=pathlib.Path),
    default=pathlib.Path.cwd(),
    help="override default path for experiment",
)
def main(
    name: str,
    workspace: pathlib.Path,
    files: Optional[list[pathlib.Path]],
    command: Optional[list[str]],
    override_path: Optional[pathlib.Path],
):
    override_path = None

    workspace = api.Workspace(workspace)
    experiment = workspace.new_experiment(name, command, files, override_path)
    api.run_experiment(experiment)


if __name__ == "__main__":
    main()
