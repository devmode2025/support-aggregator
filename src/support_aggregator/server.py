"""
support-aggregator entry point.

This module:
1. Loads configuration from environment variables
2. Instantiates the FastMCP server
3. Registers aggregator tools
4. Runs the server (stdio or HTTP transport)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP

from support_aggregator.aggregator.client import AggregatorClient
from support_aggregator.config.settings import Settings
from support_aggregator.tools.diagnostics import register_diagnostic_tools

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("support_aggregator")


@asynccontextmanager
async def lifespan(server: FastMCP):
    """FastMCP lifespan context manager."""
    settings = Settings.from_env()
    logger.info("Starting support-aggregator (name=%s)", settings.aggregator_name)

    client = AggregatorClient(settings)
    await client.connect_all()

    logger.info(
        "Connected servers: %s",
        ", ".join(client.connected_servers()) or "none",
    )
    if client.unreachable_servers():
        logger.warning(
            "Unreachable servers: %s",
            ", ".join(client.unreachable_servers()),
        )

    try:
        yield {"client": client, "settings": settings}
    finally:
        logger.info("Shutting down support-aggregator")
        await client.disconnect_all()


mcp = FastMCP(
    name="support-aggregator",
    instructions=(
        "Composition layer for diagnostic tooling. "
        "Connects to your diagnostic tool and external orchestration MCP servers "
        "(Prefect, Dagster, n8n, Kubernetes). "
        "Use the registered tools to diagnose pipeline failures, "
        "fetch logs, and aggregate cross-system health."
    ),
    lifespan=lifespan,
)

register_diagnostic_tools(mcp)


def main() -> None:
    """Launch the aggregator server."""
    transport = os.getenv("AGGREGATOR_TRANSPORT", "stdio").lower()

    if transport == "http":
        host = os.getenv("AGGREGATOR_HOST", "0.0.0.0")
        port = int(os.getenv("AGGREGATOR_PORT", "9000"))
        logger.info("Starting HTTP transport on %s:%s/mcp", host, port)
        mcp.run(transport="http", host=host, port=port)
    else:
        logger.info("Starting stdio transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
