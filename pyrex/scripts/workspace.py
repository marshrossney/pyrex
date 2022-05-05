from __future__ import annotations

import dataclasses

import click
from cookiecutter.main import cookiecutter

from pyrex.config import InputConfig, WorkspaceTemplatesCollection
from pyrex.exceptions import InvalidWorkspaceError
from pyrex.utils import prompt_for_name


@click.group("workspace")
def workspace():
    pass


@workspace.command()
@click.argument(
    "name",
    type=click.STRING,
)
def create(name):
    """Create a new workspace from a template"""
    templates = WorkspaceTemplatesCollection.load()
    template = templates[name]
    click.echo(template)
    click.confirm(
        "Confirm", prompt_suffix="?", default="yes", show_default=True, abort=True
    )
    workspace = cookiecutter(**dataclasses.asdict(template))
    click.echo(f"Workspace created at f{workspace}")


@workspace.command()
def info():
    """Display information about the current workspace"""
    try:
        click.echo(str(InputConfig.search_parents()))
    except InvalidWorkspaceError as exc:
        click.echo(exc)


@workspace.command()
def init():
    """Initialise a PyREx workspace in the current working directory"""
    # TODO interactively generate a workspace
    raise NotImplementedError


@workspace.command()
def add_exp():
    """Add a named experiment to the current workspace."""
    # TODO interactively generate an experiment config
    raise NotImplementedError


if __name__ == "__workspace__":
    workspace()
