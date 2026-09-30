"""Aggregator diagnostic tools exposed via MCP."""

import logging

from fastmcp import FastMCP

logger = logging.getLogger("support_aggregator.tools")


def register_diagnostic_tools(mcp: FastMCP) -> None:
    """Register all aggregator tools on the FastMCP instance."""

    @mcp.tool
    async def diagnose_pipeline_health(platform: str, deployment_id: str = "") -> dict:
        """
        Diagnose pipeline health across a specific orchestration platform.

        Args:
            platform: One of 'prefect', 'dagster', 'n8n', 'kubernetes'.
            deployment_id: Optional deployment/flow/job identifier.
        """
        client = mcp.get_context().request_context.lifespan_context["client"]

        if platform not in client.connected_servers():
            return {
                "platform": platform,
                "status": "unavailable",
                "detail": f"{platform} MCP server is not connected",
            }

        tools = client.tools_for(platform)
        tool_names = [t.name for t in tools]

        return {
            "platform": platform,
            "status": "connected",
            "available_tools": tool_names,
            "deployment_id": deployment_id,
        }

    @mcp.tool
    async def list_connected_servers() -> dict:
        """Return which external MCP servers are currently reachable."""
        client = mcp.get_context().request_context.lifespan_context["client"]
        return {
            "connected": client.connected_servers(),
            "unreachable": client.unreachable_servers(),
        }
