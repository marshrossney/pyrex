from __future__ import annotations

import pathlib
import shlex

import click

from pyrex.exceptions import InvalidExperimentError, InvalidWorkspaceError
import pyrex.workspace
import pyrex.utils as utils
import pyrex.experiment

try:
    _active_workspace = pyrex.workspace.Workspace.search_parents()
except InvalidWorkspaceError as _exception:
    _choices = []
    _show_choices = False
else:
    _exception = None
    _choices = _active_workspace.named_experiments.keys()
    _show_choices = True

@click.command("experiment")
@click.argument(
    "name",
    type=click.Choice(_choices),
    #show_choices=_show_choices,
    #prompt="Name",
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
    default=False,
    show_default=True,
    help="After creation, run the experiment as a Python subprocess",
)
@click.option(
    "--prompt/--no-prompt",
    default=True,
    show_default=True,
    help="Prompt user for confirmation before creating and running experiment",
)
def pyrex_experiment(name, output, run, prompt):
    """Help about command"""
    if _exception is not None:
        raise _exception

    experiment = _active_workspace.create_experiment(name, output)

    if run:
        experiment.run(skip_validation=True)


if __name__ == "__main__":
    pyrex_experiment()
