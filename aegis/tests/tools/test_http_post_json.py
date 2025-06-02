import pytest
from aegis.registry import TOOL_REGISTRY
from aegis.tools.wrappers.wrapper_network import HttpPostInput


@pytest.mark.parametrize("key,value", [("foo", "bar"), ("hello", "world")])
def test_http_post_json_echo(key, value):
    tool = TOOL_REGISTRY["http_post_json"]
    response = tool.run(
        HttpPostInput(url="https://httpbin.org/post", payload={key: value})
    )
    assert key in response
    assert value in response
