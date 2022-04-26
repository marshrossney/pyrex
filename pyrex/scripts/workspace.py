from __future__ import annotations

import click


@click.group()
def workspace():
    pass


@workspace.command()
@click.option(
    "--version",
    prompt=True,
    type=click.STRING,
    default="0.1.0",
    help="Attribute a version to the workspace",
)
@click.option(
    "--named-experiments-path",
    prompt="Default path for named experiments",
    type=click.STRING,
    default="{branch}/{version}/{name}/{timestamp}",
    help="Default path for named experiments",
)
@click.option(
    "--unnamed-experiments-path",
    prompt="Default path for unnamed experiments",
    type=click.STRING,
    default="{branch}/{version}/unnamed/{timestamp}",
    help="Default path for named experiments",
)
def init(version, named_experiment_path, unnamed_experiments_path):
    pass


@workspace.command()
@click.argument(
    "template",
    type=click.STRING,
)
def create(template):
    pass


@workspace.command()
def config():
    pass

    # workspace = api.Workspace.search_parents()
    # workspace_config = workspace.load_config()


if __name__ == "__main__":
    workspace()
