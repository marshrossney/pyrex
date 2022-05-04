import pathlib
import importlib.metadata

__version__ = importlib.metadata.version("pyrex")

INPUT_CONFIG_FILE = ".pyrex_workspace.yaml"
OUTPUT_CONFIG_FILE = ".pyrex_experiment.yaml"

WORKSPACE_TEMPLATES_FILE = pathlib.Path(__file__).joinpath("templates/workspaces.yaml")
EXPERIMENT_TEMPLATES_FILE = pathlib.Path(__file__).joinpath(
    "templates/experiments.yaml"
)
