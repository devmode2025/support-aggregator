# support-aggregator

An MCP composition layer that unifies diagnostic tooling across orchestration and infrastructure platforms.

It connects to a separately deployed **diagnostic tool** alongside third-party MCP servers for **Prefect**, **Dagster**, **n8n**, and **Kubernetes**, then routes and synthesizes their outputs through a single interface.

> **This repository does not contain the diagnostic tool itself.**
> The diagnostic tool is an independent product deployed on Replit.
> This repo is the aggregator - the component that makes the diagnostic tool's capabilities composable with the broader orchestration ecosystem.

---

## Architecture


The aggregator connects to each server as an MCP **client**, discovers tools dynamically via `list_tools()`, and routes diagnostic requests to the appropriate backend.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/devmode2025/support-aggregator.git
cd support-aggregator
uv sync

cp .env.example .env
# Edit .env with your endpoints

# Development (stdio transport)
uv run support-aggregator

# HTTP transport
AGGREGATOR_TRANSPORT=http uv run support-aggregator

fastmcp list http://localhost:9000/mcp

