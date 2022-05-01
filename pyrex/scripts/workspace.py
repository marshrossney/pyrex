from __future__ import annotations

import click

from pyrex.exceptions import InvalidWorkspaceError
from pyrex.workspace import PyrexWorkspace
from pyrex.templates import WorkspaceTemplate, WorkspaceTemplatesFile
from pyrex.utils import prompt_for_name

_templates_file = WorkspaceTemplatesFile()


@click.group("workspace")
def workspace():
    pass


@workspace.command()
@click.argument(
    "name",
    type=click.Choice(_templates_file.keys()),
)
def create(name):
    """Create a new workspace from a template"""
    template = _templates_file[name]  # WorkspaceTemplate instance
    template.create_workspace()


@workspace.command()
def init():
    """Initialise a PyREx workspace in the current working directory"""
    # TODO interactive
    pass


@workspace.command()
def info():
    """Display information about the current workspace"""
    try:
        click.echo(str(PyrexWorkspace.search_parents()))
    except InvalidWorkspaceError as e:
        click.echo(e)


@workspace.group()
def templates():
    pass


@templates.command()
def list():
    """List saved templates"""
    click.echo(str(_templates_file))


@templates.command()
@click.argument(
    "name",
    type=click.Choice(_templates_file.keys()),
)
def remove(name):
    """Remove a template from saved templates file"""
    del _templates_file[name]
    click.echo(f"Successfully removed template: {name}")


@templates.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "-n",
    "--name",
    type=click.STRING,
    help="Name to associate with template",
)
def add_path(path, name):
    """Add a local path to a template"""
    template = WorkspaceTemplate(template=path)
    template.validate()
    name = prompt_for_name(init_name=name, existing_names=_templates_file.keys())
    _templates_file[name] = template
    click.echo(f"Successfully added template: {name}!")


# TODO: allow user to specify extra context for template
@templates.command()
@click.argument(
    "url",
    type=click.STRING,
)
@click.option(
    "--checkout",
    type=click.STRING,
    prompt=True,
    default="",
    show_default=True,
    callback=lambda ctx, param, opt: opt or None,
    help="Branch, tag, or commit to checkout",
)
@click.option(
    "--directory",
    type=click.STRING,
    prompt=True,
    default="",
    show_default=True,
    callback=lambda ctx, param, opt: opt or None,
    help="Directory containing the template",
)
@click.option(
    "-n",
    "--name",
    type=click.STRING,
    help="Name to associate with template",
)
def add_repo(url, checkout, directory, name):
    """Add a remote git repository containing a template"""
    template = WorkspaceTemplate(template=url, checkout=checkout, directory=directory)
    template.validate()
    name = prompt_for_name(init_name=name, existing_names=_templates_file.keys())
    _templates_file[name] = template
    click.echo(f"Successfully added template: {name}!")


if __name__ == "__workspace__":
    workspace()
