from __future__ import annotations

import pathlib
import shlex

import click

from pyrex.exceptions import InvalidWorkspaceError
import pyrex.workspace
import pyrex.utils as utils

try:
    _active_workspace = pyrex.workspace.PyrexWorkspace.search_parents()
except InvalidWorkspaceError as _exception:
    _choices = []
    _show_choices = False
else:
    _exception = None
    _choices = _active_workspace.config.experiments.keys()
    _show_choices = True


@click.command()
@click.option(
    "-e",
    "--experiment",
    "name",
    prompt="Experiment name",
    type=click.Choice(_choices),
    show_choices=_show_choices,
    help="Experiment name",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=pathlib.Path, resolve_path=True),
    help="Create the experiment here, overriding the default location",
    callback=lambda ctx, param, output: None
    if not output
    else (
        output
        if not output.exists()
        else utils.raise_(
            FileExistsError(f"Output directory '{output}' already exists!")
        )
    ),
)
@click.option(
    "--run/--no-run",
    default=True,
    show_default=True,
    help="After creation, run the experiment as a Python subprocess",
)
@click.option(
    "--prompt/--no-prompt",
    default=True,
    show_default=True,
    help="Prompt user for confirmation before creating and running experiment",
)
@click.argument(
    "posargs",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args)
)
def create(name, output, run, prompt, posargs):
    """Help about command"""
    if _exception is not None:
        raise _exception

    experiment = _active_workspace.create_experiment(
        experiment_name=name,
        command_posargs=posargs,
        experiment_path=output,
        prompt=prompt,
    )

    if run:
        experiment.run_experiment()


if __name__ == "__main__":
    create()
