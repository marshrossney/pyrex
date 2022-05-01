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
    _abort = True
    _choices = []
    _default = ""
    _show_choices = False

else:
    _abort = False
    _exception = None
    _choices = list(_active_workspace.config.experiments.keys())
    _default = _choices[0] if len(_choices) > 0 else ""
    _show_choices = True

def abort(ctx, param, abort_flag):
    if abort_flag:
        click.echo(ctx.get_help())
        ctx.exit()

@click.command()
@click.option(
    "--abort",
    is_flag=True,
    default=_abort,
    is_eager=True,
    hidden=True,
    callback=abort,
    expose_value=False,
)
@click.option(
    "-e",
    "--experiment",
    "name",
    prompt="Experiment name",
    type=click.Choice(_choices),
    show_choices=_show_choices,
    default=_default,
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
    "arguments",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def create(name, output, run, prompt, arguments):
    """Help about command"""
    if _exception is not None:
        raise _exception

    experiment = _active_workspace.create_experiment(
        experiment_name=name,
        command_posargs=arguments,
        experiment_path=output,
        prompt=prompt,
    )

    if run:
        experiment.run_experiment(name)


if __name__ == "__main__":
    create()
