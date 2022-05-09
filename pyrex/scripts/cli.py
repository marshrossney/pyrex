from __future__ import annotations

import click

from pyrex.scripts.experiment import create
from pyrex.scripts.templates import templates
from pyrex.scripts.workspace import workspace


@click.group
def cli():
    """A tool to facilitate the production of reproducible experiments."""
    pass


cli.add_command(create)
cli.add_command(templates)
cli.add_command(workspace)

if __name__ == "__main__":
    cli(obj={})
