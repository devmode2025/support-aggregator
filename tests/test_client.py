"""
Tests for AggregatorClient connection handling.

These tests use fake MCP servers (no network calls) to verify:
- Connection lifecycle (connect / disconnect)
- Graceful handling of unreachable servers
- Tool discovery population
- Partial startup behavior
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from support_aggregator.aggregator.client import AggregatorClient
from support_aggregator.config.settings import ServerEndpoint, Settings


@pytest.fixture
def settings_with_servers():
    return Settings(
        aggregator_name="test-aggregator",
        allow_partial_startup=True,
        connection_timeout=5,
        mcp_client_mode="auto",
        servers=[
            ServerEndpoint(name="diagnostic_tool", url="http://diag:9000/mcp"),
            ServerEndpoint(name="prefect", url="http://prefect:8000/mcp"),
        ],
    )


@pytest.fixture
def settings_empty():
    return Settings(
        aggregator_name="test-aggregator",
        allow_partial_startup=True,
        connection_timeout=5,
        mcp_client_mode="auto",
        servers=[],
    )


def make_fake_client(tool_names=None):
    """Build a MagicMock that behaves like an async context manager client.

    Why this shape matters:
    - AggregatorClient does `await stack.enter_async_context(Client(...))`
    - AsyncExitStack awaits `__aenter__()` and uses its return value as the client
    - So the fake must have `__aenter__` as an AsyncMock returning itself
    """
    tool_names = tool_names or ["fake_tool_1", "fake_tool_2"]
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_tools = AsyncMock(
        return_value=[MagicMock(name=n) for n in tool_names]
    )
    return client


@pytest.fixture
def fake_client():
    return make_fake_client()


@pytest.mark.asyncio
async def test_connect_all_success(settings_with_servers, fake_client):
    with patch(
        "support_aggregator.aggregator.client.Client",
        return_value=fake_client,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()

        assert set(agg.connected_servers()) == {"diagnostic_tool", "prefect"}
        assert agg.unreachable_servers() == []
        assert len(agg.tools_for("prefect")) == 2

        await agg.disconnect_all()
        assert agg.connected_servers() == []


@pytest.mark.asyncio
async def test_connect_all_partial_failure(settings_with_servers, fake_client):
    def client_side_effect(url, mode="auto"):
        if "prefect" in url:
            raise ConnectionError("prefect unreachable")
        return fake_client

    with patch(
        "support_aggregator.aggregator.client.Client",
        side_effect=client_side_effect,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()

        assert agg.connected_servers() == ["diagnostic_tool"]
        assert agg.unreachable_servers() == ["prefect"]


@pytest.mark.asyncio
async def test_connect_all_fail_fast_when_disallowed(settings_with_servers):
    settings_with_servers.allow_partial_startup = False

    def client_side_effect(url, mode="auto"):
        raise ConnectionError("boom")

    with patch(
        "support_aggregator.aggregator.client.Client",
        side_effect=client_side_effect,
    ):
        agg = AggregatorClient(settings_with_servers)
        with pytest.raises(ConnectionError):
            await agg.connect_all()


@pytest.mark.asyncio
async def test_connect_all_skips_empty_url(settings_with_servers, fake_client):
    settings_with_servers.servers[0].url = ""

    with patch(
        "support_aggregator.aggregator.client.Client",
        return_value=fake_client,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()

        assert "diagnostic_tool" in agg.unreachable_servers()


@pytest.mark.asyncio
async def test_connect_all_empty_settings(settings_empty):
    agg = AggregatorClient(settings_empty)
    await agg.connect_all()

    assert agg.connected_servers() == []
    assert agg.unreachable_servers() == []


@pytest.mark.asyncio
async def test_tools_for_returns_discovered_tools(settings_with_servers, fake_client):
    with patch(
        "support_aggregator.aggregator.client.Client",
        return_value=fake_client,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()

        assert len(agg.tools_for("prefect")) == 2
        assert agg.tools_for("nonexistent") == []


@pytest.mark.asyncio
async def test_client_for_returns_client(settings_with_servers, fake_client):
    with patch(
        "support_aggregator.aggregator.client.Client",
        return_value=fake_client,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()

        assert agg.client_for("prefect") is fake_client
        assert agg.client_for("nonexistent") is None


@pytest.mark.asyncio
async def test_disconnect_all_clears_state(settings_with_servers, fake_client):
    with patch(
        "support_aggregator.aggregator.client.Client",
        return_value=fake_client,
    ):
        agg = AggregatorClient(settings_with_servers)
        await agg.connect_all()
        await agg.disconnect_all()

        assert agg.connected_servers() == []
        assert agg.tools_for("prefect") == []