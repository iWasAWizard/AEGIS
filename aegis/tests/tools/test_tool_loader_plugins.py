# tests/tools/test_tool_loader_plugins.py
import textwrap
from pathlib import Path

import pytest
from pydantic import BaseModel

from aegis.registry import get_tool, reset_registry_for_tests
from aegis.utils.tool_loader import import_plugins_from_dir


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()


def _write_plugin(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def test_imports_standalone_file_plugin(tmp_path: Path):
    plugin = textwrap.dedent(
        """
        from pydantic import BaseModel
        from aegis.registry import tool

        class EchoIn(BaseModel):
            msg: str

        @tool("plugins.echo", EchoIn)
        def echo(*, input_data: EchoIn):
            return {"echo": input_data.msg}
        """
    )
    _write_plugin(tmp_path, "my_plugins/echo_tool.py", plugin)

    import_plugins_from_dir(tmp_path / "my_plugins")
    t = get_tool("plugins.echo")
    assert t.name == "plugins.echo"
    assert t.input_model.__name__ == "EchoIn"


def test_imports_package_modules_once(tmp_path: Path):
    pkg_init = ""
    mod = textwrap.dedent(
        """
        from pydantic import BaseModel
        from aegis.registry import tool
        class K(BaseModel): q: int
        @tool("pkg.k", K)
        def run(*, input_data: K):
            return input_data.q
        """
    )
    _write_plugin(tmp_path, "plugpkg/__init__.py", pkg_init)
    _write_plugin(tmp_path, "plugpkg/kmod.py", mod)

    import_plugins_from_dir(tmp_path / "plugpkg")
    import_plugins_from_dir(tmp_path / "plugpkg")  # idempotent

    t = get_tool("pkg.k")
    assert t.name == "pkg.k"


def test_broken_plugin_does_not_crash_import(tmp_path: Path):
    bad = "raise RuntimeError('boom at import')"
    _write_plugin(tmp_path, "my_plugins/bad.py", bad)

    # Should not raise
    import_plugins_from_dir(tmp_path / "my_plugins")

    # And obviously the bad tool shouldn't exist
    with pytest.raises(Exception):
        get_tool("bad.tool")


def test_package_relative_imports_work(tmp_path: Path):
    # pkg with two modules where one imports the other
    _write_plugin(tmp_path, "p/__init__.py", "")
    _write_plugin(tmp_path, "p/common.py", "VALUE = 42")
    mod = textwrap.dedent(
        """
        from pydantic import BaseModel
        from aegis.registry import tool
        from .common import VALUE

        class Z(BaseModel):
            pass

        @tool("pkg.dep", Z)
        def dep(*, input_data: Z):
            return VALUE
        """
    )
    _write_plugin(tmp_path, "p/dep.py", mod)

    import_plugins_from_dir(tmp_path / "p")
    t = get_tool("pkg.dep")
    assert t.name == "pkg.dep"
