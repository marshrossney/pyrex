from __future__ import annotations

import pathlib
import shlex

import click

import pyrepcon.workspace
import pyrepcon.utils as utils
import pyrepcon.experiment
from pyrepcon.experiment import InvalidExperimentError


@click.command()
@click.option(
    "-n",
    "--name",
    type=click.STRING,
    help="An existing named experiment, or a new name to associate with this experiment",
)
@click.option(
    "-w",
    "--workspace",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path.cwd(),
    show_default="cwd",
    help="Path to the root of a workspace or a subdirectory thereof",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=pathlib.Path, resolve_path=True),
    help="Create the experiment here, overriding the default location",
    callback=lambda ctx, param, output: None
    if not output
    else (
        output
        if not output.exists()
        else utils.raise_(
            FileExistsError(f"Output directory '{output}' already exists!")
        )
    ),
)
@click.option(
    "--run/--no-run",
    default=False,
    show_default=True,
    help="After creation, run the experiment as a Python subprocess",
)
@click.option(
    "--prompt/--no-prompt",
    default=True,
    show_default=True,
    help="Skip prompts",
)
@click.argument(
    "command",
    type=click.STRING,
    nargs=-1,
    callback=lambda ctx, param, args: shlex.join(args),
)
def experiment(name, workspace, output, run, prompt, command):
    """Help about command"""
    workspace = pyrepcon.workspace.Workspace.search_parents(workspace)
    workspace_config = workspace.load_config()

    # Neither name nor command were provided
    if not name and not command:
        if not prompt:
            raise InvalidExperimentError(
                "Neither an existing named experiment or a command was provided"
            )

        # > PROMPT FOR NAME
        name = click.prompt(
            "Experiment",
            type=click.Choice(
                list(workspace_config.named_experiments.keys()) + ["NEW"]
            ),
            show_choices=True,
            default="NEW",
            show_default=True,
        )
        if name == "NEW":
            name = None

            # > PROMPT FOR COMMAND
            command = click.prompt(
                "Command",
                type=click.STRING,
            )

    # Name provided without command => should be existing named experiment
    if name and not command:
        try:
            experiment_config = workspace_config.named_experiments[name]
        except KeyError:
            click.echo(
                "Named experiments: {', '.join(list(workspace_config.named_experiments.keys()))}"
            )
            raise InvalidExperimentError("{name} is not an existing named experiment")

    # Command was provided, name may or may not have been
    if command:
        working_dir = utils.parse_files_from_command(command)
        click.echo(
            f"Working directory: {', '.join(working_dir) if working_dir else 'Empty'}."
        )

        # Create an ExperimentConfig just to use the post-init checks
        _ = pyrepcon.experiment.ExperimentConfig(command, working_dir)

        if prompt:

            # > GET ADDITIONAL FILES
            while True:
                if not click.confirm(
                    "Add files/directories to working directory", prompt_suffix="?"
                ):
                    break
                try:
                    # TODO: allow globbing, entering 'ls' to show cwd
                    # probably create a new click type, use glob or pathlib
                    new_file = click.prompt(
                        "File/directory",
                        type=click.Path(exists=True, path_type=str),
                    )
                except FileNotFoundError:
                    click.echo("File/directory does not exist!")
                    continue
                try:
                    _ = pyrepcon.experiment.ExperimentConfig(command, working_dir + [new_file])
                except InvalidExperimentError as e:
                    click.echo(e)
                    continue
                working_dir.append(new_file)

        experiment_config = pyrepcon.experiment.ExperimentConfig(command, working_dir)

    if command and prompt and not name:

        # > NAME EXPERIMENT
        if click.confirm(
            "Name this experiment", default="yes", prompt_suffix="?", show_default=True
        ):
            for attempt in range(5):  # give up after 5 attempts to name experiment
                name = click.prompt("Name", type=click.STRING, default=name)
                try:
                    workspace_config.add_named_experiment(name, experiment_config)
                except InvalidExperimentError as e:
                    click.echo(e)
                    continue
                else:
                    workspace_config.dump(workspace.config_file)
                    break

    experiment_config.command = workspace.parse_command(experiment_config.command)
    experiment_path = output or workspace.get_default_experiment_path(name)

    working_dir_pretty = "\n".join(
        ["\t" + path for path in experiment_config.working_dir]
    )
    summary = f"""
    Experiment Summary
    ==================
    Location: {experiment_path}
    Command: {experiment_config.command}
    Working directory: 
    {working_dir_pretty or '    Empty!'}
    """
    click.echo(summary)

    # > CONFIRM EXPERIMENT
    if prompt:
        click.confirm(
            "Confirm", default="yes", abort=True, prompt_suffix="?", show_default=True
        )

    workspace.create_experiment(experiment_config, experiment_path)

    # > RUN EXPERIMENT
    if prompt and not run:
        run = click.confirm("Run experiment?", default="yes", show_default=True)

    if run:
        pyrepcon.experiment.run_experiment(experiment_path)


if __name__ == "__main__":
    experiment()
