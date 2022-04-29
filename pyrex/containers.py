from __future__ import annotations

import json
import os
import pathlib
from typing import Any, Union

from pyrex.exceptions import InvalidTemplateError
from pyrex.utils import prompt_for_name

import click


class JSONConfigFile:
    """Container for JSON config files."""

    illegal_keys: list[str] = [""]
    str_header = ""
    str_footer = ""

    def __init__(self, filepath: Union[str, os.PathLike]) -> None:
        self._filepath = pathlib.Path(filepath).resolve()
        self._load()

    def __str__(self) -> str:
        contents = json.dumps(self._elements, indent=6) if self._elements else "Empty!"
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
        return contents

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
