from __future__ import annotations

import dataclasses
import logging
import pathlib
import shlex
import shutil
import subprocess

import click
from cookiecutter.main import cookiecutter

import pyrex.config
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

    workspace = pyrex.config.WorkspaceInput.search_parents()
    workspace_root = pathlib.Path(workspace.root)
    author = pyrex.config.AuthorConfig.detect(workspace_root)
    repo = pyrex.config.RepoConfig.detect(workspace_root)
    experiment = workspace.get_experiments()[experiment_name]

    extra_files = pyrex.utils.parse_files_from_command(arguments, where=workspace.root)
    experiment.files += extra_files
    for file in experiment.files:
        filepath = workspace_root.joinpath(file)
        if not filepath.exists():
            raise InvalidConfigError(
                f"File '{file}' not found in workspace"
            ) from FileNotFoundError
        if not filepath.resolve().is_file():
            raise InvalidConfigError("Only files can be copied") from IsADirectoryError

    output_path = (
        output_path or experiment.output_path or workspace.experiments_output_path
    )
    output_path = pathlib.Path(
        str(output_path)
        .replace("{workspace_root}", workspace.root)
        .replace("{workspace_name}", workspace.name)
        .replace("{version}", workspace.version)
        .replace("{repo_root}", repo.root)
        .replace("{repo_name}", repo.name)
        .replace("{branch}", repo.branch)
        .replace("{author}", author.name)
        .replace("{name}", experiment_name)
    )
    if not output_path.is_absolute():
        raise InvalidPathError(f"Output path '{output_path}' is not absolute")
    if not output_path.is_relative_to(repo.root):
        log.warning(
            "Output path '%s' is not in the same git repository as the workspace '%s'"
            % (output_path, str(workspace.root))
        )
    experiment.output_path = str(output_path)

    experiment.commands = [
        command.replace(
            "{workspace}",
            pyrex.utils.compute_relative_path(
                output_path.joinpath("dummy"), workspace.root
            ),
        ).replace("{posargs}", arguments)
        for command in experiment.commands
    ]

    dummy_path = pathlib.Path(output_path).joinpath("dummy")
    path_to_workspace_root = pyrex.utils.compute_relative_path(
        from_=dummy_path, to=workspace.root
    )
    path_to_repo_root = pyrex.utils.compute_relative_path(
        from_=dummy_path, to=repo.root
    )

    template = pyrex.utils.get_template(
        experiment.template or workspace.experiments_template,
        type_="experiment",
    )

    summary = pyrex.config.ExperimentSummary(
        author=author,
        experiment=experiment,
        repo=repo,
        workspace=workspace,
        path_to_workspace_root=path_to_workspace_root,
        path_to_repo_root=path_to_repo_root,
    )

    click.echo(summary)
    if not yes:
        click.confirm(
            "Confirm",
            prompt_suffix="?",
            default="yes",
            show_default=True,
            abort=True,
        )

    extra_context = {f"_{key}": val for key, val in dataclasses.asdict(summary).items()}
    experiment_root = cookiecutter(
        template=template.template,
        checkout=template.checkout,
        directory=template.directory,
        output_dir=str(output_path),
        extra_context=extra_context,
        no_input=True,
    )
    experiment_root = pathlib.Path(experiment_root)

    for file in experiment.files:
        experiment_root.joinpath(file).parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(workspace_root / file, experiment_root / file)

    summary.dump(experiment_root)
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
