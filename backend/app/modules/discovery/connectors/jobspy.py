from __future__ import annotations

"""JobSpy MCP Connector re-export module.

Maintains backward compatibility for callers importing JobSpyMCPConnector
from app.modules.discovery.connectors.jobspy while the canonical implementation
lives in app.modules.discovery.connectors.mcp.
"""

from app.modules.discovery.connectors.mcp import (
    JobSpyMCPConnector,
    JobSpyMCPNormalizer,
    MCPClient,
    MCPConnectionInfo,
    MCPToolInfo,
)

__all__ = [
    "JobSpyMCPConnector",
    "MCPClient",
    "JobSpyMCPNormalizer",
    "MCPConnectionInfo",
    "MCPToolInfo",
]
