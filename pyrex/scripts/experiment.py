from __future__ import annotations

import pathlib
import shlex

import click

from pyrex.exceptions import InvalidWorkspaceError
from pyrex.workspace import PyrexWorkspace
import pyrex.utils as utils


try:
    _active_workspace = PyrexWorkspace.search_parents()
except InvalidWorkspaceError:
    _in_workspace = True
    _experiments = []
    _default_experiment = None
else:
    _in_workspace = False
    _experiments = list(_active_workspace.config.experiments.keys())
    if len(_experiments) == 1:
        _default_experiment = _experiments[0]
    else:
        _default_experiment = None


def _show_help_and_abort(ctx, param, abort_flag):
    if abort_flag:
        click.echo(ctx.get_help())
        ctx.exit()


def _abort_if_outside_workspace(func):
    func = click.option(
        "--abort",
        is_flag=True,
        default=_in_workspace,
        is_eager=True,
        hidden=True,
        callback=_show_help_and_abort,
        expose_value=False,
    )(func)
    return func


@click.command(context_settings={"ignore_unknown_options": True})
@_abort_if_outside_workspace
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
@click.argument(
    "name",
    type=click.Choice(_experiments),
)
@click.argument(
    "arguments",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def create(name, output, run, prompt, arguments):
    """Help about command"""

    experiment = _active_workspace.create_experiment(
        experiment_name=name,
        command_posargs=arguments,
        experiment_path=output,
        prompt=prompt,
    )

    if run:
        experiment.run_experiment(name)


@click.command(context_settings={"ignore_unknown_options": True})
@_abort_if_outside_workspace
@click.option(
    "--prompt/--no-prompt",
    default=True,
    show_default=True,
    help="Prompt user for confirmation before creating and running experiment",
)
@click.argument(
    "name",
    type=click.Choice(_experiments),
    default=_default_experiment,
)
@click.argument(
    "arguments",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def run(name, arguments, prompt):
    _active_workspace.run_experiment(
        experiment_name=name,
        command_posargs=arguments,
        prompt=prompt,
    )


if __name__ == "__main__":
    create()
