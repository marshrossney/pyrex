from __future__ import annotations

import click

from pyrex.config import (
    TemplateConfig,
    WorkspaceTemplateConfigCollection,
    ExperimentTemplateConfigCollection,
)
from pyrex.utils import prompt_for_name


@click.group()
@click.option(
    "-w/-e",
    "select",
    default=None,
    callback=lambda ctx, param, opt: None if opt is None else ("w" if opt else "e"),
    help="Select workspace (-w) or experiment (-e) templates",
)
@click.pass_context
def templates(ctx, select: click.STRING):
    ctx.ensure_object(dict)
    if select is None:
        select = click.prompt(
            "Select workspace (w) or experiment (e) templates",
            type=click.Choice(["w", "e"]),
        )
    if select == "w":
        ctx.obj["TEMPLATES"] = WorkspaceTemplateConfigCollection.load()
    elif select == "e":
        ctx.obj["TEMPLATES"] = ExperimentTemplateConfigCollection.load()


@templates.command()
@click.pass_context
def list(ctx):
    """List saved templates"""
    click.echo(ctx.obj["TEMPLATES"])


@templates.command()
@click.argument(
    "name",
    type=click.STRING,
)
@click.pass_context
def remove(ctx, name: click.STRING):
    """Remove a template from saved templates file"""
    del ctx.obj["TEMPLATES"][name]
    ctx.obj["TEMPLATES"].dump()
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
@click.pass_context
def add_path(ctx, path, name):
    """Add a local path to a template"""
    template = TemplateConfig(template=path)
    template.validate()
    name = prompt_for_name(init_name=name, existing_names=ctx.obj["TEMPLATES"].keys)
    ctx.obj["TEMPLATES"][name] = template
    ctx.obj["TEMPLATES"].dump()
    click.echo(f"Successfully added template: {name}!")


@templates.command()
@click.argument(
    "url",
    type=click.STRING,
)
@click.option(
    "--checkout",
    type=click.STRING,
    prompt=True,
    default=None,
    show_default=True,
    callback=lambda ctx, param, opt: opt or None,
    help="Branch, tag, or commit to checkout",
)
@click.option(
    "--directory",
    type=click.STRING,
    prompt=True,
    default=None,
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
@click.pass_context
def add_repo(ctx, url, checkout, directory, name):
    """Add a remote git repository containing a template"""
    template = TemplateConfig(template=url, checkout=checkout, directory=directory)
    template.validate()
    name = prompt_for_name(init_name=name, existing_names=ctx.obj["TEMPLATES"].keys())
    ctx.obj["TEMPLATES"][name] = template
    ctx.obj["FILE"].dump()
    click.echo(f"Successfully added template: {name}!")


if __name__ == "__main__":
    templates()
