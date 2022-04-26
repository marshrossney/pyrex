from __future__ import annotations


import click

from pyrepcon.scripts.experiment import experiment
from pyrepcon.scripts.workspace import workspace
from pyrepcon.scripts.templates import templates


@click.group()
def pyrex():
    pass


pyrex.add_command(experiment)
pyrex.add_command(workspace)
pyrex.add_command(templates)


if __name__ == "__main__":
    pyrex()
