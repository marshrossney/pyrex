from __future__ import annotations


import click

from pyrex.scripts.pyrex_experiment import pyrex_experiment
from pyrex.scripts.pyrex_templates import pyrex_templates
from pyrex.scripts.pyrex_workspace import pyrex_workspace


@click.group()
def cli():
    pass


cli.add_command(pyrex_experiment)
cli.add_command(pyrex_templates)
cli.add_command(pyrex_workspace)


if __name__ == "__main__":
    cli()
