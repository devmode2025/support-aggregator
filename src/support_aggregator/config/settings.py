"""Environment-driven configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class ServerEndpoint:
    """A single external MCP server endpoint."""
    name: str
    url: str
    enabled: bool = True
    timeout: int = 10


@dataclass
class Settings:
    """Aggregator settings loaded from environment."""
    aggregator_name: str = "support-aggregator"
    allow_partial_startup: bool = True
    connection_timeout: int = 10
    mcp_client_mode: str = "auto"

    servers: list[ServerEndpoint] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""
        servers = []

        if os.getenv("DIAGNOSTIC_TOOL_ENABLED", "true").lower() == "true":
            servers.append(ServerEndpoint(
                name="diagnostic_tool",
                url=os.getenv("DIAGNOSTIC_TOOL_URL", ""),
                timeout=int(os.getenv("DIAGNOSTIC_TOOL_TIMEOUT", "30")),
            ))

        mapping = [
            ("prefect", "PREFECT_MCP_URL", "PREFECT_MCP_ENABLED"),
            ("dagster", "DAGSTER_MCP_URL", "DAGSTER_MCP_ENABLED"),
            ("n8n", "N8N_MCP_URL", "N8N_MCP_ENABLED"),
            ("kubernetes", "K8S_MCP_URL", "K8S_MCP_ENABLED"),
            ("airflow", "AIRFLOW_MCP_URL", "AIRFLOW_MCP_ENABLED"),
        ]
        for name, url_var, enabled_var in mapping:
            if os.getenv(enabled_var, "false").lower() == "true":
                servers.append(ServerEndpoint(
                    name=name,
                    url=os.getenv(url_var, ""),
                ))

        return cls(
            aggregator_name=os.getenv("AGGREGATOR_NAME", "support-aggregator"),
            allow_partial_startup=os.getenv("ALLOW_PARTIAL_STARTUP", "true").lower() == "true",
            connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "10")),
            mcp_client_mode=os.getenv("MCP_CLIENT_MODE", "auto"),
            servers=servers,
        )
