# aegis/cli/http.py
"""
HTTP CLI integration for AEGIS.

Verbs:
  - get, post, put, patch, delete, head

Features:
  - Base URL or absolute URL
  - Headers (-H/--header KEY=VAL, repeatable)
  - Query params (-Q/--param KEY=VAL, repeatable)
  - Body via --data 'raw' or --json '{"k":"v"}' (or @/path/to/file)
  - TLS verification toggle
  - --json to emit ToolResult envelope when available

This module is a thin adapter that prefers HttpExecutor.request_result(...) and
falls back to request(...) for environments that don't yet have ToolResult wrappers.
"""
from __future__ import annotations

from typing import Dict, Optional, Any, List, Tuple
import json
import os
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.cli._common import print_result
from aegis.executors.http_exec import HttpExecutor


def _parse_kv_pairs(pairs: Optional[List[str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not pairs:
        return out
    for item in pairs:
        if "=" not in item:
            # allow KEY:VAL too
            if ":" in item:
                k, v = item.split(":", 1)
            else:
                # drop malformed
                continue
        else:
            k, v = item.split("=", 1)
        out[str(k).strip()] = str(v).strip()
    return out


def _load_payload(arg: Optional[str]) -> Optional[str]:
    """
    Accepts raw string or @/path to read file contents as text.
    Returns None if arg is falsy.
    """
    if not arg:
        return None
    if arg.startswith("@"):
        path = arg[1:]
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return arg


def _maybe_json(s: Optional[str]) -> Optional[Any]:
    if s is None:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="http",
        description="HTTP operations via HttpExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="verb", required=True)

    def add_common(sp: Cmd2ArgumentParser) -> None:
        sp.add_argument("--base-url", help="Base URL (e.g., https://api.example.com)")
        sp.add_argument(
            "path_or_url",
            help="Absolute URL or path (joined to --base-url). Example: /v1/ping or https://example.com/v1/ping",
        )
        sp.add_argument(
            "-H",
            "--header",
            action="append",
            help="Header KEY=VAL (repeatable). Also accepts KEY:VAL",
        )
        sp.add_argument(
            "-Q",
            "--param",
            action="append",
            help="Query param KEY=VAL (repeatable)",
        )
        sp.add_argument("--timeout", type=float, default=30.0)
        sp.add_argument("--verify", action="store_true", default=True)
        sp.add_argument("--no-verify", dest="verify", action="store_false")
        sp.add_argument(
            "--retries", type=int, default=2, help="Max retries for transient errors"
        )
        sp.add_argument(
            "--json",
            dest="json_out",
            action="store_true",
            help="Emit ToolResult JSON if available",
        )

    # Verbs
    for verb in ("get", "head"):
        sp = sub.add_parser(verb, help=f"{verb.upper()} request")
        add_common(sp)

    for verb in ("post", "put", "patch", "delete"):
        sp = sub.add_parser(verb, help=f"{verb.upper()} request")
        add_common(sp)
        sp.add_argument(
            "--data",
            help="Raw body string or @/path/to/file (mutually exclusive with --json-body)",
        )
        sp.add_argument(
            "--json-body",
            dest="json_body",
            help="JSON string or @/path/to/file (mutually exclusive with --data)",
        )

    return p


def _resolve_url(
    base_url: Optional[str], path_or_url: str
) -> Tuple[Optional[str], str]:
    """
    Returns (base_url, request_path_or_url). If path_or_url is absolute URL, we pass it
    as the 'path' to HttpExecutor which should honor it; otherwise we keep base_url.
    """
    pu = path_or_url.strip()
    if pu.startswith("http://") or pu.startswith("https://"):
        return (None, pu)
    return (base_url, pu)


@with_default_category("HTTP")
class HttpCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    async def _do_request_toolresult(
        self,
        exe: HttpExecutor,
        method: str,
        path_or_url: str,
        *,
        headers: Dict[str, str],
        params: Dict[str, str],
        data: Optional[str],
        json_payload: Optional[Any],
        timeout: float,
    ):
        # Prefer ToolResult if present
        if hasattr(exe, "request_result"):
            return await exe.request_result(
                method.upper(),
                path_or_url,
                headers=headers or None,
                params=params or None,
                data=data,
                json=json_payload,
                timeout=timeout,
            )
        # Fallback to plain response object
        resp = await exe.request(
            method.upper(),
            path_or_url,
            headers=headers or None,
            params=params or None,
            data=data,
            json=json_payload,
            timeout=timeout,
        )
        # Create a tiny shim so print_result won't be used; we'll pretty print ourselves
        return resp

    @with_argparser(_make_parser())
    def do_http(self, ns: cmd2.Statement) -> None:
        a = ns
        method: str = a.verb.upper()

        base_url_in, path_or_url = _resolve_url(a.base_url, a.path_or_url)
        headers = _parse_kv_pairs(a.header)
        params = _parse_kv_pairs(a.param)

        # Body handling (only for verbs that allow a body)
        data_str: Optional[str] = None
        json_payload: Optional[Any] = None
        if hasattr(a, "data") or hasattr(a, "json_body"):
            if getattr(a, "data", None) and getattr(a, "json_body", None):
                self.perror("Use either --data or --json-body, not both.")
                return
            if getattr(a, "json_body", None):
                raw = _load_payload(a.json_body)
                jp = _maybe_json(raw)
                if jp is None:
                    self.perror("Invalid JSON for --json-body")
                    return
                json_payload = jp
            elif getattr(a, "data", None):
                data_str = _load_payload(a.data)

        # Construct executor
        try:
            execu = HttpExecutor(
                base_url=base_url_in,
                default_timeout=float(a.timeout),
                verify=bool(a.verify),
                headers=headers or None,
                max_retries=int(getattr(a, "retries", 2)),
            )
        except TypeError:
            # Back-compat for environments with older signature
            execu = HttpExecutor(
                base_url=base_url_in,
                default_timeout=float(a.timeout),
            )

        import anyio

        async def run_once():
            res = await self._do_request_toolresult(
                execu,
                method,
                path_or_url,
                headers=headers,
                params=params,
                data=data_str,
                json_payload=json_payload,
                timeout=float(a.timeout),
            )
            return res

        try:
            res = anyio.run(run_once)
        except Exception as e:
            self.perror(str(e))
            return

        # Print
        if hasattr(res, "ok") and hasattr(res, "stdout"):
            # ToolResult path
            print_result(self._cmd, res, as_json=bool(getattr(a, "json_out", False)))
            return

        # Fallback: plain httpx-like response
        try:
            status = getattr(res, "status_code", None)
            text = getattr(res, "text", None)
            if bool(getattr(a, "json_out", False)):
                payload = {
                    "status_code": status,
                    "text": text,
                }
                self._cmd.poutput(json.dumps(payload, indent=2))
            else:
                self._cmd.poutput(
                    f"[HTTP {status}]\n{text if text is not None else ''}"
                )
        except Exception as e:
            self.perror(f"Unexpected response type: {e}")

        # Best-effort close
        try:
            if hasattr(execu, "aclose"):
                anyio.run(execu.aclose)
        except Exception:
            pass


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(HttpCommandSet())
