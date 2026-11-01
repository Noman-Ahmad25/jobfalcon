from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import shutil
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from app.core.config import get_settings
from app.schemas.discovery import ConnectorStatus

logger = logging.getLogger(__name__)


@dataclass
class MCPToolInfo:
    """Discovered MCP tool metadata."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPConnectionInfo:
    """Diagnostic health state from an MCP protocol handshake."""

    status: ConnectorStatus
    protocol_version: Optional[str] = None
    server_name: Optional[str] = None
    server_version: Optional[str] = None
    discovered_tools: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


class MCPClient:
    """Robust, production-grade MCP client managing JSON-RPC 2.0 communication over stdio transport.

    Conforms to the Model Context Protocol specification:
    1. Protocol Handshake: invokes `session.initialize()`.
    2. Tool Discovery: dynamically queries `session.list_tools()`.
    3. Tool Execution: sends structured JSON tool calls via `session.call_tool()`.
    4. Diagnostics: surfaces honest protocol states without masking failures.
    """

    def __init__(
        self,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self.command_override = command or settings.MCP_JOBSPY_COMMAND
        self.args_override = args
        self.env = env
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.MCP_JOBSPY_TIMEOUT_SECONDS
        )
        self._cached_tools: Optional[list[MCPToolInfo]] = None

    def resolve_launch_parameters(self) -> tuple[Optional[str], list[str]]:
        """Resolves the executable command and arguments for the MCP server.

        Resolution strategy:
        1. Explicit command override / PATH check.
        2. Virtual environment bin folder check (adjacent to current Python runtime).
        3. Python module fallback: [sys.executable, "-m", "jobspy.mcp"].
        """
        # If command has path or exists on PATH
        cmd = self.command_override
        if shutil.which(cmd):
            return shutil.which(cmd), self.args_override or []

        # Check in virtualenv bin
        venv_bin = Path(sys.executable).parent / cmd
        if venv_bin.exists() and os.access(venv_bin, os.X_OK):
            return str(venv_bin), self.args_override or []

        # Check Python module execution
        if cmd in ("mcp-jobspy", "jobspy-mcp", "jobspy"):
            if importlib.util.find_spec("jobspy.mcp"):
                return sys.executable, ["-m", "jobspy.mcp"]

        return None, []

    def is_binary_available(self) -> bool:
        """True if the MCP server executable or runnable module is present on the host."""
        cmd, _ = self.resolve_launch_parameters()
        return cmd is not None

    async def check_health(self) -> MCPConnectionInfo:
        """Executes a live protocol handshake and tool discovery probe.

        Honest Health Evaluation:
        - UNAVAILABLE_MISSING_BINARY: server executable not found on PATH or in venv.
        - CONNECTED: handshake succeeded, protocol version established, and tools discovered.
        - DEGRADED: server connected but expected discovery tools are missing.
        - ERROR: connection refused, pipe closed, timeout, or protocol violation.
        """
        t0 = time.perf_counter()
        cmd, args = self.resolve_launch_parameters()

        if not cmd:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return MCPConnectionInfo(
                status=ConnectorStatus.UNAVAILABLE_MISSING_BINARY,
                latency_ms=elapsed,
                error_message=f"MCP binary '{self.command_override}' not found on system PATH or virtualenv.",
                details={
                    "command": self.command_override,
                    "suggestion": "Install via 'uv pip install mcp-jobspy' or ensure binary is on PATH.",
                },
            )

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=cmd,
                args=args,
                env=self.env,
            )

            # Bounded probe window (6.0s max for healthcheck)
            async with asyncio.timeout(min(self.timeout_seconds, 6.0)):
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        init_res = await session.initialize()
                        tools_res = await session.list_tools()

                        elapsed = round((time.perf_counter() - t0) * 1000, 2)
                        tool_names = [t.name for t in tools_res.tools]

                        # Cache discovered tools
                        self._cached_tools = [
                            MCPToolInfo(
                                name=t.name,
                                description=t.description or "",
                                input_schema=t.input_schema,
                            )
                            for t in tools_res.tools
                        ]

                        has_search_tool = any("search" in name.lower() for name in tool_names)
                        status = ConnectorStatus.CONNECTED if has_search_tool else ConnectorStatus.DEGRADED

                        return MCPConnectionInfo(
                            status=status,
                            protocol_version=str(init_res.protocol_version),
                            server_name=init_res.server_info.name if init_res.server_info else None,
                            server_version=init_res.server_info.version if init_res.server_info else None,
                            discovered_tools=tool_names,
                            latency_ms=elapsed,
                            details={
                                "transport": "stdio",
                                "command": cmd,
                                "args": args,
                                "tool_count": len(tool_names),
                            },
                        )

        except asyncio.TimeoutError:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return MCPConnectionInfo(
                status=ConnectorStatus.ERROR,
                latency_ms=elapsed,
                error_message=f"MCP server handshake timed out after {min(self.timeout_seconds, 6.0)}s.",
                details={"command": cmd},
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.warning("MCP healthcheck probe failed: %s (%s)", type(exc).__name__, exc)
            return MCPConnectionInfo(
                status=ConnectorStatus.ERROR,
                latency_ms=elapsed,
                error_message=f"MCP handshake failed: {type(exc).__name__} - {str(exc)}",
                details={"command": cmd, "exception_type": type(exc).__name__},
            )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[Any, None]:
        """Async context manager providing an active, initialized MCP ClientSession."""
        cmd, args = self.resolve_launch_parameters()
        if not cmd:
            raise FileNotFoundError(
                f"MCP server binary '{self.command_override}' is not available on PATH or virtualenv."
            )

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command=cmd,
            args=args,
            env=self.env,
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                yield mcp_session

    async def list_tools(self) -> list[MCPToolInfo]:
        """Discovers and caches advertised tools from the MCP server."""
        if self._cached_tools is not None:
            return self._cached_tools

        async with self.session() as mcp_session:
            tools_res = await mcp_session.list_tools()
            self._cached_tools = [
                MCPToolInfo(
                    name=t.name,
                    description=t.description or "",
                    input_schema=t.input_schema,
                )
                for t in tools_res.tools
            ]
            return self._cached_tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Invokes a tool on the MCP server and returns the parsed result.

        Applies bounded timeout and unmasks any tool execution errors.
        """
        eff_timeout = timeout if timeout is not None else self.timeout_seconds

        async with asyncio.timeout(eff_timeout):
            async with self.session() as mcp_session:
                result = await mcp_session.call_tool(tool_name, arguments=arguments)
                if result.is_error:
                    error_text = ""
                    for content in result.content or []:
                        if hasattr(content, "text"):
                            error_text += content.text
                    raise RuntimeError(f"MCP tool '{tool_name}' returned error: {error_text or 'Unknown tool error'}")
                return result
