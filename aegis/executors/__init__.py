# aegis/executors/__init__.py
from .http import HttpExecutor
from .local import LocalExecutor
from .pwntools import PwntoolsExecutor
from .selenium import SeleniumExecutor
from .ssh import SSHExecutor

__all__ = [
    "SSHExecutor",
    "LocalExecutor",
    "HttpExecutor",
    "SeleniumExecutor",
    "PwntoolsExecutor",
]
