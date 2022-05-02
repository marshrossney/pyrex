from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import os
import pathlib
from typing import Any, Optional, Union
from sys import version_info

# import yaml
import click

from pyrex.exceptions import InvalidTemplateError
from pyrex.utils import temp_dir

WORKSPACE_TEMPLATES_FILE = pathlib.Path(__file__).with_name("templates.json")


@dataclass
class WorkspaceTemplate:
    template: str
    checkout: Optional[str] = None
    directory: Optional[str] = None
    extra_context: dict[str] = field(default_factory=dict)

    def __post_init__(self):
        template_as_path = pathlib.Path(self.template)
        if template_as_path.exists():
            self.template = str(template_as_path.resolve())

        python_version = (
            f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        )
        self.extra_context.update({"__python_version": python_version})

    def create_workspace(self, **cookiecutter_kwargs) -> None:
        if "extra_context" in cookiecutter_kwargs:
            self.extra_context.update(cookiecutter_kwargs.pop("extra_context"))

        from cookiecutter.main import cookiecutter

        cookiecutter(
            template=self.template,
            checkout=self.checkout,
            directory=self.directory,
            extra_context=self.extra_context,
            **cookiecutter_kwargs,
        )

    def validate(self) -> None:
        with temp_dir():
            self.create_workspace(no_input=True, overwrite_if_exists=True)


class JSONConfigFile:
    """Container for JSON config files."""

    def __init__(self, filepath: Union[str, os.PathLike]) -> None:
        self._filepath = pathlib.Path(filepath).resolve()
        self._load()

    def __str__(self) -> str:
        return json.dumps(self._elements, indent=4) if self._elements else "Empty!"

    def __len__(self) -> int:
        return len(self._elements)

    def __contains__(self, item) -> bool:
        return item in self._elements

    def __getitem__(self, key) -> Any:
        return self._elements[key]

    def __setitem__(self, key, value) -> None:
        try:
            key = key.replace(" ", "-")  # really don't want crappy keys
        except TypeError:
            raise TypeError(f"Unable to convert type '{type(key)}' to string slug")
        if key in self.illegal_keys:
            raise KeyError(f"Illegal key: '{key}'")
        if key in self:
            raise KeyError(f"An element with key '{key}' already exists!")
        self._elements.update({key: value})
        self._update()

    def __delitem__(self, key) -> None:
        del self._elements[key]
        self._update()

    def _load(self) -> None:
        with self._filepath.open("r") as file:
            contents = json.load(file)
        if not contents:
            pass
            # click.echo(f"Loaded an empty config file: '{self._filepath}'")
        self._elements = contents

    def _update(self) -> None:
        try:
            _ = json.dumps(self._elements)
        except (TypeError, OverflowError):
            raise InvalidTemplateError(
                "Object not JSON serializable. Abandoning the write!"
            )
        else:
            with open(self._filepath, "w") as file:
                json.dump(self._elements, file, indent=6)

    @staticmethod
    def touch(filepath: Union[str, os.PathLike]) -> None:
        if not pathlib.Path(filepath).exists():
            with open(filepath, "w") as file:
                json.dump(dict(), file, indent=6)
            click.echo(f"Created a new file: '{filepath}'")

    def keys(self) -> list:
        return list(self._elements.keys())

    @property
    def filepath(self) -> pathlib.Path:
        return self._filepath


class WorkspaceTemplatesFile(JSONConfigFile):
    """Class acting as a container for a PyREx workspace templates file."""

    str_header = "Available templates:"

    def __init__(
        self, filepath: Union[str, os.PathLike] = WORKSPACE_TEMPLATES_FILE
    ) -> None:
        super().__init__(filepath)

    def __getitem__(self, key: str) -> WorkspaceTemplate:
        return WorkspaceTemplate(**super().__getitem__(key))

    def __setitem__(self, key: str, value: WorkspaceTemplate) -> None:
        template_stripped = {key: val for key, val in asdict(value).items() if val}
        super().__setitem__(key, template_stripped)


"""
        if self.str_header:
            contents = "\n".join(
                [
                    self.str_header,
                    "".join(["-" for _ in self.str_header]),
                    contents,
                ]
            )
        if self.str_footer:
            contents = "\n".join(
                [
                    contents,
                    "".join(["-" for _ in self.str_footer]),
                    self.str_footer,
                ]
            )
            """
