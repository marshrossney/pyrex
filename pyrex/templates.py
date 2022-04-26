from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import logging
import pathlib
from typing import Optional, Union

from cookiecutter.main import cookiecutter

import pyrepcon.utils as utils

# from cookiecutter.exceptions import CookiecutterException

log = logging.getLogger(__name__)


_TEMPLATES_FILE = pathlib.Path(__file__).with_suffix(".json")


class InvalidTemplateError(Exception):
    pass


@dataclass
class Template:
    template: str
    checkout: Optional[str] = None
    directory: Optional[str] = None
    extra_context: dict[str] = field(default_factory=dict)

    def __post_init__(self):
        template_as_path = pathlib.Path(self.template)
        if template_as_path.exists():
            self.template = str(template_as_path.resolve())

    def build(self, **cookiecutter_kwargs) -> None:
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
        with utils.temp_dir():
            self.build(no_input=True, overwrite_if_exists=True)


class Templates:
    """Container for the templates file."""

    def __init__(self):
        with open(_TEMPLATES_FILE, "r") as file:
            self._templates = json.load(file)

    def __str__(self):
        return json.dumps(self._templates, indent=6)

    def _save(self) -> None:
        try:
            _ = json.dumps(self._templates)
        except (TypeError, OverflowError):
            raise InvalidTemplateError(
                "Object not JSON serializable. Abandoning the save!"
            )
        else:
            with open(_TEMPLATES_FILE, "w") as file:
                json.dump(self._templates, file, indent=6)

    @property
    def names(self) -> list[str]:
        """Returns list of existing template names."""
        return list(self._templates.keys())

    @property
    def dict(self) -> dict[str, Union[str, dict[str, str]]]:
        """Returns templates dict."""
        return self._templates.copy()

    def exists(self, name: str) -> bool:
        """Return True if there is an existing template with 'name'."""
        return name in self._templates

    def load(self, name: str) -> Template:
        """Load template from file."""
        return Template(**self._templates[name])

    def remove(self, name: str) -> None:
        """Remove this template."""
        del self._templates[name]
        self._save()

    def add(self, name: str, template: Template):
        if name in self._templates:
            existing = self.load(name)
            log.warning(f"This action overwrites an existing template: {existing}!")
        template_asdict = {key: val for key, val in asdict(template).items() if val}
        self._templates[name] = template_asdict
        self._save()
