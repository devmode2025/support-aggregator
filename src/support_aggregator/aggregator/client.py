"""Manages connections to external MCP servers."""

import logging
from contextlib import AsyncExitStack

from fastmcp import Client

from support_aggregator.config.settings import Settings, ServerEndpoint

logger = logging.getLogger("support_aggregator.client")


class AggregatorClient:
    """Connects to external MCP servers and exposes their tools."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._stack = AsyncExitStack()
        self._clients: dict[str, Client] = {}
        self._tools: dict[str, list] = {}
        self._unreachable: list[str] = []

    async def connect_all(self) -> None:
        """Attempt to connect to every enabled server."""
        for server in self.settings.servers:
            if not server.url:
                logger.warning("Skipping %s: no URL configured", server.name)
                self._unreachable.append(server.name)
                continue

            try:
                client = await self._stack.enter_async_context(
                    Client(server.url, mode=self.settings.mcp_client_mode)
                )
                tools = await client.list_tools()
                self._clients[server.name] = client
                self._tools[server.name] = tools
                logger.info("Connected to %s (%d tools)", server.name, len(tools))
            except Exception as e:
                logger.warning("Failed to connect to %s: %s", server.name, e)
                self._unreachable.append(server.name)
                if not self.settings.allow_partial_startup:
                    raise

    async def disconnect_all(self) -> None:
        """Close all connections."""
        await self._stack.aclose()
        self._clients.clear()
        self._tools.clear()

    def connected_servers(self) -> list[str]:
        return list(self._clients.keys())

    def unreachable_servers(self) -> list[str]:
        return list(self._unreachable)

    def tools_for(self, server_name: str) -> list:
        return self._tools.get(server_name, [])

    def client_for(self, server_name: str) -> Client | None:
        return self._clients.get(server_name)
