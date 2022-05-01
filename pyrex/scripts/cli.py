from __future__ import annotations

import click

from pyrex.scripts.create import create
from pyrex.scripts.run import run
from pyrex.scripts.workspace import workspace

@click.group
def cli():
    pass

cli.add_command(create)
cli.add_command(run)
cli.add_command(workspace)

if __name__ == "__main__":
    cli()
