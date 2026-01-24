# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Smoke test tools for validating MCP handshake.

These tools avoid ctx.dispatch() to test SDK serialization and
token exchange without requiring enclave dispatch.
"""

from pydantic.dataclasses import dataclass

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations


@dataclass(frozen=True)
class PingResult:
    """Smoke ping response."""

    ok: bool = True
    message: str = "pong"


@tool(
    description="Smoke test ping (no enclave dispatch required)",
    tags=["smoke", "health"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def smoke_ping(message: str = "pong") -> PingResult:
    """Simple ping for testing MCP connection.

    Args:
        message: Message to echo back (default "pong")

    Returns:
        PingResult with ok=True and echoed message

    """
    return PingResult(message=message)


smoke_tools = [smoke_ping]
