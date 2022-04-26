from __future__ import annotations


import click

from pyrepcon.scripts.experiment import experiment
from pyrepcon.scripts.workspace import workspace
from pyrepcon.scripts.template import template


@click.group()
def pyrex():
    pass


pyrex.add_command(experiment)
pyrex.add_command(workspace)
pyrex.add_command(template)


if __name__ == "__main__":
    pyrex()
