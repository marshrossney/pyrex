from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import logging
import pathlib
from pprint import pprint
from typing import Optional

log = logging.getLogger(__name__)


_TEMPLATES_FILE = pathlib.Path(__file__).with_suffix(".json")


class InvalidTemplateError(Exception):
    pass


@dataclass
class Template:
    location: str
    branch: Optional[str] = None
    tag: Optional[str] = None
    commit: Optional[str] = None
    subdir: Optional[str] = None

    def __post_init__(self):
        if sum([bool(self.branch), bool(self.tag), bool(self.commit)]) > 1:
            raise InvalidTemplateError(
                "Only one of branch, tag and commit should be given"
            )
        # NOTE: I'm not attempting to duplicate checks performed by cookiecutter
        # Should only save templates after successful completion of cookiecutter,
        # and it's up to the user to make sure they don't break later on

    @staticmethod
    def show_all() -> None:
        """Prints all of the saved templates."""
        with open(_TEMPLATES_FILE, "r") as file:
            templates = json.load(file)
        pprint(templates)

    @classmethod
    def load(cls, name: str) -> Template:
        """Load templates file."""
        with open(_TEMPLATES_FILE, "r") as file:
            templates = json.load(file)
        return cls(**templates[name])

    def save(self, name: str) -> None:
        """Save this template so it can be accessed by name in future."""
        with open(_TEMPLATES_FILE, "w") as file:
            templates = json.load(file)

        log.info("Saving template {name} : {self}")
        if self.name in templates:
            existing = type(self)(**templates[self.name])
            log.warning(f"This action overwrites an existing template: {existing}!")

        templates[self.name] = {key: val for key, val in asdict(self) if val}
        try:
            _ = json.dumps(templates)
        except (TypeError, OverflowError):
            raise InvalidTemplateError(
                "Resulting templates file is not JSON serializable. Abandoning!"
            )
        else:
            with open(_TEMPLATES_FILE, "w") as file:
                json.dump(templates, file, indent=6)
