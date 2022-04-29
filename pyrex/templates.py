from __future__ import annotations

from dataclasses import dataclass, asdict, field
import os
import pathlib
from typing import Optional, Union

from sys import version_info

from cookiecutter.main import cookiecutter

from pyrex.containers import JSONConfigFile
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
            f"py{version_info.major}{version_info.minor}{version_info.micro}"
        )
        self.extra_context.update({"__python_version": python_version})

    def create_workspace(self, **cookiecutter_kwargs) -> None:
        if "extra_context" in cookiecutter_kwargs:
            self.extra_context.update(cookiecutter_kwargs.pop("extra_context"))

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
