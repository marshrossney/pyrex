from __future__ import annotations

import dataclasses
import logging
import pathlib
import shlex
import shutil
import subprocess

import click
from cookiecutter.main import cookiecutter

from pyrex.config import InputConfig, OutputConfig, ExperimentsCollection
import pyrex.data
from pyrex.exceptions import InvalidConfigError, InvalidPathError
import pyrex.utils

log = logging.getLogger(__name__)


@click.command(context_settings={"ignore_unknown_options": True})
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(path_type=str, resolve_path=True),
    help="Create the experiment here, overriding the default location",
)
@click.option(
    "--run",
    is_flag=True,
    help="After creation, immediately run the commands using Python's subprocess.run utility",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.argument(
    "experiment_name",
    type=click.STRING,
)
@click.argument(
    "arguments",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def create(output_path, run, yes, experiment_name, arguments):
    """Help about command"""

    workspace = InputConfig.search_parents()
    workspace_root = pathlib.Path(workspace.root).resolve()

    repository = pyrex.data.Repository.detect(workspace_root)
    author = pyrex.data.Author.detect(workspace_root)

    experiments_collection = ExperimentsCollection.load(
        workspace_root.joinpath(workspace.experiments_file)
    )
    experiment = experiments_collection[experiment_name]

    extra_files = pyrex.utils.parse_files_from_command(arguments, where=workspace_root)
    experiment.files + extra_files

    for file in experiment.files:
        filepath = workspace_root.joinpath(file)
        if not filepath.exists():
            raise InvalidConfigError(
                "File '{file}' not found in workspace"
            ) from FileNotFoundError
        if not filepath.resolve().is_file():
            raise InvalidConfigError("Only files can be copied") from IsADirectoryError

    output_path = (
        output_path or experiment.output_path or workspace.experiments_output_path
    )
    # NOTE: actually compiling an f-string probably a bad idea, hence use of replace
    output_path = pathlib.Path(
        output_path.replace("{workspace_root}", workspace.root)
        .replace("{workspace_name}", workspace.name)
        .replace("{version}", workspace.version)
        .replace("{repo_root}", repository.root)
        .replace("{repo_name}", repository.name)
        .replace("{branch}", repository.branch)
        .replace("{experiment_name}", experiment_name)
    )
    if not output_path.is_absolute():
        raise InvalidPathError(f"Output path '{output_path}' is not absolute")

    if not output_path.is_relative_to(repository.root):
        log.warning(
            "Output path '%s' is not in the same git repository as the workspace '%s'"
            % (output_path, workspace.root)
        )
    path = pyrex.data.Path.compute(
        output_path.joinpath("dummy"), workspace.root, repository.root
    )

    experiment.commands = [
        command.replace("{workspace}", path.to_workspace_root).replace(
            "{posargs}", arguments
        )
        for command in experiment.commands
    ]

    output = OutputConfig(
        author=author,
        path=path,
        repository=repository,
        experiment=experiment,
        workspace=workspace,
    )

    click.echo(output)
    click.echo(output_path)
    if not yes:
        click.confirm(
            "Confirm",
            prompt_suffix="?",
            default="yes",
            show_default=True,
            abort=True,
        )

    extra_context = {f"_{key}": val for key, val in dataclasses.asdict(output).items()}
    experiment_root = cookiecutter(
        template=experiment.template.template,
        checkout=experiment.template.checkout,
        directory=experiment.template.directory,
        password=experiment.template.password,
        output_dir=str(output_path),
        extra_context=extra_context,
        no_input=True,
    )
    experiment_root = pathlib.Path(experiment_root)

    for file in experiment.files:
        experiment_root.joinpath(file).parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(workspace_root / file, experiment_root / file)

    output.dump(experiment_root)
    # TODO dump log as well

    click.echo("Commands to run:")
    click.echo("\n".join(command for command in experiment.commands))

    if run:
        if not yes:
            click.confirm(
                "Proceed to run experiment",
                prompt_suffix="?",
                default="yes",
                show_default=True,
                abort=True,
            )
        with pyrex.utils.switch_dir(experiment_root):
            for command in experiment.commands:
                subprocess.run(shlex.split(command))


if __name__ == "__main__":
    create()
