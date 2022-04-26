from __future__ import annotations

import click
from slugify import slugify

import pyrepcon.templates

_templates = pyrepcon.templates.Templates()


@click.group()
def templates():
    pass


@templates.command()
def list():
    """List saved templates"""
    click.echo(str(_templates))


@templates.command()
@click.argument(
    "name",
    type=click.Choice(_templates.names),
)
def remove(name):
    """Remove a template from saved templates file"""
    _templates.remove(name)


@templates.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
def add_path(path):
    """Add a local path to a template"""
    template = pyrepcon.templates.Template(path)
    template.validate()
    name = click.prompt("Name this template", type=click.STRING)
    _templates.add(slugify(name), template)


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
def add_repo(url, checkout, directory):
    """Add a remote git repository containing a template"""
    template = pyrepcon.templates.Template(url, checkout, directory)
    template.validate()

    name = click.prompt("Name this template", type=click.STRING)

    _templates.add(slugify(name), template)
    click.echo(f"Added template {name} : {template}")


if __name__ == "__main__":
    templates()
