from pathlib import Path

import yaml

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class MachineManifest:
    """
    Represents the MachineManifest class.

    Used to define system characteristics, such as architecture and environment variables, for profiling and routing.
    """

    def __init__(self, path: str = "machines.yaml"):
        """
        __init__.
        :param path: Description of path
        :type path: Any
        :return: Description of return value
        :rtype: Any
        """
        self.path = Path(path)
        self.data = {}
        self.load()

    def load(self):
        """
        load.
        :return: Description of return value
        :rtype: Any
        """
        try:
            with self.path.open("r") as f:
                logger.debug(f"Loading machine manifest from {self.path}")
                self.data = yaml.safe_load(f) or {}
        except FileNotFoundError as e:
            logger.warning(f"Manifest file not found: {e}")
            self.data = {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML from {self.path}: {e}")
            self.data = {}
        except Exception as e:
            logger.exception(f"Unexpected error loading machine manifest: {e}")
            self.data = {}

    def get(self, machine: str):
        """
        get.
        :param machine: Description of machine
        :type machine: Any
        :return: Description of return value
        :rtype: Any
        """
        return self.data.get(machine)
