# aegis/cli/redis.py
"""
Redis CLI integration for AEGIS.

Subcommands:
  - get        : Get a value by key
  - set        : Set a value by key (optional expiry)
  - del        : Delete a key

This module is a thin adapter that calls `aegis.executors.redis_exec.RedisExecutor`
ToolResult wrappers directly. No business logic is duplicated here.
"""
from __future__ import annotations

from typing import Optional
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.redis_exec import RedisExecutor
from aegis.cli._common import print_result


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="redis",
        description="Redis operations via RedisExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    # Common connection options builder
    def add_conn_opts(sp: Cmd2ArgumentParser) -> None:
        sp.add_argument(
            "--host", default="localhost", help="Redis host (default: localhost)"
        )
        sp.add_argument(
            "--port", type=int, default=6379, help="Redis port (default: 6379)"
        )
        sp.add_argument("--db", type=int, default=0, help="DB index (default: 0)")
        sp.add_argument("--password", help="Password (if required)")
        sp.add_argument(
            "--timeout", type=int, default=5, help="Socket timeout seconds (default: 5)"
        )
        sp.add_argument(
            "--json",
            dest="json_out",
            action="store_true",
            help="Emit ToolResult as JSON",
        )

    # get
    p_get = sub.add_parser("get", help="Get value")
    add_conn_opts(p_get)
    p_get.add_argument("key", help="Key to fetch")

    # set
    p_set = sub.add_parser("set", help="Set value")
    add_conn_opts(p_set)
    p_set.add_argument("key", help="Key to set")
    p_set.add_argument("value", help="Value to set")
    p_set.add_argument(
        "--expire", type=int, dest="expire_s", help="Expiration in seconds"
    )

    # del
    p_del = sub.add_parser("del", help="Delete key")
    add_conn_opts(p_del)
    p_del.add_argument("key", help="Key to delete")

    return p


@with_default_category("Redis")
class RedisCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    def _exe(
        self, host: str, port: int, db: int, password: Optional[str], timeout: int
    ) -> RedisExecutor:
        # Instantiate per-invocation so different flags map cleanly
        return RedisExecutor(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=timeout,
        )

    @with_argparser(_make_parser())
    def do_redis(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "get":
            exe = self._exe(a.host, a.port, a.db, a.password, a.timeout)
            res = exe.get_value_result(a.key)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "set":
            exe = self._exe(a.host, a.port, a.db, a.password, a.timeout)
            res = exe.set_value_result(a.key, a.value, expire_s=a.expire_s)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "del":
            exe = self._exe(a.host, a.port, a.db, a.password, a.timeout)
            res = exe.delete_value_result(a.key)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        self.perror(f"Unknown subcommand: {a.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(RedisCommandSet())
