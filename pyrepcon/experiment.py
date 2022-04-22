from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import pathlib
from typing import ClassVar, Union
import subprocess

import pyrepcon.base
import pyrepcon.project
import pyrepcon.workspace
import pyrepcon.git_utils
from pyrepcon.utils import curr_datetime, switch_dir

log = logging.getLogger(__name__)


@dataclass
class ExperimentConfig(pyrepcon.base.BaseConfig):
    filename: ClassVar[str] = ".experiment.json"

    workspace: str
    commit: str
    commands: list[str]


class Experiment(pyrepcon.base.Base):
    config = ExperimentConfig

    @classmethod
    def new(
        cls,
        path: Union[str, os.PathLike],

    ) -> Experiment:
        path = pathlib.Path(str(path)).resolve()
        project = 
        workspace_path = pathlib.Path(str(workspace_path)).resolve()
        assert not path.exists(), f"{path} already exists!"

    @property
    def workspace_root(self) -> pathlib.Path:
        return 

    def run(self) -> None:
        run_dir = self.root / curr_datetime()
        run_dir.mkdir(exists_ok=False)
        with switch_dir(run_dir):
            pyrepcon.git_utils.checkout_workspace(
                self.config.commit, self.workspace_root
            )
            for command in self.config.commands:
                log.info("Executing command: %s" % command)
                subprocess.run(command.split(" "))
