from __future__ import annotations

import shlex

import click

from pyrex.exceptions import InvalidWorkspaceError
from pyrex.experiment import ExperimentConfig
from pyrex.workspace import Workspace
from pyrex.templates import WorkspaceTemplatesFile
from pyrex.utils import prompt_for_name, parse_files_from_command

_templates_file = WorkspaceTemplatesFile()


@click.group("workspace")
def pyrex_workspace():
    pass


@pyrex_workspace.command()
@click.option(
    "-n",
    "--name",
    type=click.STRING,
    help="A name to associate with this experiment",
)
@click.option(
    "-f",
    "--files",
    type=click.Path(exists=True, dir_okay=False),
    multiple=True,
    default=[],
    callback=lambda ctx, name, files: list(files),
    help="Paths to files required in the working directory",
)
@click.option(
    "-e",
    "--exec-dir",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Path to subdirectory of workspace in which to execute command",
)
@click.argument(
    "command",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def add_exp(name, files, exec_dir, command):
    """Add a named experiment configuration."""
    workspace = Workspace.search_parents()
    named_experiments = workspace.named_experiments

    # TODO: make interactive for command, files

    try:
        default_experiments_path = workspace.config["default_experiments_path"]
    except KeyError:
        default_experiments_path = (
            "{workspace}/experiments/"  # TODO set global default
        )
    output_path = default_experiments_path  # TODO make interactive

    files = parse_files_from_command(command) + files

    name = prompt_for_name(init_name=name, existing_names=named_experiments.keys())

    output_path = output_path.replace("{name}", name)

    experiment_config = ExperimentConfig(
        command=command, output_path=output_path, files=files, exec_dir=exec_dir
    )

    click.echo(str(experiment_config))
    if click.confirm(
        "Confirm", prompt_suffix="?", default=True, show_default=True, abort=True
    ):
        named_experiments[name] = experiment_config

        click.echo(f"Successfully added experiment: {name}")
        click.echo(f"Experiment configuration written to {named_experiments.filepath}")



@pyrex_workspace.command()
def init():
    """Initialise a PyREx workspace in the current working directory"""
    _ = Workspace.init()


@pyrex_workspace.command()
def info():
    """Display information about the current workspace"""
    try:
        click.echo(str(Workspace.search_parents()))
    except InvalidWorkspaceError as e:
        click.echo(e)


if __name__ == "__main__":
    workspace()
