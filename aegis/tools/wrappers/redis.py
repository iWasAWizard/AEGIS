# aegis/tools/wrappers/redis.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.executors.redis_exec import RedisExecutor
from aegis.schemas.tool_result import ToolResult


# ---------- Shared connection fields ----------


class _RedisConn(BaseModel):
    # Provide either URL or discrete fields
    url: Optional[str] = Field(
        default=None, description="redis://[:password]@host:port/db"
    )
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = 5.0
    decode_responses: bool = True


def _make_client(conn: _RedisConn) -> RedisExecutor:
    if conn.url:
        return RedisExecutor(
            url=conn.url,
            socket_timeout=conn.socket_timeout,
            decode_responses=conn.decode_responses,
        )
    return RedisExecutor(
        host=conn.host,
        port=conn.port,
        db=conn.db,
        password=conn.password,
        ssl=conn.ssl,
        socket_timeout=conn.socket_timeout,
        decode_responses=conn.decode_responses,
    )


# ---------- Inputs per operation ----------


class RedisPingInput(_RedisConn):
    pass


class RedisGetInput(_RedisConn):
    key: str


class RedisSetInput(_RedisConn):
    key: str
    value: Union[str, bytes, int, float]
    ex: Optional[int] = None
    px: Optional[int] = None
    nx: bool = False
    xx: bool = False


class RedisDelInput(_RedisConn):
    keys: List[str]


class RedisKeysInput(_RedisConn):
    pattern: str = "*"


class RedisHGetAllInput(_RedisConn):
    key: str


class RedisExpireInput(_RedisConn):
    key: str
    seconds: int


class RedisEvalInput(_RedisConn):
    script: str
    keys: List[str] = []
    args: List[Any] = []


# ---------- Tools ----------


@tool("redis.ping", RedisPingInput, timeout=5)
def redis_ping(*, input_data: RedisPingInput) -> ToolResult:
    client = _make_client(input_data)
    return client.ping_result()


@tool("redis.get", RedisGetInput, timeout=5)
def redis_get(*, input_data: RedisGetInput) -> ToolResult:
    client = _make_client(input_data)
    return client.get_result(input_data.key)


@tool("redis.set", RedisSetInput, timeout=5)
def redis_set(*, input_data: RedisSetInput) -> ToolResult:
    client = _make_client(input_data)
    return client.set_result(
        input_data.key,
        input_data.value,
        ex=input_data.ex,
        px=input_data.px,
        nx=input_data.nx,
        xx=input_data.xx,
    )


@tool("redis.delete", RedisDelInput, timeout=10)
def redis_delete(*, input_data: RedisDelInput) -> ToolResult:
    client = _make_client(input_data)
    return client.delete_result(*input_data.keys)


@tool("redis.keys", RedisKeysInput, timeout=20)
def redis_keys(*, input_data: RedisKeysInput) -> ToolResult:
    client = _make_client(input_data)
    return client.keys_result(input_data.pattern)


@tool("redis.hgetall", RedisHGetAllInput, timeout=10)
def redis_hgetall(*, input_data: RedisHGetAllInput) -> ToolResult:
    client = _make_client(input_data)
    return client.hgetall_result(input_data.key)


@tool("redis.expire", RedisExpireInput, timeout=5)
def redis_expire(*, input_data: RedisExpireInput) -> ToolResult:
    client = _make_client(input_data)
    return client.expire_result(input_data.key, input_data.seconds)


@tool("redis.eval", RedisEvalInput, timeout=30)
def redis_eval(*, input_data: RedisEvalInput) -> ToolResult:
    client = _make_client(input_data)
    return client.eval_result(
        script=input_data.script, keys=input_data.keys, args=input_data.args
    )
