from __future__ import annotations

import click

from pyrex.scripts.experiment import create
from pyrex.scripts.templates import templates

# from pyrex.scripts.workspace import workspace


@click.group
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    # TODO is it super smart or super dumb to assign ctx.obj as a loaded input config?


cli.add_command(create)
cli.add_command(templates)
# cli.add_command(workspace)

if __name__ == "__main__":
    cli(obj={})
