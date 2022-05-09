from __future__ import annotations

import io
import itertools
import logging
import pathlib
import os
import shutil
import subprocess
from typing import Callable, Optional, Union

import click
import yaml

import pyrex.config
from pyrex.exceptions import GitError, InvalidTemplateError, InvalidConfigError

log = logging.getLogger(__name__)


def get_template(spec: str, type_: str = "experiment") -> pyrex.config.TemplateConfig:
    if type_ in ["workspace", "w"]:
        templates = pyrex.config.WorkspaceTemplateConfigCollection.load()
    elif type_ in ["experiment", "e"]:
        templates = pyrex.config.ExperimentTemplateConfigCollection.load()
    else:
        raise ValueError

    # First, try to use spec as key for saved template
    try:
        template = templates[spec]
    except (TypeError, KeyError):
        pass
    else:
        return template

    # Second, see if spec is a valid path
    try:
        spec_as_path = pathlib.Path(spec)
    except TypeError:
        pass
    else:
        if spec_as_path.is_dir():
            return pyrex.config.TemplateConfig(str(spec_as_path.resolve()))

    # Finally, see if spec is a mapping
    try:
        return pyrex.config.TemplateConfig(**spec)
    except TypeError:
        pass

    raise InvalidTemplateError


def load_config(
    filepath: Union[str, os.PathLike],
    loader: Callable[io.TextIOWrapper, dict] = yaml.safe_load,
) -> Union[list[dict], dict]:
    try:
        with open(filepath, "r") as file:
            contents = loader(file)
    except Exception as exc:
        raise InvalidConfigError(f"Failed to load config from '{filepath}'") from exc
    else:
        if not any(contents):
            log.warning("Loaded an empty configuration file from %s" % filepath)
        return contents


def dump_config(
    contents: Union[list[dict], dict],
    filepath: Union[str, os.PathLike],
    dumper: Callable[dict, str] = lambda c: yaml.safe_dump(c, indent=4),
) -> None:
    if not any(contents):
        log.warning("Dumping an empty configuration to %s" % filepath)
    try:
        contents_str = dumper(contents)
    except (TypeError, OverflowError) as exc:
        raise InvalidConfigError(
            "Data serialization failed! Config will *not* be written to file."
        ) from exc
    else:
        with open(filepath, "w") as file:
            file.write(contents_str)


def compute_relative_path(
    from_: Union[str, os.PathLike], to: Union[str, os.PathLike]
) -> tuple[str, str]:
    from_ = pathlib.Path(from_).resolve()
    to = pathlib.Path(to).resolve()

    # NOTE: inner loop is through path.parents
    common_parent = None
    for t, f in itertools.product(
        to.joinpath("dummy").parents, from_.joinpath("dummy").parents
    ):
        if t == f:
            common_parent = t
            break
    assert common_parent is not None

    path = (
        pathlib.Path(".")
        .joinpath(*[".." for _ in from_.relative_to(common_parent).parts])
        .joinpath(to.relative_to(common_parent))
    )

    return str(path)


def prompt_for_name(
    init_name: Optional[str] = None,
    existing_names: list[str] = [],
    illegal_names: list[str] = [],
    attempts: int = 5,
):
    for attempt in range(attempts):
        if attempt == 0 and init_name is not None:
            name = init_name
        else:
            name = click.prompt("Name", type=click.STRING)

        slug = name.replace(" ", "-")
        if name != slug:
            click.echo(f"Simplifying: '{name}' --> '{slug}'")
            name = slug

        if not name:
            click.echo("Cannot use empty string as name")
        elif name in illegal_names:
            click.echo(f"Cannot use name '{name}'")
        elif name in existing_names:
            click.echo(f"'{name}' already exists!")
        else:
            return name

    raise click.Abort(f"Giving up after {attempts} attempts")


def git_run_command(
    *args: str,
    where: Union[str, os.PathLike] = ".",
    capture_output=True,
    strip_output=True,
):
    """Runs 'git *args' through subprocess.run, returning the contents of stdout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(where), *args],
            capture_output=capture_output,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(e)

    else:
        if capture_output:
            return result.stdout.strip() if strip_output else result.stdout


def repo_is_dirty(where: Union[str, os.PathLike] = ".") -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(where), "diff-index", "--quiet", "HEAD", "--"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(e)
    else:
        return bool(result.returncode)


def is_valid_remote(url: str) -> bool:
    try:
        _ = git_run_command("ls-remote", url)
    except GitError:
        return False
    else:
        return True


class switch_dir:
    """Context manager for changing to *existing* directory."""

    def __init__(self, path: Union[str, os.PathLike]):
        self.new = pathlib.Path(path)
        assert self.new.is_dir()

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.new)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.old)


class temp_dir:
    def __init__(self):
        self.tmp = pathlib.Path.cwd().joinpath(".pyrex_tmp")
        self.tmp.mkdir(exist_ok=False)

    def __enter__(self):
        self.old = pathlib.Path.cwd()
        os.chdir(self.tmp)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.old)
        shutil.rmtree(self.tmp)


def parse_files_from_command(
    command: str, where: Union[str, os.PathLike] = "."
) -> list[str]:
    where = pathlib.Path(where)
    parts = command.split(" ")
    files = []
    for part in parts:
        try:
            part_as_path = where.joinpath(part)
        except SyntaxError:
            pass
        else:
            if part_as_path.is_file():
                files.append(part)
    return files


def raise_(exc):
    raise exc


def check_for_files(
    directory: pathlib.Path,
    expected: list[str],
    additional: list[str] = [],
    break_after: int = 10,
):
    for path in directory.iterdir():
        if path.is_dir():
            expected, additional = check_for_files(path, expected, additional)
        elif path in expected:
            expected.remove(path)
        else:
            additional.append(path)

        # If huge number of files, e.g. from previously run expt
        if len(additional) > break_after:
            break

    return expected, additional
