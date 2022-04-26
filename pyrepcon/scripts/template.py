from __future__ import annotations

import click


@click.group()
def template():
    pass


@click.command()
def add(args):
    pass


@click.command()
def remove(name):
    pass


if __name__ == "__main__":
    template()
