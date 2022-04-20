from __future__ import annotations

import logging
import os
import pathlib
from typing import ClassVar, Union
import subprocess

import pyrepcon.git_utils
from pyrepcon.utils import ConfigBase, curr_datetime, switch_dir

log = logging.getLogger(__name__)

EXPERIMENT_CONFIG_DIR = ".experiment"


class ExperimentConfig(ConfigBase):
    config_dir: ClassVar[str] = EXPERIMENT_CONFIG_DIR

    workspace: str
    commit: str
    commands: list[str]


class Experiment:
    def __init__(self, root: Union[str, os.PathLike]):
        self._root = pathlib.Path(str(root)).resolve()
        self._config = ExperimentConfig.load(self._root)
        with switch_dir(self._root):
            self._project_root = pyrepcon.git_utils.root_dir()

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @property
    def project_root(self) -> pathlib.Path:
        return self._project_root

    @property
    def workspace_root(self) -> pathlib.Path:
        return self.project_root / self.config.workspace

    @property
    def loc_in_project(self) -> pathlib.Path:
        return self.root.relative_to(self.project_root)

    @property
    def config(self) -> ExperimentConfig:
        return self._config

    def run(self) -> None:
        experiment_dir = self.root / curr_datetime()
        experiment_dir.mkdir(exists_ok=False)
        with switch_dir(experiment_dir):
            pyrepcon.git_utils.checkout_workspace(
                self.config.commit, self.workspace_root
            )
            for command in self.config.commands:
                log.info("Executing command: %s" % command)
                subprocess.run(command.split(" "))
