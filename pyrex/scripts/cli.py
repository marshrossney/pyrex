from __future__ import annotations

import click

from pyrex.scripts.experiment import create, run
from pyrex.scripts.workspace import workspace


@click.group
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    # TODO is it super smart or super dumb to ass ctx.obj to a PyrexWorkspace?
    # Pros: can print nice info and shit
    # Cons: not able to set type=click.Choices(experiment_names) since
    # ctx not available -> load workspace globally


cli.add_command(create)
cli.add_command(run)
cli.add_command(workspace)

if __name__ == "__main__":
    cli(obj={})
